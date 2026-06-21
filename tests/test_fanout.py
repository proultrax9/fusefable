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
    results, failures = await fan_out(routes, "prompt", timeout_s=5)
    texts = {r.text for r in results}
    assert texts == {"ta", "tc"}      # ตัว b พังถูกตัดออก
    assert len(failures) == 1


@pytest.mark.asyncio
async def test_fan_out_runs_in_parallel():
    prov = FakeProvider({"a": "ta", "b": "tb"}, delays={"a": 0.3, "b": 0.3})
    routes = [(prov, "a"), (prov, "b")]
    start = asyncio.get_event_loop().time()
    results, _ = await fan_out(routes, "p", timeout_s=5)
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed < 0.5               # ขนานกัน ไม่ใช่ 0.6


@pytest.mark.asyncio
async def test_fan_out_early_exit_when_min_responses_met():
    """พอได้ min_responses ตัว → ไม่รอตัวช้า."""
    prov = FakeProvider(
        {"fast1": "a", "fast2": "b", "fast3": "c", "slow": "d"},
        delays={"fast1": 0.01, "fast2": 0.01, "fast3": 0.01, "slow": 5.0},
    )
    routes = [(prov, m) for m in ("fast1", "fast2", "fast3", "slow")]
    start = asyncio.get_event_loop().time()
    results, _ = await fan_out(routes, "p", timeout_s=10, min_responses=3)
    elapsed = asyncio.get_event_loop().time() - start
    assert len(results) == 3
    assert elapsed < 1.0


def test_resolve_min_responses():
    from fusefable.fanout import _resolve_min_responses
    assert _resolve_min_responses(3, 7) == 3
    assert _resolve_min_responses(3, 2) == 2
    assert _resolve_min_responses(0, 5) == 5
    assert _resolve_min_responses(10, 5) == 5
