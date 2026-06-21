"""Anthropic native adapter — Messages API (/v1/messages).

format ต่างจาก OpenAI: ใช้ header x-api-key + anthropic-version,
response อยู่ใน content[].text และ usage.input_tokens/output_tokens.
"""
from __future__ import annotations
import time
import httpx
from fusefable.models import Completion, ProviderConfig

ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 4096


class AnthropicProvider:
    def __init__(self, config: ProviderConfig, http: httpx.AsyncClient,
                 max_tokens: int = DEFAULT_MAX_TOKENS):
        self.config = config
        self.http = http
        self.max_tokens = max_tokens

    async def complete(self, model: str, prompt: str) -> Completion:
        url = f"{self.config.base_url.rstrip('/')}/messages"
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        start = time.monotonic()
        resp = await self.http.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        latency = time.monotonic() - start
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text")
        usage = data.get("usage", {})
        return Completion(
            model=model,
            text=text,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            latency_s=latency,
        )
