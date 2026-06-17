import httpx
import pytest
import respx
from fusefable.models import ProviderConfig
from fusefable.providers.openai_compat import OpenAICompatProvider


@pytest.mark.asyncio
@respx.mock
async def test_complete_returns_text_and_usage():
    respx.post("https://api.openrouter.ai/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "def f(): pass"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4},
        })
    )
    cfg = ProviderConfig(name="openrouter",
                         base_url="https://api.openrouter.ai/v1", api_key="k")
    async with httpx.AsyncClient() as http:
        prov = OpenAICompatProvider(cfg, http)
        c = await prov.complete("openai/gpt-5", "write f")
    assert c.text == "def f(): pass"
    assert c.prompt_tokens == 12
    assert c.completion_tokens == 4
    assert c.is_error is False


@pytest.mark.asyncio
@respx.mock
async def test_complete_raises_on_http_error():
    respx.post("https://api.openrouter.ai/v1/chat/completions").mock(
        return_value=httpx.Response(429, json={"error": "rate limit"})
    )
    cfg = ProviderConfig(name="openrouter",
                         base_url="https://api.openrouter.ai/v1", api_key="k")
    async with httpx.AsyncClient() as http:
        prov = OpenAICompatProvider(cfg, http)
        with pytest.raises(httpx.HTTPStatusError):
            await prov.complete("openai/gpt-5", "write f")
