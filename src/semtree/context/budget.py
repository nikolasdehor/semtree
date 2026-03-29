"""Token budget management with tiktoken (optional) or char-based estimate."""

from __future__ import annotations

from typing import Sequence


try:
    import tiktoken  # type: ignore
    _enc = tiktoken.get_encoding("cl100k_base")  # GPT-4 / Claude compatible
    _HAS_TIKTOKEN = True
except ImportError:
    _enc = None
    _HAS_TIKTOKEN = False


# Rough character-to-token ratio for English/code content when tiktoken is absent
_CHARS_PER_TOKEN = 3.5


def count_tokens(text: str) -> int:
    """Count tokens in text.

    Uses tiktoken cl100k_base when available (accurate for GPT-4/Claude).
    Falls back to len(text) / 3.5 otherwise.
    """
    if not text:
        return 0
    if _HAS_TIKTOKEN and _enc is not None:
        return len(_enc.encode(text))
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


def count_tokens_many(texts: Sequence[str]) -> int:
    """Count total tokens across multiple text chunks."""
    return sum(count_tokens(t) for t in texts)


def fits_in_budget(text: str, budget: int, used: int = 0) -> bool:
    """Return True if text fits within the remaining token budget."""
    return (used + count_tokens(text)) <= budget


class TokenBudget:
    """Stateful token budget tracker.

    Usage:
        budget = TokenBudget(8000)
        if budget.fits(chunk):
            budget.consume(chunk)
    """

    def __init__(self, total: int) -> None:
        self.total = total
        self.used = 0

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.used)

    @property
    def fraction_used(self) -> float:
        return self.used / self.total if self.total > 0 else 0.0

    def fits(self, text: str) -> bool:
        return self.remaining >= count_tokens(text)

    def consume(self, text: str) -> int:
        """Add text to the budget. Returns tokens consumed."""
        tokens = count_tokens(text)
        self.used += tokens
        return tokens

    def try_consume(self, text: str) -> bool:
        """Consume text if it fits. Returns True on success."""
        if self.fits(text):
            self.consume(text)
            return True
        return False

    def reset(self) -> None:
        self.used = 0

    def __repr__(self) -> str:
        return f"TokenBudget({self.used}/{self.total})"
