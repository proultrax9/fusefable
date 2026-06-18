"""Cache คำตอบ — คำถามซ้ำ (config เดิม) ไม่ต้องยิงใหม่.

เก็บเป็นไฟล์ JSON ใน ~/.fusefable/cache/<sha256>.json
key มาจาก question + รายชื่อโมเดล + flags ที่กระทบผลลัพธ์
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Sequence
from fusefable.models import Completion, FinalAnswer


def cache_dir() -> Path:
    return Path.home() / ".fusefable" / "cache"


def make_key(question: str, models: Sequence[str], *, compress: bool,
             mode: str, judge_model: str) -> str:
    payload = json.dumps({
        "q": question,
        "models": sorted(models),
        "compress": compress,
        "mode": mode,
        "judge": judge_model,
    }, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _path(key: str) -> Path:
    return cache_dir() / f"{key}.json"


def load_cached(key: str, ttl_seconds: int, *, now: float) -> Optional[FinalAnswer]:
    """คืน FinalAnswer (cached=True) ถ้ามีและยังไม่หมดอายุ; ไม่งั้น None.

    ttl_seconds = 0 หมายถึงไม่หมดอายุ.
    """
    p = _path(key)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if ttl_seconds > 0 and now - data.get("ts", 0) > ttl_seconds:
        return None
    d = data["answer"]
    return FinalAnswer(
        text=d["text"],
        chosen_model=d["chosen_model"],
        reason=d.get("reason", ""),
        cost_usd=d.get("cost_usd", 0.0),
        all_completions=[Completion(model=c["model"], text=c["text"])
                         for c in d.get("candidates", [])],
        cached=True,
    )


def save_cached(key: str, answer: FinalAnswer, *, now: float) -> None:
    d = {
        "ts": now,
        "answer": {
            "text": answer.text,
            "chosen_model": answer.chosen_model,
            "reason": answer.reason,
            "cost_usd": answer.cost_usd,
            "candidates": [{"model": c.model, "text": c.text}
                           for c in answer.all_completions],
        },
    }
    cache_dir().mkdir(parents=True, exist_ok=True)
    _path(key).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
