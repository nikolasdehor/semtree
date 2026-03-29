"""Project root detection and configuration management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Markers that indicate a project root directory
_ROOT_MARKERS = [
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    ".git",
    ".hg",
    ".svn",
]

_CTX_DIR = ".ctx"
_CONFIG_FILE = "semtree.json"


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (default: cwd) until a root marker is found.

    Falls back to cwd if no marker is found within 10 levels.
    """
    current = (start or Path.cwd()).resolve()
    for _ in range(10):
        for marker in _ROOT_MARKERS:
            if (current / marker).exists():
                return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return (start or Path.cwd()).resolve()


def ctx_dir(root: Path) -> Path:
    """Return the .ctx directory path for a project root."""
    return root / _CTX_DIR


def db_path(root: Path) -> Path:
    """Return the SQLite database path."""
    return ctx_dir(root) / "index.db"


def config_path(root: Path) -> Path:
    """Return the semtree config file path."""
    return ctx_dir(root) / _CONFIG_FILE


def lock_path(root: Path) -> Path:
    """Return the indexing lock file path."""
    return ctx_dir(root) / "indexing.lock"


@dataclass
class SemtreeConfig:
    """Project-level configuration for semtree."""

    # Indexing
    include_extensions: list[str] = field(default_factory=lambda: [
        ".py", ".js", ".ts", ".tsx", ".jsx",
        ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
        ".rb", ".php", ".swift", ".kt", ".cs",
        ".md", ".txt", ".yaml", ".yml", ".toml", ".json",
    ])
    exclude_dirs: list[str] = field(default_factory=lambda: [
        ".git", ".hg", ".svn", "node_modules", "__pycache__",
        ".venv", "venv", "env", ".env", "dist", "build",
        "target", ".ctx", ".idea", ".vscode", "*.egg-info",
        "coverage", ".coverage", "htmlcov",
    ])
    max_file_size_kb: int = 512
    use_gitignore: bool = True

    # Context
    default_token_budget: int = 8000
    git_context: bool = True

    # MCP
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 5137

    @classmethod
    def load(cls, root: Path) -> SemtreeConfig:
        """Load config from .ctx/semtree.json, merging with defaults."""
        path = config_path(root)
        if not path.exists():
            return cls()
        try:
            data: dict[str, Any] = json.loads(path.read_text())
            cfg = cls()
            for key, value in data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)
            return cfg
        except (json.JSONDecodeError, OSError):
            return cls()

    def save(self, root: Path) -> None:
        """Write config to .ctx/semtree.json."""
        ctx_dir(root).mkdir(parents=True, exist_ok=True)
        data = {
            "include_extensions": self.include_extensions,
            "exclude_dirs": self.exclude_dirs,
            "max_file_size_kb": self.max_file_size_kb,
            "use_gitignore": self.use_gitignore,
            "default_token_budget": self.default_token_budget,
            "git_context": self.git_context,
            "mcp_host": self.mcp_host,
            "mcp_port": self.mcp_port,
        }
        config_path(root).write_text(json.dumps(data, indent=2))

    def is_included(self, path: Path) -> bool:
        """Return True if the file at path should be indexed."""
        if path.suffix not in self.include_extensions:
            return False
        size_kb = path.stat().st_size / 1024
        return not size_kb > self.max_file_size_kb
