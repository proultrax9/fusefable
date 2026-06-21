from fusefable.config import Config
from fusefable.core import select_models


def _cfg(**kw):
    base = dict(mode="gateway", gateway_name="openrouter",
                gateway_base_url="https://x/v1", api_key_env="K",
                timeout_seconds=90, judge_model="judge",
                models=["m1", "m2", "m3"])
    base.update(kw)
    return Config(**base)


def test_select_models_default_all():
    assert select_models(_cfg()) is None


def test_select_models_explicit_list():
    assert select_models(_cfg(), models=["m1", "m3"]) == {"m1", "m3"}


def test_select_models_cheap_uses_config():
    cfg = _cfg(cheap_models=["m2"])
    assert select_models(cfg, cheap=True) == {"m2"}


def test_select_models_cheap_without_config_falls_back_all():
    # ไม่มี cheap_models ใน config → None (ใช้ทุกตัว)
    assert select_models(_cfg(), cheap=True) is None


def test_select_models_explicit_overrides_cheap():
    cfg = _cfg(cheap_models=["m2"])
    assert select_models(cfg, models=["m1"], cheap=True) == {"m1"}
