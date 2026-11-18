"""GroundedKB retrieval service skeleton.

The real BM25/dense/RRF implementation is migrated from the legacy project in
T1.2. Until then /search returns 501 and only /healthz is live.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="GroundedKB Retrieval", version="0.1.0")


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


@app.get("/healthz", response_model=Health, tags=["system"])
def healthz() -> Health:
    return Health()


@app.post("/search", response_model=SearchResponse, tags=["retrieval"])
def search(request: SearchRequest) -> SearchResponse:
    # Keep the contract endpoint live while the legacy retrieval algorithm is
    # being migrated. Callers get an explicit 501 instead of fake hits.
    raise HTTPException(status_code=501, detail="retrieval migration pending")
