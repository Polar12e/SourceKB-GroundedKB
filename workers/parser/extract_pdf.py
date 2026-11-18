"""Extract PDF pages into GroundedKB page JSONL and a document manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

DOCUMENT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_pages(path: Path) -> list[PageText]:
    """Extract page text with PyMuPDF.

    Text-layer quality depends on the source PDF; scanned or badly encoded
    documents are flagged in the manifest instead of being silently trusted.
    """

    pages: list[PageText] = []
    with pymupdf.open(path) as document:
        for number, page in enumerate(document, start=1):
            pages.append(PageText(page=number, text=page.get_text("text")))
    return pages


def write_pages_jsonl(document_id: str, pages: list[PageText], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for page in pages:
            record = {
                "document_id": document_id,
                "page": page.page,
                "text": page.text,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def manifest_entry(
    *,
    document_id: str,
    pdf: Path,
    title: str,
    company: str,
    year: int,
    doc_type: str,
    language: str,
    text_quality: str,
    pages: list[PageText],
    license_note: str,
) -> dict[str, object]:
    return {
        "document_id": document_id,
        "title": title,
        "company": company,
        "year": year,
        "doc_type": doc_type,
        "language": language,
        "source_file": pdf.name,
        "sha256": sha256_file(pdf),
        "page_count": len(pages),
        "text_chars": sum(len(page.text) for page in pages),
        "text_quality": text_quality,
        "license": license_note,
    }


def update_manifest(path: Path, entry: dict[str, object]) -> None:
    entries: list[dict[str, object]] = []
    if path.exists():
        current = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(current, list):
            raise ValueError(f"{path} must contain a JSON array")
        entries = [item for item in current if item.get("document_id") != entry["document_id"]]
    entries.append(entry)
    entries.sort(key=lambda item: str(item["document_id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/documents.json"))
    parser.add_argument("--title", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--doc-type", required=True)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--text-quality", choices=("high", "low"), default="high")
    parser.add_argument("--license", default="user-provided; not redistributed")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    if not DOCUMENT_ID_PATTERN.fullmatch(args.document_id):
        raise SystemExit(f"invalid document id: {args.document_id}")

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    pages = extract_pages(args.pdf)
    if not pages:
        raise SystemExit(f"no pages extracted from {args.pdf}")

    write_pages_jsonl(args.document_id, pages, args.out)
    entry = manifest_entry(
        document_id=args.document_id,
        pdf=args.pdf,
        title=args.title,
        company=args.company,
        year=args.year,
        doc_type=args.doc_type,
        language=args.language,
        text_quality=args.text_quality,
        pages=pages,
        license_note=args.license,
    )
    update_manifest(args.manifest, entry)

    print(
        f"{args.document_id}: {len(pages)} pages, "
        f"{entry['text_chars']} chars, quality={args.text_quality} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
