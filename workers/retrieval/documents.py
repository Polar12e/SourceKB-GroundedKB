"""Document metadata used for filtering and index statistics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentMeta:
    document_id: str
    company: str = ""
    year: int = 0
    doc_type: str = ""
    title: str = ""
    text_quality: str = ""


def load_documents_manifest(path: str | Path) -> dict[str, DocumentMeta]:
    """Load ``data/manifests/documents.json`` as a document-id map."""

    entries = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError(f"{path}: manifest must be a JSON array")

    documents: dict[str, DocumentMeta] = {}
    for entry in entries:
        document_id = str(entry["document_id"])
        if document_id in documents:
            raise ValueError(f"{path}: duplicate document_id {document_id}")
        documents[document_id] = DocumentMeta(
            document_id=document_id,
            company=str(entry.get("company", "")),
            year=int(entry.get("year", 0)),
            doc_type=str(entry.get("doc_type", "")),
            title=str(entry.get("title", "")),
            text_quality=str(entry.get("text_quality", "")),
        )
    return documents
