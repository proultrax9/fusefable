from fusefable.wizard import build_config_from_answers


def test_gateway_mode_builds_single_key_config():
    answers = {
        "mode": "gateway",
        "gateway_name": "openrouter",
        "gateway_base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "models": ["openai/gpt-5", "anthropic/claude-opus-4.1"],
        "judge_model": "deepseek/deepseek-chat",
        "timeout_seconds": 90,
    }
    cfg = build_config_from_answers(answers)
    assert cfg.mode == "gateway"
    assert cfg.gateway_name == "openrouter"
    assert cfg.api_key_env == "OPENROUTER_API_KEY"
    assert len(cfg.providers) == 0


def test_single_mode_builds_per_provider_config():
    answers = {
        "mode": "single",
        "providers": [
            {"name": "openai", "base_url": "https://api.openai.com/v1",
             "api_key_env": "OPENAI_API_KEY", "models": ["gpt-5"]},
            {"name": "deepseek", "base_url": "https://api.deepseek.com/v1",
             "api_key_env": "DEEPSEEK_API_KEY", "models": ["deepseek-chat"]},
        ],
        "judge_model": "deepseek-chat",
        "timeout_seconds": 90,
    }
    cfg = build_config_from_answers(answers)
    assert cfg.mode == "single"
    assert len(cfg.providers) == 2
    assert cfg.providers[0].name == "openai"
    # models รวมจากทุก provider
    assert set(cfg.models) == {"gpt-5", "deepseek-chat"}
