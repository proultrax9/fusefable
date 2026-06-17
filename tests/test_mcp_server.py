import pytest
from fusefable import mcp_server
from fusefable.models import FinalAnswer


@pytest.mark.asyncio
async def test_fuse_ask_impl_returns_best_text(monkeypatch):
    captured = {}

    def fake_load(_path):
        return "CFG"

    async def fake_fuse(cfg, question, models=None, cheap=False):
        captured.update(cfg=cfg, question=question, models=models, cheap=cheap)
        return FinalAnswer(text="the best", chosen_model="gpt-5")

    monkeypatch.setattr(mcp_server, "load_config", fake_load)
    monkeypatch.setattr(mcp_server, "fuse", fake_fuse)

    out = await mcp_server.fuse_ask_impl("write quicksort", models="a,b", cheap=True)
    assert out == "the best"
    assert captured["question"] == "write quicksort"
    assert captured["models"] == ["a", "b"]      # split comma
    assert captured["cheap"] is True


@pytest.mark.asyncio
async def test_fuse_ask_impl_no_models(monkeypatch):
    monkeypatch.setattr(mcp_server, "load_config", lambda _p: "CFG")

    async def fake_fuse(cfg, question, models=None, cheap=False):
        assert models is None
        return FinalAnswer(text="x", chosen_model="m")

    monkeypatch.setattr(mcp_server, "fuse", fake_fuse)
    out = await mcp_server.fuse_ask_impl("q")
    assert out == "x"
