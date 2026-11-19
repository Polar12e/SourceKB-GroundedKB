import json
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from workers.retrieval.config import load_config
from workers.retrieval.profile import ConfiguredProfile
from workers.retrieval.app import create_app
from workers.retrieval.corpus import load_pages_jsonl
from workers.retrieval.index import BM25Index

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "contracts" / "schemas"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_pages.jsonl"


def schema_registry() -> Registry:
    registry = Registry()
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(schema["$id"], resource)
        registry = registry.with_resource(path.as_uri(), resource)
    return registry


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_health_matches_contract() -> None:
    validator = Draft202012Validator(load_schema("health.schema.json"))
    validator.validate(TestClient(create_app()).get("/healthz").json())


def test_search_response_matches_contract() -> None:
    index = BM25Index.from_pages(
        load_pages_jsonl(FIXTURE),
        profile=ConfiguredProfile(load_config()["profiles"]["finance"]),
    )
    response = TestClient(create_app(index)).post(
        "/search",
        json={"query": "营业成本重述", "top_k": 3},
    )

    assert response.status_code == 200
    Draft202012Validator(
        load_schema("search-response.schema.json"),
        registry=schema_registry(),
    ).validate(response.json())
