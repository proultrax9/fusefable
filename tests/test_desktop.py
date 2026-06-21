import fusefable.desktop as desktop
import fusefable.history as h
from fusefable.models import FinalAnswer, Completion
from fusefable.compressor import CompressionResult


def test_answer_to_dict_includes_meta():
    ans = FinalAnswer(text="best", chosen_model="gpt", reason="r", cost_usd=0.02,
                      all_completions=[Completion(model="gpt", text="best")],
                      compression=CompressionResult("x", 1000, 400, "llm"))
    d = desktop.answer_to_dict(ans)
    assert d["answer"] == "best"
    assert d["compression"]["saved_pct"] == 60.0


def test_models_from_payload_parses_csv():
    assert desktop._models_from_payload({"models": "a, b ,c"}) == ["a", "b", "c"]
    assert desktop._models_from_payload({"models": ""}) is None
    assert desktop._models_from_payload({}) is None


def test_process_ask_saves_history_and_returns_conversation_id(monkeypatch, tmp_path):
    monkeypatch.setattr(h, "history_dir", lambda: tmp_path / "history")

    async def fake_fuse(cfg, question, **k):
        assert k["progress"] is not None or k.get("progress") is None
        return FinalAnswer(text="hi", chosen_model="m", cost_usd=0.01)

    monkeypatch.setattr(desktop, "fuse", fake_fuse)
    out = desktop.process_ask("CFG", {"question": "Q", "models": "a,b"})
    assert out["answer"] == "hi"
    cid = out["conversation_id"]
    conv = h.load_conversation(cid)
    assert conv["messages"][0]["content"] == "Q"
    assert conv["messages"][1]["role"] == "assistant"
    assert conv["messages"][1]["meta"]["chosen_model"] == "m"


def test_process_ask_appends_to_existing_conversation(monkeypatch, tmp_path):
    monkeypatch.setattr(h, "history_dir", lambda: tmp_path / "history")

    async def fake_fuse(cfg, question, **k):
        return FinalAnswer(text="a2", chosen_model="m")

    monkeypatch.setattr(desktop, "fuse", fake_fuse)
    first = desktop.process_ask("CFG", {"question": "Q1"})
    cid = first["conversation_id"]
    second = desktop.process_ask("CFG", {"question": "Q2", "conversation_id": cid})
    assert second["conversation_id"] == cid
    conv = h.load_conversation(cid)
    assert len(conv["messages"]) == 4          # 2 turns


def test_build_gateway_config_autofills_known_url():
    cfg = desktop.build_gateway_config({
        "gateway": "openrouter", "api_key": "sk-x",
        "models": "a, b", "judge_model": ""})
    assert cfg.gateway_base_url == "https://openrouter.ai/api/v1"
    assert cfg.api_key == "sk-x"
    assert cfg.models == ["a", "b"]
    assert cfg.judge_model == "a"            # ว่าง → ใช้ตัวแรก


def test_build_gateway_config_custom_uses_base_url():
    cfg = desktop.build_gateway_config({
        "gateway": "custom", "base_url": "https://my/v1",
        "api_key": "k", "models": ["m1"]})
    assert cfg.gateway_base_url == "https://my/v1"


def test_build_config_from_settings_single_provider_is_gateway():
    cfg = desktop.build_config_from_settings({"providers": [
        {"gateway": "gemini", "api_key": "k", "models": "gemini-2.5-flash"}]})
    assert cfg.mode == "gateway"
    assert cfg.gateway_base_url.endswith("/v1beta/openai")
    assert cfg.api_key == "k"


