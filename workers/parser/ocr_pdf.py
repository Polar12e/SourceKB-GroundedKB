"""OCR a PDF into GroundedKB page JSONL.

This is an optional parser path for PDFs whose text layer is missing or
mis-encoded (CID/embedded-font issues). It renders pages with PyMuPDF and runs
RapidOCR on each rendered image.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pymupdf
from rapidocr_onnxruntime import RapidOCR


def load_done(path: Path) -> set[int]:
    done: set[int] = set()
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                done.add(int(json.loads(line)["page"]))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
    return done


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=0)
    args = parser.parse_args(argv)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(args.out)
    if done:
        print(f"resuming {args.document_id}: {len(done)} pages already present", flush=True)

    ocr = RapidOCR()
    started = time.time()
    with pymupdf.open(args.pdf) as document, args.out.open("a", encoding="utf-8") as handle:
        last = min(len(document), args.end) if args.end else len(document)
        for number in range(args.start, last + 1):
            if number in done:
                continue
            page = document[number - 1]
            pix = page.get_pixmap(dpi=args.dpi, colorspace=pymupdf.csRGB, alpha=False)
            image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            result, _ = ocr(image)
            text = "\n".join(item[1] for item in (result or []))
            record = {
                "document_id": args.document_id,
                "page": number,
                "text": text,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            if number % 10 == 0 or number == last:
                elapsed = time.time() - started
                print(
                    f"{args.document_id}: {number}/{last} pages, {elapsed:.1f}s",
                    flush=True,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
