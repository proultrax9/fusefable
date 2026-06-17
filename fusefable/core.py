from __future__ import annotations
from typing import Optional, Sequence
import httpx
from fusefable.config import Config
from fusefable.routing import build_routes, build_judge_provider
from fusefable.fusion import run_fusion
from fusefable.models import FinalAnswer


def select_models(cfg: Config, models: Optional[Sequence[str]] = None,
                  cheap: bool = False) -> Optional[set[str]]:
    """ตัดสินว่าจะใช้โมเดลชุดไหน. คืน None = ใช้ทุกตัวตาม config."""
    if models:
        return set(models)
    if cheap and cfg.cheap_models:
        return set(cfg.cheap_models)
    return None


async def fuse(cfg: Config, question: str,
               models: Optional[Sequence[str]] = None,
               cheap: bool = False) -> FinalAnswer:
    """entry point กลาง — ใช้ร่วมกันทั้ง CLI และ MCP server.

    models: จำกัดเฉพาะโมเดลที่ระบุ (เช่นจาก --models)
    cheap: ใช้ cfg.cheap_models ถ้ามี
    """
    only = select_models(cfg, models, cheap)
    async with httpx.AsyncClient(timeout=None) as http:
        routes = build_routes(cfg, http)
        if only is not None:
            routes = [(p, m) for (p, m) in routes if m in only]
        if not routes:
            raise RuntimeError("ไม่มีโมเดลให้ใช้ (ตรวจ --models / config)")
        judge_prov = build_judge_provider(cfg, http)
        return await run_fusion(routes, judge_prov, cfg.judge_model,
                                question, cfg.timeout_seconds)
