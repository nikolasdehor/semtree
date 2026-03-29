"""Symbol extraction: tree-sitter primary path, regex fallback.

Produces a list of symbol dicts suitable for store.replace_file_symbols().
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .docstrings import (
    extract_go_doc_from_lines,
    extract_jsdoc_from_lines,
    extract_python_docstring,
    extract_python_docstring_regex,
    extract_rust_doc_from_lines,
)
from .parser import parse_source

Symbol = dict[str, Any]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_symbols(path: Path, source: str, language: str) -> list[Symbol]:
    """Extract symbols from source code.

    Tries tree-sitter first. Falls back to regex if unavailable.
    Returns a list of dicts with keys:
        name, kind, line_start, line_end, signature, docstring
    """
    tree = parse_source(language, source)
    if tree is not None:
        return _extract_ts(tree, source, language)
    return _extract_regex(source, language)


# ---------------------------------------------------------------------------
# Tree-sitter extraction
# ---------------------------------------------------------------------------

def _extract_ts(tree: Any, source: str, language: str) -> list[Symbol]:
    root = tree.root_node
    lines = source.split("\n")
    symbols: list[Symbol] = []

    dispatchers = {
        "python":     _visit_python,
        "javascript": _visit_js,
        "typescript": _visit_ts,
        "go":         _visit_go,
        "rust":       _visit_rust,
        "java":       _visit_java,
        "c":          _visit_c,
        "cpp":        _visit_cpp,
    }

    visitor = dispatchers.get(language)
    if visitor is None:
        return []

    visitor(root, lines, symbols)
    return symbols


def _node_text(node: Any) -> str:
    t = node.text
    if isinstance(t, bytes):
        return t.decode("utf-8", errors="replace")
    return str(t) if t else ""


def _signature_from_node(node: Any, source_lines: list[str]) -> str:
    """Extract the declaration line (first line of node) as signature."""
    row = node.start_point[0]
    if row < len(source_lines):
        return source_lines[row].strip()
    return ""


# -- Python --

def _visit_python(node: Any, lines: list[str], out: list[Symbol]) -> None:
    kind_map = {"function_definition": "function", "class_definition": "class"}

    def walk(n: Any) -> None:
        ntype = n.type
        if ntype in kind_map:
            name_node = n.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node)
                line_start = n.start_point[0] + 1
                line_end = n.end_point[0] + 1
                sig = _signature_from_node(n, lines)
                doc = extract_python_docstring(n)
                out.append({
                    "name": name,
                    "kind": kind_map[ntype],
                    "line_start": line_start,
                    "line_end": line_end,
                    "signature": sig,
                    "docstring": doc,
                })
        for child in n.children:
            walk(child)

    walk(node)


# -- JavaScript / TypeScript --

_JS_KINDS = {
    "function_declaration": "function",
    "generator_function_declaration": "function",
    "method_definition": "method",
    "class_declaration": "class",
    "lexical_declaration": "const",
    "variable_declaration": "var",
}


def _visit_js(node: Any, lines: list[str], out: list[Symbol]) -> None:
    _walk_js_ts(node, lines, out)


def _visit_ts(node: Any, lines: list[str], out: list[Symbol]) -> None:
    _walk_js_ts(node, lines, out, include_types=True)


def _walk_js_ts(node: Any, lines: list[str], out: list[Symbol], include_types: bool = False) -> None:
    def walk(n: Any) -> None:
        kind = _JS_KINDS.get(n.type)
        if kind:
            name = _js_name(n)
            if name:
                line_start = n.start_point[0] + 1
                line_end = n.end_point[0] + 1
                sig = _signature_from_node(n, lines)
                doc = extract_jsdoc_from_lines(lines, n.start_point[0])
                out.append({
                    "name": name,
                    "kind": kind,
                    "line_start": line_start,
                    "line_end": line_end,
                    "signature": sig,
                    "docstring": doc,
                })
        elif include_types and n.type in ("type_alias_declaration", "interface_declaration"):
            name_node = n.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node)
                line_start = n.start_point[0] + 1
                line_end = n.end_point[0] + 1
                sig = _signature_from_node(n, lines)
                doc = extract_jsdoc_from_lines(lines, n.start_point[0])
                out.append({
                    "name": name,
                    "kind": "type",
                    "line_start": line_start,
                    "line_end": line_end,
                    "signature": sig,
                    "docstring": doc,
                })
        for child in n.children:
            walk(child)

    walk(node)


def _js_name(node: Any) -> str:
    name_node = node.child_by_field_name("name")
    if name_node:
        return _node_text(name_node)
    # Arrow functions assigned to const/let/var
    if node.type in ("lexical_declaration", "variable_declaration"):
        for child in node.children:
            if child.type == "variable_declarator":
                n = child.child_by_field_name("name")
                if n:
                    return _node_text(n)
    return ""


# -- Go --

def _visit_go(node: Any, lines: list[str], out: list[Symbol]) -> None:
    def walk(n: Any) -> None:
        if n.type == "function_declaration":
            name_node = n.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node)
                line_start = n.start_point[0] + 1
                line_end = n.end_point[0] + 1
                sig = _signature_from_node(n, lines)
                doc = extract_go_doc_from_lines(lines, n.start_point[0])
                out.append({"name": name, "kind": "function", "line_start": line_start,
                             "line_end": line_end, "signature": sig, "docstring": doc})
        elif n.type == "method_declaration":
            name_node = n.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node)
                line_start = n.start_point[0] + 1
                line_end = n.end_point[0] + 1
                sig = _signature_from_node(n, lines)
                doc = extract_go_doc_from_lines(lines, n.start_point[0])
                out.append({"name": name, "kind": "method", "line_start": line_start,
                             "line_end": line_end, "signature": sig, "docstring": doc})
        elif n.type == "type_declaration":
            for child in n.children:
                if child.type == "type_spec":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        name = _node_text(name_node)
                        line_start = n.start_point[0] + 1
                        line_end = n.end_point[0] + 1
                        out.append({"name": name, "kind": "type", "line_start": line_start,
                                    "line_end": line_end, "signature": _signature_from_node(n, lines),
                                    "docstring": ""})
        for child in n.children:
            walk(child)

    walk(node)


# -- Rust --

def _visit_rust(node: Any, lines: list[str], out: list[Symbol]) -> None:
    rust_kinds = {
        "function_item": "function",
        "struct_item": "class",
        "enum_item": "type",
        "trait_item": "type",
        "impl_item": "class",
        "type_item": "type",
        "const_item": "const",
        "static_item": "const",
    }

    def walk(n: Any) -> None:
        kind = rust_kinds.get(n.type)
        if kind:
            name_node = n.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node)
                line_start = n.start_point[0] + 1
                line_end = n.end_point[0] + 1
                sig = _signature_from_node(n, lines)
                doc = extract_rust_doc_from_lines(lines, n.start_point[0])
                out.append({"name": name, "kind": kind, "line_start": line_start,
                             "line_end": line_end, "signature": sig, "docstring": doc})
        for child in n.children:
            walk(child)

    walk(node)


# -- Java --

def _visit_java(node: Any, lines: list[str], out: list[Symbol]) -> None:
    def walk(n: Any) -> None:
        if n.type in ("method_declaration", "constructor_declaration"):
            name_node = n.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node)
                line_start = n.start_point[0] + 1
                line_end = n.end_point[0] + 1
                sig = _signature_from_node(n, lines)
                doc = extract_jsdoc_from_lines(lines, n.start_point[0])
                out.append({"name": name, "kind": "method", "line_start": line_start,
                             "line_end": line_end, "signature": sig, "docstring": doc})
        elif n.type == "class_declaration":
            name_node = n.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node)
                line_start = n.start_point[0] + 1
                line_end = n.end_point[0] + 1
                sig = _signature_from_node(n, lines)
                doc = extract_jsdoc_from_lines(lines, n.start_point[0])
                out.append({"name": name, "kind": "class", "line_start": line_start,
                             "line_end": line_end, "signature": sig, "docstring": doc})
        for child in n.children:
            walk(child)

    walk(node)


# -- C / C++ --

def _visit_c(node: Any, lines: list[str], out: list[Symbol]) -> None:
    _walk_c_cpp(node, lines, out)


def _visit_cpp(node: Any, lines: list[str], out: list[Symbol]) -> None:
    _walk_c_cpp(node, lines, out)


def _walk_c_cpp(node: Any, lines: list[str], out: list[Symbol]) -> None:
    def walk(n: Any) -> None:
        if n.type == "function_definition":
            # name is nested: declarator -> direct_declarator -> identifier
            name = _c_function_name(n)
            if name:
                line_start = n.start_point[0] + 1
                line_end = n.end_point[0] + 1
                sig = _signature_from_node(n, lines)
                out.append({"name": name, "kind": "function", "line_start": line_start,
                             "line_end": line_end, "signature": sig, "docstring": ""})
        elif n.type in ("struct_specifier", "class_specifier"):
            name_node = n.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node)
                line_start = n.start_point[0] + 1
                line_end = n.end_point[0] + 1
                out.append({"name": name, "kind": "class", "line_start": line_start,
                             "line_end": line_end, "signature": _signature_from_node(n, lines),
                             "docstring": ""})
        for child in n.children:
            walk(child)

    walk(node)


def _c_function_name(node: Any) -> str:
    decl = node.child_by_field_name("declarator")
    while decl is not None:
        if decl.type in ("identifier", "field_identifier"):
            return _node_text(decl)
        next_decl = decl.child_by_field_name("declarator")
        if next_decl is None:
            # Try direct children
            for child in decl.children:
                if child.type == "identifier":
                    return _node_text(child)
            break
        decl = next_decl
    return ""


# ---------------------------------------------------------------------------
# Regex fallback (no tree-sitter)
# ---------------------------------------------------------------------------

_REGEX_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "python": [
        (r"^(?:async\s+)?def\s+(\w+)\s*\(", "function"),
        (r"^class\s+(\w+)", "class"),
    ],
    "javascript": [
        (r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", "function"),
        (r"^(?:export\s+)?class\s+(\w+)", "class"),
        (r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\()", "function"),
    ],
    "typescript": [
        (r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", "function"),
        (r"^(?:export\s+)?class\s+(\w+)", "class"),
        (r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\()", "function"),
        (r"^(?:export\s+)?(?:type|interface)\s+(\w+)", "type"),
    ],
    "go": [
        (r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", "function"),
        (r"^type\s+(\w+)\s+struct", "class"),
    ],
    "rust": [
        (r"^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", "function"),
        (r"^(?:pub\s+)?struct\s+(\w+)", "class"),
        (r"^(?:pub\s+)?enum\s+(\w+)", "type"),
        (r"^(?:pub\s+)?trait\s+(\w+)", "type"),
    ],
    "java": [
        (r"(?:public|protected|private|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\(", "method"),
        (r"^(?:public\s+)?(?:abstract\s+)?class\s+(\w+)", "class"),
    ],
}


def _extract_regex(source: str, language: str) -> list[Symbol]:
    """Regex-based fallback extractor for when tree-sitter is unavailable."""
    patterns = _REGEX_PATTERNS.get(language, [])
    if not patterns:
        return []

    lines = source.split("\n")
    symbols: list[Symbol] = []

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        for pattern, kind in patterns:
            m = re.match(pattern, stripped)
            if m:
                name = m.group(1)
                if name.startswith("_") and name.startswith("__") is False:
                    pass  # include private symbols
                docstring = extract_python_docstring_regex(source, lineno - 1) if language == "python" else ""
                symbols.append({
                    "name": name,
                    "kind": kind,
                    "line_start": lineno,
                    "line_end": lineno,
                    "signature": stripped[:120],
                    "docstring": docstring,
                })
                break  # one match per line

    return symbols
