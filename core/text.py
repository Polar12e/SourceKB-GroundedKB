"""Shared text normalization and tokenization."""

from __future__ import annotations

import re


def normalize(text: str) -> str:
    """Lowercase, strip thousands separators, and join split CJK labels."""

    text = re.sub(r"(?<=\d),(?=\d{3})", "", text.lower())
    return re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)


def tokenize(text: str) -> list[str]:
    """Tokenize numbers/ASCII words plus Chinese character bigrams."""

    text = normalize(text)
    tokens = re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text)
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[index:index + 2] for index in range(len(run) - 1))
    return tokens


def page_lines(text: str) -> list[str]:
    """Return non-empty stripped lines; line numbers are 1-based positions."""

    return [line.strip() for line in text.splitlines() if line.strip()]
