from eval.run_retrieval import evaluate_case
from workers.retrieval.index import SearchHit


def hit(document_id: str, page: int) -> SearchHit:
    return SearchHit(
        chunk_id=f"{document_id}:p{page}:c0",
        document_id=document_id,
        page=page,
        line_start=1,
        line_end=1,
        text=f"{document_id} {page}",
        score=1.0,
    )


CASE = {
    "case_id": "test-1",
    "gold_evidence": [
        {"document_id": "doc", "page": 1, "line_start": 1, "line_end": 1},
        {"document_id": "doc", "page": 2, "line_start": 1, "line_end": 1},
    ],
}


def test_perfect_hit() -> None:
    metrics = evaluate_case([hit("doc", 1), hit("doc", 2)], CASE, top_k=4)

    assert metrics.hit_at_k == 1.0
    assert metrics.recall_at_k == 1.0
    assert metrics.mrr == 1.0
    assert metrics.rank == 1


def test_partial_recall() -> None:
    metrics = evaluate_case([hit("doc", 9), hit("doc", 2)], CASE, top_k=4)

    assert metrics.hit_at_k == 1.0
    assert metrics.recall_at_k == 0.5
    assert metrics.mrr == 0.5
    assert metrics.rank == 2


def test_miss() -> None:
    metrics = evaluate_case([hit("doc", 9)], CASE, top_k=4)

    assert metrics.hit_at_k == 0.0
    assert metrics.recall_at_k == 0.0
    assert metrics.mrr == 0.0
    assert metrics.rank is None


def test_acceptable_evidence_counts_as_hit_but_not_canonical_recall() -> None:
    case = dict(CASE)
    case["acceptable_evidence"] = [
        {"document_id": "doc", "page": 3, "line_start": 1, "line_end": 1}
    ]
    case["hard_negatives"] = [
        {"document_id": "doc", "page": 9, "line_start": 1, "line_end": 1}
    ]

    metrics = evaluate_case([hit("doc", 3), hit("doc", 9)], case, top_k=4)

    assert metrics.hit_at_k == 1.0
    assert metrics.recall_at_k == 0.0
    assert metrics.rank == 1
    assert metrics.hard_negative_hits == 1


def test_hard_negative_does_not_count_as_hit() -> None:
    case = dict(CASE)
    case["hard_negatives"] = [
        {"document_id": "doc", "page": 9, "line_start": 1, "line_end": 1}
    ]

    metrics = evaluate_case([hit("doc", 9)], case, top_k=4)

    assert metrics.hit_at_k == 0.0
    assert metrics.hard_negative_hits == 1


def test_chunk_hit_requires_anchor_overlap() -> None:
    case = {
        "case_id": "anchor",
        "gold_evidence": [
            {"document_id": "doc", "page": 1, "line_start": 5, "line_end": 6}
        ],
    }
    wrong_chunk = SearchHit(
        chunk_id="doc:p1:c0",
        document_id="doc",
        page=1,
        line_start=1,
        line_end=8,
        anchor_start=1,
        anchor_end=2,
        text="context",
        anchor_text="wrong",
        score=1.0,
    )

    metrics = evaluate_case([wrong_chunk], case, top_k=4)

    assert metrics.hit_at_k == 1.0
    assert metrics.chunk_hit_at_k == 0.0
    assert metrics.rank == 1
    assert metrics.chunk_rank is None
