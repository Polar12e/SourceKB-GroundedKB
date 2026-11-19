"""Retrieval evaluation over GroundedKB EvalCase files."""

from __future__ import annotations

import argparse
import json
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

DEFAULT_CASES = ROOT / "eval" / "datasets" / "finance_midea_v1.json"
DEFAULT_CORPUS = ROOT / "data" / "private" / "corpus" / "midea-2024.jsonl"


@dataclass(frozen=True)
class CaseMetrics:
    hit_at_k: float
    recall_at_k: float
    mrr: float
    precision_at_k: float
    rank: int | None
    top_keys: list[tuple[str, int]]
    gold_keys: list[tuple[str, int]]


def gold_keys(case: dict) -> list[tuple[str, int]]:
    return [(item["document_id"], int(item["page"])) for item in case["gold_evidence"]]


def evaluate_case(hits: list[SearchHit], case: dict, top_k: int) -> CaseMetrics:
    gold = gold_keys(case)
    gold_set = set(gold)
    ranked = hits[:top_k]
    keys = [(hit.document_id, hit.page) for hit in ranked]
    rank = next(
        (position for position, key in enumerate(keys, start=1) if key in gold_set),
        None,
    )
    found = len(gold_set & set(keys))
    return CaseMetrics(
        hit_at_k=1.0 if rank else 0.0,
        recall_at_k=found / len(gold_set) if gold_set else 0.0,
        mrr=1.0 / rank if rank else 0.0,
        precision_at_k=found / len(keys) if keys else 0.0,
        rank=rank,
        top_keys=keys,
        gold_keys=gold,
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

    lines = [
        "# Retrieval eval",
        "",
        f"- cases: `{cases_path.name}` ({total})",
        f"- corpus: `{corpus}`",
        f"- top_k: {top_k}",
        f"- **Hit@{top_k}: {hit:.3f}**",
        f"- **Recall@{top_k}: {recall:.3f}**",
        f"- **MRR: {mrr:.3f}**",
        f"- precision@{top_k}: {precision:.3f}",
        "",
        f"| case | rank | hit@{top_k} | recall@{top_k} | mrr | top pages | gold pages |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for case, metric in zip(cases, results, strict=True):
        top = ", ".join(f"{doc}:{page}" for doc, page in metric.top_keys[:top_k]) or "-"
        gold = ", ".join(f"{doc}:{page}" for doc, page in metric.gold_keys)
        rank = str(metric.rank) if metric.rank else "miss"
        lines.append(
            f"| {case['case_id']} | {rank} | {metric.hit_at_k:.0f} | "
            f"{metric.recall_at_k:.2f} | {metric.mrr:.3f} | {top} | {gold} |"
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
        evaluate_case(index.search(case["question"], top_k=args.top_k), case, args.top_k)
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
    payload = {
        "cases": args.cases.name,
        "corpus": str(args.corpus),
        "channel": args.channel or str(config["default_channel"]),
        "top_k": args.top_k,
        "summary": {
            "hit_at_k": sum(item.hit_at_k for item in results) / len(results),
            "recall_at_k": sum(item.recall_at_k for item in results) / len(results),
            "mrr": sum(item.mrr for item in results) / len(results),
            "precision_at_k": sum(item.precision_at_k for item in results) / len(results),
        },
        "rows": [
            {
                "case_id": case["case_id"],
                "rank": metric.rank,
                "hit_at_k": metric.hit_at_k,
                "recall_at_k": metric.recall_at_k,
                "mrr": metric.mrr,
                "precision_at_k": metric.precision_at_k,
                "top_keys": metric.top_keys,
                "gold_keys": metric.gold_keys,
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
