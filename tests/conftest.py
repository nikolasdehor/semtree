"""Shared pytest fixtures for semtree tests."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from semtree.db.schema import init_db
from semtree.config import SemtreeConfig


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """A temporary directory with a few source files for testing."""
    (tmp_path / "main.py").write_text(
        '''"""Main module."""

def greet(name: str) -> str:
    """Return a greeting string."""
    return f"Hello, {name}!"

class Greeter:
    """A class that greets people."""

    def hello(self, name: str) -> str:
        """Say hello."""
        return greet(name)
'''
    )
    (tmp_path / "utils.py").write_text(
        '''"""Utility functions."""

def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b

MAX_VALUE = 1000
'''
    )
    (tmp_path / "README.md").write_text("# Test Project\n")
    return tmp_path


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    """An initialized in-memory-backed SQLite connection for tests."""
    db_path = tmp_path / ".ctx" / "index.db"
    return init_db(db_path)


@pytest.fixture
def config() -> SemtreeConfig:
    """Default configuration instance."""
    return SemtreeConfig()
