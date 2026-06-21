"""Ensemble mode — ตรวจสอบทุกคำตอบแล้วสังเคราะห์คำตอบใหม่ (ไม่เลือกตัวเดียว).

ปกปิดชื่อโมเดลเหมือน judge เพื่อให้ synthesize ที่เนื้อหาล้วน ไม่ bias ตามยี่ห้อ.
"""
from __future__ import annotations
from typing import Sequence
from fusefable.client import call_model
from fusefable.models import Completion
from fusefable.edits import ENSEMBLE_EDIT_NOTE

_LABELS = "ABCDEFGHIJ"


def build_ensemble_prompt(question: str,
                          comps: Sequence[Completion]) -> str:
    labels = [_LABELS[i] for i in range(len(comps))]
    blocks = [f"### Answer {label}\n{c.text}" for label, c in zip(labels, comps)]
    body = "\n\n".join(blocks)
    edit_note = ENSEMBLE_EDIT_NOTE if "file_edit" in question.lower() else ""
    return (
        "You are synthesizing a coding answer from multiple independent candidates.\n"
        "Do NOT pick one answer and return it — write your OWN answer.\n\n"
        "Process (internal — do not output these steps):\n"
        "1. Read every candidate carefully.\n"
        "2. Critically verify: what is correct, wrong, incomplete, or contradictory?\n"
        "3. Cross-check claims; prefer parts supported by multiple candidates.\n"
        "4. Combine the best ideas, fix errors, fill gaps, drop redundancy.\n"
        "5. Write one final answer in your own words, as if you solved it yourself.\n\n"
        "Output ONLY the final synthesized answer — no commentary about sources or steps."
        f"{edit_note}\n\n"
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
