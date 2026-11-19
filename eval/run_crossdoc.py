"""Cross-document A/B with per-company, split and filter-correctness results."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.run_retrieval import evaluate_case, load_cases  # noqa: E402
from workers.retrieval.config import load_config  # noqa: E402
from workers.retrieval.corpus import load_pages_jsonl  # noqa: E402
from workers.retrieval.documents import load_documents_manifest  # noqa: E402
from workers.retrieval.filters import matches_filters  # noqa: E402
from workers.retrieval.pipeline import build_channel  # noqa: E402

CHANNELS = ("bm25", "expanded", "dense", "hybrid")


def summarize(metrics: list) -> dict:
    total = len(metrics)
    return {
        "n": total,
        "hit_at_k": sum(item.hit_at_k for item in metrics) / total,
        "recall_at_k": sum(item.recall_at_k for item in metrics) / total,
        "mrr": sum(item.mrr for item in metrics) / total,
        "precision_at_k": sum(item.precision_at_k for item in metrics) / total,
        "hard_negative_hits": sum(item.hard_negative_hits for item in metrics),
    }


def run_channel(name, pages, documents, config, cases, top_k):
    started = time.perf_counter()
    index = build_channel(name, pages, documents, config)
    build_seconds = time.perf_counter() - started
    groups: dict[str, list] = defaultdict(list)
    filter_ok = True
    for case in cases:
        filters = case.get("filters") or {}
        hits = index.search(case["question"], top_k=top_k, filters=filters)
        if any(not matches_filters(hit.document_id, documents, filters) for hit in hits):
            filter_ok = False
        metric = evaluate_case(hits, case, top_k)
        groups[f"company:{filters.get('company', 'all')}"].append(metric)
        groups[f"split:{case['split']}"].append(metric)
    return {
        "channel": name,
        "build_seconds": build_seconds,
        "filter_ok": filter_ok,
        "overall": None,
        "groups": {key: summarize(values) for key, values in groups.items()},
    }


def channel_overall(rows: list) -> dict:
    # Each case is counted once in "overall"; compute from company groups with
    # weighted n (company groups partition the cases).
    company_groups = [value for key, value in rows["groups"].items() if key.startswith("company:")]
    total = sum(group["n"] for group in company_groups)
    return {
        "n": total,
        "hit_at_k": sum(group["hit_at_k"] * group["n"] for group in company_groups) / total,
        "recall_at_k": sum(group["recall_at_k"] * group["n"] for group in company_groups) / total,
        "mrr": sum(group["mrr"] * group["n"] for group in company_groups) / total,
        "precision_at_k": sum(group["precision_at_k"] * group["n"] for group in company_groups) / total,
        "hard_negative_hits": sum(group["hard_negative_hits"] for group in company_groups),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "eval" / "datasets" / "finance_crossdoc_v1.json")
    parser.add_argument("--corpus", type=Path, default=ROOT / "data" / "private" / "corpus" / "pages.jsonl")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "manifests" / "documents.json")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--channels", default=",".join(CHANNELS))
    parser.add_argument("--out", type=Path, default=ROOT / "eval-results" / "crossdoc_ab.md")
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    pages = load_pages_jsonl(args.corpus)
    documents = load_documents_manifest(args.manifest)
    config = load_config()
    requested = [name.strip() for name in args.channels.split(",") if name.strip()]
    rows = [
        run_channel(name, pages, documents, config, cases, args.top_k)
        for name in requested
    ]
    for row in rows:
        row["overall"] = channel_overall(row)

    companies = sorted({case["filters"]["company"] for case in cases if case.get("filters")})
    splits = sorted({case["split"] for case in cases})
    lines = [
        "# Cross-document retrieval A/B",
        "",
        f"- cases: `{args.cases.name}` ({len(cases)})",
        f"- corpus: `{args.corpus}`",
        f"- top_k: {args.top_k}",
        "",
        "## Overall",
        "",
        f"| channel | build s | Hit@{args.top_k} | Recall@{args.top_k} | MRR | precision@{args.top_k} | hard_neg | filters |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        item = row["overall"]
        lines.append(
            f"| {row['channel']} | {row['build_seconds']:.2f} | {item['hit_at_k']:.3f} | "
            f"{item['recall_at_k']:.3f} | {item['mrr']:.3f} | {item['precision_at_k']:.3f} | "
            f"{item['hard_negative_hits']} | {'OK' if row['filter_ok'] else 'FAIL'} |"
        )

    for title, prefix, keys in (
        ("By company", "company:", companies),
        ("By split", "split:", splits),
    ):
        lines += ["", f"## {title}", "", "| channel | " + " | ".join(keys) + " |", "|---|" + "---:|" * len(keys)]
        for row in rows:
            cells = []
            for key in keys:
                value = row["groups"].get(prefix + key)
                cells.append(f"{value['hit_at_k']:.3f}" if value else "-")
            lines.append(f"| {row['channel']} | " + " | ".join(cells) + " |")

    lines.append("")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(json.dumps({"rows": rows}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
