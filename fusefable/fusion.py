from __future__ import annotations
from typing import Sequence, Tuple
from fusefable.fanout import fan_out
from fusefable.judge import judge
from fusefable.ensemble import synthesize
from fusefable.cost import estimate_cost
from fusefable.models import FinalAnswer
from fusefable.providers.base import Provider

Route = Tuple[Provider, str]


async def run_fusion(routes: Sequence[Route], judge_provider: Provider,
                     judge_model: str, prompt: str, timeout_s: float,
                     judge_question: str | None = None,
                     mode: str = "judge") -> FinalAnswer:
    """fan-out → judge/ensemble → FinalAnswer. โยน RuntimeError ถ้าไม่มีตัวไหนสำเร็จ.

    prompt = ข้อความที่ส่งให้โมเดล (อาจถูกบีบแล้ว)
    judge_question = คำถามที่ใช้ตัดสิน/สังเคราะห์ (default = prompt; ส่งคำถามเดิมเพื่อคงคุณภาพ)
    mode = "judge" (เลือกตัวดีสุด) | "ensemble" (รวมคำตอบ)
    """
    completions = await fan_out(routes, prompt, timeout_s)
    if not completions:
        raise RuntimeError("no successful completions from any model")
    q = judge_question if judge_question is not None else prompt
    cost = estimate_cost(completions)

    if mode == "ensemble":
        text = await synthesize(judge_provider, judge_model, q,
                                completions, timeout_s)
        return FinalAnswer(text=text, chosen_model="ensemble",
                           reason=f"synthesized from {len(completions)} answers",
                           cost_usd=cost, all_completions=list(completions))

    chosen, reason = await judge(judge_provider, judge_model, q,
                                 completions, timeout_s)
    return FinalAnswer(text=chosen.text, chosen_model=chosen.model,
                       reason=reason, cost_usd=cost,
                       all_completions=list(completions))
