from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key: str


@dataclass
class Completion:
    model: str
    text: str
    label: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    is_error: bool = False
    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @classmethod
    def failed(cls, model: str, error: str) -> "Completion":
        return cls(model=model, text="", is_error=True, error=error)


@dataclass
class FinalAnswer:
    text: str
    chosen_model: str
    reason: str = ""
    cost_usd: float = 0.0
    all_completions: list = field(default_factory=list)
    compression: object = None   # CompressionResult | None (กัน import วน)
    cached: bool = False          # มาจาก cache หรือไม่
    budget_warning: str = ""      # ข้อความเตือนงบ (ถ้ามี)
