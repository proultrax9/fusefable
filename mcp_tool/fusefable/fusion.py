from __future__ import annotations
from typing import Callable, Optional, Sequence, Tuple
from fusefable.fanout import fan_out
from fusefable.judge import judge
from fusefable.ensemble import synthesize
from fusefable.cost import estimate_cost
from fusefable.models import FinalAnswer
from fusefable.providers.base import Provider

Route = Tuple[Provider, str]
Progress = Optional[Callable[[dict], None]]


def _emit(progress: Progress, **event) -> None:
    if progress is not None:
        try:
            progress(event)
        except Exception:  # noqa: BLE001 — progress ต้องไม่ทำให้งานหลักพัง
            pass


async def run_fusion(routes: Sequence[Route], judge_provider: Provider,
                     judge_model: str, prompt: str, timeout_s: float,
                     judge_question: str | None = None,
                     mode: str = "judge", progress: Progress = None,
                     min_responses: int = 0) -> FinalAnswer:
    """fan-out → judge/ensemble → FinalAnswer. โยน RuntimeError ถ้าไม่มีตัวไหนสำเร็จ.

    prompt = ข้อความที่ส่งให้โมเดล (อาจถูกบีบแล้ว)
    judge_question = คำถามที่ใช้ตัดสิน/สังเคราะห์ (default = prompt; ส่งคำถามเดิมเพื่อคงคุณภาพ)
    mode = "judge" (เลือกตัวดีสุด) | "ensemble" (รวมคำตอบ)
    progress = callback รับ event dict (สำหรับ UI แสดงความคืบหน้า)
    """
    _emit(progress, stage="fanout", models=len(routes))
    completions, failures = await fan_out(routes, prompt, timeout_s,
                                          min_responses=min_responses)
    if not completions:
        parts = [f"{c.model}: {c.error}" for c in failures[:5] if c.error]
        detail = "; ".join(parts) if parts else "unknown"
        raise RuntimeError(f"no successful completions from any model — {detail}")
    q = judge_question if judge_question is not None else prompt
    cost = estimate_cost(completions)
    _emit(progress, stage=mode, got=len(completions))
    synth_timeout = min(timeout_s, 30.0)

    if mode == "ensemble":
        text = await synthesize(judge_provider, judge_model, q,
                                completions, synth_timeout)
        return FinalAnswer(text=text, chosen_model="ensemble",
                           reason=f"synthesized from {len(completions)} answers",
                           cost_usd=cost, all_completions=list(completions))

    chosen, reason = await judge(judge_provider, judge_model, q,
                                 completions, synth_timeout)
    return FinalAnswer(text=chosen.text, chosen_model=chosen.model,
                       reason=reason, cost_usd=cost,
                       all_completions=list(completions))
