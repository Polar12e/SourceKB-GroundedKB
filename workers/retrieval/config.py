"""Load retrieval configuration (channels, profiles, parameters)."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "retrieval.yaml"


def load_config(path: str | Path | None = None) -> dict:
    config_path = Path(path or os.getenv("RETRIEVAL_CONFIG") or DEFAULT_CONFIG)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{config_path}: top-level config must be a mapping")
    channels = payload.get("channels")
    if not isinstance(channels, dict) or not channels:
        raise ValueError(f"{config_path}: channels must be a non-empty mapping")
    default = payload.get("default_channel")
    if default not in channels:
        raise ValueError(f"{config_path}: default_channel must be one of {sorted(channels)}")
    return payload


__all__ = ["DEFAULT_CONFIG", "ROOT", "load_config"]
