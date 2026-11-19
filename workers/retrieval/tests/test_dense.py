import numpy as np
import pytest

from workers.embedding.embedding import EmbeddingCache, unit_normalize
from workers.retrieval.chunking import Page
from workers.retrieval.dense import DenseIndex
from workers.retrieval.documents import DocumentMeta
from workers.retrieval.fusion import HybridIndex
from workers.retrieval.index import BM25Index

PAGES = [
    Page("doc-a", 1, "合并及公司资产负债表\n存货 63,339,188"),
    Page("doc-b", 1, "合并及公司利润表\n营业收入 407,149,600"),
]
DOCUMENTS = {
    "doc-a": DocumentMeta("doc-a", "AAA.HK", 2024, "annual_report"),
    "doc-b": DocumentMeta("doc-b", "BBB.HK", 2025, "annual_report"),
}


class ConceptEmbedder:
    name = "fake-concepts"
    dim = 2

    def encode(self, texts):
        rows = []
        for text in texts:
            row = [0.0, 0.0]
            if any(word in text for word in ("存货", "库存", "仓库", "货")):
                row[0] = 1.0
            if any(word in text for word in ("收入", "营收")):
                row[1] = 1.0
            rows.append(row)
        return unit_normalize(np.array(rows, dtype=np.float32))


def build_index(tmp_path) -> DenseIndex:
    return DenseIndex.from_pages(
        PAGES,
        ConceptEmbedder(),
        cache=EmbeddingCache(tmp_path),
        documents=DOCUMENTS,
    )


def test_dense_finds_semantic_match(tmp_path) -> None:
    hits = build_index(tmp_path).search("仓库里压了多少货", top_k=3)

    assert hits
    assert hits[0].document_id == "doc-a"
    assert hits[0].channel == "dense"


def test_dense_applies_metadata_filters(tmp_path) -> None:
    hits = build_index(tmp_path).search(
        "营业收入",
        top_k=3,
        filters={"company": "BBB.HK"},
    )

    assert [hit.document_id for hit in hits] == ["doc-b"]


def test_dense_empty_query_returns_empty(tmp_path) -> None:
    assert build_index(tmp_path).search("   ") == []


def test_dense_vector_row_count_is_validated() -> None:
    with pytest.raises(ValueError, match="one row per chunk"):
        DenseIndex([], {}, np.zeros((1, 2), dtype=np.float32), ConceptEmbedder(), {})


def test_hybrid_uses_dense_when_bm25_misses(tmp_path) -> None:
    dense = build_index(tmp_path)
    lexical = BM25Index.from_pages(PAGES, documents=DOCUMENTS)
    hybrid = HybridIndex([("bm25", lexical, 1.0), ("dense", dense, 0.5)])

    assert lexical.search("仓库里压了多少货") == []
    assert hybrid.search("仓库里压了多少货", top_k=1)[0].document_id == "doc-a"
