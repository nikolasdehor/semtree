"""All CRUD operations against the semtree SQLite database.

Typed returns throughout - no bare Any in public API.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(slots=True)
class FileRecord:
    id: int
    path: str
    sha1: str
    size_bytes: int
    lang: str
    indexed_at: float


@dataclass(slots=True)
class SymbolRecord:
    id: int
    file_id: int
    file_path: str
    name: str
    kind: str
    line_start: int
    line_end: int
    signature: str
    docstring: str
    git_author: str
    git_date: str


@dataclass(slots=True)
class MemoryRecord:
    id: int
    kind: str
    key: str
    value: str
    created_at: float
    updated_at: float


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def get_file_sha1(conn: sqlite3.Connection, rel_path: str) -> str | None:
    """Return the stored SHA-1 for rel_path, or None if not indexed."""
    row = conn.execute(
        "SELECT sha1 FROM files WHERE path = ?", (rel_path,)
    ).fetchone()
    return str(row["sha1"]) if row else None


def upsert_file(
    conn: sqlite3.Connection,
    rel_path: str,
    sha1: str,
    size_bytes: int,
    lang: str,
) -> int:
    """Insert or update a file record. Returns the file id."""
    now = time.time()
    cur = conn.execute(
        """
        INSERT INTO files(path, sha1, size_bytes, lang, indexed_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            sha1       = excluded.sha1,
            size_bytes = excluded.size_bytes,
            lang       = excluded.lang,
            indexed_at = excluded.indexed_at
        RETURNING id
        """,
        (rel_path, sha1, size_bytes, lang, now),
    )
    row = cur.fetchone()
    return int(row[0])


def delete_file(conn: sqlite3.Connection, rel_path: str) -> None:
    """Remove a file and all its symbols (CASCADE handles symbols)."""
    conn.execute("DELETE FROM files WHERE path = ?", (rel_path,))


def list_files(conn: sqlite3.Connection) -> list[FileRecord]:
    """Return all indexed files."""
    rows = conn.execute(
        "SELECT id, path, sha1, size_bytes, lang, indexed_at FROM files ORDER BY path"
    ).fetchall()
    return [
        FileRecord(
            id=row["id"],
            path=row["path"],
            sha1=row["sha1"],
            size_bytes=row["size_bytes"],
            lang=row["lang"],
            indexed_at=row["indexed_at"],
        )
        for row in rows
    ]


def count_files(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM files").fetchone()
    return int(row[0])


def count_symbols(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()
    return int(row[0])


# ---------------------------------------------------------------------------
# Symbol operations
# ---------------------------------------------------------------------------

def replace_file_symbols(
    conn: sqlite3.Connection,
    file_id: int,
    symbols: Sequence[dict],
) -> None:
    """Delete existing symbols for file_id and insert fresh batch.

    Each dict in symbols must have: name, kind, line_start, line_end,
    signature, docstring. git_author and git_date are optional.
    """
    conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
    conn.executemany(
        """
        INSERT INTO symbols(
            file_id, name, kind, line_start, line_end,
            signature, docstring, git_author, git_date
        ) VALUES (
            :file_id, :name, :kind, :line_start, :line_end,
            :signature, :docstring, :git_author, :git_date
        )
        """,
        [
            {
                "file_id": file_id,
                "name": sym["name"],
                "kind": sym["kind"],
                "line_start": sym["line_start"],
                "line_end": sym["line_end"],
                "signature": sym.get("signature", ""),
                "docstring": sym.get("docstring", ""),
                "git_author": sym.get("git_author", ""),
                "git_date": sym.get("git_date", ""),
            }
            for sym in symbols
        ],
    )


_FTS_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "this", "that",
    "these", "those", "how", "what", "where", "when", "why", "which",
    "and", "or", "but", "not", "if", "it", "its", "i", "my", "all",
})


def _to_fts_query(query: str) -> str:
    """Convert a natural-language query to an FTS5 OR query.

    Splits on whitespace, removes stop words and FTS5 special chars,
    then joins with OR for broad matching. Each keyword also gets a
    prefix variant (e.g. "authentication" -> "authentication OR authenticat*")
    to handle stemming differences.
    """
    # Strip FTS5 special characters to avoid syntax errors
    clean = query.replace('"', "").replace("*", "").replace("^", "").strip()
    tokens = [t.lower() for t in clean.split() if len(t) >= 2]
    # Filter stop words but keep tokens that look like identifiers
    keywords = [t for t in tokens if t not in _FTS_STOP_WORDS]
    if not keywords:
        # All tokens were stop words - use all tokens as fallback
        keywords = tokens
    if not keywords:
        return ""
    # For each keyword >= 5 chars, also add a prefix variant covering the first
    # 60% of the word (min 4 chars). This handles plurals, verb forms, and
    # morphological variants without being too broad.
    terms: list[str] = []
    for kw in keywords:
        terms.append(kw)
        if len(kw) >= 5:
            prefix_len = max(4, int(len(kw) * 0.6))
            terms.append(f"{kw[:prefix_len]}*")
    return " OR ".join(terms)


def fts_search(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
) -> list[SymbolRecord]:
    """Full-text search across symbol names, signatures, and docstrings."""
    fts_query = _to_fts_query(query)
    if not fts_query:
        return []

    try:
        rows = conn.execute(
            """
            SELECT
                s.id, s.file_id, f.path AS file_path,
                s.name, s.kind, s.line_start, s.line_end,
                s.signature, s.docstring, s.git_author, s.git_date,
                rank
            FROM symbols_fts
            JOIN symbols s  ON s.id = symbols_fts.rowid
            JOIN files   f  ON f.id = s.file_id
            WHERE symbols_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
    except Exception:
        return []
    return [_row_to_symbol(r) for r in rows]


def get_symbols_for_file(
    conn: sqlite3.Connection,
    rel_path: str,
) -> list[SymbolRecord]:
    """Return all symbols for a given relative file path."""
    rows = conn.execute(
        """
        SELECT s.id, s.file_id, f.path AS file_path,
               s.name, s.kind, s.line_start, s.line_end,
               s.signature, s.docstring, s.git_author, s.git_date
        FROM symbols s
        JOIN files f ON f.id = s.file_id
        WHERE f.path = ?
        ORDER BY s.line_start
        """,
        (rel_path,),
    ).fetchall()
    return [_row_to_symbol(r) for r in rows]


def get_symbols_by_name(
    conn: sqlite3.Connection,
    name: str,
    kind: str | None = None,
) -> list[SymbolRecord]:
    """Exact-match symbol name lookup, optionally filtered by kind."""
    if kind:
        rows = conn.execute(
            """
            SELECT s.id, s.file_id, f.path AS file_path,
                   s.name, s.kind, s.line_start, s.line_end,
                   s.signature, s.docstring, s.git_author, s.git_date
            FROM symbols s JOIN files f ON f.id = s.file_id
            WHERE s.name = ? AND s.kind = ?
            """,
            (name, kind),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT s.id, s.file_id, f.path AS file_path,
                   s.name, s.kind, s.line_start, s.line_end,
                   s.signature, s.docstring, s.git_author, s.git_date
            FROM symbols s JOIN files f ON f.id = s.file_id
            WHERE s.name = ?
            """,
            (name,),
        ).fetchall()
    return [_row_to_symbol(r) for r in rows]


def _row_to_symbol(row: sqlite3.Row) -> SymbolRecord:
    return SymbolRecord(
        id=row["id"],
        file_id=row["file_id"],
        file_path=row["file_path"],
        name=row["name"],
        kind=row["kind"],
        line_start=row["line_start"],
        line_end=row["line_end"],
        signature=row["signature"],
        docstring=row["docstring"],
        git_author=row["git_author"],
        git_date=row["git_date"],
    )


# ---------------------------------------------------------------------------
# Memory operations
# ---------------------------------------------------------------------------

def upsert_memory(
    conn: sqlite3.Connection,
    kind: str,
    key: str,
    value: str,
) -> MemoryRecord:
    """Insert or update a memory entry."""
    now = time.time()
    cur = conn.execute(
        """
        INSERT INTO memory(kind, key, value, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(kind, key) DO UPDATE SET
            value      = excluded.value,
            updated_at = excluded.updated_at
        RETURNING id, kind, key, value, created_at, updated_at
        """,
        (kind, key, value, now, now),
    )
    row = cur.fetchone()
    return MemoryRecord(
        id=row["id"],
        kind=row["kind"],
        key=row["key"],
        value=row["value"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_memory(
    conn: sqlite3.Connection,
    kind: str | None = None,
) -> list[MemoryRecord]:
    """List all memory entries, optionally filtered by kind."""
    if kind:
        rows = conn.execute(
            "SELECT id, kind, key, value, created_at, updated_at FROM memory WHERE kind = ? ORDER BY updated_at DESC",
            (kind,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, kind, key, value, created_at, updated_at FROM memory ORDER BY kind, updated_at DESC"
        ).fetchall()
    return [
        MemoryRecord(
            id=r["id"],
            kind=r["kind"],
            key=r["key"],
            value=r["value"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


def delete_memory(conn: sqlite3.Connection, kind: str, key: str) -> bool:
    """Delete a memory entry. Returns True if a row was deleted."""
    cur = conn.execute(
        "DELETE FROM memory WHERE kind = ? AND key = ?", (kind, key)
    )
    return cur.rowcount > 0
