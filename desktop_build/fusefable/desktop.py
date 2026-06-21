"""Desktop window (PyWebView) — UI แบบ Cursor: sidebar ประวัติ + คำตอบไหลออก + progress.

แยก process_ask / answer_to_dict (test ได้) ออกจาก run_app (เปิดหน้าต่างจริง).
JS เรียก Python ผ่าน js_api; Python push progress กลับด้วย window.evaluate_js.
"""
from __future__ import annotations
import asyncio
import json
import os
import time
from typing import Callable, Optional
from fusefable.config import (Config, SingleProvider, load_config, save_config,
                              default_config_path)
from fusefable.core import fuse
from fusefable.models import FinalAnswer
from fusefable import history
from fusefable import project
from fusefable import edits as edits_mod
from fusefable.wizard import KNOWN_GATEWAYS


def build_gateway_config(payload: dict) -> Config:
    """สร้าง Config (gateway mode) จากฟอร์ม settings ในตัวโปรแกรม."""
    gw = (payload.get("gateway") or "openrouter").strip()
    base = KNOWN_GATEWAYS.get(gw.lower()) or (payload.get("base_url") or "").strip()
    models = payload.get("models") or []
    if isinstance(models, str):
        models = [m.strip() for m in models.split(",") if m.strip()]
    judge = (payload.get("judge_model") or "").strip() or (models[0] if models else "")
    return Config(
        mode="gateway", gateway_name=gw, gateway_base_url=base,
        api_key_env="", api_key=(payload.get("api_key") or "").strip(),
        models=models, judge_model=judge,
        timeout_seconds=int(payload.get("timeout_seconds") or 90),
        compress=bool(payload.get("compress")),
    )


def _provider_key(sp: SingleProvider) -> str:
    return os.environ.get(sp.api_key_env, "") or sp.api_key


def _existing_key_for(existing: Optional[Config], name: str) -> str:
    """ดึง key เดิมของ provider ชื่อนี้ (เผื่อผู้ใช้เว้น key ว่าง = คงของเดิม)."""
    if existing is None:
        return ""
    if existing.mode == "gateway" and existing.gateway_name == name:
        return existing.api_key
    for p in existing.providers:
        if p.name == name:
            return p.api_key
    return ""


def build_config_from_settings(payload: dict,
                               existing: Optional[Config] = None) -> Config:
    """สร้าง Config จากฟอร์ม settings ที่รองรับหลาย provider/หลาย key.

    1 provider → gateway mode; หลาย provider → single (mixed) mode.
    """
    provs = []
    for p in payload.get("providers") or []:
        gw = (p.get("gateway") or "").strip()
        if not gw:
            continue
        base = KNOWN_GATEWAYS.get(gw.lower()) or (p.get("base_url") or "").strip()
        models = p.get("models") or []
        if isinstance(models, str):
            models = [m.strip() for m in models.split(",") if m.strip()]
        key = (p.get("api_key") or "").strip() or _existing_key_for(existing, gw)
        if not models and not key:
            continue
        provs.append({"name": gw, "base_url": base, "api_key": key, "models": models})

    compress = bool(payload.get("compress"))
    timeout = int(payload.get("timeout_seconds") or 90)
    all_models = [m for p in provs for m in p["models"]]
    judge = (payload.get("judge_model") or "").strip() or (all_models[0] if all_models else "")

    extra = {}
    if existing is not None:
        extra["fusion_mode"] = existing.fusion_mode
        extra["min_responses"] = existing.min_responses
        extra["cache"] = existing.cache
        extra["cache_ttl_seconds"] = existing.cache_ttl_seconds
    if len(provs) == 1:
        p = provs[0]
        return Config(mode="gateway", gateway_name=p["name"], gateway_base_url=p["base_url"],
                      api_key_env="", api_key=p["api_key"], models=p["models"],
                      judge_model=judge, timeout_seconds=timeout, compress=compress,
                      **extra)
    sp = [SingleProvider(name=p["name"], base_url=p["base_url"], api_key_env="",
                         models=p["models"], kind="openai_compat", api_key=p["api_key"])
          for p in provs]
    return Config(mode="single", providers=sp, models=all_models,
                  judge_model=judge, timeout_seconds=timeout, compress=compress,
                  **extra)


def is_configured(cfg: Config) -> bool:
    if not cfg.models:
        return False
    if cfg.mode == "single":
        return bool(cfg.providers) and all(_provider_key(p) for p in cfg.providers)
    return bool(cfg.resolve_api_key()) and bool(cfg.gateway_base_url)


def _load_or_default() -> Config:
    try:
        return load_config(default_config_path())
    except FileNotFoundError:
        return Config(mode="gateway", timeout_seconds=90, judge_model="", models=[])


def answer_to_dict(ans: FinalAnswer) -> dict:
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


