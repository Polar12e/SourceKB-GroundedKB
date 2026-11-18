"""Line-aware chunking and tokenization for retrieval.

Ported from the legacy project's ``src/retrieval.py`` with two changes:

- chunks carry a stable ``document_id:p<page>:c<index>`` id;
- positions are expressed as page/line locators instead of a bare page number.

Numbers are normalized (``2,928,031`` -> ``2928031``), Chinese runs are
indexed as character bigrams, and chunks are split on line boundaries with a
character overlap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.text import normalize, page_lines, tokenize

CHUNK_SIZE = 360
CHUNK_OVERLAP = 80


@dataclass(frozen=True)
class Page:
    """One page of a source document."""

    document_id: str
    page: int
    text: str


@dataclass(frozen=True)
class Chunk:
    """A line-aware chunk and its stable identity."""

    chunk_id: str
    document_id: str
    page: int
    index: int
    text: str
    line_start: int
    line_end: int


def chunk_page_spans(
    text: str,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[tuple[str, int, int]]:
    """Split a page into line-aware ``(text, line_start, line_end)`` chunks."""

    lines = page_lines(text)
    chunks: list[tuple[str, int, int]] = []
    current: list[tuple[int, str]] = []
    length = 0

    for number, line in enumerate(lines, start=1):
        if current and length + len(line) > size:
            chunks.append(
                ("\n".join(line_text for _, line_text in current), current[0][0], current[-1][0])
            )
            tail: list[tuple[int, str]] = []
            tail_length = 0
            for previous in reversed(current):
                if tail_length + len(previous[1]) > overlap:
                    break
                tail.insert(0, previous)
                tail_length += len(previous[1])
            current = tail
            length = tail_length

        current.append((number, line))
        length += len(line)

    if current:
        chunks.append(
            ("\n".join(line_text for _, line_text in current), current[0][0], current[-1][0])
        )
    return chunks


def make_chunk_id(document_id: str, page: int, index: int) -> str:
    """Stable chunk id shared by indexing, citations and re-indexing."""

    return f"{document_id}:p{page}:c{index}"


def chunk_pages(
    pages: Iterable[Page],
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Chunk pages in deterministic document/page order."""

    chunks: list[Chunk] = []
    for page in sorted(pages, key=lambda item: (item.document_id, item.page)):
        for index, (piece, line_start, line_end) in enumerate(
            chunk_page_spans(page.text, size=size, overlap=overlap)
        ):
            if piece.strip():
                chunks.append(
                    Chunk(
                        chunk_id=make_chunk_id(page.document_id, page.page, index),
                        document_id=page.document_id,
                        page=page.page,
                        index=index,
                        text=piece,
                        line_start=line_start,
                        line_end=line_end,
                    )
                )
    return chunks
