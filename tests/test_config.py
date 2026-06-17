import pytest
from fusefable.config import Config, load_config, save_config


def test_save_and_load_roundtrip(tmp_path):
    cfg = Config(
        mode="gateway",
        gateway_name="openrouter",
        gateway_base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        timeout_seconds=90,
        judge_model="deepseek/deepseek-chat",
        models=["openai/gpt-5", "anthropic/claude-opus-4.1"],
    )
    path = tmp_path / "config.yaml"
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded.gateway_name == "openrouter"
    assert loaded.models == ["openai/gpt-5", "anthropic/claude-opus-4.1"]


def test_load_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_resolve_api_key_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_KEY", "secret123")
    cfg = Config(mode="gateway", gateway_name="openrouter",
                 gateway_base_url="https://x/v1", api_key_env="MY_KEY",
                 timeout_seconds=90, judge_model="m", models=["m"])
    assert cfg.resolve_api_key() == "secret123"
