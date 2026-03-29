"""Per-task retrieval policies.

Maps intent -> retrieval strategy configuration.
Policies control how search results are filtered, ranked, and enriched
before being handed to the context builder.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalPolicy:
    """Retrieval parameters for a specific intent."""
    intent: str

    # Symbol kinds to prioritize (empty = include all)
    prefer_kinds: list[str] = field(default_factory=list)

    # Whether to include related symbols (callers/callees) - heavier
    include_related: bool = False

    # Whether to include git blame metadata
    include_git_context: bool = False

    # Context level: 0=names only, 1=signatures, 2=sigs+docstrings, 3=full
    context_level: int = 2

    # Token budget fraction for retrieved symbols (0.0-1.0)
    budget_fraction: float = 0.7

    # Max symbols to retrieve per search query
    max_symbols: int = 30

    # Whether to include the surrounding file structure summary
    include_file_tree: bool = True


# Pre-defined policies per intent
_POLICIES: dict[str, RetrievalPolicy] = {
    "implement": RetrievalPolicy(
        intent="implement",
        prefer_kinds=["class", "function", "type"],
        include_related=True,
        include_git_context=False,
        context_level=2,
        budget_fraction=0.75,
        max_symbols=25,
        include_file_tree=True,
    ),
    "debug": RetrievalPolicy(
        intent="debug",
        prefer_kinds=[],  # all kinds relevant for debugging
        include_related=True,
        include_git_context=True,   # git context helps understand recent changes
        context_level=3,
        budget_fraction=0.8,
        max_symbols=20,
        include_file_tree=False,
    ),
    "refactor": RetrievalPolicy(
        intent="refactor",
        prefer_kinds=["function", "method", "class"],
        include_related=True,
        include_git_context=True,
        context_level=2,
        budget_fraction=0.7,
        max_symbols=30,
        include_file_tree=True,
    ),
    "test": RetrievalPolicy(
        intent="test",
        prefer_kinds=["function", "class", "method"],
        include_related=False,
        include_git_context=False,
        context_level=2,
        budget_fraction=0.65,
        max_symbols=20,
        include_file_tree=False,
    ),
    "explain": RetrievalPolicy(
        intent="explain",
        prefer_kinds=[],
        include_related=False,
        include_git_context=False,
        context_level=3,           # full docstrings for explanation
        budget_fraction=0.8,
        max_symbols=15,
        include_file_tree=True,
    ),
    "review": RetrievalPolicy(
        intent="review",
        prefer_kinds=[],
        include_related=False,
        include_git_context=True,
        context_level=2,
        budget_fraction=0.6,
        max_symbols=40,
        include_file_tree=True,
    ),
    "search": RetrievalPolicy(
        intent="search",
        prefer_kinds=[],
        include_related=False,
        include_git_context=False,
        context_level=1,           # lighter: names + signatures only
        budget_fraction=0.5,
        max_symbols=50,
        include_file_tree=False,
    ),
}


def get_policy(intent: str) -> RetrievalPolicy:
    """Return the RetrievalPolicy for the given intent.

    Falls back to the "search" policy for unknown intents.
    """
    return _POLICIES.get(intent, _POLICIES["search"])


def all_policies() -> dict[str, RetrievalPolicy]:
    """Return all registered policies."""
    return dict(_POLICIES)
