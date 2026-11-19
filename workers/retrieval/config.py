"""Load and validate retrieval configuration."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "retrieval.yaml"
KNOWN_CHANNELS = {"bm25", "expanded", "dense", "hybrid"}


class BM25Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    k1: float = 1.5
    b: float = 0.75

    @field_validator("k1")
    @classmethod
    def _k1(cls, value: float) -> float:
        if value < 0:
            raise ValueError("k1 must be >= 0")
        return value

    @field_validator("b")
    @classmethod
    def _b(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("b must be between 0 and 1")
        return value


class WindowSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    radius: int = Field(default=2, ge=0)
    max_chars: int = Field(default=900, gt=0)


class RRFSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    k: int = Field(default=60, ge=0)
    depth: int = Field(default=60, ge=1)


class ProfileSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["none", "builtin", "lexicon", "auto"] = "builtin"
    term_table: str | None = None
    expansion_weight: float = 0.45
    oov_threshold: float = 0.5
    builtin_expansions: dict[str, list[str]] = Field(default_factory=dict)
    statement_titles: list[str] = Field(default_factory=list)
    notes_markers: list[str] = Field(default_factory=list)
    statement_bonus: float = 0.0

    @field_validator("expansion_weight")
    @classmethod
    def _weight(cls, value: float) -> float:
        if not 0 < value < 1:
            raise ValueError("expansion_weight must be between 0 and 1")
        return value

    @field_validator("oov_threshold")
    @classmethod
    def _threshold(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("oov_threshold must be between 0 and 1")
        return value


class ChannelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str | None = None
    provider: Literal["lsa", "openai"] | None = None
    dim: int | None = Field(default=None, gt=0)
    model: str | None = None
    base_url: str | None = None
    api_key_env: str | None = "OPENAI_API_KEY"
    batch_size: int | None = Field(default=None, gt=0)
    timeout: float | None = Field(default=None, gt=0)
    retries: int | None = Field(default=None, ge=0)
    channels: dict[str, float] | None = None

    @field_validator("model")
    @classmethod
    def _model(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("model must not be empty")
        return value

    @field_validator("base_url")
    @classmethod
    def _base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
        ):
            raise ValueError("base_url must be an http(s) URL without credentials")
        return value.rstrip("/")

    @field_validator("api_key_env")
    @classmethod
    def _api_key_env(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError("api_key_env must be an environment variable name")
        return value


class RetrievalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_channel: str
    bm25: BM25Settings
    window: WindowSettings
    rrf: RRFSettings
    profiles: dict[str, ProfileSettings]
    channels: dict[str, ChannelSettings]

    @model_validator(mode="after")
    def _validate_references(self) -> "RetrievalConfig":
        if not self.channels:
            raise ValueError("channels must not be empty")
        unknown = set(self.channels) - KNOWN_CHANNELS
        if unknown:
            raise ValueError(f"unknown channels: {sorted(unknown)}")
        if self.default_channel not in self.channels:
            raise ValueError("default_channel must reference a configured channel")

        expanded = self.channels.get("expanded")
        if expanded and expanded.profile and expanded.profile not in self.profiles:
            raise ValueError("expanded.profile must reference a configured profile")

        dense = self.channels.get("dense")
        if dense is not None:
            provider = dense.provider or "lsa"
            if provider == "openai":
                missing = [
                    name
                    for name in ("model", "base_url", "dim")
                    if getattr(dense, name) is None
                ]
                if missing:
                    raise ValueError(
                        f"dense provider openai requires: {', '.join(missing)}"
                    )
            elif provider == "lsa":
                if dense.model or dense.base_url:
                    raise ValueError("model/base_url are only valid for dense provider openai")

        hybrid = self.channels.get("hybrid")
        if hybrid is not None:
            if not hybrid.channels:
                raise ValueError("hybrid.channels must not be empty")
            for name, weight in hybrid.channels.items():
                if name not in self.channels:
                    raise ValueError(f"hybrid sub-channel not configured: {name}")
                if name == "hybrid":
                    raise ValueError("hybrid cannot reference itself")
                if weight <= 0:
                    raise ValueError("hybrid weights must be positive")

        for name, profile in self.profiles.items():
            if profile.term_table:
                path = Path(profile.term_table)
                if not path.is_absolute():
                    path = ROOT / path
                if not path.exists():
                    raise ValueError(f"profile {name}: term table not found: {path}")
        return self


def load_config(path: str | Path | None = None) -> dict:
    """Load YAML, validate it, and return a normalized mapping.

    ``RETRIEVAL_CONFIG`` selects a non-default file. Validation happens before
    any index is built, so a bad parameter fails at startup with a clear error.
    """

    config_path = Path(path or os.getenv("RETRIEVAL_CONFIG") or DEFAULT_CONFIG)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{config_path}: top-level config must be a mapping")
    try:
        config = RetrievalConfig.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"{config_path}: invalid retrieval config: {exc}") from exc
    return config.model_dump()


__all__ = ["DEFAULT_CONFIG", "ROOT", "RetrievalConfig", "load_config"]
