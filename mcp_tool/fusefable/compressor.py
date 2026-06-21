"""Prompt compressor — ลด token แต่คงความหมาย (2 ชั้น).

ชั้น 1 (lossless): normalize whitespace/บรรทัดว่าง/zero-width — ปลอดภัย ไม่เสียความหมาย
ชั้น 2 (LLM): ให้โมเดลถูกบีบเชิงความหมาย เฉพาะ prompt ยาวเกิน threshold
มี guard: ถ้าผลบีบ ว่าง/ยาวกว่าเดิม/สั้นเกินไป → fallback ใช้ lossless
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from fusefable.client import call_model
from fusefable.providers.base import Provider

_BLANKS = re.compile(r"\n{3,}")
_ZEROWIDTH = re.compile(r"[​‌‍﻿]")

COMPRESS_SYSTEM = (
    "You compress prompts to save tokens while preserving meaning EXACTLY. "
    "Keep ALL technical details, code, numbers, names, constraints, and requirements. "
    "Remove only filler words, redundancy, and repetition. "
    "Output ONLY the compressed prompt itself — no preamble, no explanation, no quotes."
)


@dataclass
class CompressionResult:
    text: str
    original_chars: int
    final_chars: int
    method: str  # "lossless" | "llm"

    @property
    def saved_pct(self) -> float:
        if self.original_chars == 0:
            return 0.0
        return (1 - self.final_chars / self.original_chars) * 100


def normalize_lossless(text: str) -> str:
    """ชั้น 1: ตัด trailing space + บรรทัดว่างซ้ำ + zero-width.

    คง indentation และช่องว่างภายในบรรทัดไว้ครบ (ปลอดภัยสำหรับโค้ด).
    """
    text = _ZEROWIDTH.sub("", text)
    lines = [ln.rstrip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = _BLANKS.sub("\n\n", text)
    return text.strip()


async def compress_prompt(provider: Provider, model: str, text: str, *,
                          min_chars: int, timeout_s: float,
                          min_ratio: float = 0.3) -> CompressionResult:
    """บีบ prompt 2 ชั้น. คืน CompressionResult (มี text ที่จะใช้จริง)."""
    original = len(text)
    lossless = normalize_lossless(text)

    # prompt สั้น → ข้ามชั้น 2
    if len(lossless) < min_chars:
        return CompressionResult(lossless, original, len(lossless), "lossless")

    # ชั้น 2: LLM
    instruction = f"{COMPRESS_SYSTEM}\n\n---\n{lossless}"
    result = await call_model(provider, model, instruction, timeout_s)
    if result.is_error:
        return CompressionResult(lossless, original, len(lossless), "lossless")

    compressed = result.text.strip()
    # guard กันคุณภาพตก: ว่าง / ยาวกว่าเดิม / สั้นเกินไป → ใช้ lossless
    if (not compressed
            or len(compressed) >= len(lossless)
            or len(compressed) < len(lossless) * min_ratio):
        return CompressionResult(lossless, original, len(lossless), "lossless")

    return CompressionResult(compressed, original, len(compressed), "llm")
