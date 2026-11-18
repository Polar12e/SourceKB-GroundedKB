from fastapi.testclient import TestClient

from workers.retrieval.app import app

client = TestClient(app)


def test_healthz() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "retrieval"}


def test_search_returns_not_implemented() -> None:
    response = client.post(
        "/search",
        json={"query": "2023年营业成本为什么重述？", "top_k": 5},
    )

    assert response.status_code == 501
    assert response.json()["detail"] == "retrieval migration pending"


def test_search_rejects_empty_query() -> None:
    response = client.post("/search", json={"query": ""})

    assert response.status_code == 422


def test_search_rejects_top_k_out_of_range() -> None:
    response = client.post("/search", json={"query": "x", "top_k": 0})

    assert response.status_code == 422
