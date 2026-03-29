"""MCP server for semtree - exposes 3 tools to AI assistants.

Tools:
  1. index_project  - (re)index the current project
  2. get_context    - build context string for a task/query
  3. search_symbols - search for specific symbols by name or query

Run with: semtree-mcp
Or:        python -m semtree.mcp
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from .config import SemtreeConfig, find_project_root, db_path
from .db.schema import init_db
from .context.builder import build_context, build_context_for_file
from .retrieval.search import search, search_by_file
from .indexer.coordinator import run_index


def _get_root() -> Path:
    """Determine project root from SEMTREE_ROOT env or cwd."""
    env_root = os.environ.get("SEMTREE_ROOT")
    if env_root:
        return Path(env_root)
    return find_project_root()


def _open_db(root: Path) -> sqlite3.Connection:
    """Open (and initialize) the semtree database."""
    return init_db(db_path(root))


def serve() -> None:
    """Entry point for the semtree-mcp binary.

    Starts the MCP server using the mcp library if available,
    otherwise prints an error and exits.
    """
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except ImportError:
        print("ERROR: mcp package not installed. Run: pip install 'semtree[mcp]'")
        raise SystemExit(1)

    mcp = FastMCP("semtree")

    @mcp.tool()
    def index_project(force: bool = False) -> dict[str, Any]:
        """Index (or re-index) the current project.

        Scans all source files, extracts symbols, and stores them in the
        local semtree index. Subsequent tool calls will use this index.

        Args:
            force: If True, re-index all files even if unchanged.

        Returns:
            Stats including counts of new/updated/skipped files and symbols.
        """
        root = _get_root()
        config = SemtreeConfig.load(root)
        stats = run_index(root, config=config, force=force)
        return {
            "status": "ok" if not stats.errors else "partial",
            "root": str(root),
            "total_files": stats.total_files,
            "new_files": stats.new_files,
            "updated_files": stats.updated_files,
            "skipped_files": stats.skipped_files,
            "total_symbols": stats.total_symbols,
            "elapsed_seconds": round(stats.elapsed_seconds, 2),
            "errors": stats.errors[:5],  # cap at 5 to avoid huge responses
        }

    @mcp.tool()
    def get_context(
        query: str,
        token_budget: int = 8000,
        level: int | None = None,
        file: str | None = None,
    ) -> str:
        """Build a context string for an AI coding task.

        Analyzes the query intent, retrieves relevant symbols, and formats
        them within the token budget. Use this before implementing any task
        to give the AI assistant relevant project context.

        Args:
            query:        Describe what you want to implement or understand.
            token_budget: Maximum tokens to use (default: 8000).
            level:        Context detail level 0-3 (auto-selected if None).
            file:         Restrict context to a specific file path.

        Returns:
            Formatted markdown context string ready for AI consumption.
        """
        root = _get_root()
        conn = _open_db(root)

        if file:
            return build_context_for_file(conn, file, token_budget, level or 2)

        return build_context(conn, query, token_budget, root, force_level=level)

    @mcp.tool()
    def search_symbols(
        query: str,
        kind: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for symbols by name or description.

        Uses FTS5 full-text search across symbol names, signatures, and
        docstrings. Supports exact name lookup and fuzzy keyword matching.

        Args:
            query: Symbol name or keyword to search for.
            kind:  Optional filter: function | class | method | const | type | var
            limit: Maximum number of results (default: 20).

        Returns:
            List of symbol dicts with name, kind, file, line numbers,
            signature, docstring, and git metadata.
        """
        root = _get_root()
        conn = _open_db(root)
        results = search(conn, query, limit=limit)

        output = []
        for r in results:
            sym = r.symbol
            if kind and sym.kind != kind:
                continue
            output.append({
                "name": sym.name,
                "kind": sym.kind,
                "file": sym.file_path,
                "line_start": sym.line_start,
                "line_end": sym.line_end,
                "signature": sym.signature,
                "docstring": sym.docstring[:200] if sym.docstring else "",
                "git_author": sym.git_author,
                "git_date": sym.git_date,
                "score": r.score,
                "match_source": r.source,
            })

        return output

    mcp.run()


if __name__ == "__main__":
    serve()