def test_build_config_from_settings_multi_provider_is_single():
    cfg = desktop.build_config_from_settings({"providers": [
        {"gateway": "openrouter", "api_key": "k1", "models": "openai/gpt-5"},
        {"gateway": "gemini", "api_key": "k2", "models": "gemini-2.5-flash, gemini-2.5-pro"}]})
    assert cfg.mode == "single"
    assert len(cfg.providers) == 2
    assert cfg.providers[0].api_key == "k1" and cfg.providers[1].api_key == "k2"
    assert set(cfg.models) == {"openai/gpt-5", "gemini-2.5-flash", "gemini-2.5-pro"}
    assert desktop.is_configured(cfg) is True


def test_build_config_preserves_blank_key_from_existing():
    old = desktop.build_config_from_settings({"providers": [
        {"gateway": "openrouter", "api_key": "secret", "models": "m1"}]})
    new = desktop.build_config_from_settings(
        {"providers": [{"gateway": "openrouter", "api_key": "", "models": "m1, m2"}]},
        existing=old)
    assert new.api_key == "secret"           # คง key เดิมเมื่อเว้นว่าง


def test_is_configured():
    ok = desktop.build_gateway_config({"gateway": "openrouter", "api_key": "k",
                                       "models": "m1"})
    assert desktop.is_configured(ok) is True
    nokey = desktop.build_gateway_config({"gateway": "openrouter", "models": "m1"})
    assert desktop.is_configured(nokey) is False


def test_process_ask_passes_context_separately_and_stores_plain_question(monkeypatch, tmp_path):
    monkeypatch.setattr(h, "history_dir", lambda: tmp_path / "history")
    seen = {}

    async def fake_fuse(cfg, question, **k):
        seen["q"] = question
        seen["context"] = k.get("context")
        return FinalAnswer(text="ok", chosen_model="m")

    monkeypatch.setattr(desktop, "fuse", fake_fuse)
    out = desktop.process_ask("CFG", {"question": "explain", "context": "### a.py\nprint(1)"})
    # fuse ได้คำถามเดิม (bare) + context แยก → judge ไม่ต้องเห็น context ก้อนใหญ่
    assert seen["q"] == "explain"
    assert "print(1)" in seen["context"]
    conv = h.load_conversation(out["conversation_id"])
    assert conv["messages"][0]["content"] == "explain"


def test_process_ask_error(monkeypatch, tmp_path):
    monkeypatch.setattr(h, "history_dir", lambda: tmp_path / "history")

    async def boom(*a, **k):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(desktop, "fuse", boom)
    out = desktop.process_ask("CFG", {"question": "Q"})
    assert out["error"] == "kaboom"


def test_process_ask_applies_file_edits(monkeypatch, tmp_path):
    monkeypatch.setattr(h, "history_dir", lambda: tmp_path / "history")
    (tmp_path / "a.py").write_text("old", encoding="utf-8")

    async def fake_fuse(cfg, question, **k):
        assert "file_edit" in question.lower()
        return FinalAnswer(text=(
            '<file_edit path="a.py">\nnew content\n</file_edit>\n'
            "อัปเดต a.py แล้ว"), chosen_model="ensemble")

    monkeypatch.setattr(desktop, "fuse", fake_fuse)
    out = desktop.process_ask("CFG", {
        "question": "แก้ a.py", "project_root": str(tmp_path),
        "context": "### a.py\nold",
    })
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "\nnew content\n"
    assert out["answer"] == "อัปเดต a.py แล้ว"
    assert out["edits"][0]["ok"] is True
    conv = h.load_conversation(out["conversation_id"])
    assert conv["messages"][1]["content"] == "อัปเดต a.py แล้ว"


def test_process_ask_skips_edits_without_project_root(monkeypatch, tmp_path):
    monkeypatch.setattr(h, "history_dir", lambda: tmp_path / "history")

    async def fake_fuse(cfg, question, **k):
        return FinalAnswer(text='<file_edit path="a.py">\nx\n</file_edit>',
                           chosen_model="m")

    monkeypatch.setattr(desktop, "fuse", fake_fuse)
    out = desktop.process_ask("CFG", {"question": "fix"})
    assert out["edits"] == []
    assert out["answer"] == ""
