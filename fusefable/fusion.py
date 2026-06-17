from __future__ import annotations
from typing import Sequence, Tuple
from fusefable.fanout import fan_out
from fusefable.judge import judge
from fusefable.cost import estimate_cost
from fusefable.models import FinalAnswer
from fusefable.providers.base import Provider

Route = Tuple[Provider, str]


async def run_fusion(routes: Sequence[Route], judge_provider: Provider,
                     judge_model: str, prompt: str, timeout_s: float) -> FinalAnswer:
    """fan-out → judge → FinalAnswer. โยน RuntimeError ถ้าไม่มีตัวไหนสำเร็จ."""
    completions = await fan_out(routes, prompt, timeout_s)
    if not completions:
        raise RuntimeError("no successful completions from any model")
    chosen, reason = await judge(judge_provider, judge_model, prompt,
                                 completions, timeout_s)
    cost = estimate_cost(completions)
    return FinalAnswer(text=chosen.text, chosen_model=chosen.model,
                       reason=reason, cost_usd=cost,
                       all_completions=list(completions))
