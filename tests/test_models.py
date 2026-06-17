from fusefable.models import Completion, FinalAnswer, ProviderConfig


def test_completion_holds_result():
    c = Completion(label="A", model="gpt-5", text="hello",
                   prompt_tokens=10, completion_tokens=5, latency_s=1.2)
    assert c.label == "A"
    assert c.text == "hello"
    assert c.total_tokens == 15


def test_completion_error_factory():
    c = Completion.failed(model="gpt-5", error="timeout")
    assert c.text == ""
    assert c.is_error is True
    assert c.error == "timeout"


def test_provider_config_defaults():
    p = ProviderConfig(name="openrouter", base_url="https://x/api/v1", api_key="k")
    assert p.name == "openrouter"


def test_final_answer():
    fa = FinalAnswer(text="best", chosen_model="gpt-5", reason="clearest",
                     cost_usd=0.01)
    assert fa.chosen_model == "gpt-5"
