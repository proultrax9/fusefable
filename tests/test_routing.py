import httpx
from fusefable.config import Config, SingleProvider
from fusefable.routing import build_routes, build_judge_provider


def test_build_routes_gateway_mode(monkeypatch):
    monkeypatch.setenv("OR_KEY", "k")
    cfg = Config(mode="gateway", gateway_name="openrouter",
                 gateway_base_url="https://openrouter.ai/api/v1",
                 api_key_env="OR_KEY", timeout_seconds=90,
                 judge_model="deepseek/deepseek-chat",
                 models=["openai/gpt-5", "anthropic/claude-opus-4.1"])
    http = httpx.AsyncClient()
    routes = build_routes(cfg, http)
    assert len(routes) == 2
    assert routes[0][1] == "openai/gpt-5"          # (provider, model)


def test_build_routes_single_mode(monkeypatch):
    monkeypatch.setenv("OAI", "k1")
    monkeypatch.setenv("DS", "k2")
    cfg = Config(mode="single", timeout_seconds=90, judge_model="deepseek-chat",
                 providers=[
                     SingleProvider("openai", "https://api.openai.com/v1", "OAI", ["gpt-5"]),
                     SingleProvider("deepseek", "https://api.deepseek.com/v1", "DS", ["deepseek-chat"]),
                 ],
                 models=["gpt-5", "deepseek-chat"])
    http = httpx.AsyncClient()
    routes = build_routes(cfg, http)
    assert {r[1] for r in routes} == {"gpt-5", "deepseek-chat"}
