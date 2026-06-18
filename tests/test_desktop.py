import pytest
from fusefable import desktop
from fusefable.models import FinalAnswer, Completion
from fusefable.compressor import CompressionResult


def test_answer_to_dict_includes_meta():
    ans = FinalAnswer(text="best", chosen_model="gpt", reason="r", cost_usd=0.02,
                      all_completions=[Completion(model="gpt", text="best")],
                      compression=CompressionResult("x", 1000, 400, "llm"))
    d = desktop.answer_to_dict(ans)
    assert d["answer"] == "best"
    assert d["chosen_model"] == "gpt"
    assert d["candidates"][0]["model"] == "gpt"
    assert d["compression"]["method"] == "llm"
    assert d["compression"]["saved_pct"] == 60.0


def test_models_from_payload_parses_csv():
    assert desktop._models_from_payload({"models": "a, b ,c"}) == ["a", "b", "c"]
    assert desktop._models_from_payload({"models": ""}) is None
    assert desktop._models_from_payload({}) is None


def test_run_query_calls_fuse_and_serializes(monkeypatch):
    captured = {}

    async def fake_fuse(cfg, question, models=None, compress=None,
                        ensemble=None, use_cache=None):
        captured.update(question=question, models=models, compress=compress,
                        ensemble=ensemble, use_cache=use_cache)
        return FinalAnswer(text="hi", chosen_model="m")

    monkeypatch.setattr(desktop, "fuse", fake_fuse)
    out = desktop.run_query("CFG", {"question": "Q", "models": "a,b",
                                    "compress": True, "ensemble": False, "cache": True})
    assert out["answer"] == "hi"
    assert captured["question"] == "Q"
    assert captured["models"] == ["a", "b"]
    assert captured["compress"] is True
    assert captured["use_cache"] is True


def test_run_query_returns_error_on_failure(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(desktop, "fuse", boom)
    out = desktop.run_query("CFG", {"question": "Q"})
    assert out["error"] == "kaboom"
