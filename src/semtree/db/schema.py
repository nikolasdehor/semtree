"""SQLite schema v1 for semtree.

Design goals:
- FTS5 full-text search on symbol names and docstrings
- Vec-ready: embedding column stored as BLOB (sqlite-vec compatible)
- Incremental hashing: skip re-parse if SHA-1 unchanged
- Lean writes: single transaction per file update
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = 1

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA cache_size = -20000;

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- One row per indexed source file
CREATE TABLE IF NOT EXISTS files (
    id          INTEGER PRIMARY KEY,
    path        TEXT    NOT NULL UNIQUE,   -- relative to project root
    sha1        TEXT    NOT NULL,          -- SHA-1 hex of file contents
    size_bytes  INTEGER NOT NULL DEFAULT 0,
    lang        TEXT    NOT NULL DEFAULT '',
    indexed_at  REAL    NOT NULL           -- Unix timestamp
);

-- One row per extracted symbol (function, class, method, const, etc.)
CREATE TABLE IF NOT EXISTS symbols (
    id          INTEGER PRIMARY KEY,
    file_id     INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    kind        TEXT    NOT NULL,          -- function | class | method | const | type | var
    line_start  INTEGER NOT NULL,
    line_end    INTEGER NOT NULL,
    signature   TEXT    NOT NULL DEFAULT '',
    docstring   TEXT    NOT NULL DEFAULT '',
    embedding   BLOB,                     -- float32 array, NULL until embedded
    git_author  TEXT    NOT NULL DEFAULT '',
    git_date    TEXT    NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_symbols_file  ON symbols(file_id);
CREATE INDEX IF NOT EXISTS idx_symbols_name  ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_kind  ON symbols(kind);

-- FTS5 index over symbol names + docstrings for fast keyword search
CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
    name,
    signature,
    docstring,
    content      = symbols,
    content_rowid = id,
    tokenize     = 'unicode61 remove_diacritics 2'
);

-- Keep FTS in sync with symbols
CREATE TRIGGER IF NOT EXISTS symbols_ai AFTER INSERT ON symbols BEGIN
    INSERT INTO symbols_fts(rowid, name, signature, docstring)
    VALUES (new.id, new.name, new.signature, new.docstring);
END;

CREATE TRIGGER IF NOT EXISTS symbols_ad AFTER DELETE ON symbols BEGIN
    INSERT INTO symbols_fts(symbols_fts, rowid, name, signature, docstring)
    VALUES ('delete', old.id, old.name, old.signature, old.docstring);
END;

CREATE TRIGGER IF NOT EXISTS symbols_au AFTER UPDATE ON symbols BEGIN
    INSERT INTO symbols_fts(symbols_fts, rowid, name, signature, docstring)
    VALUES ('delete', old.id, old.name, old.signature, old.docstring);
    INSERT INTO symbols_fts(rowid, name, signature, docstring)
    VALUES (new.id, new.name, new.signature, new.docstring);
END;

-- Project-level memory: rules, references, notes
CREATE TABLE IF NOT EXISTS memory (
    id         INTEGER PRIMARY KEY,
    kind       TEXT NOT NULL,              -- rule | ref | note
    key        TEXT NOT NULL,
    value      TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(kind, key)
);
"""


def init_db(path: Path) -> sqlite3.Connection:
    """Create or open the database at path, applying DDL if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_DDL)

    cur = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'")
    row = cur.fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO schema_meta(key, value) VALUES ('version', ?)",
            (str(SCHEMA_VERSION),),
        )
        conn.commit()

    return conn


def get_version(conn: sqlite3.Connection) -> int:
    """Return the schema version stored in the database."""
    cur = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'")
    row = cur.fetchone()
    return int(row["value"]) if row else 0
