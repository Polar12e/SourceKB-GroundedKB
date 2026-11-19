"""Shared metadata filter parsing for retrieval channels."""

from __future__ import annotations

from collections.abc import Mapping

from .documents import DocumentMeta

FILTER_FIELDS = frozenset({"document_id", "company", "year", "doc_type"})


def normalize_filters(filters: Mapping[str, str] | None) -> dict[str, str]:
    if not filters:
        return {}
    unknown = {str(key) for key in filters} - FILTER_FIELDS
    if unknown:
        raise ValueError(f"unknown filter fields: {', '.join(sorted(unknown))}")
    normalized = {
        str(key): str(value).strip()
        for key, value in filters.items()
        if str(value).strip()
    }
    year = normalized.get("year")
    if year is not None and not year.isdigit():
        raise ValueError("year filter must be an integer")
    return normalized


def matches_filters(
    document_id: str,
    documents: Mapping[str, DocumentMeta],
    filters: Mapping[str, str],
) -> bool:
    if not filters:
        return True
    if "document_id" in filters and document_id != filters["document_id"]:
        return False
    if set(filters) == {"document_id"}:
        return True

    document = documents.get(document_id)
    if document is None:
        return False
    if "company" in filters and document.company.upper() != filters["company"].upper():
        return False
    if "year" in filters and str(document.year) != filters["year"]:
        return False
    if "doc_type" in filters and document.doc_type != filters["doc_type"]:
        return False
    return True
