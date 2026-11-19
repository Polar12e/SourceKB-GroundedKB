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
