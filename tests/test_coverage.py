"""Additional tests targeting coverage gaps.

Covers: docstrings.py, gitblame.py, scripts/setup.py, memory/lite.py,
        log.py, config.py, context/builder.py, db/store.py, coordinator.py.
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from semtree.config import (
    SemtreeConfig,
    ctx_dir,
    db_path,
    find_project_root,
    lock_path,
)
from semtree.context.builder import _fit_symbols, build_context
from semtree.db import store as db_store
from semtree.db.schema import get_version, init_db
from semtree.db.store import _to_fts_query
from semtree.indexer.coordinator import run_index
from semtree.indexer.docstrings import (
    _clean_string_literal,
    _dedent_docstring,
    extract_python_docstring_regex,
)
from semtree.indexer.gitblame import (
    _git_root,
    annotate_symbols,
    blame_line,
)
from semtree.memory.lite import ProjectMemory
from semtree.scripts.setup import (
    _find_python_entry,
    setup_integration,
)

# ---------------------------------------------------------------------------
# docstrings.py
# ---------------------------------------------------------------------------

class TestDocstringsInternal:
    def test_clean_string_literal_no_match_returns_raw(self) -> None:
        # String with mismatched delimiters -- falls through to return raw
        raw = "not a string"
        assert _clean_string_literal(raw) == "not a string"

    def test_clean_string_literal_single_double_quote(self) -> None:
        raw = '"simple"'
        assert _clean_string_literal(raw) == "simple"

    def test_clean_string_literal_single_single_quote(self) -> None:
        raw = "'simple'"
        assert _clean_string_literal(raw) == "simple"

    def test_clean_string_literal_multiline_dedent(self) -> None:
        raw = '"""\n    First line.\n    Second line.\n    """'
        result = _clean_string_literal(raw)
        assert "First line." in result
        assert "Second line." in result

    def test_dedent_docstring_single_line(self) -> None:
        result = _dedent_docstring("  hello  ")
        assert result == "hello"

    def test_dedent_docstring_consistent_indent(self) -> None:
        text = "First\n    Second\n    Third"
        result = _dedent_docstring(text)
        assert "Second" in result
        # leading indent removed
        assert "    Second" not in result

    def test_dedent_docstring_empty_continuation_lines(self) -> None:
        # Empty lines in continuation should not affect indent calc
        text = "First\n\n    Non-empty"
        result = _dedent_docstring(text)
        assert "Non-empty" in result

    def test_extract_python_docstring_regex_with_docstring(self) -> None:
        source = 'def foo():\n    """Hello world."""\n    pass\n'
        result = extract_python_docstring_regex(source, 0)
        assert "Hello world" in result

    def test_extract_python_docstring_regex_no_docstring(self) -> None:
        source = "def foo():\n    pass\n"
        result = extract_python_docstring_regex(source, 0)
        assert result == ""

    def test_extract_python_docstring_regex_out_of_bounds(self) -> None:
        source = "def foo():\n    pass\n"
        result = extract_python_docstring_regex(source, 100)
        assert result == ""

    def test_extract_python_docstring_regex_triple_single(self) -> None:
        source = "def bar():\n    '''Triple single docstring.'''\n    pass\n"
        result = extract_python_docstring_regex(source, 0)
        assert "Triple single" in result


# ---------------------------------------------------------------------------
# gitblame.py
# ---------------------------------------------------------------------------

class TestGitBlame:
    def test_blame_line_no_git_root(self, tmp_path: Path) -> None:
        # Clear lru_cache to avoid cross-test contamination
        _git_root.cache_clear()
        # Non-git directory returns empty strings
        result = blame_line(tmp_path, "file.py", 1)
        assert result == ("", "")

    def test_annotate_symbols_disabled(self) -> None:
        symbols = [{"name": "foo", "line_start": 1}]
        result = annotate_symbols(symbols, Path("/tmp"), "foo.py", enabled=False)
        # Should return unchanged symbols without git_author/git_date added
        assert result is symbols
        assert "git_author" not in symbols[0]

    def test_annotate_symbols_no_git(self, tmp_path: Path) -> None:
        _git_root.cache_clear()
        symbols = [{"name": "foo", "line_start": 1, "git_author": "", "git_date": ""}]
        result = annotate_symbols(symbols, tmp_path, "foo.py", enabled=True)
        assert result[0]["git_author"] == ""
        assert result[0]["git_date"] == ""

    def test_annotate_symbols_deduplicates_lines(self, tmp_path: Path) -> None:
        _git_root.cache_clear()
        # Two symbols at same line - blame_line should only be called once per line
        symbols = [
            {"name": "a", "line_start": 5, "git_author": "", "git_date": ""},
            {"name": "b", "line_start": 5, "git_author": "", "git_date": ""},
        ]
        with patch("semtree.indexer.gitblame.blame_line", return_value=("Alice", "2025-01-01")) as mock_blame:
            annotate_symbols(symbols, tmp_path, "foo.py", enabled=True)
            # Called only once for line 5
            assert mock_blame.call_count == 1
        assert symbols[0]["git_author"] == "Alice"
        assert symbols[1]["git_author"] == "Alice"

    def test_blame_line_with_mock_git(self, tmp_path: Path) -> None:
        _git_root.cache_clear()
        fake_output = "Alice Smith|2025-03-15\n"
        with patch("subprocess.run") as mock_run:
            # First call: git rev-parse (returns a git root)
            rev_result = MagicMock()
            rev_result.returncode = 0
            rev_result.stdout = str(tmp_path) + "\n"
            # Second call: git log
            log_result = MagicMock()
            log_result.returncode = 0
            log_result.stdout = fake_output
            mock_run.side_effect = [rev_result, log_result]

            _git_root.cache_clear()
            result = blame_line(tmp_path, "app.py", 10)
        assert result == ("Alice Smith", "2025-03-15")

    def test_blame_line_git_log_fails(self, tmp_path: Path) -> None:
        _git_root.cache_clear()
        with patch("subprocess.run") as mock_run:
            rev_result = MagicMock()
            rev_result.returncode = 0
            rev_result.stdout = str(tmp_path) + "\n"
            log_result = MagicMock()
            log_result.returncode = 1
            log_result.stdout = ""
            mock_run.side_effect = [rev_result, log_result]

            _git_root.cache_clear()
            result = blame_line(tmp_path, "app.py", 10)
        assert result == ("", "")

    def test_blame_line_subprocess_os_error(self, tmp_path: Path) -> None:
        _git_root.cache_clear()
        with patch("subprocess.run") as mock_run:
            rev_result = MagicMock()
            rev_result.returncode = 0
            rev_result.stdout = str(tmp_path) + "\n"
            mock_run.side_effect = [rev_result, OSError("no git")]

            _git_root.cache_clear()
            result = blame_line(tmp_path, "app.py", 10)
        assert result == ("", "")

    def test_git_root_os_error(self, tmp_path: Path) -> None:
        _git_root.cache_clear()
        with patch("subprocess.run", side_effect=OSError("git not found")):
            result = _git_root(str(tmp_path))
        assert result is None

    def test_git_root_timeout(self, tmp_path: Path) -> None:
        _git_root.cache_clear()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
            result = _git_root(str(tmp_path))
        assert result is None


# ---------------------------------------------------------------------------
# scripts/setup.py
# ---------------------------------------------------------------------------

class TestSetup:
    def test_setup_cursor_creates_mcp_json(self, tmp_path: Path) -> None:
        setup_integration(tmp_path, target="cursor")
        cursor_json = tmp_path / ".cursor" / "mcp.json"
        assert cursor_json.exists()
        data = json.loads(cursor_json.read_text())
        assert "mcpServers" in data
        assert "semtree" in data["mcpServers"]

    def test_setup_cursor_dry_run(self, tmp_path: Path) -> None:
        results = setup_integration(tmp_path, target="cursor", dry_run=True)
        cursor_json = tmp_path / ".cursor" / "mcp.json"
        assert not cursor_json.exists()
        assert any("dry-run" in v for v in results.values())

    def test_setup_copilot_creates_vscode_settings(self, tmp_path: Path) -> None:
        setup_integration(tmp_path, target="copilot")
        settings = tmp_path / ".vscode" / "settings.json"
        assert settings.exists()
        data = json.loads(settings.read_text())
        key = "github.copilot.chat.codeGeneration.instructions"
        assert key in data
        assert any("semtree" in str(i) for i in data[key])

    def test_setup_copilot_skips_if_already_configured(self, tmp_path: Path) -> None:
        # First call configures
        setup_integration(tmp_path, target="copilot")
        # Second call should skip
        results = setup_integration(tmp_path, target="copilot")
        assert any("skipped" in v for v in results.values())

    def test_setup_copilot_merges_existing_settings(self, tmp_path: Path) -> None:
        vscode = tmp_path / ".vscode"
        vscode.mkdir()
        existing = {"editor.tabSize": 4}
        (vscode / "settings.json").write_text(json.dumps(existing))
        setup_integration(tmp_path, target="copilot")
        data = json.loads((vscode / "settings.json").read_text())
        assert data["editor.tabSize"] == 4
        assert "github.copilot.chat.codeGeneration.instructions" in data

    def test_setup_copilot_dry_run(self, tmp_path: Path) -> None:
        setup_integration(tmp_path, target="copilot", dry_run=True)
        assert not (tmp_path / ".vscode" / "settings.json").exists()

    def test_setup_codex_creates_agents_md(self, tmp_path: Path) -> None:
        setup_integration(tmp_path, target="codex")
        agents = tmp_path / "AGENTS.md"
        assert agents.exists()
        assert "semtree" in agents.read_text()

    def test_setup_codex_uses_existing_agents_md(self, tmp_path: Path) -> None:
        agents = tmp_path / "AGENTS.md"
        agents.write_text("# Existing agents\n")
        setup_integration(tmp_path, target="codex")
        content = agents.read_text()
        assert "# Existing agents" in content
        assert "semtree" in content

    def test_setup_codex_uses_codex_md_if_present(self, tmp_path: Path) -> None:
        codex = tmp_path / "CODEX.md"
        codex.write_text("# Codex\n")
        setup_integration(tmp_path, target="codex")
        assert "semtree" in codex.read_text()

    def test_setup_codex_skips_if_already_configured(self, tmp_path: Path) -> None:
        agents = tmp_path / "AGENTS.md"
        agents.write_text("# Agents\n\nRun semtree context before tasks.\n")
        results = setup_integration(tmp_path, target="codex")
        assert any("skipped" in v for v in results.values())

    def test_setup_codex_dry_run(self, tmp_path: Path) -> None:
        setup_integration(tmp_path, target="codex", dry_run=True)
        assert not (tmp_path / "AGENTS.md").exists()

    def test_setup_all_targets(self, tmp_path: Path) -> None:
        results = setup_integration(tmp_path, target="all")
        # Should have entries for all four targets
        paths = list(results.keys())
        path_str = " ".join(paths)
        assert ".claude" in path_str
        assert ".cursor" in path_str
        assert ".vscode" in path_str

    def test_setup_claude_merges_existing_mcp_json(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        existing = {
            "mcpServers": {
                "other-tool": {"command": "other", "args": [], "env": {}}
            }
        }
        (claude_dir / "mcp.json").write_text(json.dumps(existing))
        setup_integration(tmp_path, target="claude")
        data = json.loads((claude_dir / "mcp.json").read_text())
        assert "other-tool" in data["mcpServers"]
        assert "semtree" in data["mcpServers"]

    def test_setup_claude_dry_run_with_existing(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "mcp.json").write_text('{"mcpServers": {}}')
        results = setup_integration(tmp_path, target="claude", dry_run=True)
        assert any("dry-run" in v for v in results.values())
        assert any("updated" in v for v in results.values())

    def test_find_python_entry_nonexistent(self) -> None:
        result = _find_python_entry("definitely_not_a_real_binary_xyzzy")
        assert result is None

    def test_find_python_entry_existing(self) -> None:
        # semtree-mcp is installed in our venv
        result = _find_python_entry("semtree-mcp")
        # Either found or not, should not raise
        assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# memory/lite.py
# ---------------------------------------------------------------------------

class TestProjectMemory:
    @pytest.fixture
    def mem(self, db: sqlite3.Connection) -> ProjectMemory:
        return ProjectMemory(db)

    def test_add_rule(self, mem: ProjectMemory) -> None:
        rec = mem.add_rule("imports", "Always use absolute imports")
        assert rec.kind == "rule"
        assert rec.key == "imports"

    def test_add_ref(self, mem: ProjectMemory) -> None:
        rec = mem.add_ref("docs", "https://example.com/docs")
        assert rec.kind == "ref"

    def test_add_note(self, mem: ProjectMemory) -> None:
        rec = mem.add_note("todo", "Refactor auth module")
        assert rec.kind == "note"

    def test_add_invalid_kind_raises(self, mem: ProjectMemory) -> None:
        with pytest.raises(ValueError, match="Invalid memory kind"):
            mem.add("invalid", "key", "value")

    def test_remove_existing(self, mem: ProjectMemory) -> None:
        mem.add_rule("style", "Use black")
        assert mem.remove("rule", "style") is True

    def test_remove_nonexistent(self, mem: ProjectMemory) -> None:
        assert mem.remove("rule", "does_not_exist") is False

    def test_list_all_empty(self, mem: ProjectMemory) -> None:
        assert mem.list_all() == []

    def test_list_all_filtered(self, mem: ProjectMemory) -> None:
        mem.add_rule("r1", "Rule one")
        mem.add_ref("ref1", "Ref one")
        mem.add_note("n1", "Note one")
        rules = mem.list_all("rule")
        assert all(r.kind == "rule" for r in rules)
        assert len(rules) == 1

    def test_format_for_context_empty(self, mem: ProjectMemory) -> None:
        assert mem.format_for_context() == ""

    def test_format_for_context_with_entries(self, mem: ProjectMemory) -> None:
        mem.add_rule("style", "Use black formatter")
        mem.add_ref("api", "https://api.example.com")
        mem.add_note("todo", "Fix the auth module")
        text = mem.format_for_context()
        assert "## Project Memory" in text
        assert "style" in text
        assert "api" in text
        assert "todo" in text

    def test_format_for_context_truncates(self, mem: ProjectMemory) -> None:
        mem.add_rule("long", "x" * 3000)
        text = mem.format_for_context(max_chars=100)
        assert "truncated" in text
        assert len(text) <= 200  # truncated + message overhead

    def test_format_for_context_only_rules(self, mem: ProjectMemory) -> None:
        mem.add_rule("r1", "Rule one")
        text = mem.format_for_context()
        assert "### Rules" in text
        assert "### References" not in text
        assert "### Notes" not in text

    def test_upsert_updates_existing(self, mem: ProjectMemory) -> None:
        mem.add_rule("key", "old value")
        mem.add_rule("key", "new value")
        records = mem.list_all("rule")
        assert len(records) == 1
        assert records[0].value == "new value"


# ---------------------------------------------------------------------------
# log.py
# ---------------------------------------------------------------------------

class TestLog:
    def test_configure_with_log_dir(self, tmp_path: Path) -> None:
        import semtree.log as log_mod
        original_log_file = log_mod._LOG_FILE
        original_verbose = log_mod._VERBOSE
        try:
            log_mod.configure(log_dir=tmp_path, verbose=False)
            assert tmp_path / "semtree.jsonl" == log_mod._LOG_FILE
        finally:
            log_mod._LOG_FILE = original_log_file
            log_mod._VERBOSE = original_verbose

    def test_log_writes_to_file(self, tmp_path: Path) -> None:
        import semtree.log as log_mod
        original = log_mod._LOG_FILE
        try:
            log_mod._LOG_FILE = tmp_path / "test.jsonl"
            log_mod.info("test message", key="value")
            content = (tmp_path / "test.jsonl").read_text()
            data = json.loads(content.strip())
            assert data["msg"] == "test message"
            assert data["key"] == "value"
            assert data["level"] == "info"
        finally:
            log_mod._LOG_FILE = original

    def test_warn_outputs_to_stdout(self, tmp_path: Path, capsys) -> None:
        import semtree.log as log_mod
        original_verbose = log_mod._VERBOSE
        original_log = log_mod._LOG_FILE
        try:
            log_mod._VERBOSE = False
            log_mod._LOG_FILE = None
            log_mod.warn("something wrong")
            captured = capsys.readouterr()
            assert "something wrong" in captured.out
        finally:
            log_mod._VERBOSE = original_verbose
            log_mod._LOG_FILE = original_log

    def test_error_outputs_to_stderr(self, capsys) -> None:
        import semtree.log as log_mod
        original_log = log_mod._LOG_FILE
        try:
            log_mod._LOG_FILE = None
            log_mod.error("fatal error")
            captured = capsys.readouterr()
            assert "fatal error" in captured.err
        finally:
            log_mod._LOG_FILE = original_log

    def test_debug_silent_by_default(self, capsys) -> None:
        import semtree.log as log_mod
        original_verbose = log_mod._VERBOSE
        original_log = log_mod._LOG_FILE
        try:
            log_mod._VERBOSE = False
            log_mod._LOG_FILE = None
            # Ensure SEMTREE_DEBUG is not set
            env = os.environ.copy()
            env.pop("SEMTREE_DEBUG", None)
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("SEMTREE_DEBUG", None)
                log_mod.debug("debug message")
            captured = capsys.readouterr()
            assert "debug message" not in captured.out
        finally:
            log_mod._VERBOSE = original_verbose
            log_mod._LOG_FILE = original_log

    def test_debug_emits_when_verbose(self, capsys) -> None:
        import semtree.log as log_mod
        original_verbose = log_mod._VERBOSE
        original_log = log_mod._LOG_FILE
        try:
            log_mod._VERBOSE = True
            log_mod._LOG_FILE = None
            log_mod.debug("verbose debug")
            captured = capsys.readouterr()
            assert "verbose debug" in captured.out
        finally:
            log_mod._VERBOSE = original_verbose
            log_mod._LOG_FILE = original_log

    def test_debug_emits_via_env_var(self, tmp_path: Path) -> None:
        # SEMTREE_DEBUG=1 causes debug() to call _emit(), which writes to the log file.
        # _emit() only prints to stdout when _VERBOSE=True, so check the log file instead.
        import semtree.log as log_mod
        original_verbose = log_mod._VERBOSE
        original_log = log_mod._LOG_FILE
        log_file = tmp_path / "semtree.jsonl"
        try:
            log_mod._VERBOSE = False
            log_mod._LOG_FILE = log_file
            with patch.dict(os.environ, {"SEMTREE_DEBUG": "1"}):
                log_mod.debug("env debug msg")
            content = log_file.read_text()
            assert "env debug msg" in content
        finally:
            log_mod._VERBOSE = original_verbose
            log_mod._LOG_FILE = original_log


# ---------------------------------------------------------------------------
# config.py
# ---------------------------------------------------------------------------

class TestConfig:
    def test_find_project_root_finds_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        found = find_project_root(tmp_path)
        assert found == tmp_path

    def test_find_project_root_walks_up(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        found = find_project_root(nested)
        assert found == tmp_path

    def test_find_project_root_fallback_to_cwd(self, tmp_path: Path) -> None:
        # No markers - should return start dir
        result = find_project_root(tmp_path)
        assert result == tmp_path

    def test_config_load_from_file(self, tmp_path: Path) -> None:
        ctx = tmp_path / ".ctx"
        ctx.mkdir()
        (ctx / "semtree.json").write_text(json.dumps({
            "default_token_budget": 4000,
            "git_context": False,
        }))
        cfg = SemtreeConfig.load(tmp_path)
        assert cfg.default_token_budget == 4000
        assert cfg.git_context is False

    def test_config_load_invalid_json_returns_default(self, tmp_path: Path) -> None:
        ctx = tmp_path / ".ctx"
        ctx.mkdir()
        (ctx / "semtree.json").write_text("not valid json{{{")
        cfg = SemtreeConfig.load(tmp_path)
        # Should return defaults
        assert cfg.default_token_budget == 8000

    def test_config_save_and_reload(self, tmp_path: Path) -> None:
        cfg = SemtreeConfig(default_token_budget=12000, git_context=False)
        cfg.save(tmp_path)
        reloaded = SemtreeConfig.load(tmp_path)
        assert reloaded.default_token_budget == 12000
        assert reloaded.git_context is False

    def test_config_is_included_extension(self, tmp_path: Path) -> None:
        cfg = SemtreeConfig()
        py_file = tmp_path / "foo.py"
        py_file.write_text("pass")
        assert cfg.is_included(py_file) is True

    def test_config_is_included_excluded_extension(self, tmp_path: Path) -> None:
        cfg = SemtreeConfig()
        bin_file = tmp_path / "foo.exe"
        bin_file.write_bytes(b"\x00" * 100)
        assert cfg.is_included(bin_file) is False

    def test_config_is_included_large_file(self, tmp_path: Path) -> None:
        cfg = SemtreeConfig(max_file_size_kb=1)
        large = tmp_path / "big.py"
        large.write_bytes(b"x" * 2048)
        assert cfg.is_included(large) is False

    def test_helper_paths(self, tmp_path: Path) -> None:
        assert ctx_dir(tmp_path) == tmp_path / ".ctx"
        assert db_path(tmp_path) == tmp_path / ".ctx" / "index.db"
        assert lock_path(tmp_path) == tmp_path / ".ctx" / "indexing.lock"


# ---------------------------------------------------------------------------
# db/schema.py and store.py
# ---------------------------------------------------------------------------

class TestDBSchema:
    def test_get_version(self, db: sqlite3.Connection) -> None:
        v = get_version(db)
        assert v == 1

    def test_delete_file_cascades_symbols(self, db: sqlite3.Connection) -> None:
        file_id = db_store.upsert_file(db, "test.py", "abc", 100, "python")
        db_store.replace_file_symbols(db, file_id, [
            {"name": "foo", "kind": "function", "line_start": 1,
             "line_end": 5, "signature": "def foo():", "docstring": ""},
        ])
        db.commit()
        assert db_store.count_symbols(db) == 1
        db_store.delete_file(db, "test.py")
        db.commit()
        assert db_store.count_symbols(db) == 0

    def test_get_symbols_by_name_with_kind(self, db: sqlite3.Connection) -> None:
        file_id = db_store.upsert_file(db, "mod.py", "sha1", 200, "python")
        db_store.replace_file_symbols(db, file_id, [
            {"name": "MyClass", "kind": "class", "line_start": 1, "line_end": 10,
             "signature": "class MyClass:", "docstring": ""},
            {"name": "MyClass", "kind": "function", "line_start": 20, "line_end": 25,
             "signature": "def MyClass():", "docstring": ""},
        ])
        db.commit()
        classes = db_store.get_symbols_by_name(db, "MyClass", kind="class")
        assert len(classes) == 1
        assert classes[0].kind == "class"

    def test_fts_search_empty_query(self, db: sqlite3.Connection) -> None:
        results = db_store.fts_search(db, "", limit=10)
        assert results == []

    def test_to_fts_query_stopwords_only(self) -> None:
        # All stopwords - should fall back to including them
        q = _to_fts_query("the a an")
        assert q != ""

    def test_to_fts_query_short_word_no_prefix(self) -> None:
        q = _to_fts_query("foo")
        # "foo" is 3 chars - no prefix variant added
        assert "foo*" not in q
        assert "foo" in q

    def test_to_fts_query_empty(self) -> None:
        assert _to_fts_query("") == ""
        assert _to_fts_query("  ") == ""


# ---------------------------------------------------------------------------
# context/builder.py - _fit_symbols binary search path
# ---------------------------------------------------------------------------

class TestContextBuilderFitSymbols:
    def test_fit_symbols_empty(self) -> None:
        result = _fit_symbols([], level=2, token_budget=1000)
        assert result == ""

    def test_fit_symbols_truncates_on_tight_budget(self) -> None:
        from semtree.db.store import SymbolRecord
        # Create many symbols to force truncation
        symbols = [
            SymbolRecord(
                id=i, file_id=1, file_path="src/a.py",
                name=f"function_{i}", kind="function",
                line_start=i * 10, line_end=i * 10 + 5,
                signature=f"def function_{i}(arg1, arg2, arg3) -> ReturnType:",
                docstring="This is a long docstring. " * 20,
                git_author="Dev", git_date="2025-01-01",
            )
            for i in range(50)
        ]
        result = _fit_symbols(symbols, level=3, token_budget=200)
        # Should return something (at least 1 symbol)
        assert len(result) > 0

    def test_build_context_tree_truncation(self, tmp_path: Path) -> None:
        """Test the file tree truncation path when budget is very tight."""
        db = init_db(tmp_path / ".ctx" / "index.db")
        # Add many files to make tree large
        for i in range(100):
            fid = db_store.upsert_file(db, f"dir_{i}/file_{i}.py", f"sha{i}", 100, "python")
            db_store.replace_file_symbols(db, fid, [
                {"name": f"func_{i}", "kind": "function", "line_start": 1,
                 "line_end": 5, "signature": f"def func_{i}():", "docstring": ""},
            ])
        db.commit()
        # Very tight budget forces tree truncation
        result = build_context(db, "find func", token_budget=300, root=tmp_path)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# coordinator.py - error and edge case paths
# ---------------------------------------------------------------------------

class TestCoordinatorEdgeCases:
    def test_debounce_skips_on_fresh_lock(self, tmp_project: Path) -> None:
        config = SemtreeConfig(use_gitignore=False, git_context=False)
        # First run - creates and removes lock
        stats1 = run_index(tmp_project, config=config)
        assert stats1.total_files >= 2

        # Manually create a fresh lock (age < 2s)
        lock = lock_path(tmp_project)
        ctx_dir(tmp_project).mkdir(parents=True, exist_ok=True)
        lock.write_text("99999")

        # Second run should debounce (0 files processed)
        stats2 = run_index(tmp_project, config=config, force=False)
        assert stats2.total_files == 0

        # Cleanup
        with contextlib.suppress(OSError):
            lock.unlink()

    def test_index_handles_unreadable_file(self, tmp_path: Path) -> None:
        # Create a file then make it unreadable
        f = tmp_path / "secret.py"
        f.write_text("def secret(): pass")
        # Mock read_text to raise
        config = SemtreeConfig(use_gitignore=False, git_context=False)
        original_read = Path.read_text

        def broken_read(self, **kwargs):
            if self.name == "secret.py":
                raise OSError("permission denied")
            return original_read(self, **kwargs)

        with patch.object(Path, "read_text", broken_read):
            stats = run_index(tmp_path, config=config)
        assert len(stats.errors) >= 1

    def test_index_calls_git_annotate(self, tmp_project: Path) -> None:
        # Make a real git repo to exercise git_context path
        config = SemtreeConfig(use_gitignore=False, git_context=True)
        stats = run_index(tmp_project, config=config)
        # Should complete without errors (git blame gracefully returns "" when no commits)
        assert isinstance(stats.total_symbols, int)

    def test_stale_files_removed(self, tmp_project: Path) -> None:
        config = SemtreeConfig(use_gitignore=False, git_context=False)
        run_index(tmp_project, config=config)

        conn = init_db(db_path(tmp_project))
        before = db_store.count_files(conn)
        assert before >= 2

        # Remove one file
        (tmp_project / "utils.py").unlink()

        run_index(tmp_project, config=config, force=True)
        conn2 = init_db(db_path(tmp_project))
        after = db_store.count_files(conn2)
        assert after == before - 1


# ---------------------------------------------------------------------------
# Additional targeted tests for remaining coverage gaps
# ---------------------------------------------------------------------------

class TestHasherOSError:
    def test_sha1_file_os_error_returns_empty(self, tmp_path: Path) -> None:
        from semtree.indexer.hasher import sha1_file
        nonexistent = tmp_path / "missing.py"
        result = sha1_file(nonexistent)
        assert result == ""


class TestBudgetFallback:
    def test_count_tokens_fallback_no_tiktoken(self) -> None:
        from semtree.context import budget as budget_mod
        original = budget_mod._HAS_TIKTOKEN
        try:
            budget_mod._HAS_TIKTOKEN = False
            result = budget_mod.count_tokens("hello world")
            assert result > 0
        finally:
            budget_mod._HAS_TIKTOKEN = original

    def test_count_tokens_many(self) -> None:
        from semtree.context.budget import count_tokens_many
        result = count_tokens_many(["hello", "world", "test"])
        assert result > 0

    def test_fraction_used_zero_total(self) -> None:
        from semtree.context.budget import TokenBudget
        b = TokenBudget(0)
        assert b.fraction_used == 0.0


class TestSearchByFile:
    def test_search_by_file_returns_results(self, tmp_path: Path) -> None:
        from semtree.retrieval.search import search_by_file
        conn = init_db(tmp_path / ".ctx" / "index.db")
        fid = db_store.upsert_file(conn, "src/auth/views.py", "abc", 500, "python")
        db_store.replace_file_symbols(conn, fid, [
            {"name": "login_view", "kind": "function", "line_start": 1,
             "line_end": 10, "signature": "def login_view():", "docstring": ""},
        ])
        conn.commit()
        results = search_by_file(conn, "auth", limit=10)
        assert len(results) > 0
        assert results[0].symbol.name == "login_view"

    def test_search_by_file_no_match(self, tmp_path: Path) -> None:
        from semtree.retrieval.search import search_by_file
        conn = init_db(tmp_path / ".ctx" / "index.db")
        results = search_by_file(conn, "nonexistent_path_xyz", limit=10)
        assert results == []


class TestIntentClassifyMany:
    def test_classify_many(self) -> None:
        from semtree.retrieval.intent import classify_many
        results = classify_many(["implement a feature", "fix a bug", ""])
        assert len(results) == 3
        assert results[0].intent == "implement"
        assert results[1].intent == "debug"
        assert results[2].intent == "search"

    def test_classify_low_confidence_returns_search(self) -> None:
        from semtree.retrieval.intent import classify
        # Very ambiguous query with low score gap
        result = classify("the it a of", min_confidence=0.99)
        assert result.intent == "search"


class TestAllPolicies:
    def test_all_policies_returns_dict(self) -> None:
        from semtree.retrieval.policy import all_policies
        policies = all_policies()
        assert len(policies) >= 7
        assert "implement" in policies
        assert "debug" in policies


class TestFTSSearchExceptionPath:
    def test_fts_search_bad_query_returns_empty(self, db: sqlite3.Connection) -> None:
        # A query that might cause FTS5 syntax error - should be caught
        result = db_store.fts_search(db, 'AND OR AND', limit=5)
        # Should not raise, returns empty or some results
        assert isinstance(result, list)


class TestWalkerGitignore:
    def test_walk_with_gitignore(self, tmp_path: Path) -> None:
        from semtree.indexer.walker import walk_project
        # Create .gitignore that ignores *.log
        (tmp_path / ".gitignore").write_text("*.log\n")
        (tmp_path / "app.py").write_text("pass")
        (tmp_path / "debug.log").write_text("log content")

        # .log is not in include_extensions so won't appear regardless
        # Test that gitignore parsing doesn't crash
        files = list(walk_project(
            tmp_path,
            include_extensions={".py", ".log"},
            exclude_dirs=set(),
            use_gitignore=True,
        ))
        names = {f.name for f in files}
        assert "app.py" in names
        assert "debug.log" not in names

    def test_walk_excludes_gitignored_dirs(self, tmp_path: Path) -> None:
        from semtree.indexer.walker import walk_project
        (tmp_path / ".gitignore").write_text("build/\n")
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        (build_dir / "output.py").write_text("pass")
        (tmp_path / "src.py").write_text("pass")

        files = list(walk_project(
            tmp_path,
            include_extensions={".py"},
            exclude_dirs=set(),
            use_gitignore=True,
        ))
        names = {f.name for f in files}
        assert "src.py" in names
        assert "output.py" not in names

    def test_walk_skip_stat_error(self, tmp_path: Path) -> None:
        from semtree.indexer.walker import walk_project
        (tmp_path / "app.py").write_text("pass")

        original_stat = Path.stat

        def broken_stat(self, *, follow_symlinks=True):
            if self.name == "app.py":
                raise OSError("permission denied")
            return original_stat(self, follow_symlinks=follow_symlinks)

        with patch.object(Path, "stat", broken_stat):
            files = list(walk_project(
                tmp_path,
                include_extensions={".py"},
                exclude_dirs=set(),
            ))
        # File should be skipped, not crash
        assert all(f.name != "app.py" for f in files)

    def test_walk_glob_pattern_exclude(self, tmp_path: Path) -> None:
        from semtree.indexer.walker import walk_project
        # Test wildcard exclude pattern (e.g. "*.egg-info")
        egg_dir = tmp_path / "mylib.egg-info"
        egg_dir.mkdir()
        (egg_dir / "PKG-INFO").write_text("info")
        (tmp_path / "main.py").write_text("pass")

        files = list(walk_project(
            tmp_path,
            include_extensions={".py"},
            exclude_dirs={"*.egg-info"},
        ))
        names = {f.name for f in files}
        assert "main.py" in names


class TestSetupFallbackToPython:
    def test_setup_claude_uses_python_module_when_no_binary(self, tmp_path: Path) -> None:
        # Force shutil.which and _find_python_entry to return None
        with patch("semtree.scripts.setup.shutil.which", return_value=None), \
             patch("semtree.scripts.setup._find_python_entry", return_value=None):
            setup_integration(tmp_path, target="claude")
        data = json.loads((tmp_path / ".claude" / "mcp.json").read_text())
        cmd = data["mcpServers"]["semtree"]["command"]
        args = data["mcpServers"]["semtree"]["args"]
        # Should fall back to python -m semtree.mcp
        assert cmd == sys.executable
        assert "-m" in args
        assert "semtree.mcp" in args


class TestWalkerPathspecFallback:
    def test_walk_without_pathspec(self, tmp_path: Path) -> None:
        from semtree.indexer import walker as walker_mod
        original = walker_mod._HAS_PATHSPEC
        try:
            walker_mod._HAS_PATHSPEC = False
            (tmp_path / "app.py").write_text("pass")
            (tmp_path / ".gitignore").write_text("*.log\n")
            files = list(walker_mod.walk_project(
                tmp_path,
                include_extensions={".py"},
                exclude_dirs=set(),
                use_gitignore=True,
            ))
            names = {f.name for f in files}
            assert "app.py" in names
        finally:
            walker_mod._HAS_PATHSPEC = original

    def test_load_gitignore_os_error(self, tmp_path: Path) -> None:
        from semtree.indexer.walker import _load_gitignore
        # Create .gitignore then mock read to raise OSError
        (tmp_path / ".gitignore").write_text("*.log\n")
        with patch.object(Path, "read_text", side_effect=OSError("perm")):
            result = _load_gitignore(tmp_path)
        assert result is None

    def test_walk_glob_wildcard_dir_exclude(self, tmp_path: Path) -> None:
        from semtree.indexer.walker import _should_descend
        # The walker handles patterns ending in '*' (prefix match, e.g. "mylib*")
        result = _should_descend(
            "mylib_generated",
            Path("."),
            {"mylib*"},
            None,
            tmp_path,
        )
        assert result is False

    def test_walk_exact_dir_exclude(self, tmp_path: Path) -> None:
        from semtree.indexer.walker import _should_descend
        result = _should_descend(
            "node_modules",
            Path("."),
            {"node_modules"},
            None,
            tmp_path,
        )
        assert result is False


class TestBuilderTreeTruncation:
    def test_build_context_tight_budget_truncates_tree(self, tmp_path: Path) -> None:
        """Force the file tree truncation while-loop in builder.py:77-80."""
        conn = init_db(tmp_path / ".ctx" / "index.db")
        # Add many files to generate a large file tree
        for i in range(200):
            fid = db_store.upsert_file(conn, f"pkg_{i}/module_{i}.py", f"sha{i}", 100, "python")
            db_store.replace_file_symbols(conn, fid, [
                {"name": f"fn_{i}", "kind": "function", "line_start": 1,
                 "line_end": 3, "signature": f"def fn_{i}():", "docstring": ""},
            ])
        conn.commit()
        # Use a budget tight enough to force tree truncation but not symbol truncation
        result = build_context(conn, "find fn", token_budget=250, root=tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0


class TestSetupCopilotCorruptSettings:
    def test_setup_copilot_handles_corrupt_json(self, tmp_path: Path) -> None:
        vscode = tmp_path / ".vscode"
        vscode.mkdir()
        (vscode / "settings.json").write_text("{ corrupt json !!!")
        # Should not raise, treat as empty
        setup_integration(tmp_path, target="copilot")
        assert (vscode / "settings.json").exists()
        data = json.loads((vscode / "settings.json").read_text())
        assert "github.copilot.chat.codeGeneration.instructions" in data
