from __future__ import annotations
import os
import httpx
from fusefable.config import Config
from fusefable.models import ProviderConfig
from fusefable.providers.factory import make_provider


def build_routes(cfg: Config, http: httpx.AsyncClient) -> list[tuple]:
    """แปลง Config → list ของ (provider, model)."""
    routes = []
    if cfg.mode == "gateway":
        # gateway เป็น OpenAI-compatible เสมอ
        pc = ProviderConfig(cfg.gateway_name, cfg.gateway_base_url,
                            os.environ.get(cfg.api_key_env, ""))
        prov = make_provider("openai_compat", pc, http)
        for model in cfg.models:
            routes.append((prov, model))
    else:
        for sp in cfg.providers:
            pc = ProviderConfig(sp.name, sp.base_url,
                                os.environ.get(sp.api_key_env, ""))
            prov = make_provider(sp.kind, pc, http)
            for model in sp.models:
                routes.append((prov, model))
    return routes


def build_judge_provider(cfg: Config, http: httpx.AsyncClient):
    """provider สำหรับ judge — ใช้ gateway หรือ provider แรกใน single mode."""
    if cfg.mode == "gateway":
        pc = ProviderConfig(cfg.gateway_name, cfg.gateway_base_url,
                            os.environ.get(cfg.api_key_env, ""))
        return make_provider("openai_compat", pc, http)
    sp = cfg.providers[0]
    pc = ProviderConfig(sp.name, sp.base_url, os.environ.get(sp.api_key_env, ""))
    return make_provider(sp.kind, pc, http)
