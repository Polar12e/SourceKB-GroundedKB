"""Retrieval evaluation over GroundedKB EvalCase files."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workers.retrieval.config import load_config  # noqa: E402
from workers.retrieval.corpus import load_pages_jsonl  # noqa: E402
from workers.retrieval.documents import load_documents_manifest  # noqa: E402
from workers.retrieval.index import SearchHit  # noqa: E402
from workers.retrieval.pipeline import build_channel  # noqa: E402
from eval.fingerprint import fingerprint  # noqa: E402

DEFAULT_CASES = ROOT / "eval" / "datasets" / "finance_midea_v1.json"
DEFAULT_CORPUS = ROOT / "data" / "private" / "corpus" / "midea-2024.jsonl"


@dataclass(frozen=True)
class CaseMetrics:
    # Page-level metrics (kept for continuity with previous reports).
    hit_at_k: float
    recall_at_k: float
    mrr: float
    precision_at_k: float
    rank: int | None
    top_keys: list[tuple[str, int]]
    gold_keys: list[tuple[str, int]]
    acceptable_keys: list[tuple[str, int]]
    # Evidence-level metrics: anchor chunk must overlap a gold/acceptable line range.
    chunk_hit_at_k: float
    chunk_recall_at_k: float
    chunk_rank: int | None
    ndcg_at_10: float
    top_chunks: list[str]
    hard_negative_hits: int


def gold_keys(case: dict) -> list[tuple[str, int]]:
    return [(item["document_id"], int(item["page"])) for item in case["gold_evidence"]]


def _ranges(case: dict, *, include_acceptable: bool) -> list[tuple[str, int, int, int]]:
    items = list(case["gold_evidence"])
    if include_acceptable:
        items += case.get("acceptable_evidence", [])
    return [
        (
            item["document_id"],
            int(item["page"]),
            int(item["line_start"]),
            int(item["line_end"]),
        )
        for item in items
    ]


def _anchor(hit: SearchHit) -> tuple[int, int]:
    start = hit.anchor_start if hit.anchor_start is not None else hit.line_start
    end = hit.anchor_end if hit.anchor_end is not None else hit.line_end
    return start, end


def _overlaps(start: int, end: int, gold_start: int, gold_end: int) -> bool:
    return not (end < gold_start or gold_end < start)


def _chunk_relevant(hit: SearchHit, ranges: list[tuple[str, int, int, int]]) -> bool:
    start, end = _anchor(hit)
    return any(
        hit.document_id == document_id
        and hit.page == page
        and _overlaps(start, end, gold_start, gold_end)
        for document_id, page, gold_start, gold_end in ranges
    )


def _ndcg_at_10(hits: list[SearchHit], canonical_ranges: list[tuple[str, int, int, int]]) -> float:
    if not canonical_ranges:
        return 0.0
    remaining = list(canonical_ranges)
    dcg = 0.0
    for position, hit in enumerate(hits[:10], start=1):
        covered = [item for item in remaining if _chunk_relevant(hit, [item])]
        if covered:
            dcg += 1.0 / math.log2(position + 1)
            remaining.remove(covered[0])
    ideal = sum(
        1.0 / math.log2(position + 1)
        for position in range(1, min(len(canonical_ranges), 10) + 1)
    )
    return dcg / ideal if ideal else 0.0


def evaluate_case(hits: list[SearchHit], case: dict, top_k: int) -> CaseMetrics:
    canonical = set(gold_keys(case))
    acceptable = canonical | {
        (item["document_id"], int(item["page"]))
        for item in case.get("acceptable_evidence", [])
    }
    hard_negatives = {
        (item["document_id"], int(item["page"]))
        for item in case.get("hard_negatives", [])
    }
    ranked = hits[:top_k]
    keys = [(hit.document_id, hit.page) for hit in ranked]
    rank = next(
        (position for position, key in enumerate(keys, start=1) if key in acceptable),
        None,
    )
    acceptable_ranges = _ranges(case, include_acceptable=True)
    canonical_ranges = _ranges(case, include_acceptable=False)
    chunk_rank = next(
        (
            position
            for position, hit in enumerate(ranked, start=1)
            if _chunk_relevant(hit, acceptable_ranges)
        ),
        None,
    )
    covered = sum(
        1 for item in canonical_ranges
        if any(_chunk_relevant(hit, [item]) for hit in ranked)
    )
    canonical_found = len(canonical & set(keys))
    acceptable_found = len(acceptable & set(keys))
    return CaseMetrics(
        hit_at_k=1.0 if rank else 0.0,
        recall_at_k=canonical_found / len(canonical) if canonical else 0.0,
        mrr=1.0 / rank if rank else 0.0,
        precision_at_k=acceptable_found / len(keys) if keys else 0.0,
        rank=rank,
        top_keys=keys,
        gold_keys=sorted(canonical),
        acceptable_keys=sorted(acceptable),
        chunk_hit_at_k=1.0 if chunk_rank else 0.0,
        chunk_recall_at_k=covered / len(canonical_ranges) if canonical_ranges else 0.0,
        chunk_rank=chunk_rank,
        ndcg_at_10=_ndcg_at_10(ranked, canonical_ranges),
        top_chunks=[hit.chunk_id for hit in ranked],
        hard_negative_hits=len(hard_negatives & set(keys)),
    )


def load_cases(path: Path) -> list[dict]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path}: expected a non-empty JSON array")
    for case in cases:
        missing = {"case_id", "question", "type", "gold_evidence", "split"} - set(case)
        if missing:
            raise ValueError(f"{path}: case missing {sorted(missing)}")
    return cases


def build_markdown(
    cases: list[dict],
    results: list[CaseMetrics],
    *,
    top_k: int,
    corpus: Path,
    cases_path: Path,
) -> str:
    total = len(results)
    hit = sum(item.hit_at_k for item in results) / total
    recall = sum(item.recall_at_k for item in results) / total
    mrr = sum(item.mrr for item in results) / total
    precision = sum(item.precision_at_k for item in results) / total
    chunk_hit = sum(item.chunk_hit_at_k for item in results) / total
    chunk_recall = sum(item.chunk_recall_at_k for item in results) / total
    ndcg = sum(item.ndcg_at_10 for item in results) / total
    fp = fingerprint(corpus, cases_path)

    lines = [
        "# Retrieval eval",
        "",
        f"- cases: `{cases_path.name}` ({total})",
        f"- corpus: `{corpus}`",
        f"- top_k: {top_k}",
        f"- corpus_sha256: `{fp['corpus_sha256']}`",
        f"- config_sha256: `{fp['config_sha256']}`",
        f"- cases_sha256: `{fp['cases_sha256']}`",
        f"- git_rev: `{fp['git_rev']}`",
        f"- **page Hit@{top_k}: {hit:.3f}**",
        f"- **chunk Hit@{top_k}: {chunk_hit:.3f}**",
        f"- page Recall@{top_k}: {recall:.3f}",
        f"- chunk Recall@{top_k}: {chunk_recall:.3f}",
        f"- page MRR: {mrr:.3f}",
        f"- chunk nDCG@10: {ndcg:.3f}",
        f"- page precision@{top_k}: {precision:.3f}",
        "",
        f"| case | page rank | chunk rank | page hit | chunk hit | page recall | chunk recall | nDCG@10 | top chunks | gold pages |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for case, metric in zip(cases, results, strict=True):
        top = ", ".join(metric.top_chunks[:top_k]) or "-"
        gold = ", ".join(f"{doc}:{page}" for doc, page in metric.gold_keys)
        page_rank = str(metric.rank) if metric.rank else "miss"
        chunk_rank = str(metric.chunk_rank) if metric.chunk_rank else "miss"
        lines.append(
            f"| {case['case_id']} | {page_rank} | {chunk_rank} | {metric.hit_at_k:.0f} | "
            f"{metric.chunk_hit_at_k:.0f} | {metric.recall_at_k:.2f} | "
            f"{metric.chunk_recall_at_k:.2f} | {metric.ndcg_at_10:.3f} | {top} | {gold} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--channel", default=None, help="bm25|expanded|dense|hybrid")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "manifests" / "documents.json",
    )
    parser.add_argument("--out", type=Path, default=ROOT / "eval-results" / "retrieval_midea_v1.md")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=ROOT / "eval-results" / "retrieval_midea_v1.json",
    )
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    if not args.corpus.exists():
        raise SystemExit(f"corpus not found: {args.corpus}")
    config = load_config()
    pages = load_pages_jsonl(args.corpus)
    documents = (
        load_documents_manifest(args.manifest) if args.manifest.exists() else {}
    )
    index = build_channel(
        args.channel or str(config["default_channel"]),
        pages,
        documents,
        config,
    )

    results = [
        evaluate_case(index.search(case["question"], top_k=args.top_k, filters=case.get("filters")), case, args.top_k)
        for case in cases
    ]
    markdown = build_markdown(
        cases,
        results,
        top_k=args.top_k,
        corpus=args.corpus,
        cases_path=args.cases,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown, encoding="utf-8")
    fp = fingerprint(args.corpus, args.cases)
    payload = {
        "cases": args.cases.name,
        "corpus": str(args.corpus),
        "channel": args.channel or str(config["default_channel"]),
        "top_k": args.top_k,
        "fingerprint": fp,
        "summary": {
            "hit_at_k": sum(item.hit_at_k for item in results) / len(results),
            "recall_at_k": sum(item.recall_at_k for item in results) / len(results),
            "mrr": sum(item.mrr for item in results) / len(results),
            "precision_at_k": sum(item.precision_at_k for item in results) / len(results),
            "chunk_hit_at_k": sum(item.chunk_hit_at_k for item in results) / len(results),
            "chunk_recall_at_k": sum(item.chunk_recall_at_k for item in results) / len(results),
            "ndcg_at_10": sum(item.ndcg_at_10 for item in results) / len(results),
        },
        "rows": [
            {
                "case_id": case["case_id"],
                "rank": metric.rank,
                "hit_at_k": metric.hit_at_k,
                "recall_at_k": metric.recall_at_k,
                "mrr": metric.mrr,
                "precision_at_k": metric.precision_at_k,
                "chunk_hit_at_k": metric.chunk_hit_at_k,
                "chunk_recall_at_k": metric.chunk_recall_at_k,
                "chunk_rank": metric.chunk_rank,
                "ndcg_at_10": metric.ndcg_at_10,
                "top_keys": metric.top_keys,
                "top_chunks": metric.top_chunks,
                "gold_keys": metric.gold_keys,
                "acceptable_keys": metric.acceptable_keys,
                "hard_negative_hits": metric.hard_negative_hits,
            }
            for case, metric in zip(cases, results, strict=True)
        ],
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
