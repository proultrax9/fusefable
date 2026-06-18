from __future__ import annotations
from typing import Optional, Sequence
import httpx
from fusefable.config import Config
from fusefable.routing import build_routes, build_judge_provider
from fusefable.fusion import run_fusion
from fusefable.compressor import compress_prompt
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
               cheap: bool = False,
               compress: Optional[bool] = None) -> FinalAnswer:
    """entry point กลาง — ใช้ร่วมกันทั้ง CLI และ MCP server.

    models: จำกัดเฉพาะโมเดลที่ระบุ (เช่นจาก --models)
    cheap: ใช้ cfg.cheap_models ถ้ามี
    compress: บีบ prompt ก่อนส่ง (None = ใช้ค่า cfg.compress)
    """
    only = select_models(cfg, models, cheap)
    do_compress = cfg.compress if compress is None else compress
    async with httpx.AsyncClient(timeout=None) as http:
        routes = build_routes(cfg, http)
        if only is not None:
            routes = [(p, m) for (p, m) in routes if m in only]
        if not routes:
            raise RuntimeError("ไม่มีโมเดลให้ใช้ (ตรวจ --models / config)")
        judge_prov = build_judge_provider(cfg, http)

        # บีบ prompt ครั้งเดียว แล้วส่งตัวที่บีบไปทุกโมเดล (judge ใช้คำถามเดิม)
        model_prompt = question
        comp = None
        if do_compress:
            comp = await compress_prompt(
                judge_prov, cfg.compress_model or cfg.judge_model, question,
                min_chars=cfg.compress_min_chars, timeout_s=cfg.timeout_seconds)
            model_prompt = comp.text

        result = await run_fusion(routes, judge_prov, cfg.judge_model,
                                  model_prompt, cfg.timeout_seconds,
                                  judge_question=question)
        result.compression = comp
        return result
