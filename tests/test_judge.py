import pytest
from fusefable.judge import build_judge_prompt, parse_judge_choice, judge
from fusefable.models import Completion


def test_build_judge_prompt_anonymizes_models():
    comps = [Completion(model="claude", text="ans1"),
             Completion(model="gpt", text="ans2")]
    prompt, labels = build_judge_prompt("question?", comps)
    assert "claude" not in prompt and "gpt" not in prompt  # ปกปิดชื่อ
    assert "Answer A" in prompt and "Answer B" in prompt
    assert labels == ["A", "B"]


def test_parse_judge_choice_extracts_letter():
    assert parse_judge_choice("The best is B because...", ["A", "B"]) == "B"


def test_parse_judge_choice_fallback_first():
    # ถ้า parse ไม่เจอ → คืน label แรก
    assert parse_judge_choice("unclear response", ["A", "B"]) == "A"


@pytest.mark.asyncio
async def test_judge_picks_completion():
    comps = [Completion(model="claude", text="ans1"),
             Completion(model="gpt", text="ans2")]

    class FakeJudgeProvider:
        async def complete(self, model, prompt):
            return Completion(model=model, text="I choose B")

    chosen, reason = await judge(FakeJudgeProvider(), "judge-model",
                                 "question?", comps, timeout_s=5)
    assert chosen.model == "gpt"          # B = ตัวที่ 2
    assert "B" in reason
