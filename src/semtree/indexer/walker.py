"""File walker with .gitignore and semtree exclude support."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

try:
    import pathspec  # type: ignore
    _HAS_PATHSPEC = True
except ImportError:
    _HAS_PATHSPEC = False


def _load_gitignore(root: Path) -> pathspec.PathSpec | None:
    """Parse .gitignore at root into a PathSpec matcher."""
    if not _HAS_PATHSPEC:
        return None
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return None
    try:
        patterns = gitignore.read_text(errors="replace").splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)  # type: ignore
    except OSError:
        return None


def walk_project(
    root: Path,
    include_extensions: set[str],
    exclude_dirs: set[str],
    max_file_size_kb: int = 512,
    use_gitignore: bool = True,
) -> Iterator[Path]:
    """Yield absolute paths of indexable source files under root.

    Respects .gitignore patterns and explicit exclude_dirs.
    Files larger than max_file_size_kb are silently skipped.
    """
    gitignore_spec = _load_gitignore(root) if use_gitignore else None

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current = Path(dirpath)
        rel_dir = current.relative_to(root)

        # Prune excluded directories in-place (modifies dirnames to prevent descent)
        dirnames[:] = [
            d for d in dirnames
            if _should_descend(d, rel_dir, exclude_dirs, gitignore_spec, root)
        ]

        for fname in filenames:
            fpath = current / fname
            rel = fpath.relative_to(root)

            suffix = fpath.suffix.lower()
            if suffix not in include_extensions:
                continue

            # Check gitignore
            if gitignore_spec and gitignore_spec.match_file(str(rel)):
                continue

            try:
                size_kb = fpath.stat().st_size / 1024
            except OSError:
                continue

            if size_kb > max_file_size_kb:
                continue

            yield fpath


def _should_descend(
    dirname: str,
    parent_rel: Path,
    exclude_dirs: set[str],
    gitignore_spec: pathspec.PathSpec | None,
    root: Path,
) -> bool:
    """Return True if we should recurse into dirname."""
    # Always skip hidden dirs except .github
    if dirname.startswith(".") and dirname not in (".github",):
        return False

    # Check against explicit exclude patterns
    rel_str = str(parent_rel / dirname)
    for pattern in exclude_dirs:
        if pattern.endswith("*"):
            if dirname.startswith(pattern[:-1]):
                return False
        elif dirname == pattern or rel_str == pattern:
            return False

    # Check gitignore for directories
    if gitignore_spec:
        dir_rel = str(parent_rel / dirname) + "/"
        if gitignore_spec.match_file(dir_rel):
            return False

    return True


def detect_language(path: Path) -> str:
    """Map file extension to a language identifier."""
    _EXT_MAP: dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".hpp": "cpp",
        ".cc": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".cs": "csharp",
        ".md": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".json": "json",
    }
    return _EXT_MAP.get(path.suffix.lower(), "unknown")
