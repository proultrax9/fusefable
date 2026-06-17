import asyncio
import pytest
from fusefable.fanout import fan_out
from fusefable.models import Completion


class FakeProvider:
    def __init__(self, mapping, delays=None):
        self.mapping = mapping            # model -> text
        self.delays = delays or {}

    async def complete(self, model, prompt):
        await asyncio.sleep(self.delays.get(model, 0))
        if self.mapping[model] is None:
            raise RuntimeError("fail")
        return Completion(model=model, text=self.mapping[model])


@pytest.mark.asyncio
async def test_fan_out_returns_only_successful():
    prov = FakeProvider({"a": "ta", "b": None, "c": "tc"})
    routes = [(prov, "a"), (prov, "b"), (prov, "c")]
    results = await fan_out(routes, "prompt", timeout_s=5)
    texts = {r.text for r in results}
    assert texts == {"ta", "tc"}      # ตัว b พังถูกตัดออก


@pytest.mark.asyncio
async def test_fan_out_runs_in_parallel():
    prov = FakeProvider({"a": "ta", "b": "tb"}, delays={"a": 0.3, "b": 0.3})
    routes = [(prov, "a"), (prov, "b")]
    start = asyncio.get_event_loop().time()
    await fan_out(routes, "p", timeout_s=5)
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed < 0.5               # ขนานกัน ไม่ใช่ 0.6
