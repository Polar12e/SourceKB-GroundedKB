"""Run the black-box system test set against local gateway/retrieval/agent."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = Path(__file__).parent / "cases.json"
DEFAULT_REPORT = Path(__file__).parent / "report.md"
PORTS = {
    "gateway": int(os.getenv("E2E_GATEWAY_PORT", "18080")),
    "retrieval": int(os.getenv("E2E_RETRIEVAL_PORT", "18081")),
    "agent": int(os.getenv("E2E_AGENT_PORT", "18083")),
    "model-gateway": int(os.getenv("E2E_MODEL_GATEWAY_PORT", "18084")),
}
LINE_PREFIX = re.compile(r"^\s*\d+\s*:")


def request(case: dict) -> tuple[int, dict | None, str]:
    url = f"http://127.0.0.1:{PORTS[case['service']]}{case['path']}"
    body = json.dumps(case.get("body"), ensure_ascii=False).encode() if "body" in case else None
    req = urllib.request.Request(url, data=body, method=case.get("method", "GET"))
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        status = exc.code
    try:
        payload = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        payload = None
    return status, payload, raw


def contains(actual, expected) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and contains(actual[key], value)
            for key, value in expected.items()
        )
    return actual == expected


def assert_case(case: dict, status: int, payload: dict | None) -> list[str]:
    expect = case.get("expect", {})
    errors: list[str] = []
    if "status" in expect and status != expect["status"]:
        errors.append(f"status {status} != {expect['status']}")
    if "json_contains" in expect and not contains(payload, expect["json_contains"]):
        errors.append(f"json does not contain {expect['json_contains']}: {payload}")
    hits = payload.get("hits") if isinstance(payload, dict) else None
    if expect.get("hits_nonempty") and not hits:
        errors.append("expected non-empty hits")
    if expect.get("hits_empty") and hits:
        errors.append(f"expected no hits, got {len(hits)}")
    if isinstance(hits, list):
        if "all_hits_have" in expect:
            for index, hit in enumerate(hits):
                missing = [key for key in expect["all_hits_have"] if key not in hit]
                if missing:
                    errors.append(f"hit {index} missing {missing}")
        if "all_hit_documents" in expect:
            docs = {hit.get("document_id") for hit in hits}
            if docs != set(expect["all_hit_documents"]):
                errors.append(f"hit documents {docs} != {set(expect['all_hit_documents'])}")
        if "first_hit_document" in expect and (not hits or hits[0].get("document_id") != expect["first_hit_document"]):
            errors.append("first hit document mismatch")
        if "first_hit_page" in expect and (not hits or hits[0].get("locator", {}).get("page") != expect["first_hit_page"]):
            errors.append("first hit page mismatch")
        if "all_hit_channels_include" in expect:
            for index, hit in enumerate(hits):
                channels = hit.get("channels") or []
                if expect["all_hit_channels_include"] not in channels:
                    errors.append(f"hit {index} channels {channels} missing {expect['all_hit_channels_include']}")
        if expect.get("anchor_text_nonempty"):
            for index, hit in enumerate(hits):
                if not str(hit.get("anchor_text", "")).strip():
                    errors.append(f"hit {index} empty anchor_text")
        if expect.get("anchor_within_locator"):
            for index, hit in enumerate(hits):
                anchor = hit.get("anchor", {})
                locator = hit.get("locator", {})
                if not (
                    anchor.get("line_start", 0) >= locator.get("line_start", 0)
                    and anchor.get("line_end", 0) <= locator.get("line_end", 0)
                ):
                    errors.append(f"hit {index} anchor outside locator")

    if isinstance(payload, dict) and "answer" in payload:
        if "answer_status" in expect and payload.get("status") != expect["answer_status"]:
            errors.append(f"answer status {payload.get('status')} != {expect['answer_status']}")
        answer = str(payload.get("answer", ""))
        if expect.get("answer_no_line_prefix") and LINE_PREFIX.search(answer):
            errors.append("answer has line-number prefix")
        if "answer_contains" in expect and expect["answer_contains"] not in answer:
            errors.append(f"answer does not contain {expect['answer_contains']!r}")
        citations = payload.get("citations") or []
        if "citations_min" in expect and len(citations) < expect["citations_min"]:
            errors.append(f"citations {len(citations)} < {expect['citations_min']}")
        if "citations_count" in expect and len(citations) != expect["citations_count"]:
            errors.append(f"citations {len(citations)} != {expect['citations_count']}")
        if "citation_fields" in expect:
            for index, citation in enumerate(citations):
                missing = [key for key in expect["citation_fields"] if key not in citation]
                if missing:
                    errors.append(f"citation {index} missing {missing}")
        if expect.get("citation_quote_nonempty") and any(not str(c.get("quote", "")).strip() for c in citations):
            errors.append("empty citation quote")
        if expect.get("citation_quote_no_line_prefix") and any(LINE_PREFIX.search(str(c.get("quote", ""))) for c in citations):
            errors.append("citation quote has line-number prefix")
        if "first_citation_document" in expect and (not citations or citations[0].get("document_id") != expect["first_citation_document"]):
            errors.append("first citation document mismatch")

    if expect.get("error_shape"):
        if not isinstance(payload, dict) or set(payload) != {"error"}:
            errors.append(f"error envelope mismatch: {payload}")
        else:
            error = payload.get("error") or {}
            if set(error) != {"code", "message"}:
                errors.append(f"error object mismatch: {error}")
            if expect.get("error_code") and error.get("code") != expect["error_code"]:
                errors.append(f"error code {error.get('code')} != {expect['error_code']}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    rows = []
    failed = 0
    for case in cases:
        started = time.perf_counter()
        status, payload, raw = request(case)
        errors = assert_case(case, status, payload)
        elapsed = (time.perf_counter() - started) * 1000
        failed += bool(errors)
        rows.append((case, status, errors, elapsed, raw))
        print(f"[{'PASS' if not errors else 'FAIL'}] {case['id']} ({elapsed:.0f} ms)")
        for error in errors:
            print(f"        {error}")

    lines = [
        "# System test report",
        "",
        f"- cases: {len(cases)}",
        f"- passed: {len(cases) - failed}",
        f"- failed: {failed}",
        f"- generated: {time.strftime('%F %T')}",
        "",
        "| case | service | endpoint | status | result | latency |",
        "|---|---|---|---:|---|---:|",
    ]
    for case, status, errors, elapsed, _ in rows:
        lines.append(
            f"| {case['id']} | {case['service']} | `{case['method']} {case['path']}` | "
            f"{status} | {'PASS' if not errors else 'FAIL'} | {elapsed:.0f} ms |"
        )
    lines.append("")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{len(cases) - failed}/{len(cases)} passed; report: {args.report}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
