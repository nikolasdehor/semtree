"""Structured JSONL logger for semtree."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


_LOG_FILE: Path | None = None
_VERBOSE: bool = False


def configure(log_dir: Path | None = None, verbose: bool = False) -> None:
    """Configure the logger. Call once at startup."""
    global _LOG_FILE, _VERBOSE
    _VERBOSE = verbose
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        _LOG_FILE = log_dir / "semtree.jsonl"


def _emit(level: str, msg: str, **fields: Any) -> None:
    entry: dict[str, Any] = {
        "ts": time.time(),
        "level": level,
        "msg": msg,
        **fields,
    }
    if _LOG_FILE is not None:
        with _LOG_FILE.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")
    if _VERBOSE or level in ("warn", "error"):
        stream = sys.stderr if level == "error" else sys.stdout
        prefix = {"info": "  ", "warn": "! ", "error": "✗ ", "debug": "· "}.get(level, "  ")
        extra = " ".join(f"{k}={v}" for k, v in fields.items())
        print(f"{prefix}{msg}{' ' + extra if extra else ''}", file=stream)


def info(msg: str, **fields: Any) -> None:
    _emit("info", msg, **fields)


def warn(msg: str, **fields: Any) -> None:
    _emit("warn", msg, **fields)


def error(msg: str, **fields: Any) -> None:
    _emit("error", msg, **fields)


def debug(msg: str, **fields: Any) -> None:
    if _VERBOSE or os.environ.get("SEMTREE_DEBUG"):
        _emit("debug", msg, **fields)
