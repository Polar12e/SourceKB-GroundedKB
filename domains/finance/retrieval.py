"""Finance-specific retrieval profile.

Ported from the legacy ``src/retrieval.py`` "builtin" expansion and statement
prior. It stays outside the generic BM25 index so other domains can plug in
their own vocabulary without copying accounting rules.

This profile intentionally covers the *builtin* ratio/restatement expansions
used by the legacy ``bm25`` baseline. The broader colloquial lexicon
(``src/lexicon.py``) is a separate migration for ``domains/finance``.
"""

from __future__ import annotations

from core.text import normalize, tokenize

from .lexicon import expand_terms

QUERY_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "毛利率": ("营业收入", "营业成本"),
    "资产负债率": ("负债合计", "资产总计"),
    "营收同比": ("营业收入",),
    "同比增长": ("营业收入",),
    "净利率": ("净利润", "营业收入"),
    "重述": ("重分类", "会计政策变更", "可比期间"),
    "质保费": ("质量保证",),
}

STATEMENT_TITLES = (
    "合并及公司利润表",
    "合并及公司资产负债表",
    "合并及公司现金流量表",
    "合并利润表",
    "合并资产负债表",
    "合并现金流量表",
)
STATEMENT_BONUS = 18.0
NOTES_MARKERS = ("为什么", "重述", "重分类", "影响", "附注", "会计政策", "调整")
EXPANSION_MODES = ("none", "builtin", "lexicon", "auto")
OOV_EXPANSION_THRESHOLD = 0.5


class FinanceRetrievalProfile:
    """Query expansion and statement-page prior for annual reports.

    ``builtin`` keeps the ratio/restatement expansion used by the legacy
    ``bm25`` baseline. ``lexicon`` adds the full colloquial concept table;
    ``auto`` only adds it when query coverage is below
    ``OOV_EXPANSION_THRESHOLD``. Lexicon terms are down-weighted.
    """

    def __init__(self, mode: str = "builtin") -> None:
        if mode not in EXPANSION_MODES:
            raise ValueError(f"mode must be one of {EXPANSION_MODES}")
        self.mode = mode

    def expanded_terms(
        self,
        query: str,
        coverage: float | None = None,
    ) -> dict[str, float]:
        if self.mode == "none":
            return {}

        query = normalize(query)
        weights: dict[str, float] = {}
        for key, terms in QUERY_EXPANSIONS.items():
            if key not in query:
                continue
            for term in terms:
                for token in tokenize(term):
                    weights.setdefault(token, 1.0)

        rewrite = self.mode == "lexicon" or (
            self.mode == "auto"
            and coverage is not None
            and coverage < OOV_EXPANSION_THRESHOLD
        )
        if rewrite:
            for term, weight in expand_terms(query):
                for token in tokenize(term):
                    weights[token] = max(weights.get(token, 0.0), weight)
        return weights

    def page_prior(self, query: str, page_text: str) -> float:
        query = normalize(query)
        if any(marker in query for marker in NOTES_MARKERS):
            return 0.0
        head = normalize(page_text[:240])
        return STATEMENT_BONUS if any(title in head for title in STATEMENT_TITLES) else 0.0
