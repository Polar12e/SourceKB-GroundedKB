from __future__ import annotations

import pytest

from workers.retrieval.fusion import HybridIndex
from workers.retrieval.index import SearchHit


def make_hit(document_id: str, page: int) -> SearchHit:
    return SearchHit(
        chunk_id=f"{document_id}:p{page}:c0",
        document_id=document_id,
        page=page,
        line_start=1,
        line_end=1,
        text=f"{document_id} page {page}",
        score=1.0,
    )


class StubChannel:
    def __init__(self, order: list[tuple[str, int]]) -> None:
        self.order = order

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        return [make_hit(document_id, page) for document_id, page in self.order[:top_k]]


def test_single_channel_preserves_order() -> None:
    index = HybridIndex([("only", StubChannel([("doc", 3), ("doc", 1), ("doc", 2)]), 1.0)])

    assert [hit.page for hit in index.search("x")] == [3, 1, 2]


def test_zero_weight_channels_are_ignored() -> None:
    index = HybridIndex(
        [
            ("primary", StubChannel([("doc", 2)]), 1.0),
            ("silent", StubChannel([("doc", 1), ("doc", 3)]), 0.0),
        ]
    )

    assert [hit.page for hit in index.search("x")] == [2]


def test_pages_found_by_both_channels_win() -> None:
    index = HybridIndex(
        [
            ("a", StubChannel([("doc", 1), ("doc", 2), ("doc", 3)]), 1.0),
            ("b", StubChannel([("doc", 3), ("doc", 1)]), 0.5),
        ]
    )

    assert [hit.page for hit in index.search("x")] == [1, 3, 2]


def test_fusion_score_is_the_weighted_reciprocal_rank() -> None:
    index = HybridIndex(
        [
            ("a", StubChannel([("doc", 2)]), 1.0),
            ("b", StubChannel([("doc", 1), ("doc", 2)]), 0.5),
        ],
        k=60,
    )

    scores = {hit.page: hit.score for hit in index.search("x")}

    assert scores[2] == pytest.approx(1 / 61 + 0.5 / 62)
    assert scores[1] == pytest.approx(0.5 / 61)


def test_empty_query_returns_empty() -> None:
    index = HybridIndex([("a", StubChannel([("doc", 1)]), 1.0)])
    assert index.search("  ") == []


def test_empty_channel_list_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one channel"):
        HybridIndex([])


def test_pages_keep_the_best_channel_hit_metadata() -> None:
    index = HybridIndex(
        [
            ("a", StubChannel([("doc", 1)]), 1.0),
            ("b", StubChannel([("doc", 1)]), 0.5),
        ]
    )

    hit = index.search("x")[0]

    assert hit.chunk_id == "doc:p1:c0"
    assert hit.channel == "a"
