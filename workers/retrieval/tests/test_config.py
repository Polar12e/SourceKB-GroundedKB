import copy

import pytest
import yaml

from workers.retrieval.config import DEFAULT_CONFIG, load_config


def raw_config() -> dict:
    return yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))


def write_config(tmp_path, payload: dict):
    path = tmp_path / "retrieval.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    return path


def test_default_config_is_valid() -> None:
    config = load_config()
    assert config["default_channel"] == "expanded"
    assert set(config["channels"]) == {"bm25", "expanded", "dense", "hybrid"}


def test_invalid_default_channel_is_rejected(tmp_path) -> None:
    payload = raw_config()
    payload["default_channel"] = "missing"
    with pytest.raises(ValueError, match="default_channel"):
        load_config(write_config(tmp_path, payload))


def test_hybrid_subchannel_must_exist(tmp_path) -> None:
    payload = raw_config()
    payload["channels"]["hybrid"]["channels"] = {"missing": 1.0}
    with pytest.raises(ValueError, match="hybrid sub-channel"):
        load_config(write_config(tmp_path, payload))


def test_missing_term_table_is_rejected(tmp_path) -> None:
    payload = raw_config()
    payload["profiles"]["finance"]["term_table"] = "domains/finance/missing.json"
    with pytest.raises(ValueError, match="term table not found"):
        load_config(write_config(tmp_path, payload))


def test_expansion_weight_must_be_below_one(tmp_path) -> None:
    payload = raw_config()
    payload["profiles"]["finance"]["expansion_weight"] = 1.0
    with pytest.raises(ValueError, match="expansion_weight"):
        load_config(write_config(tmp_path, payload))


def test_unknown_top_level_key_is_rejected(tmp_path) -> None:
    payload = raw_config()
    payload["unknown_parameter"] = 1
    with pytest.raises(ValueError, match="invalid retrieval config"):
        load_config(write_config(tmp_path, payload))


def test_openai_provider_accepts_required_fields(tmp_path) -> None:
    payload = raw_config()
    payload["channels"]["dense"].update(
        {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "base_url": "https://api.example.com/v1/",
            "dim": 1536,
            "api_key_env": "EMBED_API_KEY",
        }
    )
    config = load_config(write_config(tmp_path, payload))
    dense = config["channels"]["dense"]
    assert dense["provider"] == "openai"
    assert dense["base_url"] == "https://api.example.com/v1"
    assert dense["dim"] == 1536


def test_openai_provider_requires_base_url(tmp_path) -> None:
    payload = raw_config()
    payload["channels"]["dense"].update(
        {"provider": "openai", "model": "m", "dim": 3}
    )
    with pytest.raises(ValueError, match="requires: base_url"):
        load_config(write_config(tmp_path, payload))


def test_openai_base_url_rejects_credentials(tmp_path) -> None:
    payload = raw_config()
    payload["channels"]["dense"].update(
        {
            "provider": "openai",
            "model": "m",
            "base_url": "https://user:secret@example.com/v1",
            "dim": 3,
        }
    )
    with pytest.raises(ValueError, match="without credentials"):
        load_config(write_config(tmp_path, payload))


def test_openai_api_key_env_must_be_a_name(tmp_path) -> None:
    payload = raw_config()
    payload["channels"]["dense"].update(
        {
            "provider": "openai",
            "model": "m",
            "base_url": "https://example.com/v1",
            "dim": 3,
            "api_key_env": "not a var name",
        }
    )
    with pytest.raises(ValueError, match="api_key_env"):
        load_config(write_config(tmp_path, payload))


def test_lsa_rejects_openai_only_fields(tmp_path) -> None:
    payload = raw_config()
    payload["channels"]["dense"]["model"] = "should-not-be-used"
    with pytest.raises(ValueError, match="only valid for dense provider openai"):
        load_config(write_config(tmp_path, payload))
