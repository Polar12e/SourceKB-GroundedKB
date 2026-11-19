"""A/B the four retrieval channels on the same EvalCase set."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.run_retrieval import DEFAULT_CASES, DEFAULT_CORPUS, evaluate_case, load_cases  # noqa: E402
from workers.retrieval.config import load_config  # noqa: E402
from workers.retrieval.corpus import load_pages_jsonl  # noqa: E402
from workers.retrieval.documents import load_documents_manifest  # noqa: E402
from workers.retrieval.pipeline import CHANNELS, build_channel  # noqa: E402
from eval.fingerprint import fingerprint  # noqa: E402


def run_channel(name: str, pages, documents, config, cases, top_k: int) -> dict:
    started = time.perf_counter()
    try:
        index = build_channel(name, pages, documents, config)
    except Exception as exc:
        return {
            "channel": name,
            "error": f"{type(exc).__name__}: {exc}",
            "build_seconds": time.perf_counter() - started,
        }
    build_seconds = time.perf_counter() - started
    results = [
        evaluate_case(index.search(case["question"], top_k=top_k, filters=case.get("filters")), case, top_k)
        for case in cases
    ]
    total = len(results)
    return {
        "channel": name,
        "build_seconds": build_seconds,
        "hit_at_k": sum(item.hit_at_k for item in results) / total,
        "recall_at_k": sum(item.recall_at_k for item in results) / total,
        "mrr": sum(item.mrr for item in results) / total,
        "precision_at_k": sum(item.precision_at_k for item in results) / total,
        "chunk_hit_at_k": sum(item.chunk_hit_at_k for item in results) / total,
        "chunk_recall_at_k": sum(item.chunk_recall_at_k for item in results) / total,
        "ndcg_at_10": sum(item.ndcg_at_10 for item in results) / total,
        "hard_negative_hits": sum(item.hard_negative_hits for item in results),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "manifests" / "documents.json",
    )
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--channels", default=",".join(CHANNELS))
    parser.add_argument("--out", type=Path, default=ROOT / "eval-results" / "ab_channels.md")
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    pages = load_pages_jsonl(args.corpus)
    documents = load_documents_manifest(args.manifest) if args.manifest.exists() else {}
    config = load_config()
    requested = [name.strip() for name in args.channels.split(",") if name.strip()]
    unknown = [name for name in requested if name not in CHANNELS]
    if unknown:
        parser.error(f"unknown channels: {', '.join(unknown)}")

    rows = [run_channel(name, pages, documents, config, cases, args.top_k) for name in requested]
    fp = fingerprint(args.corpus, args.cases)
    lines = [
        "# Four-channel retrieval A/B",
        "",
        f"- cases: `{args.cases.name}` ({len(cases)})",
        f"- corpus: `{args.corpus}`",
        f"- top_k: {args.top_k}",
        f"- corpus_sha256: `{fp['corpus_sha256']}`",
        f"- config_sha256: `{fp['config_sha256']}`",
        f"- git_rev: `{fp['git_rev']}`",
        "",
        f"| channel | build s | page Hit@{args.top_k} | chunk Hit@{args.top_k} | page Recall@{args.top_k} | chunk Recall@{args.top_k} | page MRR | chunk nDCG@10 | hard_neg |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        if "error" in row:
            lines.append(f"| {row['channel']} | {row['build_seconds']:.2f} | error | error | error | error | error | error | error |")
            continue
        lines.append(
            f"| {row['channel']} | {row['build_seconds']:.2f} | "
            f"{row['hit_at_k']:.3f} | {row['chunk_hit_at_k']:.3f} | "
            f"{row['recall_at_k']:.3f} | {row['chunk_recall_at_k']:.3f} | "
            f"{row['mrr']:.3f} | {row['ndcg_at_10']:.3f} | {row['hard_negative_hits']} |"
        )
    lines.append("")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(json.dumps({"rows": rows}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
