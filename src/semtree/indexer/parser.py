"""Tree-sitter parser pool.

Caches one parser instance per language to avoid repeated Language object
construction overhead on large codebases.

Falls back gracefully when tree-sitter or a language grammar is not installed.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any


_lock = threading.Lock()
_parsers: dict[str, Any] = {}
_UNAVAILABLE: set[str] = set()

# Maps language id -> importable module name in the tree-sitter ecosystem
_GRAMMAR_MODULES: dict[str, str] = {
    "python":     "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "go":         "tree_sitter_go",
    "rust":       "tree_sitter_rust",
    "java":       "tree_sitter_java",
    "c":          "tree_sitter_c",
    "cpp":        "tree_sitter_cpp",
}


def get_parser(language: str) -> Any | None:
    """Return a cached tree-sitter Parser for the given language, or None.

    Thread-safe. Returns None when tree-sitter or the grammar is unavailable.
    """
    if language in _UNAVAILABLE:
        return None

    with _lock:
        if language in _parsers:
            return _parsers[language]

        parser = _build_parser(language)
        if parser is None:
            _UNAVAILABLE.add(language)
        else:
            _parsers[language] = parser
        return parser


def _build_parser(language: str) -> Any | None:
    try:
        import tree_sitter  # type: ignore  # noqa: F401
        from tree_sitter import Language, Parser  # type: ignore
    except ImportError:
        return None

    module_name = _GRAMMAR_MODULES.get(language)
    if module_name is None:
        return None

    try:
        import importlib
        grammar_mod = importlib.import_module(module_name)
    except ImportError:
        return None

    try:
        # tree-sitter >= 0.22 exposes language() directly on the module
        if hasattr(grammar_mod, "language"):
            lang = Language(grammar_mod.language())
        elif hasattr(grammar_mod, "Language"):
            # older binding style
            lang = grammar_mod.Language
        else:
            return None

        parser = Parser(lang)
        return parser
    except Exception:
        return None


def parse_source(language: str, source: str | bytes) -> Any | None:
    """Parse source code and return the tree-sitter Tree, or None."""
    parser = get_parser(language)
    if parser is None:
        return None
    if isinstance(source, str):
        source = source.encode("utf-8", errors="replace")
    try:
        return parser.parse(source)
    except Exception:
        return None


def available_languages() -> list[str]:
    """Return language ids for which a tree-sitter grammar is installed."""
    available = []
    for lang, mod_name in _GRAMMAR_MODULES.items():
        try:
            import importlib
            importlib.import_module(mod_name)
            available.append(lang)
        except ImportError:
            pass
    return available
