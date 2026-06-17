from __future__ import annotations
import asyncio
from fusefable.models import Completion
from fusefable.providers.base import Provider


async def call_model(provider: Provider, model: str, prompt: str,
                     timeout_s: float) -> Completion:
    """ยิง 1 โมเดล โดยไม่โยน exception — คืน Completion.failed เมื่อ timeout/error."""
    try:
        return await asyncio.wait_for(provider.complete(model, prompt),
                                      timeout=timeout_s)
    except asyncio.TimeoutError:
        return Completion.failed(model=model, error=f"timeout after {timeout_s}s")
    except Exception as e:  # noqa: BLE001 — ตั้งใจกันทุก error ไม่ให้ระบบล่ม
        return Completion.failed(model=model, error=str(e))
