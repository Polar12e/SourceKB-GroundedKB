from pathlib import Path

import pytest

from workers.retrieval.config import load_config
from workers.retrieval.profile import ConfiguredProfile
from workers.retrieval.chunking import (
    Page,
    chunk_page_spans,
    chunk_pages,
    tokenize,
)
from workers.retrieval.corpus import load_pages_jsonl
from workers.retrieval.documents import DocumentMeta
from workers.retrieval.index import BM25Index
from workers.retrieval.windows import window_for_lines

FINANCE_PROFILE = load_config()["profiles"]["finance"]


def finance_profile(mode: str | None = None) -> ConfiguredProfile:
    settings = dict(FINANCE_PROFILE)
    if mode is not None:
        settings["mode"] = mode
    return ConfiguredProfile(settings)


class TestTokenize:
    def test_commas_in_numbers_are_removed(self) -> None:
        assert "2928031" in tokenize("2,928,031")

    def test_cjk_line_break_is_joined(self) -> None:
        assert "的净" in tokenize("归属于母公司股东的\n净利润")

    def test_bigrams(self) -> None:
        assert tokenize("营业收入") == ["营业", "业收", "收入"]

    def test_traditional_and_simplified_share_tokens(self) -> None:
        assert tokenize("營業收入") == tokenize("营业收入")


class TestChunking:
    def test_chunk_spans_are_line_aware(self) -> None:
        text = "第一行\n\n第二行\n第三行\n第四行"
        spans = chunk_page_spans(text, size=4, overlap=0)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        assert len(spans) > 1
        for piece, start, end in spans:
            assert start >= 1
            assert start <= end
            assert piece == "\n".join(lines[start - 1:end])
        assert spans[0][1] == 1

    def test_chunk_ids_are_stable(self) -> None:
        pages = [Page(document_id="doc-a", page=1, text="第一行\n第二行\n第三行")]
        first = chunk_pages(pages, size=4, overlap=0)
        second = chunk_pages(pages, size=4, overlap=0)
        assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
        assert first[0].chunk_id == "doc-a:p1:c0"


class TestBM25:
    def test_income_statement_lookup(self) -> None:
        pages = [
            Page(
                "midea-2024",
                159,
                "合并及公司利润表\n营业收入 407,149,600\n营业成本 2,928,031",
            ),
            Page(
                "midea-2024",
                199,
                "财务报表附注\n营业成本重述说明\n质保费重分类",
            ),
        ]
        index = BM25Index.from_pages(pages)

        hits = index.search("2024年营业收入是多少？", top_k=3)

        assert hits
        assert hits[0].page == 159
        assert hits[0].document_id == "midea-2024"
        assert hits[0].chunk_id.startswith("midea-2024:p159:c")
        assert "营业收入" in hits[0].text
        assert hits[0].line_start >= 1
        assert hits[0].line_end >= hits[0].line_start

    def test_traditional_document_matches_simplified_query(self) -> None:
        index = BM25Index.from_pages([Page("tencent", 1, "營業收入 1")])
        hits = index.search("营业收入", top_k=3)
        assert hits and hits[0].document_id == "tencent"

    def test_metadata_filters(self) -> None:
        documents = {
            "doc-a": DocumentMeta("doc-a", "AAA.HK", 2024, "annual_report"),
            "doc-b": DocumentMeta("doc-b", "BBB.HK", 2025, "interim_report"),
        }
        index = BM25Index.from_pages(
            [
                Page("doc-a", 1, "营业收入 1"),
                Page("doc-b", 1, "营业收入 2"),
            ],
            documents=documents,
        )

        assert {hit.document_id for hit in index.search("营业收入")} == {"doc-a", "doc-b"}
        assert [hit.document_id for hit in index.search("营业收入", filters={"company": "BBB.HK"})] == ["doc-b"]
        assert [hit.document_id for hit in index.search("营业收入", filters={"year": "2024"})] == ["doc-a"]
        assert [hit.document_id for hit in index.search("营业收入", filters={"doc_type": "interim_report"})] == ["doc-b"]
        assert [hit.document_id for hit in index.search("营业收入", filters={"document_id": "doc-a"})] == ["doc-a"]

    def test_unknown_or_invalid_filter_is_rejected(self) -> None:
        index = BM25Index.from_pages([Page("doc-a", 1, "营业收入 1")])
        with pytest.raises(ValueError, match="unknown filter"):
            index.search("营业收入", filters={"unknown": "x"})
        with pytest.raises(ValueError, match="year filter"):
            index.search("营业收入", filters={"year": "not-a-year"})

    def test_documents_with_same_page_number_do_not_collide(self) -> None:
        pages = [
            Page("doc-a", 1, "营业收入 1"),
            Page("doc-b", 1, "营业成本 2"),
        ]
        hits = BM25Index.from_pages(pages).search("营业成本", top_k=5)

        assert hits
        assert hits[0].document_id == "doc-b"
        assert hits[0].page == 1
        assert hits[0].chunk_id == "doc-b:p1:c0"

    def test_unknown_query_returns_empty(self) -> None:
        index = BM25Index.from_pages([Page("doc-a", 1, "营业收入 1")])
        assert index.search("xxyyzz") == []

    def test_empty_query_returns_empty(self) -> None:
        index = BM25Index.from_pages([Page("doc-a", 1, "营业收入 1")])
        assert index.search("   ") == []

    def test_duplicate_page_is_rejected(self) -> None:
        pages = [Page("doc-a", 1, "a"), Page("doc-a", 1, "b")]
        with pytest.raises(ValueError, match="duplicate page"):
            BM25Index.from_pages(pages)


