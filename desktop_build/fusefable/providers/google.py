"""Google Gemini native adapter — generateContent API.

format ต่างจาก OpenAI: model อยู่ใน path, key เป็น query param,
response อยู่ใน candidates[].content.parts[].text,
usage ใน usageMetadata.promptTokenCount/candidatesTokenCount.
"""
from __future__ import annotations
import time
import httpx
from fusefable.models import Completion, ProviderConfig


class GoogleProvider:
    def __init__(self, config: ProviderConfig, http: httpx.AsyncClient):
        self.config = config
        self.http = http

    async def complete(self, model: str, prompt: str) -> Completion:
        base = self.config.base_url.rstrip("/")
        url = f"{base}/models/{model}:generateContent"
        params = {"key": self.config.api_key}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        start = time.monotonic()
        resp = await self.http.post(url, params=params, json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency = time.monotonic() - start
        parts = (data.get("candidates", [{}])[0]
                 .get("content", {}).get("parts", []))
        text = "".join(p.get("text", "") for p in parts)
        usage = data.get("usageMetadata", {})
        return Completion(
            model=model,
            text=text,
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
            latency_s=latency,
        )
