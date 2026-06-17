import pytest
from fusefable.fusion import run_fusion
from fusefable.models import Completion


class FakeProvider:
    def __init__(self, mapping):
        self.mapping = mapping   # model -> text

    async def complete(self, model, prompt):
        return Completion(model=model, text=self.mapping[model],
                          prompt_tokens=10, completion_tokens=5)


@pytest.mark.asyncio
async def test_run_fusion_end_to_end():
    prov = FakeProvider({
        "m1": "answer one", "m2": "answer two",
        "judge": "I choose B because it is clearer",
    })
    routes = [(prov, "m1"), (prov, "m2")]
    result = await run_fusion(routes, prov, "judge", "question?", timeout_s=5)
    assert result.chosen_model == "m2"        # B
    assert result.text == "answer two"
    assert result.cost_usd > 0
    assert len(result.all_completions) == 2


@pytest.mark.asyncio
async def test_run_fusion_raises_when_all_fail():
    class DeadProvider:
        async def complete(self, model, prompt):
            raise RuntimeError("dead")
    routes = [(DeadProvider(), "m1")]
    with pytest.raises(RuntimeError, match="no successful"):
        await run_fusion(routes, DeadProvider(), "judge", "q", timeout_s=5)
