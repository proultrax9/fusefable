from __future__ import annotations
import asyncio
from typing import Sequence, Tuple
from fusefable.client import call_model
from fusefable.models import Completion
from fusefable.providers.base import Provider

Route = Tuple[Provider, str]   # (provider, model)


def _resolve_min_responses(min_responses: int, n_routes: int) -> int:
    """คำนวณจำนวนคำตอบที่ต้องได้ก่อนไปขั้น synthesize.

    min_responses <= 0 หรือ >= n → รอทุกตัวจบ (พฤติกรรมเดิม)
    มิฉะนั้น → พอได้ N ตัวที่สำเร็จแล้วตัดโมเดลที่เหลือ (เร็วขึ้นมาก)
    """
    if n_routes <= 1:
        return 1
    if min_responses <= 0 or min_responses >= n_routes:
        return n_routes
    return min_responses


async def fan_out(routes: Sequence[Route], prompt: str,
                  timeout_s: float, min_responses: int = 0) -> tuple[list[Completion], list[Completion]]:
    """ยิงทุก route พร้อมกัน. คืน (สำเร็จ, ล้มเหลว)."""
    n = len(routes)
    if n == 0:
        return [], []

    need = _resolve_min_responses(min_responses, n)
    tasks = [asyncio.create_task(call_model(prov, model, prompt, timeout_s))
             for prov, model in routes]
    successes: list[Completion] = []
    failures: list[Completion] = []

    if need >= n:
        results = await asyncio.gather(*tasks)
        for c in results:
            (failures if c.is_error else successes).append(c)
        return successes, failures

    pending = set(tasks)
    while pending:
        done, pending = await asyncio.wait(pending,
                                           return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            c = t.result()
            if c.is_error:
                failures.append(c)
            else:
                successes.append(c)
        if len(successes) >= need:
            for t in pending:
                t.cancel()
            if pending:
                rest = await asyncio.gather(*pending, return_exceptions=True)
                for item in rest:
                    if isinstance(item, Completion):
                        (failures if item.is_error else successes).append(item)
            return successes, failures
    return successes, failures
