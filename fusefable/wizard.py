from __future__ import annotations
from fusefable.config import Config, SingleProvider

# base_url ของ AI gateway ที่รู้จัก (OpenAI-compatible) — เติมอัตโนมัติ
# เจ้าที่ไม่อยู่ในนี้ก็ยังใช้ได้ แค่ผู้ใช้พิมพ์ base_url เอง → รองรับทุกเจ้า
KNOWN_GATEWAYS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "deepinfra": "https://api.deepinfra.com/v1/openai",
    "novita": "https://api.novita.ai/v3/openai",
    "hyperbolic": "https://api.hyperbolic.xyz/v1",
    "aimlapi": "https://api.aimlapi.com/v1",
    "portkey": "https://api.portkey.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
}


def build_config_from_answers(answers: dict) -> Config:
    """แปลงคำตอบจาก wizard เป็น Config (logic ล้วน — แยกจาก I/O เพื่อ test ได้)."""
    if answers["mode"] == "gateway":
        return Config(
            mode="gateway",
            gateway_name=answers["gateway_name"],
            gateway_base_url=answers["gateway_base_url"],
            api_key_env=answers["api_key_env"],
            models=answers["models"],
            judge_model=answers["judge_model"],
            timeout_seconds=answers["timeout_seconds"],
        )
    providers = [SingleProvider(**p) for p in answers["providers"]]
    all_models = [m for p in providers for m in p.models]
    return Config(
        mode="single",
        providers=providers,
        models=all_models,
        judge_model=answers["judge_model"],
        timeout_seconds=answers["timeout_seconds"],
    )


def run_wizard(prompt=input) -> Config:
    """ถาม interactive แล้วคืน Config. `prompt` ฉีดเข้าได้เพื่อ test."""
    print("=== Fuse Fable setup ===")
    print("1) AI Gateway (เช่น OpenRouter) — key เดียวเรียกทุกโมเดล")
    print("2) Provider เดี่ยว (ผสมหลายเจ้า)")
    choice = prompt("เลือก [1/2]: ").strip()

    if choice == "1":
        print("Gateway ที่รองรับ (เติม URL อัตโนมัติ): "
              + ", ".join(sorted(KNOWN_GATEWAYS)))
        print("(เจ้าอื่นก็ใช้ได้ — พิมพ์ชื่อแล้วใส่ base_url เอง)")
        gw = prompt("Gateway เจ้าไหน?: ").strip()
        base = KNOWN_GATEWAYS.get(gw.lower())
        if not base:   # gateway ที่ไม่รู้จัก → ถาม base_url เอง
            base = prompt("Base URL (เช่น https://openrouter.ai/api/v1): ").strip()
        key_env = prompt("ชื่อ env var ของ API key (เช่น OPENROUTER_API_KEY): ").strip()
        n = int(prompt("จะใช้กี่โมเดล?: ").strip())
        models = []
        for i in range(n):
            m = prompt(f"  โมเดลที่ {i + 1} (เช่น openai/gpt-5): ").strip()
            if m:
                models.append(m)
        judge = prompt("judge model: ").strip()
        return build_config_from_answers({
            "mode": "gateway", "gateway_name": gw, "gateway_base_url": base,
            "api_key_env": key_env, "models": models, "judge_model": judge,
            "timeout_seconds": 90,
        })

    n = int(prompt("จะใช้กี่เจ้า?: ").strip())
    providers = []
    for i in range(n):
        print(f"-- เจ้าที่ {i + 1} --")
        name = prompt("  ชื่อ: ").strip()
        base = prompt("  base_url: ").strip()
        key_env = prompt("  ชื่อ env var ของ API key: ").strip()
        models_raw = prompt("  โมเดล (คั่นด้วย comma): ").strip()
        models = [m.strip() for m in models_raw.split(",") if m.strip()]
        providers.append({"name": name, "base_url": base,
                          "api_key_env": key_env, "models": models})
    judge = prompt("judge model: ").strip()
    return build_config_from_answers({
        "mode": "single", "providers": providers,
        "judge_model": judge, "timeout_seconds": 90,
    })
