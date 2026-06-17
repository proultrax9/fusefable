from __future__ import annotations
from fusefable.config import Config, SingleProvider


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
        gw = prompt("Gateway เจ้าไหน? (เช่น openrouter): ").strip()
        base = prompt("Base URL (เช่น https://openrouter.ai/api/v1): ").strip()
        key_env = prompt("ชื่อ env var ของ API key (เช่น OPENROUTER_API_KEY): ").strip()
        models_raw = prompt("รายชื่อโมเดล คั่นด้วย comma: ").strip()
        models = [m.strip() for m in models_raw.split(",") if m.strip()]
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
