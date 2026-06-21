from __future__ import annotations
import re
from typing import Sequence
from fusefable.client import call_model
from fusefable.models import Completion
from fusefable.providers.base import Provider

_LABELS = "ABCDEFGHIJ"


def build_judge_prompt(question: str,
                       comps: Sequence[Completion]) -> tuple[str, list[str]]:
    """สร้าง prompt สำหรับ judge โดยปกปิดชื่อโมเดล (Answer A/B/C...)."""
    labels = [_LABELS[i] for i in range(len(comps))]
    blocks = [f"### Answer {label}\n{c.text}" for label, c in zip(labels, comps)]
    body = "\n\n".join(blocks)
    prompt = (
        "You are judging coding answers. Pick the single best answer.\n\n"
        f"## Question\n{question}\n\n"
        f"## Candidate Answers\n{body}\n\n"
        "Reply with the letter of the best answer first (e.g. 'B'), "
        "then one sentence why."
    )
    return prompt, labels


def parse_judge_choice(text: str, labels: list[str]) -> str:
    """ดึงตัวอักษรที่ judge เลือก; ถ้าไม่เจอคืน label แรก (fallback).

    หา single-letter token ตัวแรกที่เป็น label จริง — เลี่ยงคำอย่าง 'I'
    ในประโยค 'I choose B' ถูกจับผิด.
    """
    for token in re.findall(r"\b([A-J])\b", text):
        if token in labels:
            return token
    return labels[0]


async def judge(provider: Provider, judge_model: str, question: str,
                comps: Sequence[Completion], timeout_s: float
                ) -> tuple[Completion, str]:
    """คืน (Completion ที่ถูกเลือก, เหตุผล). fallback = ตัวแรกถ้า judge พัง."""
    prompt, labels = build_judge_prompt(question, comps)
    result = await call_model(provider, judge_model, prompt, timeout_s)
    if result.is_error:
        return comps[0], f"judge failed ({result.error}); fell back to first answer"
    choice = parse_judge_choice(result.text, labels)
    idx = labels.index(choice)
    return comps[idx], result.text
