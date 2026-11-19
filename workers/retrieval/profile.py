"""Configuration-driven query profile for the generic four-channel retrieval."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from core.retrieval.terms import TermTable, expand_terms, load_term_table
from core.text import normalize, tokenize

EXPANSION_MODES = ("none", "builtin", "lexicon", "auto")


class ConfiguredProfile:
    """Parameter bundle for query expansion and page priors.

    All domain values (term table, builtin expansion map, statement titles,
    notes markers, bonus) come from configuration; this class contains no
    finance-specific constants.
    """

    def __init__(self, settings: Mapping) -> None:
        mode = str(settings.get("mode", "builtin"))
        if mode not in EXPANSION_MODES:
            raise ValueError(f"mode must be one of {EXPANSION_MODES}")
        self.mode = mode

        term_table = settings.get("term_table")
        self.term_table: TermTable | None = None
        if term_table:
            path = Path(str(term_table))
            if not path.is_absolute():
                path = Path(__file__).resolve().parents[2] / path
            self.term_table = load_term_table(path)

        fallback_weight = 0.45
        self.expansion_weight = float(settings.get("expansion_weight", fallback_weight))
        if not 0 < self.expansion_weight < 1:
            raise ValueError("expansion_weight must be between 0 and 1")
        self.oov_threshold = float(settings.get("oov_threshold", 0.5))
        if not 0 <= self.oov_threshold <= 1:
            raise ValueError("oov_threshold must be between 0 and 1")

        builtins = settings.get("builtin_expansions") or {}
        self.builtin_expansions = {
            str(key): tuple(str(term) for term in terms)
            for key, terms in builtins.items()
        }
        self.statement_titles = tuple(
            str(title) for title in settings.get("statement_titles", ())
        )
        self.notes_markers = tuple(
            str(marker) for marker in settings.get("notes_markers", ())
        )
        self.statement_bonus = float(settings.get("statement_bonus", 0.0))

    def expanded_terms(
        self,
        query: str,
        coverage: float | None = None,
    ) -> dict[str, float]:
        if self.mode == "none":
            return {}

        query = normalize(query)
        weights: dict[str, float] = {}
        for key, terms in self.builtin_expansions.items():
            if key not in query:
                continue
            for term in terms:
                for token in tokenize(term):
                    weights.setdefault(token, 1.0)

        rewrite = self.mode == "lexicon" or (
            self.mode == "auto"
            and coverage is not None
            and coverage < self.oov_threshold
        )
        if rewrite and self.term_table is not None:
            for term, _ in expand_terms(query, self.term_table):
                for token in tokenize(term):
                    weights[token] = max(
                        weights.get(token, 0.0),
                        self.expansion_weight,
                    )
        return weights

    def page_prior(self, query: str, page_text: str) -> float:
        query = normalize(query)
        if any(marker in query for marker in self.notes_markers):
            return 0.0
        head = normalize(page_text[:240])
        return (
            self.statement_bonus
            if any(title in head for title in self.statement_titles)
            else 0.0
        )


def profile_from_config(config: Mapping, name: str) -> ConfiguredProfile:
    profiles = config.get("profiles")
    if not isinstance(profiles, Mapping) or name not in profiles:
        raise ValueError(f"unknown retrieval profile: {name}")
    return ConfiguredProfile(profiles[name])


__all__ = ["ConfiguredProfile", "EXPANSION_MODES", "profile_from_config"]
