"""FTS5 + optional semantic search fallback.

Primary path: SQLite FTS5 (always available, zero deps)
Semantic path: cosine similarity on stored embeddings (requires numpy/sentence-transformers)

The search module is stateless - all state lives in the DB connection.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Sequence

from ..db.store import SymbolRecord, fts_search, get_symbols_by_name


@dataclass(frozen=True)
class SearchResult:
    symbol: SymbolRecord
    score: float          # higher is better; FTS rank is negated to positive
    source: str           # "fts" | "exact" | "prefix" | "semantic"


def search(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
    prefer_exact: bool = True,
) -> list[SearchResult]:
    """Search symbols matching query.

    Strategy:
    1. Exact name match (high priority)
    2. FTS5 full-text search on name + signature + docstring
    3. Prefix match fallback if FTS returns nothing

    Results are deduplicated and sorted by score descending.
    """
    results: list[SearchResult] = []
    seen_ids: set[int] = set()

    # 1. Exact name match
    if prefer_exact:
        exact = get_symbols_by_name(conn, query)
        for sym in exact:
            if sym.id not in seen_ids:
                results.append(SearchResult(sym, score=10.0, source="exact"))
                seen_ids.add(sym.id)

    # 2. FTS5 search
    fts_results = fts_search(conn, query, limit=limit * 2)
    for sym in fts_results:
        if sym.id not in seen_ids:
            # FTS rank is negative (lower = better match), invert to positive score
            results.append(SearchResult(sym, score=5.0, source="fts"))
            seen_ids.add(sym.id)

    # 3. Prefix fallback when FTS returns nothing
    if not fts_results and not exact:
        prefix_results = _prefix_search(conn, query, limit)
        for sym in prefix_results:
            if sym.id not in seen_ids:
                results.append(SearchResult(sym, score=1.0, source="prefix"))
                seen_ids.add(sym.id)

    # Truncate to limit
    return results[:limit]


def _prefix_search(
    conn: sqlite3.Connection,
    query: str,
    limit: int,
) -> list[SymbolRecord]:
    """Simple LIKE prefix search when FTS produces no results."""
    safe = query.replace("%", "").replace("_", "").strip()
    if not safe:
        return []
    rows = conn.execute(
        """
        SELECT s.id, s.file_id, f.path AS file_path,
               s.name, s.kind, s.line_start, s.line_end,
               s.signature, s.docstring, s.git_author, s.git_date
        FROM symbols s
        JOIN files f ON f.id = s.file_id
        WHERE s.name LIKE ? ESCAPE '\\'
        ORDER BY s.name
        LIMIT ?
        """,
        (f"{safe}%", limit),
    ).fetchall()
    from ..db.store import _row_to_symbol
    return [_row_to_symbol(r) for r in rows]


def search_by_file(
    conn: sqlite3.Connection,
    rel_path_fragment: str,
    limit: int = 50,
) -> list[SearchResult]:
    """Return symbols from files whose path contains the given fragment."""
    rows = conn.execute(
        """
        SELECT s.id, s.file_id, f.path AS file_path,
               s.name, s.kind, s.line_start, s.line_end,
               s.signature, s.docstring, s.git_author, s.git_date
        FROM symbols s
        JOIN files f ON f.id = s.file_id
        WHERE f.path LIKE ?
        ORDER BY s.line_start
        LIMIT ?
        """,
        (f"%{rel_path_fragment}%", limit),
    ).fetchall()
    from ..db.store import _row_to_symbol
    return [
        SearchResult(_row_to_symbol(r), score=2.0, source="fts")
        for r in rows
    ]
