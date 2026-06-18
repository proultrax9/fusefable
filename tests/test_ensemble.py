import pytest
from fusefable.ensemble import build_ensemble_prompt, synthesize
from fusefable.models import Completion


def test_build_ensemble_prompt_anonymizes():
    comps = [Completion(model="claude", text="a1"),
             Completion(model="gpt", text="a2")]
    p = build_ensemble_prompt("q?", comps)
    assert "claude" not in p and "gpt" not in p
    assert "Answer A" in p and "Answer B" in p
    assert "merg" in p.lower()


@pytest.mark.asyncio
async def test_synthesize_returns_merged_text():
    comps = [Completion(model="a", text="x"), Completion(model="b", text="y")]

    class P:
        async def complete(self, model, prompt):
            return Completion(model=model, text="MERGED")

    out = await synthesize(P(), "judge", "q?", comps, timeout_s=5)
    assert out == "MERGED"


@pytest.mark.asyncio
async def test_synthesize_fallback_on_error():
    comps = [Completion(model="a", text="first"), Completion(model="b", text="y")]

    class P:
        async def complete(self, model, prompt):
            raise RuntimeError("boom")

    out = await synthesize(P(), "judge", "q?", comps, timeout_s=5)
    assert out == "first"          # fallback คำตอบแรก
