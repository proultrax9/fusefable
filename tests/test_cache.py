import fusefable.cache as cache_mod
from fusefable.cache import make_key, load_cached, save_cached
from fusefable.models import FinalAnswer, Completion


def _use_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(cache_mod, "cache_dir", lambda: tmp_path / "cache")


def test_make_key_stable_and_order_independent():
    k1 = make_key("q", ["a", "b"], compress=False, mode="judge", judge_model="j")
    k2 = make_key("q", ["b", "a"], compress=False, mode="judge", judge_model="j")
    assert k1 == k2                          # ลำดับโมเดลไม่มีผล
    k3 = make_key("q", ["a"], compress=False, mode="judge", judge_model="j")
    assert k1 != k3                          # ชุดโมเดลต่าง = key ต่าง


def test_make_key_differs_by_mode_and_compress():
    base = dict(models=["a"], judge_model="j")
    assert (make_key("q", compress=False, mode="judge", **base)
            != make_key("q", compress=True, mode="judge", **base))
    assert (make_key("q", compress=False, mode="judge", **base)
            != make_key("q", compress=False, mode="ensemble", **base))


def test_save_and_load_roundtrip(monkeypatch, tmp_path):
    _use_tmp(monkeypatch, tmp_path)
    ans = FinalAnswer(text="best", chosen_model="gpt", reason="r", cost_usd=0.02,
                      all_completions=[Completion(model="gpt", text="best")])
    save_cached("k1", ans, now=1000.0)
    got = load_cached("k1", ttl_seconds=0, now=2000.0)
    assert got is not None
    assert got.text == "best"
    assert got.cached is True                # mark ว่ามาจาก cache
    assert got.all_completions[0].model == "gpt"


def test_load_miss_returns_none(monkeypatch, tmp_path):
    _use_tmp(monkeypatch, tmp_path)
    assert load_cached("nope", ttl_seconds=0, now=1.0) is None


def test_ttl_expiry(monkeypatch, tmp_path):
    _use_tmp(monkeypatch, tmp_path)
    ans = FinalAnswer(text="x", chosen_model="m")
    save_cached("k", ans, now=1000.0)
    assert load_cached("k", ttl_seconds=60, now=1030.0) is not None   # ภายใน TTL
    assert load_cached("k", ttl_seconds=60, now=1100.0) is None       # เกิน TTL
