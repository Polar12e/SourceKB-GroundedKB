"""Build the generic four retrieval channels from configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping

from workers.embedding.embedding import (
    EmbeddingCache,
    Embedder,
    LsaEmbedder,
    OpenAICompatibleEmbedder,
)

from .chunking import Page
from .config import load_config
from .dense import DenseIndex
from .documents import DocumentMeta
from .fusion import HybridIndex
from .index import BM25Index
from .profile import profile_from_config

CHANNELS = ("bm25", "expanded", "dense", "hybrid")


def create_embedder(settings: Mapping) -> Embedder:
    """Dispatch dense provider settings to an Embedder instance.

    LSA is offline and default. OpenAI-compatible endpoints require an explicit
    base_url/model/dim and read the API key from an environment variable; keys
    never appear in the YAML config.
    """

    provider = str(settings.get("provider") or "lsa").lower()
    if provider == "lsa":
        return LsaEmbedder(dim=int(settings.get("dim") or 192))

    if provider == "openai":
        api_key_env = str(settings.get("api_key_env") or "OPENAI_API_KEY")
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(
                f"missing embedding API key: set {api_key_env} in the environment"
            )
        return OpenAICompatibleEmbedder(
            model=str(settings["model"]),
            base_url=str(settings["base_url"]),
            api_key=api_key,
            dim=int(settings["dim"]),
            batch_size=int(settings.get("batch_size") or 64),
            timeout=float(settings.get("timeout") or 30.0),
            retries=int(settings.get("retries") if settings.get("retries") is not None else 2),
        )

    raise ValueError(f"unsupported dense provider: {provider}")


def build_channel(
    name: str,
    pages: list[Page],
    documents: Mapping[str, DocumentMeta],
    config: Mapping,
    *,
    cache: EmbeddingCache | None = None,
):
    """Instantiate one channel by name.

    ``bm25``      lexical only
    ``expanded``  lexical + configurable query profile
    ``dense``     embedding cosine
    ``hybrid``    weighted RRF over configured sub-channels
    """

    channels = config.get("channels", {})
    if name not in channels:
        raise ValueError(f"unknown retrieval channel: {name}")
    settings = channels[name] or {}
    bm25_settings = config.get("bm25", {})
    window = config.get("window", {})
    common = {
        "k1": float(bm25_settings.get("k1", 1.5)),
        "b": float(bm25_settings.get("b", 0.75)),
        "window_radius": int(window.get("radius", 2)),
        "window_max_chars": int(window.get("max_chars", 900)),
        "documents": documents,
    }

    if name == "bm25":
        return BM25Index.from_pages(pages, **common)

    if name == "expanded":
        profile_name = settings.get("profile")
        profile = (
            profile_from_config(config, str(profile_name))
            if profile_name
            else None
        )
        return BM25Index.from_pages(pages, profile=profile, **common)

    if name == "dense":
        embedder = create_embedder(settings)
        return DenseIndex.from_pages(
            pages,
            embedder,
            cache=cache or EmbeddingCache(),
            window_radius=common["window_radius"],
            window_max_chars=common["window_max_chars"],
            documents=documents,
        )

    if name == "hybrid":
        specifications = settings.get("channels") or {}
        if not specifications:
            raise ValueError("hybrid channel needs channels weights")
        sub_channels = [
            (
                sub_name,
                build_channel(sub_name, pages, documents, config, cache=cache),
                float(weight),
            )
            for sub_name, weight in specifications.items()
        ]
        rrf = config.get("rrf", {})
        return HybridIndex(
            sub_channels,
            k=int(rrf.get("k", 60)),
            depth=int(rrf.get("depth", 60)),
        )

    raise ValueError(f"unknown retrieval channel: {name}")


def build_default_channel(
    pages: list[Page],
    documents: Mapping[str, DocumentMeta],
    config_path: str | None = None,
    *,
    channel: str | None = None,
    cache: EmbeddingCache | None = None,
):
    config = load_config(config_path)
    return build_channel(
        channel or str(config["default_channel"]),
        pages,
        documents,
        config,
        cache=cache,
    )


__all__ = ["CHANNELS", "build_channel", "build_default_channel"]
