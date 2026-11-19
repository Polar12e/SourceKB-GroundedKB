"""GroundedKB retrieval service.

The BM25 / hit-window / RRF algorithm is ported from the legacy project in
T1.2. The service loads a JSONL corpus when ``RETRIEVAL_CORPUS`` is set;
without a corpus the API returns an empty result set rather than fake hits.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from domains.finance.retrieval import FinanceRetrievalProfile

from .corpus import load_pages_jsonl
from .documents import load_documents_manifest
from .index import BM25Index


class Health(BaseModel):
    status: str = "ok"
    service: str = "retrieval"


class Locator(BaseModel):
    page: int = Field(ge=1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    section: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    filters: dict[str, str] = Field(default_factory=dict)
    top_k: int = Field(default=5, ge=1, le=50)


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    locator: Locator
    score: float
    matched_terms: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    hits: list[SearchHit] = Field(default_factory=list)


def _default_index() -> BM25Index:
    corpus = os.getenv("RETRIEVAL_CORPUS")
    profile = FinanceRetrievalProfile(os.getenv("RETRIEVAL_EXPANSION", "builtin"))
    if not corpus:
        return BM25Index.from_pages([], profile=profile)

    manifest = Path(
        os.getenv("RETRIEVAL_MANIFEST", "data/manifests/documents.json")
    )
    documents = load_documents_manifest(manifest) if manifest.exists() else None
    return BM25Index.from_pages(
        load_pages_jsonl(Path(corpus)),
        profile=profile,
        documents=documents,
    )


def create_app(index: BM25Index | None = None) -> FastAPI:
    """Build the app; tests inject an index, production reads the environment."""

    active = index if index is not None else _default_index()
    application = FastAPI(title="GroundedKB Retrieval", version="0.1.0")
    application.state.index = active

    @application.get("/healthz", response_model=Health, tags=["system"])
    def healthz() -> Health:
        return Health()

    @application.post(
        "/search",
        response_model=SearchResponse,
        response_model_exclude_none=True,
        tags=["retrieval"],
    )
    def search(request: SearchRequest) -> SearchResponse:
        try:
            hits = active.search(
                request.query,
                top_k=request.top_k,
                filters=request.filters,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return SearchResponse(
            hits=[SearchHit(**hit.to_contract()) for hit in hits]
        )

    return application


app = create_app()
