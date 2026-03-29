"""Lightweight project memory: rules, references, notes.

Memory entries are stored in the semtree SQLite database alongside symbols.
They persist across index rebuilds and are included in context output when
the AI needs project-specific guidelines.

Kinds:
  rule  - coding conventions, architecture decisions ("Always use async views")
  ref   - external references, API docs, ticket numbers
  note  - miscellaneous observations, TODOs, reminders
"""

from __future__ import annotations

import sqlite3

from ..db.store import (
    MemoryRecord,
    delete_memory,
    list_memory,
    upsert_memory,
)


class ProjectMemory:
    """High-level interface for project memory operations."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, kind: str, key: str, value: str) -> MemoryRecord:
        """Store or update a memory entry."""
        if kind not in ("rule", "ref", "note"):
            raise ValueError(f"Invalid memory kind '{kind}'. Use: rule, ref, note")
        rec = upsert_memory(self._conn, kind, key, value)
        self._conn.commit()
        return rec

    def add_rule(self, key: str, value: str) -> MemoryRecord:
        return self.add("rule", key, value)

    def add_ref(self, key: str, value: str) -> MemoryRecord:
        return self.add("ref", key, value)

    def add_note(self, key: str, value: str) -> MemoryRecord:
        return self.add("note", key, value)

    def remove(self, kind: str, key: str) -> bool:
        """Delete a memory entry. Returns True if it existed."""
        removed = delete_memory(self._conn, kind, key)
        if removed:
            self._conn.commit()
        return removed

    def list_all(self, kind: str | None = None) -> list[MemoryRecord]:
        """List all memory entries, optionally filtered by kind."""
        return list_memory(self._conn, kind)

    def format_for_context(self, max_chars: int = 2000) -> str:
        """Format memory as a compact markdown block for AI context injection."""
        records = list_memory(self._conn)
        if not records:
            return ""

        sections: dict[str, list[str]] = {"rule": [], "ref": [], "note": []}
        for rec in records:
            sections[rec.kind].append(f"- **{rec.key}**: {rec.value}")

        parts = ["## Project Memory\n"]
        kind_labels = {"rule": "Rules", "ref": "References", "note": "Notes"}
        for kind, label in kind_labels.items():
            items = sections[kind]
            if items:
                parts.append(f"### {label}")
                parts.extend(items)

        text = "\n".join(parts)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... (truncated)"
        return text
