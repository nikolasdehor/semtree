"""Main indexer coordinator.

Orchestrates: walk -> hash -> parse -> extract -> git blame -> store.

Features:
- Debounce: skip re-index if re-run within the last 2 seconds
- Lock file: prevent concurrent writes with .ctx/indexing.lock
- Incremental: only re-process files whose SHA-1 has changed
- Progress callback for CLI display
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .. import log
from ..config import SemtreeConfig, ctx_dir, db_path, lock_path
from ..db import store as db_store
from ..db.schema import init_db
from .extractor import extract_symbols
from .gitblame import annotate_symbols
from .hasher import sha1_file
from .walker import detect_language, walk_project

_DEBOUNCE_SECONDS = 2.0


@dataclass
class IndexStats:
    total_files: int = 0
    new_files: int = 0
    updated_files: int = 0
    skipped_files: int = 0
    total_symbols: int = 0
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


ProgressCallback = Callable[[str, int, int], None]  # (path, current, total)


def run_index(
    root: Path,
    config: SemtreeConfig | None = None,
    force: bool = False,
    progress: ProgressCallback | None = None,
) -> IndexStats:
    """Run a full incremental index of the project at root.

    Args:
        root:     Project root directory.
        config:   Configuration (loaded from .ctx/semtree.json if None).
        force:    Re-index all files even if SHA-1 matches.
        progress: Optional callback(rel_path, current, total) for progress reporting.

    Returns:
        IndexStats with counts and timing.
    """
    if config is None:
        config = SemtreeConfig.load(root)

    stats = IndexStats()
    start = time.monotonic()

    # Debounce check
    lock = lock_path(root)
    if not force and lock.exists():
        try:
            age = time.time() - lock.stat().st_mtime
            if age < _DEBOUNCE_SECONDS:
                log.debug("Skipping index (debounce)", age=age)
                return stats
        except OSError:
            pass

    # Acquire lock
    ctx_dir(root).mkdir(parents=True, exist_ok=True)
    lock.write_text(str(os.getpid()))

    try:
        conn = init_db(db_path(root))
        _run_index_locked(root, config, conn, force, progress, stats)
        conn.commit()
    except Exception as exc:
        stats.errors.append(str(exc))
        log.error("Index failed", error=str(exc))
    finally:
        with contextlib.suppress(OSError):
            lock.unlink(missing_ok=True)
        stats.elapsed_seconds = time.monotonic() - start

    return stats


def _run_index_locked(
    root: Path,
    config: SemtreeConfig,
    conn: sqlite3.Connection,
    force: bool,
    progress: ProgressCallback | None,
    stats: IndexStats,
) -> None:
    """Inner indexing loop (called with lock held)."""
    # Collect all indexable files first for progress reporting
    all_files = list(
        walk_project(
            root,
            include_extensions=set(config.include_extensions),
            exclude_dirs=set(config.exclude_dirs),
            max_file_size_kb=config.max_file_size_kb,
            use_gitignore=config.use_gitignore,
        )
    )
    stats.total_files = len(all_files)

    # Build set of currently-tracked relative paths for deletion detection
    tracked = {f.path for f in db_store.list_files(conn)}
    seen: set[str] = set()

    for idx, fpath in enumerate(all_files):
        try:
            rel = str(fpath.relative_to(root))
        except ValueError:
            rel = str(fpath)

        seen.add(rel)

        if progress:
            progress(rel, idx + 1, len(all_files))

        # Incremental: skip unchanged files
        stored_sha1 = db_store.get_file_sha1(conn, rel)
        current_sha1 = sha1_file(fpath)

        if not force and stored_sha1 == current_sha1:
            stats.skipped_files += 1
            continue

        is_new = stored_sha1 is None
        lang = detect_language(fpath)

        try:
            source = fpath.read_text(errors="replace")
        except OSError as exc:
            stats.errors.append(f"{rel}: {exc}")
            continue

        symbols = extract_symbols(fpath, source, lang)

        if config.git_context:
            annotate_symbols(symbols, root, rel, enabled=True)

        file_id = db_store.upsert_file(
            conn,
            rel_path=rel,
            sha1=current_sha1,
            size_bytes=fpath.stat().st_size,
            lang=lang,
        )
        db_store.replace_file_symbols(conn, file_id, symbols)

        stats.total_symbols += len(symbols)
        if is_new:
            stats.new_files += 1
        else:
            stats.updated_files += 1

        log.debug("Indexed", file=rel, symbols=len(symbols), lang=lang)

    # Remove stale files (deleted from disk)
    stale = tracked - seen
    for rel in stale:
        db_store.delete_file(conn, rel)
        log.debug("Removed stale file", file=rel)
