"""Weighted reciprocal-rank fusion (RRF) over retrieval channels."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol, Sequence

from .index import SearchHit

RRF_K = 60
FUSION_DEPTH = 60


class Channel(Protocol):
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, str] | None = None,
    ) -> list[SearchHit]:
        ...


class HybridIndex:
    """Fuse channels by rank instead of by incompatible raw scores.

    ``weight`` encodes trust, not a calibrated score. With ``k=60`` a page ranked
    #1 by a weight-0.5 channel contributes ``0.5/61``, which stays below the
    primary channel's winner.
    """

    def __init__(
        self,
        channels: Sequence[tuple[str, Channel, float]],
        *,
        k: int = RRF_K,
        depth: int = FUSION_DEPTH,
    ) -> None:
        if not channels:
            raise ValueError("a hybrid index needs at least one channel")
        if k < 0:
            raise ValueError("k must be >= 0")
        if depth < 1:
            raise ValueError("depth must be >= 1")
        self.channels = tuple(channels)
        self.k = k
        self.depth = depth

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, str] | None = None,
    ) -> list[SearchHit]:
        if top_k <= 0 or not query.strip():
            return []

        fused: dict[tuple[str, int], float] = {}
        best: dict[tuple[str, int], tuple[float, SearchHit, str]] = {}

        for name, channel, weight in self.channels:
            if weight <= 0:
                continue
            hits = channel.search(
                query,
                top_k=max(self.depth, top_k),
                filters=filters,
            )
            for rank, hit in enumerate(hits, start=1):
                key = (hit.document_id, hit.page)
                contribution = weight / (self.k + rank)
                fused[key] = fused.get(key, 0.0) + contribution
                current = best.get(key)
                if current is None or contribution > current[0]:
                    best[key] = (contribution, hit, name)

        ordered = sorted(
            fused.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1]),
        )
        results: list[SearchHit] = []
        for key, score in ordered[:top_k]:
            _, hit, name = best[key]
            results.append(replace(hit, score=score, channel=name))
        return results
