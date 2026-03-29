"""End-to-end integration tests.

Tests the full pipeline: index -> search -> context -> CLI.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from semtree.cli import main
from semtree.indexer.coordinator import run_index
from semtree.config import SemtreeConfig, db_path
from semtree.db.schema import init_db
from semtree.db import store as db_store
from semtree.context.builder import build_context
from semtree.memory.lite import ProjectMemory


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_index_then_search(self, tmp_project: Path) -> None:
        config = SemtreeConfig(use_gitignore=False, git_context=False)
        stats = run_index(tmp_project, config=config)
        assert stats.total_symbols > 0

        conn = init_db(db_path(tmp_project))
        from semtree.retrieval.search import search
        results = search(conn, "greet", limit=10)
        assert len(results) > 0

    def test_index_then_context(self, tmp_project: Path) -> None:
        config = SemtreeConfig(use_gitignore=False, git_context=False)
        run_index(tmp_project, config=config)

        conn = init_db(db_path(tmp_project))
        ctx = build_context(conn, "implement greeting feature", token_budget=4000)
        assert "semtree" in ctx.lower()

    def test_memory_persists_across_index(self, tmp_project: Path) -> None:
        config = SemtreeConfig(use_gitignore=False, git_context=False)
        run_index(tmp_project, config=config)

        conn = init_db(db_path(tmp_project))
        mem = ProjectMemory(conn)
        mem.add_rule("imports", "Always use absolute imports")

        # Re-index
        run_index(tmp_project, config=config, force=True)

        # Memory should still be there
        conn2 = init_db(db_path(tmp_project))
        mem2 = ProjectMemory(conn2)
        rules = mem2.list_all("rule")
        assert any(r.key == "imports" for r in rules)


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

class TestCLI:
    def test_index_command(self, tmp_project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--root", str(tmp_project), "index", "--quiet"])
        assert result.exit_code == 0
        assert "Done" in result.output

    def test_status_command_after_index(self, tmp_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(main, ["--root", str(tmp_project), "index", "--quiet"])
        result = runner.invoke(main, ["--root", str(tmp_project), "status"])
        assert result.exit_code == 0
        assert "Files:" in result.output
        assert "Symbols:" in result.output

    def test_status_command_no_index(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--root", str(tmp_path), "status"])
        assert result.exit_code == 0
        assert "No index found" in result.output

    def test_search_command(self, tmp_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(main, ["--root", str(tmp_project), "index", "--quiet"])
        result = runner.invoke(main, ["--root", str(tmp_project), "search", "greet"])
        assert result.exit_code == 0

    def test_search_command_json(self, tmp_project: Path) -> None:
        import json
        runner = CliRunner()
        runner.invoke(main, ["--root", str(tmp_project), "index", "--quiet"])
        result = runner.invoke(main, ["--root", str(tmp_project), "search", "--json", "greet"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_context_command(self, tmp_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(main, ["--root", str(tmp_project), "index", "--quiet"])
        result = runner.invoke(main, ["--root", str(tmp_project), "context", "implement greeting"])
        assert result.exit_code == 0
        assert "semtree" in result.output.lower()

    def test_memory_add_list_remove(self, tmp_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(main, ["--root", str(tmp_project), "index", "--quiet"])

        result = runner.invoke(
            main, ["--root", str(tmp_project), "memory", "add", "rule", "style", "Use black formatter"]
        )
        assert result.exit_code == 0

        result = runner.invoke(main, ["--root", str(tmp_project), "memory", "list"])
        assert result.exit_code == 0
        assert "style" in result.output

        result = runner.invoke(
            main, ["--root", str(tmp_project), "memory", "remove", "rule", "style"]
        )
        assert result.exit_code == 0

        result = runner.invoke(main, ["--root", str(tmp_project), "memory", "list"])
        assert "style" not in result.output

    def test_config_show(self, tmp_project: Path) -> None:
        import json
        runner = CliRunner()
        result = runner.invoke(main, ["--root", str(tmp_project), "config"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "root" in data
        assert "include_extensions" in data

    def test_setup_dry_run(self, tmp_project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main, ["--root", str(tmp_project), "setup", "--target", "claude", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "dry-run" in result.output

    def test_setup_claude_creates_mcp_json(self, tmp_project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main, ["--root", str(tmp_project), "setup", "--target", "claude"]
        )
        assert result.exit_code == 0
        mcp_json = tmp_project / ".claude" / "mcp.json"
        assert mcp_json.exists()
        import json
        data = json.loads(mcp_json.read_text())
        assert "mcpServers" in data
        assert "semtree" in data["mcpServers"]

    def test_version_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
