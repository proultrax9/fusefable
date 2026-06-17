from __future__ import annotations
import time
import httpx
from fusefable.models import Completion, ProviderConfig


class OpenAICompatProvider:
    """รองรับทุกเจ้าที่เป็น OpenAI-compatible (OpenRouter/OpenAI/DeepSeek/GLM/...)."""

    def __init__(self, config: ProviderConfig, http: httpx.AsyncClient):
        self.config = config
        self.http = http

    async def complete(self, model: str, prompt: str) -> Completion:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        start = time.monotonic()
        resp = await self.http.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        latency = time.monotonic() - start
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return Completion(
            model=model,
            text=text,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_s=latency,
        )
