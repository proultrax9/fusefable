from fusefable.wizard import build_config_from_answers, run_wizard


def _scripted(responses):
    """สร้าง fake prompt ที่ตอบตามลำดับ responses."""
    it = iter(responses)

    def fake_prompt(_msg=""):
        return next(it)

    return fake_prompt


def test_run_wizard_gateway_asks_how_many_then_each_model():
    # เลือก gateway(1) → openrouter → key env → จำนวน 3 → 3 โมเดล → judge
    answers = _scripted([
        "1",                       # mode = gateway
        "openrouter",              # gateway name (base_url เติมอัตโนมัติ)
        "OPENROUTER_API_KEY",      # key env
        "3",                       # จะใช้กี่ตัว
        "openai/gpt-5",            # โมเดลที่ 1
        "anthropic/claude-opus-4.1",  # โมเดลที่ 2
        "qwen/qwen3-coder",        # โมเดลที่ 3
        "deepseek/deepseek-chat",  # judge
    ])
    cfg = run_wizard(prompt=answers)
    assert cfg.mode == "gateway"
    assert cfg.gateway_name == "openrouter"
    assert cfg.gateway_base_url == "https://openrouter.ai/api/v1"  # เติมอัตโนมัติ
    assert len(cfg.models) == 3
    assert cfg.models == ["openai/gpt-5", "anthropic/claude-opus-4.1",
                          "qwen/qwen3-coder"]
    assert cfg.judge_model == "deepseek/deepseek-chat"


def test_run_wizard_gateway_autofills_other_known_gateway():
    # groq เป็น gateway ที่รู้จัก → เติม base_url อัตโนมัติ ไม่ถาม URL
    answers = _scripted([
        "1", "groq", "GROQ_API_KEY", "1", "llama-3.3-70b", "llama-3.3-70b",
    ])
    cfg = run_wizard(prompt=answers)
    assert cfg.gateway_base_url == "https://api.groq.com/openai/v1"


def test_run_wizard_gateway_unknown_asks_base_url():
    # gateway ที่ไม่รู้จัก → ถาม base_url เอง (รองรับทุกเจ้า)
    answers = _scripted([
        "1", "mygw", "https://my.gateway/v1", "MY_KEY", "1", "m1", "m1",
    ])
    cfg = run_wizard(prompt=answers)
    assert cfg.gateway_name == "mygw"
    assert cfg.gateway_base_url == "https://my.gateway/v1"


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


def test_run_wizard_single_mode_native_autofills_base_url():
    # 2 เจ้า: anthropic (native, เติม URL) + openai_compat (พิมพ์ URL เอง)
    answers = _scripted([
        "2",                       # mode = single
        "2",                       # จะใช้กี่เจ้า
        # เจ้าที่ 1: anthropic native
        "claude", "anthropic", "ANTHROPIC_API_KEY", "claude-opus-4-8",
        # เจ้าที่ 2: openai_compat
        "ds", "openai_compat", "https://api.deepseek.com/v1", "DS_KEY", "deepseek-chat",
        "deepseek-chat",           # judge
    ])
    cfg = run_wizard(prompt=answers)
    assert cfg.mode == "single"
    assert cfg.providers[0].kind == "anthropic"
    assert cfg.providers[0].base_url == "https://api.anthropic.com/v1"  # เติมอัตโนมัติ
    assert cfg.providers[1].kind == "openai_compat"
    assert cfg.providers[1].base_url == "https://api.deepseek.com/v1"


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
