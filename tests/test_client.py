import asyncio
import pytest
from fusefable.client import call_model
from fusefable.models import Completion


class FakeProvider:
    def __init__(self, text="", delay=0.0, raise_exc=None):
        self.text, self.delay, self.raise_exc = text, delay, raise_exc

    async def complete(self, model, prompt):
        await asyncio.sleep(self.delay)
        if self.raise_exc:
            raise self.raise_exc
        return Completion(model=model, text=self.text)


@pytest.mark.asyncio
async def test_call_model_success():
    c = await call_model(FakeProvider(text="ok"), "m", "p", timeout_s=5)
    assert c.text == "ok"
    assert c.is_error is False


@pytest.mark.asyncio
async def test_call_model_timeout_returns_failed():
    c = await call_model(FakeProvider(text="ok", delay=2), "m", "p", timeout_s=0.1)
    assert c.is_error is True
    assert "timeout" in c.error.lower()


@pytest.mark.asyncio
async def test_call_model_exception_returns_failed():
    c = await call_model(FakeProvider(raise_exc=ValueError("boom")), "m", "p", timeout_s=5)
    assert c.is_error is True
    assert "boom" in c.error
