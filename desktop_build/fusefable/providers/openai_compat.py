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
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        # OpenRouter แนะนำ header เหล่านี้ (ไม่บังคับ แต่ช่วย rate-limit / attribution)
        if "openrouter.ai" in self.config.base_url:
            headers["HTTP-Referer"] = "https://github.com/fusion-fable/desktop"
            headers["X-Title"] = "Fusion Fable"
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        start = time.monotonic()
        resp = await self.http.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            detail = resp.text.strip()
            try:
                detail = resp.json().get("error", {}).get("message", detail)
            except Exception:  # noqa: BLE001
                pass
            raise httpx.HTTPStatusError(
                f"{resp.status_code} {resp.reason_phrase}: {detail}",
                request=resp.request, response=resp)
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