def process_ask(cfg: Config, payload: dict,
                progress: Optional[Callable[[dict], None]] = None) -> dict:
    """รัน fuse + apply file edits + บันทึกลงประวัติ."""
    question = payload["question"]
    context = payload.get("context") or ""
    project_root = (payload.get("project_root") or "").strip()
    fuse_question = (question + "\n\n" + edits_mod.AGENT_INSTRUCTIONS
                     if project_root else question)
    use_cache = False if project_root else payload.get("cache")
    try:
        ans = asyncio.run(fuse(
            cfg, fuse_question,
            models=_models_from_payload(payload),
            compress=payload.get("compress"),
            ensemble=payload.get("ensemble"),
            use_cache=use_cache,
            context=context,
            progress=progress,
        ))
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}

    edits_applied: list[dict] = []
    specs = edits_mod.parse_file_edits(ans.text)
    if project_root and specs:
        edits_applied = edits_mod.apply_edits(project_root, specs)
    ok_n = sum(1 for e in edits_applied if e.get("ok"))
    display = edits_mod.display_answer(ans.text, ok_n)

    d = answer_to_dict(ans)
    d["answer"] = display
    d["edits"] = edits_applied
    now = time.time()
    conv_id = payload.get("conversation_id")
    conv = history.load_conversation(conv_id) if conv_id else None
    if conv is None:
        conv = history.new_conversation(
            history.derive_title(payload["question"]), now=now)
    meta = {"chosen_model": d["chosen_model"], "cost_usd": d["cost_usd"],
            "cached": d["cached"]}
    if "compression" in d:
        meta["compression"] = d["compression"]
    if edits_applied:
        meta["edits"] = [{"path": e["path"], "ok": e.get("ok")}
                          for e in edits_applied]
    conv["messages"].append({"role": "user", "content": payload["question"]})
    conv["messages"].append({"role": "assistant", "content": display, "meta": meta})
    conv["updated"] = now
    history.save_conversation(conv)
    d["conversation_id"] = conv["id"]
    return d


class Api:
    """js_api ให้ฝั่ง JS เรียก."""

    def __init__(self, cfg: Config, window=None):
        self.cfg = cfg
        self.window = window

    def set_window(self, window) -> None:
        self.window = window

    def _progress(self, ev: dict) -> None:
        if self.window is not None:
            try:
                self.window.evaluate_js(f"window.ffProgress({json.dumps(ev)})")
            except Exception:  # noqa: BLE001
                pass

    # --- chat ---
    def ask(self, payload: dict) -> dict:
        return process_ask(self.cfg, payload, self._progress)

    # --- history ---
    def list_conversations(self) -> list:
        return history.list_conversations()

    def load_conversation(self, conv_id: str) -> Optional[dict]:
        return history.load_conversation(conv_id)

    def delete_conversation(self, conv_id: str) -> bool:
        history.delete_conversation(conv_id)
        return True

    # --- project files ---
    def pick_folder(self) -> dict:
        if self.window is None:
            return {"path": None}
        try:
            import webview
            res = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}
        if not res:
            return {"path": None}
        path = res[0] if isinstance(res, (list, tuple)) else res
        return {"path": path, "files": project.list_files(path)}

    def list_files(self, path: str) -> dict:
        try:
            return {"path": path, "files": project.list_files(path)}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def read_context(self, payload: dict) -> dict:
        try:
            root = payload["root"]
            all_paths = payload.get("all_paths")
            if all_paths is not None:
                paths = project.pick_context_paths(
                    all_paths,
                    open_path=payload.get("open_path") or "",
                    mentioned=payload.get("mentioned") or [],
                )
            else:
                paths = payload.get("paths") or []
            return project.read_files(
                root, paths,
                overrides=payload.get("overrides") or {},
            )
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def open_file(self, payload: dict) -> dict:
        try:
            return project.open_file(payload["root"], payload["path"])
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def read_image(self, payload: dict) -> dict:
        try:
            return project.read_image(payload["root"], payload["path"])
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def save_file(self, payload: dict) -> dict:
        try:
            return project.write_file(payload["root"], payload["path"],
                                      payload.get("content", ""))
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    # --- settings ---
    def get_status(self) -> dict:
        cfg = self.cfg
        if cfg.mode == "single" and cfg.providers:
            providers = [{"gateway": p.name, "base_url": p.base_url,
                          "models": p.models, "has_key": bool(_provider_key(p)),
                          "api_key": p.api_key}
                         for p in cfg.providers]
        else:
            providers = [{"gateway": cfg.gateway_name or "openrouter",
                          "base_url": cfg.gateway_base_url, "models": cfg.models,
                          "has_key": bool(cfg.resolve_api_key()),
                          "api_key": cfg.api_key}]
        return {
            "configured": is_configured(cfg),
            "mode": cfg.mode,
            "providers": providers,
            "judge_model": cfg.judge_model,
            "compress": cfg.compress,
            "fusion_mode": cfg.fusion_mode,
            "cache": cfg.cache,
            "gateways": sorted(KNOWN_GATEWAYS),
        }

    def save_settings(self, payload: dict) -> dict:
        try:
            cfg = build_config_from_settings(payload, self.cfg)
            save_config(cfg, default_config_path())
            self.cfg = cfg
            return {"ok": True, "configured": is_configured(cfg)}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}


def run_app(cfg: Optional[Config] = None) -> None:
    """เปิดหน้าต่าง desktop. ต้องติดตั้ง: pip install 'fusefable[app]'."""
    try:
        import webview
    except ImportError:
        raise SystemExit("ติดตั้งก่อน: pip install 'fusefable[app]'")
    from fusefable.web import INDEX_HTML
    if cfg is None:
        cfg = _load_or_default()
    api = Api(cfg)
    window = webview.create_window("Fusion Fable", html=INDEX_HTML, js_api=api,
                                   width=1080, height=760, min_size=(720, 520))
    api.set_window(window)
    webview.start()


def main() -> None:
    """Entry point สำหรับ executable (PyInstaller) — เปิด GUI ตรงๆ."""
    run_app()
