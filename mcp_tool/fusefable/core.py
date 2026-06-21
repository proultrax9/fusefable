from __future__ import annotations
import time
from typing import Callable, Optional, Sequence
import httpx
from fusefable.config import Config
from fusefable.routing import build_routes, build_judge_provider
from fusefable.fusion import run_fusion
from fusefable.compressor import compress_prompt
from fusefable.cost import estimate_prefire_cost
from fusefable import cache as cache_mod
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
               compress: Optional[bool] = None,
               ensemble: Optional[bool] = None,
               use_cache: Optional[bool] = None,
               context: str = "",
               progress: Optional[Callable[[dict], None]] = None) -> FinalAnswer:
    """entry point กลาง — ใช้ร่วมกันทั้ง CLI และ MCP server.

    models: จำกัดเฉพาะโมเดลที่ระบุ
    cheap: ใช้ cfg.cheap_models
    compress: บีบ prompt (None = cfg.compress)
    ensemble: รวมคำตอบแทนเลือกตัวเดียว (None = cfg.mode)
    use_cache: ใช้ cache (None = cfg.cache)
    """
    only = select_models(cfg, models, cheap)
    do_compress = cfg.compress if compress is None else compress
    mode = cfg.fusion_mode if ensemble is None else ("ensemble" if ensemble else "judge")
    do_cache = cfg.cache if use_cache is None else use_cache
    effective_models = sorted(only) if only is not None else sorted(cfg.models)

    # โมเดลเห็น context (ไฟล์โปรเจกต์) + คำถาม; judge เห็นแค่คำถามเดิม (สั้น → เร็ว/ถูก)
    model_question = (f"<project_files>\n{context}\n</project_files>\n\n{question}"
                      if context else question)

    key = cache_mod.make_key(model_question, effective_models, compress=do_compress,
                             mode=mode, judge_model=cfg.judge_model)
    def _emit(**ev):
        if progress is not None:
            try:
                progress(ev)
            except Exception:  # noqa: BLE001
                pass

    if do_cache:
        hit = cache_mod.load_cached(key, cfg.cache_ttl_seconds, now=time.time())
        if hit is not None:
            _emit(stage="cached")
            return hit

    async with httpx.AsyncClient(timeout=None) as http:
        routes = build_routes(cfg, http)
        if only is not None:
            routes = [(p, m) for (p, m) in routes if m in only]
        if not routes:
            raise RuntimeError("ไม่มีโมเดลให้ใช้ (ตรวจ --models / config)")
        judge_prov = build_judge_provider(cfg, http)

        # บีบ prompt ครั้งเดียว แล้วส่งตัวที่บีบไปทุกโมเดล (judge ใช้คำถามเดิม)
        model_prompt = model_question
        comp = None
        if do_compress:
            _emit(stage="compress")
            comp = await compress_prompt(
                judge_prov, cfg.compress_model or cfg.judge_model, model_question,
                min_chars=cfg.compress_min_chars, timeout_s=cfg.timeout_seconds)
            model_prompt = comp.text

        # budget cap — ประเมินก่อนยิง: stop = ยกเลิก, warn = เตือนแต่ทำต่อ
        budget_warning = ""
        if cfg.budget_cap_usd is not None:
            est = estimate_prefire_cost(model_prompt, len(routes))
            if est > cfg.budget_cap_usd:
                if cfg.budget_action == "stop":
                    raise RuntimeError(
                        f"ประเมินค่าใช้จ่าย ~${est:.4f} เกิน budget "
                        f"${cfg.budget_cap_usd} (budget_action=stop) — ยกเลิกก่อนยิง")
                budget_warning = (f"ประเมิน ~${est:.4f} เกิน budget "
                                  f"${cfg.budget_cap_usd} (budget_action=warn)")

        result = await run_fusion(routes, judge_prov, cfg.judge_model,
                                  model_prompt, cfg.timeout_seconds,
                                  judge_question=question, mode=mode,
                                  progress=progress,
                                  min_responses=cfg.min_responses)
        result.compression = comp
        result.budget_warning = budget_warning
        _emit(stage="done")

    if do_cache:
        cache_mod.save_cached(key, result, now=time.time())
    return result
