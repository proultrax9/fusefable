from typer.testing import CliRunner
from fusefable.cli import app
from fusefable.models import FinalAnswer, Completion

runner = CliRunner()


def _fake_cfg():
    from fusefable.config import Config
    return Config(mode="gateway", gateway_name="openrouter",
                  gateway_base_url="https://x/v1", api_key_env="K",
                  timeout_seconds=90, judge_model="judge", models=["gpt-5"])


def test_ask_command_prints_answer(monkeypatch):
    fake = FinalAnswer(text="best answer", chosen_model="gpt-5",
                       reason="clearest", cost_usd=0.01,
                       all_completions=[Completion(model="gpt-5", text="best answer")])

    async def fake_run_fusion(*a, **k):
        return fake

    monkeypatch.setattr("fusefable.cli.run_fusion", fake_run_fusion)
    monkeypatch.setattr("fusefable.cli._load_or_die", lambda: _fake_cfg())
    result = runner.invoke(app, ["ask", "write quicksort"])
    assert result.exit_code == 0
    assert "best answer" in result.stdout
    assert "gpt-5" in result.stdout