class TestCorpus:
    def test_sample_corpus_loads(self) -> None:
        pages = load_pages_jsonl(
            Path(__file__).parent / "fixtures" / "sample_pages.jsonl"
        )

        assert [page.page for page in pages] == [1, 2]
        assert pages[0].document_id == "demo-2024"
        assert "营业收入" in pages[0].text


class TestFinanceProfile:
    def test_restatement_expands_to_accounting_terms(self) -> None:
        terms = finance_profile().expanded_terms("2023年营业成本为什么重述？")

        assert "会计" in terms
        assert "分类" in terms
        assert "期间" in terms

    def test_none_mode_disables_builtin_expansion(self) -> None:
        profile = finance_profile("none")
        assert profile.expanded_terms("毛利率是多少") == {}

    def test_lexicon_mode_adds_colloquial_terms(self) -> None:
        profile = finance_profile("lexicon")
        terms = profile.expanded_terms("仓库里压了多少货")
        assert "存货" in terms
        assert "库存" in terms

    def test_auto_mode_only_rewrites_under_oov_pressure(self) -> None:
        profile = finance_profile("auto")
        assert "存货" in profile.expanded_terms("仓库里压了多少货", coverage=0.2)
        assert "存货" not in profile.expanded_terms("存货是多少", coverage=0.9)

    def test_invalid_mode_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="mode"):
            finance_profile("magic")

    def test_statement_prior_is_disabled_for_notes_questions(self) -> None:
        profile = finance_profile()
        page = "合并及公司利润表\n营业收入 1"
        assert profile.page_prior("营业收入是多少", page) > 0
        assert profile.page_prior("营业收入为什么变化", page) == 0

    def test_finance_profile_prefers_the_statement_page(self) -> None:
        pages = [
            Page("doc", 1, "合并及公司利润表\n营业收入 1"),
            Page("doc", 2, "附注\n营业收入 1\n营业收入 2\n营业收入 3\n营业收入 4\n营业收入 5"),
        ]

        generic = BM25Index.from_pages(pages)
        finance = BM25Index.from_pages(pages, profile=finance_profile())

        assert generic.search("营业收入是多少")[0].page == 2
        assert finance.search("营业收入是多少")[0].page == 1


class TestWindow:
    def test_window_crosses_the_best_chunk_boundary(self) -> None:
        text = "标题\n表头\n销售费用 1\n营业成本 2\n三 税项"
        spans = chunk_page_spans(text, size=8, overlap=0)
        piece, start, end = next(span for span in spans if "销售费用" in span[0])

        window = window_for_lines(text, start, end, radius=2, max_chars=900)

        assert piece == "销售费用 1"
        assert "销售费用 1" in window.text
        assert "营业成本 2" in window.text
        assert window.line_start == 1
        assert window.line_end >= 4

    def test_window_falls_back_to_chunk_text_without_line_metadata(self) -> None:
        window = window_for_lines("", 1, 1, fallback_text="b\nc", radius=1)

        assert "b" in window.text
        assert "c" in window.text
