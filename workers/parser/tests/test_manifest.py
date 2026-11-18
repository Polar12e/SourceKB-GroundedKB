import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "data" / "manifests" / "documents.json"


def load_manifest() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_has_ten_unique_documents() -> None:
    entries = load_manifest()

    assert len(entries) == 10
    ids = [entry["document_id"] for entry in entries]
    assert len(ids) == len(set(ids))


def test_manifest_metadata_is_complete() -> None:
    for entry in load_manifest():
        assert entry["page_count"] > 0
        assert entry["text_chars"] > 0
        assert len(entry["sha256"]) == 64
        assert entry["text_quality"] in {"high", "low", "ocr"}
        assert entry["doc_type"] in {"annual_report", "interim_report"}
