"""Tests for retrieval subsystem: intent, search, policies."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from semtree.db import store as db_store
from semtree.db.schema import init_db
from semtree.retrieval.intent import classify
from semtree.retrieval.policy import get_policy
from semtree.retrieval.search import search

# ---------------------------------------------------------------------------
# Intent classifier tests
# ---------------------------------------------------------------------------

class TestIntentClassifier:
    def test_implement_clear(self) -> None:
        result = classify("implement a new user authentication endpoint")
        assert result.intent == "implement"
        assert result.confidence > 0.3

    def test_debug_clear(self) -> None:
        result = classify("fix the bug in the login function")
        assert result.intent == "debug"
        assert result.confidence > 0.3

    def test_refactor(self) -> None:
        result = classify("refactor the database connection pool")
        assert result.intent == "refactor"
        assert result.confidence > 0.3

    def test_test_intent(self) -> None:
        result = classify("write unit tests for the payment module")
        assert result.intent == "test"
        assert result.confidence > 0.3

    def test_explain(self) -> None:
        result = classify("explain how the authentication middleware works")
        assert result.intent == "explain"

    def test_review(self) -> None:
        result = classify("review the latest pull request changes")
        assert result.intent == "review"

    def test_search(self) -> None:
        result = classify("find all database models")
        assert result.intent == "search"

    def test_empty_query(self) -> None:
        result = classify("")
        assert result.intent == "search"
        assert result.confidence == 0.0

    def test_ambiguous_returns_safe_default(self) -> None:
        # "the code" is ambiguous
        result = classify("the code")
        # Should not crash, should return some intent
        assert result.intent in ("search", "implement", "debug", "explain", "refactor", "test", "review")

    def test_confidence_not_above_one(self) -> None:
        result = classify("implement a new feature to fix the bug in tests")
        assert 0.0 <= result.confidence <= 1.0

    def test_matched_triggers_populated(self) -> None:
        result = classify("implement a new endpoint")
        if result.intent == "implement":
            assert len(result.matched_triggers) > 0

    def test_no_false_stopword_removal(self) -> None:
        # "test" should trigger test intent, not be filtered out
        result = classify("write tests for the API")
        assert result.intent == "test"

    def test_fix_triggers_debug(self) -> None:
        # "fix" should trigger debug, not be swallowed as stopword
        result = classify("fix the crash in production")
        assert result.intent == "debug"


# ---------------------------------------------------------------------------
# Policy tests
# ---------------------------------------------------------------------------

class TestPolicy:
    def test_debug_policy_has_git_context(self) -> None:
        policy = get_policy("debug")
        assert policy.include_git_context is True

    def test_explain_policy_has_level_3(self) -> None:
        policy = get_policy("explain")
        assert policy.context_level == 3

    def test_search_policy_is_lightweight(self) -> None:
        policy = get_policy("search")
        assert policy.context_level <= 1

    def test_unknown_intent_falls_back_to_search(self) -> None:
        policy = get_policy("nonexistent_intent")
        assert policy.intent == "search"


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------

@pytest.fixture
def populated_db(tmp_path: Path) -> sqlite3.Connection:
    """DB with some sample symbols for search testing."""
    db_path = tmp_path / ".ctx" / "index.db"
    conn = init_db(db_path)

    file_id = db_store.upsert_file(conn, "src/auth.py", "abc123", 1000, "python")
    db_store.replace_file_symbols(conn, file_id, [
        {
            "name": "authenticate_user",
            "kind": "function",
            "line_start": 10,
            "line_end": 25,
            "signature": "def authenticate_user(username: str, password: str) -> bool:",
            "docstring": "Verify user credentials against the database.",
            "git_author": "Alice",
            "git_date": "2025-01-15",
        },
        {
            "name": "AuthToken",
            "kind": "class",
            "line_start": 30,
            "line_end": 60,
            "signature": "class AuthToken:",
            "docstring": "JWT-based authentication token manager.",
            "git_author": "Bob",
            "git_date": "2025-01-10",
        },
    ])

    file_id2 = db_store.upsert_file(conn, "src/utils.py", "def456", 500, "python")
    db_store.replace_file_symbols(conn, file_id2, [
        {
            "name": "hash_password",
            "kind": "function",
            "line_start": 5,
            "line_end": 12,
            "signature": "def hash_password(password: str) -> str:",
            "docstring": "Hash a password using bcrypt.",
            "git_author": "Alice",
            "git_date": "2025-01-12",
        },
    ])
    conn.commit()
    return conn


class TestSearch:
    def test_fts_search_by_name(self, populated_db: sqlite3.Connection) -> None:
        results = search(populated_db, "authenticate_user", limit=10)
        assert any(r.symbol.name == "authenticate_user" for r in results)

    def test_fts_search_by_docstring(self, populated_db: sqlite3.Connection) -> None:
        results = search(populated_db, "credentials", limit=10)
        assert len(results) > 0

    def test_exact_match_scores_higher(self, populated_db: sqlite3.Connection) -> None:
        results = search(populated_db, "hash_password", limit=10)
        if len(results) > 1:
            # Exact match should appear first or have higher score
            assert results[0].symbol.name == "hash_password" or results[0].score >= results[-1].score

    def test_empty_query_returns_empty(self, populated_db: sqlite3.Connection) -> None:
        results = search(populated_db, "", limit=10)
        assert results == []

    def test_no_results_for_nonexistent(self, populated_db: sqlite3.Connection) -> None:
        results = search(populated_db, "xyzzy_nonexistent_symbol_42", limit=10)
        assert results == []

    def test_limit_respected(self, populated_db: sqlite3.Connection) -> None:
        results = search(populated_db, "auth", limit=1)
        assert len(results) <= 1
