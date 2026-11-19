from workers.retrieval.chunking import Page
from workers.retrieval.config import load_config
from workers.retrieval.documents import DocumentMeta
from workers.retrieval.index import BM25Index
from workers.retrieval.pipeline import build_channel


def test_config_declares_four_channels() -> None:
    config = load_config()
    assert set(config["channels"]) == {"bm25", "expanded", "dense", "hybrid"}
    assert config["default_channel"] in config["channels"]


def test_unknown_channel_is_rejected() -> None:
    config = load_config()
    try:
        build_channel("unknown", [], {}, config)
    except ValueError as exc:
        assert "unknown retrieval channel" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_expanded_channel_uses_the_configured_profile() -> None:
    config = load_config()
    pages = [
        Page("doc", 1, "合并及公司利润表\n营业收入 1"),
    ]
    documents = {"doc": DocumentMeta("doc", "AAA.HK", 2024, "annual_report")}
    index = build_channel("expanded", pages, documents, config)

    assert isinstance(index, BM25Index)
    assert index.profile is not None
    assert "营业" in index.profile.expanded_terms("毛利率")
