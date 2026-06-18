from fusefable.cost import estimate_cost, estimate_prefire_cost
from fusefable.models import Completion


def test_estimate_prefire_scales_with_models():
    one = estimate_prefire_cost("x" * 4000, n_models=1)
    five = estimate_prefire_cost("x" * 4000, n_models=5)
    assert five > one              # ยิ่งหลายโมเดล ยิ่งแพง
    assert one > 0


def test_estimate_cost_sums_tokens():
    comps = [
        Completion(model="a", text="x", prompt_tokens=1000, completion_tokens=500),
        Completion(model="b", text="y", prompt_tokens=2000, completion_tokens=1000),
    ]
    # default rate $1/1M in, $3/1M out เมื่อไม่รู้ราคาโมเดล
    cost = estimate_cost(comps, default_in=1.0, default_out=3.0)
    # (3000/1e6 * 1) + (1500/1e6 * 3) = 0.003 + 0.0045 = 0.0075
    assert round(cost, 6) == 0.0075
