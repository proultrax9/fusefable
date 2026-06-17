from __future__ import annotations
import asyncio
from typing import Sequence, Tuple
from fusefable.client import call_model
from fusefable.models import Completion
from fusefable.providers.base import Provider

Route = Tuple[Provider, str]   # (provider, model)


async def fan_out(routes: Sequence[Route], prompt: str,
                  timeout_s: float) -> list[Completion]:
    """ยิงทุก route พร้อมกัน คืนเฉพาะ Completion ที่สำเร็จ."""
    tasks = [call_model(prov, model, prompt, timeout_s) for prov, model in routes]
    completions = await asyncio.gather(*tasks)
    return [c for c in completions if not c.is_error]
