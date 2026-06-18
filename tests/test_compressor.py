import pytest
from fusefable.compressor import normalize_lossless, compress_prompt
from fusefable.models import Completion


def test_normalize_lossless_trims_safely_keeps_indent():
    raw = "def  f():\n\n\n\n    return   1   \n"
    out = normalize_lossless(raw)
    assert "\n\n\n" not in out                 # บรรทัดว่างซ้ำถูกยุบ
    assert out == "def  f():\n\n    return   1"  # คง indent + ช่องว่างภายใน, ตัดแค่ trailing


def test_normalize_strips_zero_width():
    assert normalize_lossless("a​b‌") == "ab"


class FakeProvider:
    def __init__(self, text=None, error=False):
        self.text, self.error = text, error
        self.called = False

    async def complete(self, model, prompt):
        self.called = True
        if self.error:
            raise RuntimeError("boom")
        return Completion(model=model, text=self.text)


@pytest.mark.asyncio
async def test_short_prompt_skips_llm():
    prov = FakeProvider(text="should not be used")
    r = await compress_prompt(prov, "m", "short text", min_chars=2000, timeout_s=5)
    assert r.method == "lossless"
    assert prov.called is False          # ไม่เรียก LLM


@pytest.mark.asyncio
async def test_long_prompt_uses_llm_when_shorter():
    big = "word " * 1000                 # ~5000 chars (lossless ~4999)
    prov = FakeProvider(text="C" * 2000) # อยู่ในช่วง 30%-100% → ผ่าน guard
    r = await compress_prompt(prov, "m", big, min_chars=2000, timeout_s=5)
    assert r.method == "llm"
    assert r.final_chars == 2000
    assert r.final_chars < r.original_chars
    assert r.saved_pct > 0


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_lossless():
    big = "word " * 1000
    prov = FakeProvider(error=True)
    r = await compress_prompt(prov, "m", big, min_chars=2000, timeout_s=5)
    assert r.method == "lossless"        # LLM พัง → ใช้ lossless


@pytest.mark.asyncio
async def test_guard_rejects_too_short_compression():
    big = "word " * 1000                 # ~5000 chars
    prov = FakeProvider(text="x")        # สั้นเกินไป (< 30%)
    r = await compress_prompt(prov, "m", big, min_chars=2000, timeout_s=5)
    assert r.method == "lossless"        # ป้องกันโมเดลตัดเนื้อหาทิ้ง


@pytest.mark.asyncio
async def test_guard_rejects_longer_result():
    big = "word " * 1000
    prov = FakeProvider(text="y" * 99999)  # ยาวกว่าเดิม
    r = await compress_prompt(prov, "m", big, min_chars=2000, timeout_s=5)
    assert r.method == "lossless"
