"""เลือก provider class จาก 'kind' — รองรับหลายรูปแบบ API."""
from __future__ import annotations
import httpx
from fusefable.models import ProviderConfig
from fusefable.providers.openai_compat import OpenAICompatProvider
from fusefable.providers.anthropic import AnthropicProvider
from fusefable.providers.google import GoogleProvider

# default base_url ของ native provider แต่ละเจ้า (เติมอัตโนมัติถ้าไม่ระบุ)
NATIVE_BASE_URLS = {
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
}

_KINDS = {
    "openai_compat": OpenAICompatProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
}


def make_provider(kind: str, config: ProviderConfig, http: httpx.AsyncClient):
    """สร้าง provider ตาม kind. kind ที่ไม่รู้จัก → openai_compat."""
    cls = _KINDS.get(kind, OpenAICompatProvider)
    return cls(config, http)
