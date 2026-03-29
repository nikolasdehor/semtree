"""L0-L3 context formatters.

Each level produces progressively richer context:

  L0 - File tree only: paths and stats
  L1 - Symbol names + kinds per file (outline)
  L2 - L1 + signatures + first line of docstring (default)
  L3 - L2 + full docstrings + git context

Level selection follows the retrieval policy's context_level setting.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..db.store import FileRecord, SymbolRecord


def format_file_tree(files: Sequence[FileRecord], root: Path) -> str:
    """L0: compact file tree grouped by directory."""
    if not files:
        return ""

    # Group by directory prefix
    by_dir: dict[str, list[str]] = {}
    for f in files:
        parts = Path(f.path).parts
        dir_key = "/".join(parts[:-1]) if len(parts) > 1 else "."
        by_dir.setdefault(dir_key, []).append(parts[-1])

    lines = ["## Project Files\n"]
    for dir_path in sorted(by_dir):
        lines.append(f"**{dir_path}/**")
        for fname in sorted(by_dir[dir_path]):
            lines.append(f"  {fname}")
    return "\n".join(lines)


def format_l1(symbols: Sequence[SymbolRecord]) -> str:
    """L1: symbol names and kinds, grouped by file."""
    if not symbols:
        return ""

    by_file: dict[str, list[SymbolRecord]] = {}
    for sym in symbols:
        by_file.setdefault(sym.file_path, []).append(sym)

    lines = []
    for file_path in sorted(by_file):
        lines.append(f"\n### {file_path}")
        for sym in sorted(by_file[file_path], key=lambda s: s.line_start):
            lines.append(f"  [{sym.kind}] {sym.name} (L{sym.line_start})")

    return "\n".join(lines)


def format_l2(symbols: Sequence[SymbolRecord]) -> str:
    """L2: signatures + first line of docstring, grouped by file."""
    if not symbols:
        return ""

    by_file: dict[str, list[SymbolRecord]] = {}
    for sym in symbols:
        by_file.setdefault(sym.file_path, []).append(sym)

    lines = []
    for file_path in sorted(by_file):
        lines.append(f"\n### {file_path}")
        for sym in sorted(by_file[file_path], key=lambda s: s.line_start):
            lines.append(f"\n**{sym.kind}** `{sym.name}` — L{sym.line_start}-{sym.line_end}")
            if sym.signature:
                lines.append(f"```\n{sym.signature}\n```")
            if sym.docstring:
                first_line = sym.docstring.split("\n")[0].strip()
                if first_line:
                    lines.append(f"_{first_line}_")

    return "\n".join(lines)


def format_l3(symbols: Sequence[SymbolRecord]) -> str:
    """L3: full docstrings + git context, grouped by file."""
    if not symbols:
        return ""

    by_file: dict[str, list[SymbolRecord]] = {}
    for sym in symbols:
        by_file.setdefault(sym.file_path, []).append(sym)

    lines = []
    for file_path in sorted(by_file):
        lines.append(f"\n### {file_path}")
        for sym in sorted(by_file[file_path], key=lambda s: s.line_start):
            lines.append(f"\n#### `{sym.name}` ({sym.kind})")
            lines.append(f"Lines {sym.line_start}-{sym.line_end}")

            if sym.git_author and sym.git_date:
                lines.append(f"Last modified by **{sym.git_author}** on {sym.git_date}")

            if sym.signature:
                lines.append(f"\n```\n{sym.signature}\n```")

            if sym.docstring:
                lines.append(f"\n{sym.docstring}")

    return "\n".join(lines)


def format_by_level(
    symbols: Sequence[SymbolRecord],
    level: int,
    files: Sequence[FileRecord] | None = None,
    root: Path | None = None,
) -> str:
    """Dispatch to the appropriate level formatter."""
    if level == 0:
        if files and root:
            return format_file_tree(files, root)
        return format_l1(symbols)
    elif level == 1:
        return format_l1(symbols)
    elif level == 2:
        return format_l2(symbols)
    else:
        return format_l3(symbols)
