import json

import numpy as np

from workers.embedding.embedding import (
    EmbeddingCache,
    LsaEmbedder,
    OpenAICompatibleEmbedder,
    corpus_fingerprint,
    embed_documents,
    unit_normalize,
)

FIT = [
    ["存货", "库存", "商品", "存货"],
    ["存货", "库存", "销售", "商品"],
    ["员工", "薪酬", "工资", "员工"],
    ["员工", "人数", "薪酬", "工资"],
    ["营业收入", "销售", "商品", "库存"],
]


def test_unit_normalize_handles_zero_rows() -> None:
    vectors = unit_normalize(np.array([[3.0, 4.0], [0.0, 0.0]], dtype=np.float32))
    assert np.allclose(vectors[0], [0.6, 0.8])
    assert np.allclose(vectors[1], [0.0, 0.0])


def test_lsa_fit_and_encode_are_unit_normalized() -> None:
    embedder = LsaEmbedder(dim=2, min_df=1, max_df_ratio=1.0).fit(FIT)
    vectors = embedder.encode(["存货库存", "员工薪酬"])

    assert vectors.shape == (2, 2)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)


def test_cache_roundtrip(tmp_path) -> None:
    cache = EmbeddingCache(tmp_path)
    vectors = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    key = cache.key("fake", "fingerprint", 2, 2)

    cache.save(key, vectors)
    loaded = cache.load(key, 2, 2)

    assert loaded is not None
    assert np.allclose(loaded, vectors)


def test_corpus_fingerprint_changes_with_content() -> None:
    assert corpus_fingerprint(["a", "b"]) != corpus_fingerprint(["a", "c"])


def test_openai_compatible_embedder_with_fake_transport() -> None:
    def transport(request, timeout):
        payload = json.loads(request.data)
        data = [
            {"index": index, "embedding": [1.0, float(index + 1)]}
            for index, _ in enumerate(payload["input"])
        ]
        return json.dumps({"data": data}).encode("utf-8")

    embedder = OpenAICompatibleEmbedder(
        model="fake",
        base_url="http://fake",
        dim=2,
        batch_size=2,
        transport=transport,
    )
    vectors = embedder.encode(["a", "b", "c"])

    assert vectors.shape == (3, 2)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)


def test_embed_documents_uses_cache(tmp_path) -> None:
    embedder = LsaEmbedder(dim=2, min_df=1, max_df_ratio=1.0).fit(FIT)
    cache = EmbeddingCache(tmp_path)
    texts = ["存货", "员工"]
    first = embed_documents(texts, embedder, cache=cache, fit_on=FIT)
    second = embed_documents(texts, embedder, cache=cache, fit_on=FIT)

    assert np.allclose(first, second)
    assert first.shape == (2, 2)
