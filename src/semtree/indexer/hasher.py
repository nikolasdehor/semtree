"""SHA-1 incremental hashing for change detection."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha1_file(path: Path) -> str:
    """Return the SHA-1 hex digest of a file's contents.

    Reads in 64 KB chunks to handle large files without loading them
    entirely into memory.
    """
    h = hashlib.sha1(usedforsecurity=False)
    try:
        with path.open("rb") as fh:
            while chunk := fh.read(65536):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def sha1_text(text: str) -> str:
    """Return the SHA-1 hex digest of a UTF-8 string."""
    return hashlib.sha1(text.encode(), usedforsecurity=False).hexdigest()


def is_changed(path: Path, stored_sha1: str | None) -> bool:
    """Return True when the file on disk differs from the stored hash."""
    if stored_sha1 is None:
        return True
    return sha1_file(path) != stored_sha1
