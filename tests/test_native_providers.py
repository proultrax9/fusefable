import httpx
import pytest
import respx
from fusefable.models import ProviderConfig
from fusefable.providers.anthropic import AnthropicProvider
from fusefable.providers.google import GoogleProvider
from fusefable.providers.factory import make_provider
from fusefable.providers.openai_compat import OpenAICompatProvider


@pytest.mark.asyncio
@respx.mock
async def test_anthropic_provider_parses_messages_format():
    route = respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json={
            "content": [{"type": "text", "text": "def f(): pass"}],
            "usage": {"input_tokens": 7, "output_tokens": 3},
        })
    )
    cfg = ProviderConfig("anthropic", "https://api.anthropic.com/v1", "k")
    async with httpx.AsyncClient() as http:
        c = await AnthropicProvider(cfg, http).complete("claude-opus-4-8", "hi")
    assert c.text == "def f(): pass"
    assert c.prompt_tokens == 7 and c.completion_tokens == 3
    # ส่ง header anthropic-version + x-api-key
    sent = route.calls[0].request
    assert sent.headers["x-api-key"] == "k"
    assert sent.headers["anthropic-version"] == "2023-06-01"


@pytest.mark.asyncio
@respx.mock
async def test_google_provider_parses_generatecontent_format():
    respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
    ).mock(return_value=httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": "hello"}]}}],
        "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2},
    }))
    cfg = ProviderConfig("google",
                         "https://generativelanguage.googleapis.com/v1beta", "k")
    async with httpx.AsyncClient() as http:
        c = await GoogleProvider(cfg, http).complete("gemini-2.5-pro", "hi")
    assert c.text == "hello"
    assert c.prompt_tokens == 5 and c.completion_tokens == 2


def test_factory_picks_class_by_kind():
    cfg = ProviderConfig("x", "https://x/v1", "k")
    with httpx.Client():
        pass
    import httpx as _h
    http = _h.AsyncClient()
    assert isinstance(make_provider("anthropic", cfg, http), AnthropicProvider)
    assert isinstance(make_provider("google", cfg, http), GoogleProvider)
    assert isinstance(make_provider("openai_compat", cfg, http), OpenAICompatProvider)
    # kind ไม่รู้จัก → openai_compat
    assert isinstance(make_provider("???", cfg, http), OpenAICompatProvider)
