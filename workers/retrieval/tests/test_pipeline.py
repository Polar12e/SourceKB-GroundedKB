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
    assert index.search("毛利率", top_k=1)[0].channels == ("expanded",)


def test_create_embedder_dispatches_lsa() -> None:
    from workers.embedding.embedding import LsaEmbedder
    from workers.retrieval.pipeline import create_embedder

    embedder = create_embedder({"provider": "lsa", "dim": 8})
    assert isinstance(embedder, LsaEmbedder)
    assert embedder.dim == 8


def test_create_embedder_dispatches_openai(monkeypatch) -> None:
    from workers.embedding.embedding import OpenAICompatibleEmbedder
    from workers.retrieval.pipeline import create_embedder

    monkeypatch.setenv("TEST_EMBED_KEY", "secret")
    embedder = create_embedder(
        {
            "provider": "openai",
            "model": "m",
            "base_url": "https://example.com/v1",
            "dim": 3,
            "api_key_env": "TEST_EMBED_KEY",
            "batch_size": 8,
            "timeout": 5,
            "retries": 0,
        }
    )
    assert isinstance(embedder, OpenAICompatibleEmbedder)
    assert embedder.model == "m"
    assert embedder.base_url == "https://example.com/v1"
    assert embedder.dim == 3
    assert embedder.batch_size == 8
    assert embedder.retries == 0


def test_create_embedder_requires_api_key(monkeypatch) -> None:
    from workers.retrieval.pipeline import create_embedder

    monkeypatch.delenv("TEST_MISSING_KEY", raising=False)
    try:
        create_embedder(
            {
                "provider": "openai",
                "model": "m",
                "base_url": "https://example.com/v1",
                "dim": 3,
                "api_key_env": "TEST_MISSING_KEY",
            }
        )
    except ValueError as exc:
        assert "missing embedding API key" in str(exc)
    else:
        raise AssertionError("expected missing API key error")
