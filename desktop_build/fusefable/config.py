from __future__ import annotations
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml


@dataclass
class SingleProvider:
    name: str
    base_url: str
    api_key_env: str
    models: list[str] = field(default_factory=list)
    kind: str = "openai_compat"   # openai_compat | anthropic | google
    api_key: str = ""             # เก็บ key ตรงๆ (สำหรับ desktop app); ว่าง=ใช้ env


@dataclass
class Config:
    mode: str                       # "gateway" | "single"
    timeout_seconds: int
    judge_model: str
    models: list[str] = field(default_factory=list)
    gateway_name: str = ""
    gateway_base_url: str = ""
    api_key_env: str = ""
    api_key: str = ""             # gateway: เก็บ key ตรงๆ (desktop app); ว่าง=ใช้ env
    providers: list[SingleProvider] = field(default_factory=list)
    min_responses: int = 3                 # พอได้ N ตัว → synthesize เลย ไม่รอตัวช้า
    budget_cap_usd: float | None = None
    cheap_models: list[str] = field(default_factory=list)
    compress: bool = False              # บีบ prompt ก่อนส่ง (opt-in)
    compress_min_chars: int = 2000      # ต่ำกว่านี้ไม่เรียก LLM บีบ
    compress_model: str = ""            # ว่าง = ใช้ judge_model
    fusion_mode: str = "ensemble"       # "ensemble" (สังเคราะห์คำตอบใหม่) | "judge" (เลือกตัวเดียว)
    cache: bool = True                  # cache คำตอบ — คำถามซ้ำตอบทันที
    cache_ttl_seconds: int = 0          # 0 = ไม่หมดอายุ
    budget_action: str = "warn"         # "warn" | "stop" เมื่อประเมินเกิน budget_cap_usd

    def resolve_api_key(self) -> str:
        return os.environ.get(self.api_key_env, "") or self.api_key


def default_config_path() -> Path:
    return Path.home() / ".fusefable" / "config.yaml"


def save_config(cfg: Config, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(cfg)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def load_config(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    data = yaml.safe_load(path.read_text())
    providers = [SingleProvider(**p) for p in data.pop("providers", [])]
    return Config(providers=providers, **data)
