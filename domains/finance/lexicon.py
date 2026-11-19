"""Finance term table and query-term conversion.

The table is a **finance term configuration** (``terms.json``). A group lists
terms that are considered equivalent or near-equivalent for query expansion; no
group replaces the user's original wording.

Conversion logic
----------------

1. Normalize the query: lowercase, traditional -> simplified (``zhconv``),
   remove thousands separators, join split CJK labels.
2. Build the query's CJK character bigrams (plus ASCII/number tokens for the
   retrieval index). Matching uses bigram overlap, not substring matching, so
   ``技术上要投多少钱`` still matches the term ``技术投入`` through ``技术``.
3. For every term group, if any group member shares a bigram with the query,
   all sibling terms that are not literally present in the query become
   expansion candidates.
4. Deduplicate candidates while preserving group order.
5. Convert each candidate term to its retrieval tokens and attach
   ``EXPANSION_WEIGHT`` (0.45). The original query terms keep weight 1.0, so an
   expansion can add recall but cannot outvote the user's own words.
6. The retrieval profile decides *when* to apply the expansion:
   ``builtin`` = ratio/restatement terms only, ``lexicon`` = always add the
   term table, ``auto`` = only when corpus coverage is below 0.5, ``none`` =
   never.

The table is intentionally a flat configuration rather than hard-coded Python;
it can be reviewed and changed without touching retrieval logic.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from core.text import normalize

_TERMS_PATH = Path(__file__).with_name("terms.json")
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")


def _load_terms() -> tuple[tuple[tuple[str, ...], ...], float]:
    config = json.loads(_TERMS_PATH.read_text(encoding="utf-8"))
    groups = tuple(
        tuple(str(term) for term in group)
        for group in config["groups"]
    )
    if not groups:
        raise ValueError(f"{_TERMS_PATH}: groups must not be empty")
    for group in groups:
        if len(group) < 2:
            raise ValueError(f"{_TERMS_PATH}: each group needs at least two terms")
        if any(len(term) < 2 for term in group):
            raise ValueError(f"{_TERMS_PATH}: single-character term is too broad")
    weight = float(config["expansion_weight"])
    if not 0 < weight < 1:
        raise ValueError(f"{_TERMS_PATH}: expansion_weight must be between 0 and 1")
    return groups, weight


TERM_GROUPS, EXPANSION_WEIGHT = _load_terms()


def _bigrams(text: str) -> set[str]:
    pairs: set[str] = set()
    for run in _CJK_RUN.findall(normalize(text)):
        if len(run) == 1:
            pairs.add(run)
        else:
            pairs.update(run[index:index + 2] for index in range(len(run) - 1))
    return pairs


def terms_for(text: str) -> tuple[str, ...]:
    """Return matching name-table siblings that are absent from ``text``."""

    normalized = normalize(text)
    query_pairs = _bigrams(normalized)
    matched: list[str] = []
    for group in TERM_GROUPS:
        if any(query_pairs & _bigrams(member) for member in group):
            matched.extend(member for member in group if member not in normalized)
    return tuple(dict.fromkeys(matched))


def expand_terms(query: str) -> list[tuple[str, float]]:
    """Return ``(term, weight)`` expansions for the configured name table."""

    return [(term, EXPANSION_WEIGHT) for term in terms_for(query)]


__all__ = [
    "EXPANSION_WEIGHT",
    "TERM_GROUPS",
    "expand_terms",
    "terms_for",
]
