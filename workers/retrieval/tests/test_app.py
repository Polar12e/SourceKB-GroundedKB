from fastapi.testclient import TestClient

from workers.retrieval.app import app, create_app
from workers.retrieval.chunking import Page
from workers.retrieval.index import BM25Index

client = TestClient(app)


def test_healthz() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "retrieval"}


def test_search_without_corpus_returns_empty() -> None:
    response = client.post("/search", json={"query": "2023年营业成本为什么重述？"})

    assert response.status_code == 200
    assert response.json() == {"hits": []}


def test_search_returns_hits_with_locator() -> None:
    index = BM25Index.from_pages(
        [
            Page(
                "midea-2024",
                159,
                "合并及公司利润表\n营业收入 407,149,600\n营业成本 2,928,031",
            )
        ]
    )
    local = TestClient(create_app(index))

    response = local.post("/search", json={"query": "营业收入", "top_k": 3})

    assert response.status_code == 200
    hits = response.json()["hits"]
    assert hits
    assert hits[0]["document_id"] == "midea-2024"
    assert hits[0]["chunk_id"].startswith("midea-2024:p159:c")
    assert hits[0]["locator"]["page"] == 159
    assert hits[0]["locator"]["line_start"] >= 1
    assert "section" not in hits[0]["locator"]
    assert "营业收入" in hits[0]["text"]


def test_search_rejects_empty_query() -> None:
    response = client.post("/search", json={"query": ""})

    assert response.status_code == 422


def test_search_rejects_top_k_out_of_range() -> None:
    response = client.post("/search", json={"query": "x", "top_k": 0})

    assert response.status_code == 422
