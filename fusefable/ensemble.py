"""Ensemble mode — รวมจุดเด่นหลายคำตอบเป็นคำตอบเดียว (แทนการเลือกตัวเดียว).

ปกปิดชื่อโมเดลเหมือน judge เพื่อให้ synthesize ที่เนื้อหาล้วน.
"""
from __future__ import annotations
from typing import Sequence
from fusefable.client import call_model
from fusefable.models import Completion
from fusefable.providers.base import Provider

_LABELS = "ABCDEFGHIJ"


def build_ensemble_prompt(question: str,
                          comps: Sequence[Completion]) -> str:
    labels = [_LABELS[i] for i in range(len(comps))]
    blocks = [f"### Answer {label}\n{c.text}" for label, c in zip(labels, comps)]
    body = "\n\n".join(blocks)
    return (
        "You are merging multiple coding answers into ONE superior answer.\n"
        "Combine correct and complementary parts, fix mistakes, drop redundancy.\n"
        "Output ONLY the final merged answer — no commentary about the sources.\n\n"
        f"## Question\n{question}\n\n"
        f"## Candidate Answers\n{body}"
    )


async def synthesize(provider: Provider, model: str, question: str,
                     comps: Sequence[Completion], timeout_s: float) -> str:
    """คืนข้อความคำตอบที่สังเคราะห์รวม. ถ้าพัง → fallback คำตอบแรก."""
    prompt = build_ensemble_prompt(question, comps)
    result = await call_model(provider, model, prompt, timeout_s)
    if result.is_error or not result.text.strip():
        return comps[0].text
    return result.text
