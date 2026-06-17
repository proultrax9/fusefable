import json
from typer.testing import CliRunner
from fusefable.cli import app
from fusefable.models import FinalAnswer, Completion

runner = CliRunner()


def _fake_cfg():
    from fusefable.config import Config
    return Config(mode="gateway", gateway_name="openrouter",
                  gateway_base_url="https://x/v1", api_key_env="K",
                  timeout_seconds=90, judge_model="judge", models=["gpt-5"])


def _fake_answer():
    return FinalAnswer(text="best answer", chosen_model="gpt-5",
                       reason="clearest", cost_usd=0.01,
                       all_completions=[Completion(model="gpt-5", text="best answer")])


def _patch(monkeypatch):
    async def fake_fuse(*a, **k):
        return _fake_answer()
    monkeypatch.setattr("fusefable.cli.fuse", fake_fuse)
    monkeypatch.setattr("fusefable.cli._load_or_die", lambda: _fake_cfg())


def test_ask_command_prints_answer(monkeypatch):
    _patch(monkeypatch)
    result = runner.invoke(app, ["ask", "write quicksort"])
    assert result.exit_code == 0
    assert "best answer" in result.stdout
    assert "gpt-5" in result.stdout


def test_ask_quiet_prints_only_text(monkeypatch):
    _patch(monkeypatch)
    result = runner.invoke(app, ["ask", "q", "--quiet"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "best answer"   # เฉพาะคำตอบ ไม่มี header


def test_ask_json_output(monkeypatch):
    _patch(monkeypatch)
    result = runner.invoke(app, ["ask", "q", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["answer"] == "best answer"
    assert data["chosen_model"] == "gpt-5"
    assert data["candidates"][0]["model"] == "gpt-5"


def test_ask_reads_from_stdin(monkeypatch):
    _patch(monkeypatch)
    result = runner.invoke(app, ["ask", "--quiet"], input="piped question\n")
    assert result.exit_code == 0
    assert result.stdout.strip() == "best answer"
