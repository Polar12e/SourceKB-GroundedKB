"""Hit windows: expand a chunk locator into readable surrounding lines."""

from __future__ import annotations

from dataclasses import dataclass

from .chunking import page_lines

WINDOW_RADIUS = 2
WINDOW_MAX_CHARS = 900


@dataclass(frozen=True)
class Window:
    text: str
    line_start: int
    line_end: int
    truncated: bool = False


def window_for_lines(
    page_text: str,
    line_start: int,
    line_end: int,
    *,
    fallback_text: str = "",
    radius: int = WINDOW_RADIUS,
    max_chars: int = WINDOW_MAX_CHARS,
) -> Window:
    """Return numbered lines around ``[line_start, line_end]``.

    The chunk is the retrieval anchor; the window may cross into neighbouring
    chunks on the same page. This is what makes a hit on a "销售费用" chunk
    still show the adjacent "营业成本" row.
    """

    lines = page_lines(page_text)
    if not lines:
        text = fallback_text[:max_chars]
        return Window(text=text, line_start=0, line_end=0, truncated=len(fallback_text) > max_chars)

    start = min(max(line_start - 1, 0), len(lines))
    end = min(max(line_end, line_start), len(lines))
    if start >= end:
        start = min(max(line_start - 1, 0), len(lines) - 1)
        end = min(start + 1, len(lines))

    lo = max(0, start - radius)
    hi = min(len(lines), max(end, start + 1) + radius)
    text = "\n".join(f"{number}: {lines[number - 1]}" for number in range(lo + 1, hi + 1))
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]
    return Window(text=text, line_start=lo + 1, line_end=hi, truncated=truncated)
