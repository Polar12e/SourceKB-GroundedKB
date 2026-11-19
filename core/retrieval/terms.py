"""Generic term-table loading and query expansion.

The term table is configuration data; the conversion logic is independent of
any domain. Finance stores its table in ``domains/finance/terms.json``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from core.text import normalize

_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")


@dataclass(frozen=True)
class TermTable:
    name: str
    groups: tuple[tuple[str, ...], ...]


def load_term_table(path: str | Path) -> TermTable:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    groups = tuple(
        tuple(str(term) for term in group)
        for group in payload["groups"]
    )
    if not groups:
        raise ValueError(f"{path}: groups must not be empty")
    for group in groups:
        if len(group) < 2:
            raise ValueError(f"{path}: each group needs at least two terms")
        if any(len(term) < 2 for term in group):
            raise ValueError(f"{path}: single-character term is too broad")
    return TermTable(
        name=str(payload.get("name", "term-table")),
        groups=groups,
    )


def _bigrams(text: str) -> set[str]:
    pairs: set[str] = set()
    for run in _CJK_RUN.findall(normalize(text)):
        if len(run) == 1:
            pairs.add(run)
        else:
            pairs.update(run[index:index + 2] for index in range(len(run) - 1))
    return pairs


def terms_for(text: str, table: TermTable) -> tuple[str, ...]:
    """Name-table siblings matched by bigram overlap and absent from ``text``."""

    normalized = normalize(text)
    query_pairs = _bigrams(normalized)
    matched: list[str] = []
    for group in table.groups:
        if any(query_pairs & _bigrams(member) for member in group):
            matched.extend(member for member in group if member not in normalized)
    return tuple(dict.fromkeys(matched))


def expand_terms(
    query: str,
    table: TermTable,
    weight: float = 0.45,
) -> list[tuple[str, float]]:
    return [(term, weight) for term in terms_for(query, table)]


__all__ = ["TermTable", "expand_terms", "load_term_table", "terms_for"]
