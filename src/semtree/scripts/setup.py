"""Integration setup for Claude Code, Cursor, Copilot, and Codex.

Creates the selected project config files when running `semtree setup`.

Supports --dry-run to preview changes without writing.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Literal

IntegrationTarget = Literal["claude", "cursor", "copilot", "codex", "all"]


def _write_json_atomically(path: Path, value: dict) -> bool:
    """Replace a JSON file without exposing a truncated intermediate state."""
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(value, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
        return True
    except OSError:
        return False
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)


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
        if any(action.startswith("error") for action in result.values()):
            return results

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
    """Create or update the project-scoped Claude Code ``.mcp.json``."""
    mcp_json = root / ".mcp.json"

    config: dict = {
        "mcpServers": {
            "semtree": {
                "command": "semtree-mcp",
                "args": [],
            }
        }
    }

    target_str = str(mcp_json)
    if mcp_json.is_symlink():
        return {target_str: "error (invalid existing config; unchanged)"}
    if mcp_json.exists():
        try:
            existing = json.loads(mcp_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeError):
            return {target_str: "error (invalid existing config; unchanged)"}
        if not isinstance(existing, dict):
            return {target_str: "error (invalid existing config; unchanged)"}
        servers = existing.get("mcpServers", {})
        if not isinstance(servers, dict):
            return {target_str: "error (invalid existing config; unchanged)"}
        final_config = dict(existing)
        final_config["mcpServers"] = {
            **servers,
            "semtree": config["mcpServers"]["semtree"],
        }
        action = "updated"
    else:
        final_config = config
        action = "created"

    if dry_run:
        return {target_str: f"[dry-run] would be {action}"}

    if not _write_json_atomically(mcp_json, final_config):
        return {target_str: "error (write failed; unchanged)"}
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
        "text": f'When given a task, first run: {semtree_bin} context "${{input}}" to load structural context.'
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

    snippet = '\n\n## Code Context\n\nRun `semtree context "<task description>"` before implementing any task to get relevant code context.\n'
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
