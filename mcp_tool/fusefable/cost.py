from __future__ import annotations
from typing import Sequence
from fusefable.models import Completion


def estimate_cost(comps: Sequence[Completion],
                  default_in: float = 1.0, default_out: float = 3.0) -> float:
    """ประมาณค่าใช้จ่ายรวม (USD) จาก usage tokens. rate = $/1M tokens."""
    total_in = sum(c.prompt_tokens for c in comps)
    total_out = sum(c.completion_tokens for c in comps)
    return total_in / 1_000_000 * default_in + total_out / 1_000_000 * default_out


def estimate_prefire_cost(prompt: str, n_models: int,
                          default_in: float = 1.0, default_out: float = 3.0,
                          assumed_out_tokens: int = 600) -> float:
    """ประเมินค่าใช้จ่ายคร่าวๆ ก่อนยิง (สำหรับ budget cap).

    หยาบ: input tokens ≈ len(prompt)/4 ต่อโมเดล, output สมมติ assumed_out_tokens.
    +1 สำหรับ judge/synthesize. ใช้เป็น guard ไม่ใช่ตัวเลขเป๊ะ.
    """
    in_tokens = len(prompt) / 4
    per_model = (in_tokens / 1_000_000 * default_in
                 + assumed_out_tokens / 1_000_000 * default_out)
    return per_model * (n_models + 1)
