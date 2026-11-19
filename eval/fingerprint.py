"""Stable hashes for reproducible retrieval reports."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from workers.retrieval.config import DEFAULT_CONFIG, ROOT, load_config


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_rev() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def fingerprint(
    corpus: Path,
    cases: Path | None = None,
    config_path: Path | None = None,
) -> dict[str, object]:
    """Hash every input that can change retrieval numbers."""

    path = Path(config_path or os.getenv("RETRIEVAL_CONFIG") or DEFAULT_CONFIG)
    config = load_config(path)
    terms: dict[str, str] = {}
    for profile in config.get("profiles", {}).values():
        table = profile.get("term_table")
        if not table:
            continue
        table_path = Path(table)
        if not table_path.is_absolute():
            table_path = ROOT / table_path
        try:
            label = str(table_path.relative_to(ROOT))
        except ValueError:
            label = str(table_path)
        terms[label] = sha256_file(table_path)
    payload: dict[str, object] = {
        "corpus_sha256": sha256_file(corpus),
        "config_sha256": sha256_file(path),
        "terms_sha256": terms,
        "git_rev": git_rev(),
    }
    if cases is not None:
        payload["cases_sha256"] = sha256_file(cases)
    return payload
