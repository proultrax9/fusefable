"""เก็บประวัติแชตของ GUI เป็นไฟล์ JSON ใน ~/.fusefable/history/<id>.json.

แต่ละ conversation: {id, title, created, updated, messages:[{role, content, meta}]}
แยก logic ออกจาก UI เพื่อ test ได้ (monkeypatch history_dir).
"""
from __future__ import annotations
import json
import uuid
from pathlib import Path
from typing import Optional


def history_dir() -> Path:
    return Path.home() / ".fusefable" / "history"


def _path(conv_id: str) -> Path:
    return history_dir() / f"{conv_id}.json"


def new_conversation(title: str = "New chat", *, now: float) -> dict:
    return {
        "id": uuid.uuid4().hex[:12],
        "title": title or "New chat",
        "created": now,
        "updated": now,
        "messages": [],
    }


def save_conversation(conv: dict) -> None:
    history_dir().mkdir(parents=True, exist_ok=True)
    _path(conv["id"]).write_text(
        json.dumps(conv, ensure_ascii=False), encoding="utf-8")


def load_conversation(conv_id: str) -> Optional[dict]:
    p = _path(conv_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def list_conversations() -> list[dict]:
    """คืน [{id, title, updated}] เรียงใหม่สุดก่อน."""
    d = history_dir()
    if not d.exists():
        return []
    items = []
    for f in d.glob("*.json"):
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
            items.append({"id": c["id"], "title": c.get("title", "Chat"),
                          "updated": c.get("updated", 0)})
        except (ValueError, OSError, KeyError):
            continue
    items.sort(key=lambda x: x["updated"], reverse=True)
    return items


def delete_conversation(conv_id: str) -> None:
    p = _path(conv_id)
    if p.exists():
        p.unlink()


def derive_title(text: str) -> str:
    """ตั้งชื่อแชตจากข้อความแรก (ตัดสั้น)."""
    t = " ".join(text.split())
    return (t[:40] + "…") if len(t) > 40 else (t or "New chat")
