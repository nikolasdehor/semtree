"""Tests for the indexer subsystem."""

from __future__ import annotations

from pathlib import Path

from semtree.config import SemtreeConfig
from semtree.db import store as db_store
from semtree.indexer.coordinator import run_index
from semtree.indexer.docstrings import (
    _clean_string_literal,
    extract_go_doc_from_lines,
    extract_jsdoc_from_lines,
    extract_rust_doc_from_lines,
)
from semtree.indexer.extractor import extract_symbols
from semtree.indexer.hasher import is_changed, sha1_file, sha1_text
from semtree.indexer.walker import detect_language, walk_project

# ---------------------------------------------------------------------------
# Walker tests
# ---------------------------------------------------------------------------

class TestWalker:
    def test_finds_python_files(self, tmp_project: Path) -> None:
        files = list(
            walk_project(
                tmp_project,
                include_extensions={".py"},
                exclude_dirs=set(),
            )
        )
        names = {f.name for f in files}
        assert "main.py" in names
        assert "utils.py" in names

    def test_excludes_node_modules(self, tmp_path: Path) -> None:
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "foo.js").write_text("const x = 1;")
        (tmp_path / "app.js").write_text("const y = 2;")
        files = list(
            walk_project(
                tmp_path,
                include_extensions={".js"},
                exclude_dirs={"node_modules"},
            )
        )
        names = {f.name for f in files}
        assert "app.js" in names
        assert "foo.js" not in names

    def test_skips_large_files(self, tmp_path: Path) -> None:
        large = tmp_path / "big.py"
        large.write_bytes(b"x" * (600 * 1024))  # 600 KB
        files = list(
            walk_project(
                tmp_path,
                include_extensions={".py"},
                exclude_dirs=set(),
                max_file_size_kb=512,
            )
        )
        assert large not in files

    def test_excludes_dot_dirs(self, tmp_path: Path) -> None:
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "secret.py").write_text("pass")
        (tmp_path / "visible.py").write_text("pass")
        files = list(
            walk_project(tmp_path, include_extensions={".py"}, exclude_dirs=set())
        )
        names = {f.name for f in files}
        assert "visible.py" in names
        assert "secret.py" not in names

    def test_detect_language(self) -> None:
        assert detect_language(Path("foo.py")) == "python"
        assert detect_language(Path("bar.ts")) == "typescript"
        assert detect_language(Path("main.go")) == "go"
        assert detect_language(Path("lib.rs")) == "rust"
        assert detect_language(Path("unknown.xyz")) == "unknown"


# ---------------------------------------------------------------------------
# Hasher tests
# ---------------------------------------------------------------------------

