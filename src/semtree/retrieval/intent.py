"""Improved intent classifier for AI task queries.

Fixes the overlapping-keyword problem from naive implementations by:
  1. Using weighted scoring per trigger
  2. Normalizing scores to [0.0, 1.0] (confidence)
  3. Requiring a minimum confidence gap to avoid ties
  4. Context-aware disambiguation: "test" and "fix" are NOT stopwords
     when they're the primary verb of the query

Intent categories and their retrieval implications:
  - implement   -> full signatures + docstrings, similar file context
  - debug       -> recent changes (git context), error-adjacent symbols
  - refactor    -> all references to target symbol, callers/callees
  - test        -> module under test, existing test patterns
  - explain     -> rich docstrings, class hierarchies
  - review      -> file-level overview, recent modifications
  - search      -> FTS5 keyword search, broad context
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: float   # 0.0 - 1.0
    matched_triggers: list[str]


# Weighted trigger patterns per intent
# Format: (pattern_regex, weight)
_TRIGGERS: dict[str, list[tuple[str, float]]] = {
    "implement": [
        (r"\bimplement\b", 3.0),
        (r"\badd\s+(?:a\s+)?(?:new\s+)?\w+", 2.0),
        (r"\bcreate\b", 2.0),
        (r"\bbuild\b", 1.5),
        (r"\bwrite\b", 0.8),
        (r"\bmake\b", 1.0),
        (r"\bfeature\b", 1.0),
        (r"\bendpoint\b", 1.5),
    ],
    "debug": [
        (r"\bfix\b", 3.0),
        (r"\bbug\b", 3.0),
        (r"\berror\b", 2.5),
        (r"\bexception\b", 2.5),
        (r"\bcrash\b", 3.0),
        (r"\bfail(?:ing|ed|ure)?\b", 2.0),
        (r"\bnot\s+work(?:ing)?\b", 2.5),
        (r"\bbroken\b", 2.5),
        (r"\bdebug\b", 3.0),
        (r"\btraceback\b", 2.0),
        (r"\bstack\s+trace\b", 2.0),
    ],
    "refactor": [
        (r"\brefactor\b", 3.0),
        (r"\brename\b", 2.5),
        (r"\bmove\b", 1.5),
        (r"\bextract\b", 2.0),
        (r"\bclean\s*up\b", 2.0),
        (r"\brestructure\b", 2.5),
        (r"\bsimplify\b", 2.0),
        (r"\bdry\b", 2.0),
        (r"\bduplication\b", 2.0),
    ],
    "test": [
        (r"\btests?\b", 3.0),
        (r"\bunit\s+tests?\b", 3.5),
        (r"\bintegration\s+tests?\b", 3.5),
        (r"\bpytest\b", 3.0),
        (r"\bspec\b", 2.0),
        (r"\bassert\b", 2.0),
        (r"\bmock\b", 2.0),
        (r"\bcoverage\b", 2.5),
        (r"\btdd\b", 3.0),
        (r"\btest\s+case\b", 3.0),
    ],
    "explain": [
        (r"\bexplain\b", 3.0),
        (r"\bwhat\s+(?:does|is)\b", 2.5),
        (r"\bhow\s+(?:does|do)\b", 2.5),
        (r"\bunderstand\b", 2.0),
        (r"\bdescribe\b", 2.0),
        (r"\bwalk\s+(?:me\s+)?through\b", 2.5),
        (r"\bsummariz\w+\b", 2.0),
        (r"\barchitecture\b", 2.0),
        (r"\boverview\b", 1.5),
    ],
    "review": [
        (r"\breview\b", 3.0),
        (r"\baudit\b", 2.5),
        (r"\bcheck\b", 1.5),
        (r"\binspect\b", 2.0),
        (r"\bpr\b", 2.0),
        (r"\bpull\s+request\b", 2.5),
        (r"\bcode\s+quality\b", 2.5),
        (r"\blint\b", 2.0),
        (r"\bsecurity\b", 2.0),
    ],
    "search": [
        (r"\bfind\b", 2.0),
        (r"\bsearch\b", 2.5),
        (r"\bwhere\s+is\b", 2.5),
        (r"\blocate\b", 2.0),
        (r"\bshow\s+me\b", 1.5),
        (r"\blist\b", 1.5),
        (r"\ball\s+\w+\s+that\b", 2.0),
    ],
}

# Compiled cache
_COMPILED: dict[str, list[tuple[re.Pattern, float]]] = {}


def _compile() -> None:
    for intent, patterns in _TRIGGERS.items():
        _COMPILED[intent] = [
            (re.compile(p, re.IGNORECASE), w)
            for p, w in patterns
        ]


_compile()


def classify(query: str, min_confidence: float = 0.25) -> IntentResult:
    """Classify a natural-language query into an intent.

    Returns IntentResult with the winning intent, its confidence,
    and the list of matched trigger phrases.

    When no intent reaches min_confidence, returns intent="search"
    as the safe default.
    """
    if not query.strip():
        return IntentResult("search", 0.0, [])

    scores: dict[str, float] = {}
    matched: dict[str, list[str]] = {}

    for intent, patterns in _COMPILED.items():
        score = 0.0
        hits: list[str] = []
        for pattern, weight in patterns:
            m = pattern.search(query)
            if m:
                score += weight
                hits.append(m.group(0))
        scores[intent] = score
        matched[intent] = hits

    total = sum(scores.values())
    if total == 0.0:
        return IntentResult("search", 0.0, [])

    # Normalize to confidence
    best_intent = max(scores, key=lambda k: scores[k])
    best_score = scores[best_intent]
    confidence = best_score / total

    # Require minimum confidence gap over second-best
    sorted_scores = sorted(scores.values(), reverse=True)
    second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
    gap = (best_score - second_score) / total if total > 0 else 0.0

    if confidence < min_confidence or gap < 0.05:
        # Ambiguous - lean towards search as safe default
        return IntentResult(
            "search",
            max(confidence, 0.1),
            matched.get(best_intent, []),
        )

    return IntentResult(
        best_intent,
        round(confidence, 3),
        matched[best_intent],
    )


def classify_many(queries: Sequence[str]) -> list[IntentResult]:
    """Classify multiple queries in batch."""
    return [classify(q) for q in queries]
