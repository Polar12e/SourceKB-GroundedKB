"""Corpus loading for the retrieval worker."""

from __future__ import annotations

import json
from pathlib import Path

from .chunking import Page


def load_pages_jsonl(path: str | Path) -> list[Page]:
    """Load JSONL pages.

    Each line must have ``page`` and ``text``. ``document_id`` is optional for
    legacy-compatible fixtures and defaults to ``legacy``.
    """

    pages: list[Page] = []
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            try:
                page = int(record["page"])
                text = str(record.get("text", ""))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{path}:{number}: invalid page record") from exc
            if page < 1:
                raise ValueError(f"{path}:{number}: page must be >= 1")
            document_id = str(record.get("document_id") or "legacy")
            pages.append(Page(document_id=document_id, page=page, text=text))
    return pages
