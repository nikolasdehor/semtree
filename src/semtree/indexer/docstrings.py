"""Multi-language docstring extraction.

Handles:
  Python   - first string literal in function/class body
  JS/TS    - JSDoc blocks (/** ... */) immediately above declarations
  Go       - // comment blocks above func declarations
  Rust     - /// doc comments above items
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

def extract_python_docstring(node: Any) -> str:
    """Extract docstring from a Python function or class tree-sitter node.

    Looks for the first expression_statement containing a string literal
    in the function/class body.
    """
    body = None
    for child in node.children:
        if child.type == "block":
            body = child
            break
    if body is None:
        return ""

    for child in body.children:
        if child.type == "expression_statement":
            for sub in child.children:
                if sub.type in ("string", "concatenated_string"):
                    text = sub.text
                    if isinstance(text, bytes):
                        text = text.decode("utf-8", errors="replace")
                    return _clean_string_literal(text)
    return ""


def _clean_string_literal(raw: str) -> str:
    """Strip quotes and leading/trailing whitespace from a Python string literal."""
    s = raw.strip()
    for quote in ('"""', "'''", '"', "'"):
        if s.startswith(quote) and s.endswith(quote) and len(s) >= len(quote) * 2:
            inner = s[len(quote):-len(quote)]
            return _dedent_docstring(inner)
    return s


def _dedent_docstring(text: str) -> str:
    """Remove consistent leading whitespace from all non-first lines."""
    lines = text.split("\n")
    if len(lines) <= 1:
        return text.strip()
    # Find minimum indent of non-empty continuation lines
    indent = None
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            spaces = len(line) - len(stripped)
            indent = spaces if indent is None else min(indent, spaces)
    if indent:
        lines[1:] = [line[indent:] for line in lines[1:]]
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# JavaScript / TypeScript (JSDoc)
# ---------------------------------------------------------------------------

_JSDOC_RE = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)
_JSDOC_LINE_RE = re.compile(r"^\s*\*\s?", re.MULTILINE)


def extract_jsdoc_from_lines(
    source_lines: list[str],
    decl_line: int,  # 0-indexed line of the declaration
) -> str:
    """Find the JSDoc block /** ... */ immediately before decl_line.

    Scans backwards from decl_line to find a closing */ and then the
    matching /** opener.
    """
    # Walk backwards from decl_line - 1 to find '*/''
    end_idx = decl_line - 1
    while end_idx >= 0 and source_lines[end_idx].strip() == "":
        end_idx -= 1

    if end_idx < 0 or "*/" not in source_lines[end_idx]:
        return ""

    # Now find matching '/**'
    start_idx = end_idx
    while start_idx >= 0:
        if "/**" in source_lines[start_idx]:
            break
        start_idx -= 1

    if start_idx < 0 or "/**" not in source_lines[start_idx]:
        return ""

    block = "\n".join(source_lines[start_idx : end_idx + 1])
    m = _JSDOC_RE.search(block)
    if not m:
        return ""
    inner = m.group(1)
    # Remove leading ' * ' from each line
    inner = _JSDOC_LINE_RE.sub("", inner)
    return inner.strip()


# ---------------------------------------------------------------------------
# Go
# ---------------------------------------------------------------------------

_GO_COMMENT_RE = re.compile(r"^//\s?(.*)")


def extract_go_doc_from_lines(
    source_lines: list[str],
    decl_line: int,  # 0-indexed line of 'func ...'
) -> str:
    """Extract the // comment block immediately preceding a Go func declaration.

    Consecutive // lines ending just before decl_line (allowing blank lines
    to break the block) form the doc comment.
    """
    comments: list[str] = []
    idx = decl_line - 1
    while idx >= 0 and source_lines[idx].strip() == "":
        idx -= 1

    while idx >= 0:
        line = source_lines[idx].strip()
        m = _GO_COMMENT_RE.match(line)
        if m:
            comments.append(m.group(1))
            idx -= 1
        else:
            break

    return " ".join(reversed(comments)).strip()


# ---------------------------------------------------------------------------
# Rust
# ---------------------------------------------------------------------------

_RUST_DOC_RE = re.compile(r"^///\s?(.*)")


def extract_rust_doc_from_lines(
    source_lines: list[str],
    decl_line: int,  # 0-indexed
) -> str:
    """Extract /// doc comments immediately preceding a Rust item declaration.

    Also handles //! module-level doc comments when decl_line is 0.
    """
    comments: list[str] = []
    idx = decl_line - 1
    while idx >= 0 and source_lines[idx].strip() == "":
        idx -= 1

    while idx >= 0:
        line = source_lines[idx].strip()
        m = _RUST_DOC_RE.match(line)
        if m:
            comments.append(m.group(1))
            idx -= 1
        else:
            break

    return "\n".join(reversed(comments)).strip()


# ---------------------------------------------------------------------------
# Regex-based fallbacks (no tree-sitter)
# ---------------------------------------------------------------------------

_PY_DOCSTRING_RE = re.compile(
    r'(?:def|class)\s+\w+[^:]*:\s*(?:\n\s+)?("""(?:.*?)"""|\'\'\'(?:.*?)\'\'\')',
    re.DOTALL,
)


def extract_python_docstring_regex(source: str, func_line: int) -> str:
    """Fallback: regex extraction of Python docstrings when tree-sitter is unavailable."""
    lines = source.split("\n")
    # Find the function/class def at func_line, then look for docstring
    if func_line >= len(lines):
        return ""
    snippet = "\n".join(lines[func_line : func_line + 10])
    m = re.search(
        r":\s*\n\s+(?P<ds>\"\"\".*?\"\"\"|\'\'\'.*?\'\'\'|\".*?\"|\'.*?\')",
        snippet,
        re.DOTALL,
    )
    if m:
        return _clean_string_literal(m.group("ds"))
    return ""
