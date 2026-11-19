from pathlib import Path

from eval.fingerprint import fingerprint


def test_fingerprint_covers_every_changing_input() -> None:
    root = Path(__file__).resolve().parents[2]
    payload = fingerprint(
        root / "workers" / "retrieval" / "tests" / "fixtures" / "sample_pages.jsonl",
        root / "eval" / "datasets" / "finance_midea_v1.json",
    )

    assert len(payload["corpus_sha256"]) == 64
    assert len(payload["config_sha256"]) == 64
    assert len(payload["cases_sha256"]) == 64
    assert payload["git_rev"]
    assert "domains/finance/terms.json" in payload["terms_sha256"]
