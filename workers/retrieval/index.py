"""BM25 retrieval over line-aware chunks."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

from .chunking import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    Chunk,
    Page,
    chunk_pages,
    tokenize,
)
from .documents import DocumentMeta
from .filters import matches_filters, normalize_filters
from .windows import WINDOW_MAX_CHARS, WINDOW_RADIUS, window_for_lines

BM25_K1 = 1.5
BM25_B = 0.75


class QueryProfile(Protocol):
    """Domain hook for query expansion and page priors."""

    def expanded_terms(
        self,
        query: str,
        coverage: float | None = None,
    ) -> dict[str, float]:
        ...

    def page_prior(self, query: str, page_text: str) -> float:
        ...


@dataclass(frozen=True)
class SearchHit:
    """Internal hit; page/line fields are flattened into a contract locator."""

    chunk_id: str
    document_id: str
    page: int
    line_start: int
    line_end: int
    text: str
    score: float
    matched_terms: tuple[str, ...] = ()
    channel: str = "bm25"

    def to_contract(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "locator": {
                "page": self.page,
                "line_start": self.line_start,
                "line_end": self.line_end,
            },
            "score": self.score,
            "matched_terms": list(self.matched_terms),
        }


class BM25Index:
    """BM25 baseline over chunks, aggregated to one best chunk per page."""

    def __init__(
        self,
        chunks: list[Chunk],
        pages: dict[tuple[str, int], str],
        *,
        k1: float = BM25_K1,
        b: float = BM25_B,
        profile: QueryProfile | None = None,
        documents: Mapping[str, DocumentMeta] | None = None,
        window_radius: int = WINDOW_RADIUS,
        window_max_chars: int = WINDOW_MAX_CHARS,
    ) -> None:
        if k1 < 0:
            raise ValueError("k1 must be >= 0")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")
        self.chunks = chunks
        self.pages = pages
        self.k1 = k1
        self.b = b
        self.profile = profile
        self.documents = dict(documents or {})
        self.window_radius = window_radius
        self.window_max_chars = window_max_chars
        self.tokens = [tokenize(chunk.text) for chunk in chunks]
        self.term_counts = [Counter(tokens) for tokens in self.tokens]
        self.lengths = [len(tokens) for tokens in self.tokens]
        self.avg_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0

        document_frequency: Counter[str] = Counter()
        for counts in self.term_counts:
            document_frequency.update(counts.keys())
        total = len(chunks)
        self.idf = {
            term: math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    @classmethod
    def from_pages(
        cls,
        pages: Iterable[Page],
        *,
        size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
        k1: float = BM25_K1,
        b: float = BM25_B,
        profile: QueryProfile | None = None,
        documents: Mapping[str, DocumentMeta] | None = None,
        window_radius: int = WINDOW_RADIUS,
        window_max_chars: int = WINDOW_MAX_CHARS,
    ) -> BM25Index:
        page_list = list(pages)
        page_text: dict[tuple[str, int], str] = {}
        for page in page_list:
            key = (page.document_id, page.page)
            if key in page_text:
                raise ValueError(f"duplicate page: {page.document_id} page {page.page}")
            page_text[key] = page.text
        return cls(
            chunk_pages(page_list, size=size, overlap=overlap),
            page_text,
            k1=k1,
            b=b,
            profile=profile,
            documents=documents,
            window_radius=window_radius,
            window_max_chars=window_max_chars,
        )

    def page_text(self, document_id: str, page: int) -> str:
        return self.pages.get((document_id, page), "")

    def coverage(self, query: str) -> float:
        """Share of query tokens that exist somewhere in the corpus."""

        terms = set(tokenize(query))
        if not terms:
            return 0.0
        return sum(1 for term in terms if term in self.idf) / len(terms)

    def weighted_terms(self, query: str) -> dict[str, float]:
        weights: dict[str, float] = {term: 1.0 for term in tokenize(query)}
        if self.profile is not None:
            for term, weight in self.profile.expanded_terms(
                query, coverage=self.coverage(query)
            ).items():
                weights[term] = max(weights.get(term, 0.0), weight)
        return weights

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Mapping[str, str] | None = None,
    ) -> list[SearchHit]:
        if top_k <= 0:
            return []

        active_filters = normalize_filters(filters)
        if not query.strip() or not self.chunks:
            return []

        weights = self.weighted_terms(query)
        if not weights:
            return []

        scored: list[tuple[float, int]] = []
        average_length = self.avg_length or 1.0
        for index, counts in enumerate(self.term_counts):
            if not matches_filters(self.chunks[index].document_id, self.documents, active_filters):
                continue
            score = 0.0
            for term, weight in weights.items():
                frequency = counts.get(term)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * self.lengths[index] / average_length
                )
                score += (
                    weight
                    * self.idf.get(term, 0.0)
                    * frequency
                    * (self.k1 + 1)
                    / denominator
                )
            if score > 0:
                scored.append((score, index))

        # Rank pages, not chunks: a page's best chunk is its anchor. The chunk
        # id stays stable even when the window later expands into neighbouring
        # chunks on the same page.
        best_by_page: dict[tuple[str, int], tuple[float, int]] = {}
        for score, index in scored:
            chunk = self.chunks[index]
            key = (chunk.document_id, chunk.page)
            if self.profile is not None:
                score += self.profile.page_prior(
                    query, self.page_text(chunk.document_id, chunk.page)
                )
            if key not in best_by_page or score > best_by_page[key][0]:
                best_by_page[key] = (score, index)

        ranked = sorted(
            best_by_page.values(),
            key=lambda item: (
                -item[0],
                self.chunks[item[1]].document_id,
                self.chunks[item[1]].page,
                self.chunks[item[1]].index,
            ),
        )

        hits: list[SearchHit] = []
        for score, index in ranked[:top_k]:
            chunk = self.chunks[index]
            window = window_for_lines(
                self.page_text(chunk.document_id, chunk.page),
                chunk.line_start,
                chunk.line_end,
                fallback_text=chunk.text,
                radius=self.window_radius,
                max_chars=self.window_max_chars,
            )
            chunk_terms = set(self.tokens[index])
            matched = tuple(term for term in weights if term in chunk_terms)
            hits.append(
                SearchHit(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    page=chunk.page,
                    line_start=window.line_start,
                    line_end=window.line_end,
                    text=window.text,
                    score=score,
                    matched_terms=matched,
                )
            )
        return hits
