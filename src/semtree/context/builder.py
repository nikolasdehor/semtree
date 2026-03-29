"""Context assembly orchestrator.

Coordinates intent classification -> retrieval policy -> symbol search
-> token-budgeted formatting into a single context string.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..retrieval.intent import classify
from ..retrieval.policy import get_policy
from ..retrieval.search import search, search_by_file
from ..db.store import list_files
from .budget import TokenBudget
from .levels import format_by_level, format_file_tree


def build_context(
    conn: sqlite3.Connection,
    query: str,
    token_budget: int = 8000,
    root: Path | None = None,
    force_level: int | None = None,
) -> str:
    """Build a context string for an AI assistant given a natural-language query.

    Steps:
    1. Classify intent
    2. Select retrieval policy
    3. Search for relevant symbols
    4. Format within token budget
    5. Append file tree if policy requests it and budget remains
    """
    budget = TokenBudget(token_budget)

    # 1. Classify intent
    intent_result = classify(query)
    policy = get_policy(intent_result.intent)

    # 2. Search
    results = search(conn, query, limit=policy.max_symbols)

    # Filter by preferred kinds if specified
    if policy.prefer_kinds:
        preferred = [r for r in results if r.symbol.kind in policy.prefer_kinds]
        others = [r for r in results if r.symbol.kind not in policy.prefer_kinds]
        results = preferred + others

    symbols = [r.symbol for r in results]

    level = force_level if force_level is not None else policy.context_level

    # 3. Header
    header_parts = [
        f"<!-- semtree context | intent={intent_result.intent} confidence={intent_result.confidence:.2f} -->",
        f"# Code Context for: {query}\n",
    ]
    if intent_result.matched_triggers:
        header_parts.append(f"_Detected: {', '.join(intent_result.matched_triggers[:3])}_\n")
    header = "\n".join(header_parts)
    budget.consume(header)

    # 4. Symbol context
    sym_budget = int(budget.remaining * policy.budget_fraction)
    sym_text = _fit_symbols(symbols, level, sym_budget)
    budget.consume(sym_text)

    # 5. File tree (if policy requests and budget allows)
    tree_text = ""
    if policy.include_file_tree and budget.remaining > 200:
        files = list_files(conn)
        tree_text = format_file_tree(files, root or Path("."))
        if not budget.fits(tree_text):
            # Truncate to what fits
            lines = tree_text.split("\n")
            while lines and not budget.fits("\n".join(lines)):
                lines = lines[:-5]
            tree_text = "\n".join(lines)
        budget.consume(tree_text)

    parts = [header]
    if sym_text:
        parts.append(sym_text)
    if tree_text:
        parts.append("\n---\n" + tree_text)

    stats = f"\n\n---\n_semtree: {len(symbols)} symbols, ~{budget.used} tokens used of {token_budget}_"
    parts.append(stats)

    return "\n".join(parts)


def _fit_symbols(symbols: list, level: int, token_budget: int) -> str:
    """Format symbols at the given level, dropping from the end if over budget."""
    if not symbols:
        return ""

    # Try with all symbols first
    full = format_by_level(symbols, level)
    from .budget import count_tokens
    if count_tokens(full) <= token_budget:
        return full

    # Binary search to find how many symbols fit
    lo, hi = 1, len(symbols)
    best = format_by_level(symbols[:1], level)
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = format_by_level(symbols[:mid], level)
        if count_tokens(candidate) <= token_budget:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1

    return best


def build_context_for_file(
    conn: sqlite3.Connection,
    rel_path: str,
    token_budget: int = 8000,
    level: int = 2,
) -> str:
    """Build context for a specific file (used by MCP get_context tool)."""
    from ..db.store import get_symbols_for_file
    symbols = get_symbols_for_file(conn, rel_path)

    header = f"# Context: {rel_path}\n"
    budget = TokenBudget(token_budget)
    budget.consume(header)

    sym_text = _fit_symbols(symbols, level, budget.remaining)
    budget.consume(sym_text)

    stats = f"\n\n---\n_semtree: {len(symbols)} symbols, ~{budget.used}/{token_budget} tokens_"
    return header + sym_text + stats
