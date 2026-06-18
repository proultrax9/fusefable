"""Desktop window (PyWebView) — หน้าต่างโปรแกรมแบบ Cursor/VS Code.

ห่อ web UI ด้วย webview ของระบบ; JS เรียก Python ผ่าน js_api (ไม่ต้องมี web server).
แยก answer_to_dict / run_query (test ได้) ออกจาก run_app (เปิดหน้าต่างจริง).
"""
from __future__ import annotations
import asyncio
from typing import Optional
from fusefable.config import Config
from fusefable.core import fuse
from fusefable.models import FinalAnswer


def answer_to_dict(ans: FinalAnswer) -> dict:
    """แปลง FinalAnswer → dict ส่งให้ JS."""
    d = {
        "answer": ans.text,
        "chosen_model": ans.chosen_model,
        "reason": ans.reason,
        "cost_usd": ans.cost_usd,
        "cached": ans.cached,
        "budget_warning": ans.budget_warning,
        "candidates": [{"model": c.model, "text": c.text}
                       for c in ans.all_completions],
    }
    if ans.compression is not None:
        c = ans.compression
        d["compression"] = {
            "original_chars": c.original_chars,
            "final_chars": c.final_chars,
            "saved_pct": round(c.saved_pct, 1),
            "method": c.method,
        }
    return d


def _models_from_payload(payload: dict) -> Optional[list[str]]:
    raw = payload.get("models")
    if not raw:
        return None
    if isinstance(raw, str):
        items = [m.strip() for m in raw.split(",") if m.strip()]
        return items or None
    return list(raw) or None


def run_query(cfg: Config, payload: dict) -> dict:
    """รัน fuse จาก payload ของ UI. คืน dict (มี key 'error' ถ้าพัง) — ไม่โยน."""
    try:
        ans = asyncio.run(fuse(
            cfg, payload["question"],
            models=_models_from_payload(payload),
            compress=payload.get("compress"),
            ensemble=payload.get("ensemble"),
            use_cache=payload.get("cache"),
        ))
        return answer_to_dict(ans)
    except Exception as e:  # noqa: BLE001 — ส่ง error กลับ UI ไม่ให้หน้าต่างค้าง
        return {"error": str(e)}


class Api:
    """js_api ให้ฝั่ง JS เรียก (pywebview.api.ask(...))."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def ask(self, payload: dict) -> dict:
        return run_query(self.cfg, payload)


def run_app(cfg: Config) -> None:
    """เปิดหน้าต่าง desktop. ต้องติดตั้ง: pip install 'fusefable[app]'."""
    try:
        import webview
    except ImportError:
        raise SystemExit("ติดตั้งก่อน: pip install 'fusefable[app]'")
    from fusefable.web import INDEX_HTML
    api = Api(cfg)
    webview.create_window("Fuse Fable", html=INDEX_HTML, js_api=api,
                          width=960, height=720, min_size=(640, 480))
    webview.start()