class TestHasher:
    def test_sha1_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h = sha1_file(f)
        assert len(h) == 40
        assert h == sha1_file(f)  # deterministic

    def test_sha1_changes_on_content_change(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        h1 = sha1_file(f)
        f.write_text("world")
        h2 = sha1_file(f)
        assert h1 != h2

    def test_is_changed_no_stored(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("content")
        assert is_changed(f, None) is True

    def test_is_changed_same(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("content")
        h = sha1_file(f)
        assert is_changed(f, h) is False

    def test_sha1_text(self) -> None:
        h = sha1_text("hello")
        assert len(h) == 40
        assert sha1_text("hello") == h


# ---------------------------------------------------------------------------
# Extractor tests (regex path, no tree-sitter required)
# ---------------------------------------------------------------------------

class TestExtractor:
    def test_python_functions_regex(self) -> None:
        source = '''
def foo(x: int) -> str:
    """Do foo."""
    return str(x)

async def bar():
    pass

class MyClass:
    def method(self):
        pass
'''
        symbols = extract_symbols(Path("test.py"), source, "python")
        names = {s["name"] for s in symbols}
        assert "foo" in names
        assert "bar" in names
        assert "MyClass" in names

    def test_javascript_functions_regex(self) -> None:
        source = '''
function fetchData(url) {
    return fetch(url);
}

const processResult = async function(data) {
    return data;
};

class ApiClient {
    constructor() {}
}
'''
        symbols = extract_symbols(Path("test.js"), source, "javascript")
        names = {s["name"] for s in symbols}
        assert "fetchData" in names
        assert "ApiClient" in names

    def test_go_functions_regex(self) -> None:
        source = '''
func HandleRequest(w http.ResponseWriter, r *http.Request) {
    // handler
}

type Server struct {
    Port int
}
'''
        symbols = extract_symbols(Path("test.go"), source, "go")
        names = {s["name"] for s in symbols}
        assert "HandleRequest" in names

    def test_rust_functions_regex(self) -> None:
        source = '''
pub fn process_data(input: &str) -> Result<(), Error> {
    Ok(())
}

pub struct Config {
    pub timeout: u64,
}
'''
        symbols = extract_symbols(Path("test.rs"), source, "rust")
        names = {s["name"] for s in symbols}
        assert "process_data" in names
        assert "Config" in names

    def test_unknown_language_returns_empty(self) -> None:
        symbols = extract_symbols(Path("test.xyz"), "content", "unknown")
        assert symbols == []


# ---------------------------------------------------------------------------
# Docstring extraction tests
# ---------------------------------------------------------------------------

class TestDocstrings:
    def test_clean_string_literal_triple_double(self) -> None:
        raw = '"""This is a docstring."""'
        assert _clean_string_literal(raw) == "This is a docstring."

    def test_clean_string_literal_triple_single(self) -> None:
        raw = "'''Multi\n    line\n    docstring.'''"
        result = _clean_string_literal(raw)
        assert "Multi" in result

    def test_jsdoc_extraction(self) -> None:
        lines = [
            "/**",
            " * Calculate sum of two numbers.",
            " * @param {number} a",
            " * @param {number} b",
            " */",
            "function add(a, b) {",
        ]
        doc = extract_jsdoc_from_lines(lines, decl_line=5)
        assert "Calculate sum" in doc

    def test_jsdoc_no_comment_returns_empty(self) -> None:
        lines = ["", "function foo() {"]
        doc = extract_jsdoc_from_lines(lines, decl_line=1)
        assert doc == ""

    def test_go_doc_extraction(self) -> None:
        lines = [
            "// HandleRequest processes incoming HTTP requests.",
            "// It validates the input and returns a response.",
            "func HandleRequest(w http.ResponseWriter, r *http.Request) {",
        ]
        doc = extract_go_doc_from_lines(lines, decl_line=2)
        assert "HandleRequest processes" in doc

    def test_rust_doc_extraction(self) -> None:
        lines = [
            "/// Process the input data.",
            "/// Returns an error if input is invalid.",
            "pub fn process(input: &str) -> Result<(), Error> {",
        ]
        doc = extract_rust_doc_from_lines(lines, decl_line=2)
        assert "Process the input" in doc


# ---------------------------------------------------------------------------
# Full integration: coordinator
# ---------------------------------------------------------------------------

class TestCoordinator:
    def test_full_index(self, tmp_project: Path) -> None:
        config = SemtreeConfig(use_gitignore=False, git_context=False)
        stats = run_index(tmp_project, config=config)
        assert stats.total_files >= 2
        assert stats.total_symbols > 0
        assert stats.errors == []

    def test_incremental_index_skips_unchanged(self, tmp_project: Path) -> None:
        config = SemtreeConfig(use_gitignore=False, git_context=False)
        stats1 = run_index(tmp_project, config=config)
        stats2 = run_index(tmp_project, config=config)
        assert stats2.skipped_files == stats1.total_files
        assert stats2.new_files == 0

    def test_force_reindex(self, tmp_project: Path) -> None:
        config = SemtreeConfig(use_gitignore=False, git_context=False)
        run_index(tmp_project, config=config)
        stats = run_index(tmp_project, config=config, force=True)
        assert stats.skipped_files == 0

    def test_symbols_stored_in_db(self, tmp_project: Path) -> None:
        from semtree.config import db_path
        from semtree.db.schema import init_db

        config = SemtreeConfig(use_gitignore=False, git_context=False)
        run_index(tmp_project, config=config)
        conn = init_db(db_path(tmp_project))
        symbols = db_store.fts_search(conn, "greet")
        assert any(s.name == "greet" for s in symbols)
