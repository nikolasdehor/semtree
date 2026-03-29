"""Tests for context assembly: budget, levels, builder."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from semtree.context.budget import TokenBudget, count_tokens, fits_in_budget
from semtree.context.builder import build_context, build_context_for_file
from semtree.context.levels import format_by_level, format_l1, format_l2, format_l3
from semtree.db import store as db_store
from semtree.db.schema import init_db
from semtree.db.store import SymbolRecord

# ---------------------------------------------------------------------------
# Budget tests
# ---------------------------------------------------------------------------

class TestTokenBudget:
    def test_count_tokens_nonempty(self) -> None:
        n = count_tokens("hello world")
        assert n > 0

    def test_count_tokens_empty(self) -> None:
        assert count_tokens("") == 0

    def test_fits_in_budget_true(self) -> None:
        assert fits_in_budget("hi", 1000) is True

    def test_fits_in_budget_false(self) -> None:
        long_text = "word " * 10000
        assert fits_in_budget(long_text, 10) is False

    def test_budget_consume(self) -> None:
        b = TokenBudget(1000)
        b.consume("hello world")
        assert b.used > 0
        assert b.remaining < 1000

    def test_budget_try_consume_success(self) -> None:
        b = TokenBudget(1000)
        result = b.try_consume("short text")
        assert result is True
        assert b.used > 0

    def test_budget_try_consume_failure(self) -> None:
        b = TokenBudget(1)
        result = b.try_consume("this is definitely longer than 1 token")
        assert result is False
        assert b.used == 0

    def test_budget_repr(self) -> None:
        b = TokenBudget(500)
        assert "500" in repr(b)

    def test_budget_reset(self) -> None:
        b = TokenBudget(1000)
        b.consume("hello")
        b.reset()
        assert b.used == 0


# ---------------------------------------------------------------------------
# Level formatter tests
# ---------------------------------------------------------------------------

def _make_symbols() -> list[SymbolRecord]:
    return [
        SymbolRecord(
            id=1, file_id=1, file_path="src/auth.py",
            name="login", kind="function",
            line_start=10, line_end=25,
            signature="def login(username: str) -> bool:",
            docstring="Authenticate a user by username.",
            git_author="Alice", git_date="2025-01-15",
        ),
        SymbolRecord(
            id=2, file_id=1, file_path="src/auth.py",
            name="UserManager", kind="class",
            line_start=30, line_end=80,
            signature="class UserManager:",
            docstring="Manages user creation and deletion.\n\nThreadsafe.",
            git_author="Bob", git_date="2025-01-10",
        ),
    ]


class TestLevels:
    def test_l1_contains_names(self) -> None:
        text = format_l1(_make_symbols())
        assert "login" in text
        assert "UserManager" in text
        assert "function" in text.lower() or "[function]" in text

    def test_l2_contains_signatures(self) -> None:
        text = format_l2(_make_symbols())
        assert "def login(username: str)" in text
        assert "Authenticate a user" in text

    def test_l3_contains_full_docstring(self) -> None:
        text = format_l3(_make_symbols())
        assert "Manages user creation" in text
        assert "Threadsafe" in text
        assert "Alice" in text

    def test_l3_contains_git_context(self) -> None:
        text = format_l3(_make_symbols())
        assert "Alice" in text
        assert "2025-01-15" in text

    def test_level_0_fallback(self) -> None:
        text = format_by_level(_make_symbols(), level=0)
        assert "login" in text

    def test_empty_symbols_returns_empty(self) -> None:
        for level in range(4):
            assert format_by_level([], level) == ""


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------

@pytest.fixture
def builder_db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / ".ctx" / "index.db"
    conn = init_db(db_path)

    file_id = db_store.upsert_file(conn, "app/views.py", "sha1abc", 2000, "python")
    db_store.replace_file_symbols(conn, file_id, [
        {
            "name": "create_user",
            "kind": "function",
            "line_start": 15,
            "line_end": 35,
            "signature": "def create_user(name: str, email: str) -> User:",
            "docstring": "Create a new user in the database.",
            "git_author": "Dev",
            "git_date": "2025-02-01",
        },
        {
            "name": "UserView",
            "kind": "class",
            "line_start": 40,
            "line_end": 100,
            "signature": "class UserView(APIView):",
            "docstring": "REST API view for user management.",
            "git_author": "Dev",
            "git_date": "2025-02-01",
        },
    ])
    conn.commit()
    return conn


class TestBuilder:
    def test_build_context_returns_string(self, builder_db: sqlite3.Connection) -> None:
        result = build_context(builder_db, "implement user registration", token_budget=4000)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_context_contains_header(self, builder_db: sqlite3.Connection) -> None:
        result = build_context(builder_db, "implement user registration", token_budget=4000)
        assert "semtree" in result.lower()

    def test_build_context_contains_symbol(self, builder_db: sqlite3.Connection) -> None:
        result = build_context(builder_db, "create user", token_budget=4000)
        assert "create_user" in result or "UserView" in result

    def test_build_context_respects_budget(self, builder_db: sqlite3.Connection) -> None:
        from semtree.context.budget import count_tokens
        result = build_context(builder_db, "test query", token_budget=500)
        # Should not massively exceed the budget
        assert count_tokens(result) < 1000  # allow some overhead

    def test_build_context_for_file(self, builder_db: sqlite3.Connection) -> None:
        result = build_context_for_file(builder_db, "app/views.py", token_budget=4000)
        assert "create_user" in result
        assert "UserView" in result

    def test_build_context_empty_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / ".ctx" / "empty.db"
        conn = init_db(db_path)
        result = build_context(conn, "find anything", token_budget=4000)
        assert isinstance(result, str)
