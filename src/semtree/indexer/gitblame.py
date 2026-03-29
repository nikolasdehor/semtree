"""Git blame / log integration for per-symbol last-modified metadata.

Provides author name and ISO date for a line range in a file.
Gracefully no-ops when git is unavailable or the file is not tracked.
"""

from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=256)
def _git_root(start: str) -> str | None:
    """Return the git repository root for a path, or None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def blame_line(repo_root: Path, rel_path: str, line: int) -> tuple[str, str]:
    """Return (author, iso_date) for the given line in the file.

    Returns ("", "") when git blame fails or git is not available.
    """
    git_root = _git_root(str(repo_root))
    if git_root is None:
        return ("", "")

    try:
        result = subprocess.run(
            [
                "git", "log", "--follow", "-1",
                "--format=%an|%as",  # author name | date YYYY-MM-DD
                f"-L{line},{line}",
                rel_path,
            ],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return ("", "")
        parts = result.stdout.strip().split("|", 1)
        if len(parts) == 2:
            return (parts[0].strip(), parts[1].strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ("", "")


def annotate_symbols(
    symbols: list[dict],
    repo_root: Path,
    rel_path: str,
    enabled: bool = True,
) -> list[dict]:
    """Add git_author and git_date to each symbol dict in-place.

    When enabled=False or git is unavailable, leaves fields as empty strings.
    Only fetches blame for the first line of each symbol to keep it fast.
    """
    if not enabled:
        return symbols

    # Deduplicate line lookups
    line_cache: dict[int, tuple[str, str]] = {}
    for sym in symbols:
        ln = sym.get("line_start", 1)
        if ln not in line_cache:
            line_cache[ln] = blame_line(repo_root, rel_path, ln)
        author, date = line_cache[ln]
        sym["git_author"] = author
        sym["git_date"] = date

    return symbols
