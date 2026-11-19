"""Dense cosine retrieval channel over chunk embeddings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from workers.embedding.embedding import (
    Embedder,
    EmbeddingCache,
    EmbeddingError,
    embed_documents,
)

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
from .index import SearchHit
from .windows import WINDOW_MAX_CHARS, WINDOW_RADIUS, window_for_lines


@dataclass(frozen=True)
class DenseIndex:
    """Cosine similarity over chunk vectors, aggregated by page."""

    chunks: list[Chunk]
    pages: dict[tuple[str, int], str]
    vectors: np.ndarray
    embedder: Embedder
    documents: dict[str, DocumentMeta]
    window_radius: int = WINDOW_RADIUS
    window_max_chars: int = WINDOW_MAX_CHARS

    def __post_init__(self) -> None:
        if self.vectors.shape[0] != len(self.chunks):
            raise ValueError("vectors must have one row per chunk")
        if self.vectors.ndim != 2:
            raise ValueError("vectors must be a 2-D array")

    @classmethod
    def from_pages(
        cls,
        pages: list[Page],
        embedder: Embedder,
        *,
        cache: EmbeddingCache | None = None,
        size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
        documents: Mapping[str, DocumentMeta] | None = None,
        window_radius: int = WINDOW_RADIUS,
        window_max_chars: int = WINDOW_MAX_CHARS,
    ) -> DenseIndex:
        page_text: dict[tuple[str, int], str] = {}
        for page in pages:
            key = (page.document_id, page.page)
            if key in page_text:
                raise ValueError(f"duplicate page: {page.document_id} page {page.page}")
            page_text[key] = page.text

        chunks = chunk_pages(pages, size=size, overlap=overlap)
        texts = [chunk.text for chunk in chunks]
        tokens = [tokenize(text) for text in texts]
        vectors = embed_documents(
            texts,
            embedder,
            cache=cache,
            fit_on=tokens,
        )
        if vectors.shape != (len(chunks), embedder.dim):
            raise EmbeddingError(
                f"provider returned {vectors.shape}, expected {(len(chunks), embedder.dim)}"
            )
        return cls(
            chunks=chunks,
            pages=page_text,
            vectors=np.asarray(vectors, dtype=np.float32),
            embedder=embedder,
            documents=dict(documents or {}),
            window_radius=window_radius,
            window_max_chars=window_max_chars,
        )

    def page_text(self, document_id: str, page: int) -> str:
        return self.pages.get((document_id, page), "")

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

        query_vector = np.asarray(self.embedder.encode([query])[0], dtype=np.float32)
        if query_vector.shape != (self.vectors.shape[1],):
            raise EmbeddingError(
                f"query vector shape {query_vector.shape} does not match index dim "
                f"{self.vectors.shape[1]}"
            )
        if not np.isfinite(query_vector).all() or not query_vector.any():
            return []

        similarities = self.vectors @ query_vector
        best_by_page: dict[tuple[str, int], tuple[float, int]] = {}
        for index, similarity in enumerate(similarities.tolist()):
            chunk = self.chunks[index]
            if not matches_filters(chunk.document_id, self.documents, active_filters):
                continue
            key = (chunk.document_id, chunk.page)
            if key not in best_by_page or similarity > best_by_page[key][0]:
                best_by_page[key] = (float(similarity), index)

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
            chunk_terms = set(tokenize(chunk.text))
            matched = tuple(
                term for term in dict.fromkeys(tokenize(query)) if term in chunk_terms
            )
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
                    channel="dense",
                )
            )
        return hits
