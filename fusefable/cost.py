from __future__ import annotations
from typing import Sequence
from fusefable.models import Completion


def estimate_cost(comps: Sequence[Completion],
                  default_in: float = 1.0, default_out: float = 3.0) -> float:
    """ประมาณค่าใช้จ่ายรวม (USD) จาก usage tokens. rate = $/1M tokens."""
    total_in = sum(c.prompt_tokens for c in comps)
    total_out = sum(c.completion_tokens for c in comps)
    return total_in / 1_000_000 * default_in + total_out / 1_000_000 * default_out
