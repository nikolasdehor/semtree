"""Integration setup for Claude Code, Cursor, Copilot, and Codex.

Creates necessary config files (e.g., .claude/mcp.json) automatically
when running `semtree setup --auto`.

Supports --dry-run to preview changes without writing.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Literal


IntegrationTarget = Literal["claude", "cursor", "copilot", "codex", "all"]


def setup_integration(
    root: Path,
    target: IntegrationTarget = "all",
    dry_run: bool = False,
    host: str = "127.0.0.1",
    port: int = 5137,
) -> dict[str, str]:
    """Set up semtree integration for the specified AI assistant.

    Returns a dict of {file_path: "created"|"updated"|"skipped"|"error"}.
    """
    results: dict[str, str] = {}

    if target in ("claude", "all"):
        result = _setup_claude(root, dry_run=dry_run, host=host, port=port)
        results.update(result)

    if target in ("cursor", "all"):
        result = _setup_cursor(root, dry_run=dry_run, host=host, port=port)
        results.update(result)

    if target in ("copilot", "all"):
        result = _setup_copilot(root, dry_run=dry_run)
        results.update(result)

    if target in ("codex", "all"):
        result = _setup_codex(root, dry_run=dry_run)
        results.update(result)

    return results


def _setup_claude(
    root: Path,
    dry_run: bool,
    host: str,
    port: int,
) -> dict[str, str]:
    """Create .claude/mcp.json with the semtree MCP server config."""
    claude_dir = root / ".claude"
    mcp_json = claude_dir / "mcp.json"

    # Find semtree-mcp binary
    mcp_binary = shutil.which("semtree-mcp") or _find_python_entry("semtree-mcp")
    if mcp_binary is None:
        # Fall back to module invocation
        python = sys.executable
        mcp_cmd = [python, "-m", "semtree.mcp"]
    else:
        mcp_cmd = [mcp_binary]

    config: dict = {
        "mcpServers": {
            "semtree": {
                "command": mcp_cmd[0],
                "args": mcp_cmd[1:] if len(mcp_cmd) > 1 else [],
                "env": {
                    "SEMTREE_ROOT": str(root),
                },
            }
        }
    }

    # Merge with existing config if present
    existing: dict = {}
    if mcp_json.exists():
        try:
            existing = json.loads(mcp_json.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    if existing:
        # Merge mcpServers section
        servers = existing.get("mcpServers", {})
        servers["semtree"] = config["mcpServers"]["semtree"]
        existing["mcpServers"] = servers
        final_config = existing
        action = "updated"
    else:
        final_config = config
        action = "created"

    target_str = str(mcp_json)
    if dry_run:
        return {target_str: f"[dry-run] would be {action}"}

    claude_dir.mkdir(parents=True, exist_ok=True)
    mcp_json.write_text(json.dumps(final_config, indent=2) + "\n")
    return {target_str: action}


def _setup_cursor(
    root: Path,
    dry_run: bool,
    host: str,
    port: int,
) -> dict[str, str]:
    """Create/update .cursor/mcp.json for Cursor IDE."""
    cursor_dir = root / ".cursor"
    mcp_json = cursor_dir / "mcp.json"

    mcp_binary = shutil.which("semtree-mcp") or _find_python_entry("semtree-mcp")
    mcp_cmd = [mcp_binary] if mcp_binary else [sys.executable, "-m", "semtree.mcp"]

    config: dict = {
        "mcpServers": {
            "semtree": {
                "command": mcp_cmd[0],
                "args": mcp_cmd[1:] if len(mcp_cmd) > 1 else [],
                "env": {"SEMTREE_ROOT": str(root)},
            }
        }
    }

    target_str = str(mcp_json)
    if dry_run:
        return {target_str: "[dry-run] would be created"}

    cursor_dir.mkdir(parents=True, exist_ok=True)
    mcp_json.write_text(json.dumps(config, indent=2) + "\n")
    return {target_str: "created"}


def _setup_copilot(root: Path, dry_run: bool) -> dict[str, str]:
    """Add semtree context command to .vscode/settings.json for Copilot."""
    vscode_dir = root / ".vscode"
    settings_json = vscode_dir / "settings.json"

    semtree_bin = shutil.which("semtree") or "semtree"
    copilot_key = "github.copilot.chat.codeGeneration.instructions"
    new_instruction = {
        "text": f"When given a task, first run: {semtree_bin} context \"${{input}}\" to load semantic context."
    }

    target_str = str(settings_json)
    if dry_run:
        return {target_str: "[dry-run] would add Copilot instructions"}

    existing: dict = {}
    if settings_json.exists():
        try:
            existing = json.loads(settings_json.read_text())
        except (json.JSONDecodeError, OSError):
            existing = {}

    instructions = existing.get(copilot_key, [])
    # Avoid duplicate
    if not any("semtree" in str(i) for i in instructions):
        instructions.append(new_instruction)
        existing[copilot_key] = instructions
        vscode_dir.mkdir(parents=True, exist_ok=True)
        settings_json.write_text(json.dumps(existing, indent=2) + "\n")
        return {target_str: "updated"}

    return {target_str: "skipped (already configured)"}


def _setup_codex(root: Path, dry_run: bool) -> dict[str, str]:
    """Add semtree to AGENTS.md or CODEX.md for Codex auto-context."""
    candidates = [root / "AGENTS.md", root / "CODEX.md"]
    target_file = None
    for c in candidates:
        if c.exists():
            target_file = c
            break
    if target_file is None:
        target_file = root / "AGENTS.md"

    snippet = "\n\n## Code Context\n\nRun `semtree context \"<task description>\"` before implementing any task to get relevant code context.\n"
    target_str = str(target_file)

    if dry_run:
        return {target_str: "[dry-run] would append semtree context instructions"}

    if target_file.exists():
        content = target_file.read_text()
        if "semtree" in content:
            return {target_str: "skipped (already configured)"}
        target_file.write_text(content + snippet)
        return {target_str: "updated"}

    target_file.write_text(f"# Agents\n{snippet}")
    return {target_str: "created"}


def _find_python_entry(name: str) -> str | None:
    """Find a pip-installed entry point script."""
    # Check common locations relative to current Python
    python_dir = Path(sys.executable).parent
    for candidate in [python_dir / name, python_dir / f"{name}.exe"]:
        if candidate.exists():
            return str(candidate)
    return None
