# Fuse Fable Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้าง CLI tool `fusefable` ที่ยิงหลาย AI model พร้อมกัน (fan-out) แล้วใช้ judge เลือกคำตอบที่ดีที่สุดสำหรับงานโค้ด โดย latency ≈ x2

**Architecture:** Python async (`asyncio` + `httpx`). Provider เป็น OpenAI-compatible adapter (ครอบคลุม OpenRouter/OpenAI/DeepSeek/GLM/Qwen ฯลฯ). orchestrator: fan-out → judge → final answer. ตั้งค่าผ่าน setup wizard เขียนลง config.yaml

**Tech Stack:** Python 3.10+, asyncio, httpx, typer, pyyaml, pytest, pytest-asyncio, respx (mock HTTP)

---

## File Structure

```
fusefable/
├── __init__.py
├── models.py        # dataclass: Completion, FinalAnswer, ProviderConfig
├── config.py        # โหลด/validate/เขียน config.yaml
├── providers/
│   ├── __init__.py
│   ├── base.py      # Protocol: async complete(model, prompt) -> Completion
│   └── openai_compat.py  # OpenAI-compatible (OpenRouter เป็น default)
├── client.py        # ยิง 1 โมเดล + timeout/error
├── fanout.py        # ยิง N ตัวขนาน (asyncio.gather)
├── judge.py         # ปกปิดชื่อ → ให้ judge เลือก
├── fusion.py        # orchestrator
├── wizard.py        # setup wizard (interactive)
└── cli.py           # typer CLI
tests/
├── test_models.py
├── test_config.py
├── test_openai_compat.py
├── test_client.py
├── test_fanout.py
├── test_judge.py
├── test_fusion.py
└── test_wizard.py
pyproject.toml
```

---

### Task 0: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `fusefable/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: Init git repo**

Run: `git init`
Expected: "Initialized empty Git repository"

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
venv/
*.egg-info/
.pytest_cache/
config.yaml
.fusefable/
.env
```

- [ ] **Step 3: Create `pyproject.toml`**

```toml
[project]
name = "fusefable"
version = "0.1.0"
description = "Fuse multiple AI models and judge the best answer for coding"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.27",
    "typer>=0.12",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "respx>=0.21"]

[project.scripts]
fusefable = "fusefable.cli:app"
ff = "fusefable.cli:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 4: Create empty package files**

`fusefable/__init__.py`:
```python
__version__ = "0.1.0"
```

`tests/__init__.py`: (empty file)

- [ ] **Step 5: Install dev deps**

Run: `pip install -e ".[dev]"`
Expected: ติดตั้งสำเร็จ, `fusefable` command ใช้ได้

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: project scaffolding"
```

---

### Task 1: Data models

**Files:**
- Create: `fusefable/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — "No module named 'fusefable.models'"

- [ ] **Step 3: Write minimal implementation**

```python
# fusefable/models.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key: str


@dataclass
class Completion:
    model: str
    text: str
    label: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    is_error: bool = False
    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @classmethod
    def failed(cls, model: str, error: str) -> "Completion":
        return cls(model=model, text="", is_error=True, error=error)


@dataclass
class FinalAnswer:
    text: str
    chosen_model: str
    reason: str = ""
    cost_usd: float = 0.0
    all_completions: list = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add fusefable/models.py tests/test_models.py
git commit -m "feat: add data models"
```

---

### Task 2: OpenAI-compatible provider

**Files:**
- Create: `fusefable/providers/__init__.py`
- Create: `fusefable/providers/base.py`
- Create: `fusefable/providers/openai_compat.py`
- Test: `tests/test_openai_compat.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_openai_compat.py
import httpx
import pytest
import respx
from fusefable.models import ProviderConfig
from fusefable.providers.openai_compat import OpenAICompatProvider


@pytest.mark.asyncio
@respx.mock
async def test_complete_returns_text_and_usage():
    respx.post("https://api.openrouter.ai/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "def f(): pass"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 4},
        })
    )
    cfg = ProviderConfig(name="openrouter",
                         base_url="https://api.openrouter.ai/v1", api_key="k")
    async with httpx.AsyncClient() as http:
        prov = OpenAICompatProvider(cfg, http)
        c = await prov.complete("openai/gpt-5", "write f")
    assert c.text == "def f(): pass"
    assert c.prompt_tokens == 12
    assert c.completion_tokens == 4
    assert c.is_error is False


@pytest.mark.asyncio
@respx.mock
async def test_complete_raises_on_http_error():
    respx.post("https://api.openrouter.ai/v1/chat/completions").mock(
        return_value=httpx.Response(429, json={"error": "rate limit"})
    )
    cfg = ProviderConfig(name="openrouter",
                         base_url="https://api.openrouter.ai/v1", api_key="k")
    async with httpx.AsyncClient() as http:
        prov = OpenAICompatProvider(cfg, http)
        with pytest.raises(httpx.HTTPStatusError):
            await prov.complete("openai/gpt-5", "write f")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_openai_compat.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write base Protocol**

`fusefable/providers/__init__.py`: (empty file)

```python
# fusefable/providers/base.py
from __future__ import annotations
from typing import Protocol
from fusefable.models import Completion


class Provider(Protocol):
    async def complete(self, model: str, prompt: str) -> Completion:
        """ยิง 1 โมเดล คืน Completion. โยน exception ได้เมื่อ HTTP error."""
        ...
```

- [ ] **Step 4: Write the OpenAI-compatible provider**

```python
# fusefable/providers/openai_compat.py
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_openai_compat.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add fusefable/providers/ tests/test_openai_compat.py
git commit -m "feat: add OpenAI-compatible provider"
```

---

### Task 3: Client (single call + timeout/error wrapper)

**Files:**
- Create: `fusefable/client.py`
- Test: `tests/test_client.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_client.py
import asyncio
import pytest
from fusefable.client import call_model
from fusefable.models import Completion


class FakeProvider:
    def __init__(self, text="", delay=0.0, raise_exc=None):
        self.text, self.delay, self.raise_exc = text, delay, raise_exc

    async def complete(self, model, prompt):
        await asyncio.sleep(self.delay)
        if self.raise_exc:
            raise self.raise_exc
        return Completion(model=model, text=self.text)


@pytest.mark.asyncio
async def test_call_model_success():
    c = await call_model(FakeProvider(text="ok"), "m", "p", timeout_s=5)
    assert c.text == "ok"
    assert c.is_error is False


@pytest.mark.asyncio
async def test_call_model_timeout_returns_failed():
    c = await call_model(FakeProvider(text="ok", delay=2), "m", "p", timeout_s=0.1)
    assert c.is_error is True
    assert "timeout" in c.error.lower()


@pytest.mark.asyncio
async def test_call_model_exception_returns_failed():
    c = await call_model(FakeProvider(raise_exc=ValueError("boom")), "m", "p", timeout_s=5)
    assert c.is_error is True
    assert "boom" in c.error
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_client.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# fusefable/client.py
from __future__ import annotations
import asyncio
from fusefable.models import Completion
from fusefable.providers.base import Provider


async def call_model(provider: Provider, model: str, prompt: str,
                     timeout_s: float) -> Completion:
    """ยิง 1 โมเดล โดยไม่โยน exception — คืน Completion.failed เมื่อ timeout/error."""
    try:
        return await asyncio.wait_for(provider.complete(model, prompt),
                                      timeout=timeout_s)
    except asyncio.TimeoutError:
        return Completion.failed(model=model, error=f"timeout after {timeout_s}s")
    except Exception as e:  # noqa: BLE001 — ตั้งใจกันทุก error ไม่ให้ระบบล่ม
        return Completion.failed(model=model, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_client.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add fusefable/client.py tests/test_client.py
git commit -m "feat: add client with timeout/error handling"
```

---

### Task 4: Fan-out

**Files:**
- Create: `fusefable/fanout.py`
- Test: `tests/test_fanout.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fanout.py
import asyncio
import pytest
from fusefable.fanout import fan_out
from fusefable.models import Completion


class FakeProvider:
    def __init__(self, mapping, delays=None):
        self.mapping = mapping            # model -> text
        self.delays = delays or {}

    async def complete(self, model, prompt):
        await asyncio.sleep(self.delays.get(model, 0))
        if self.mapping[model] is None:
            raise RuntimeError("fail")
        return Completion(model=model, text=self.mapping[model])


@pytest.mark.asyncio
async def test_fan_out_returns_only_successful():
    prov = FakeProvider({"a": "ta", "b": None, "c": "tc"})
    routes = [(prov, "a"), (prov, "b"), (prov, "c")]
    results = await fan_out(routes, "prompt", timeout_s=5)
    texts = {r.text for r in results}
    assert texts == {"ta", "tc"}      # ตัว b พังถูกตัดออก


@pytest.mark.asyncio
async def test_fan_out_runs_in_parallel():
    prov = FakeProvider({"a": "ta", "b": "tb"}, delays={"a": 0.3, "b": 0.3})
    routes = [(prov, "a"), (prov, "b")]
    start = asyncio.get_event_loop().time()
    await fan_out(routes, "p", timeout_s=5)
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed < 0.5               # ขนานกัน ไม่ใช่ 0.6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fanout.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# fusefable/fanout.py
from __future__ import annotations
import asyncio
from typing import Sequence, Tuple
from fusefable.client import call_model
from fusefable.models import Completion
from fusefable.providers.base import Provider

Route = Tuple[Provider, str]   # (provider, model)


async def fan_out(routes: Sequence[Route], prompt: str,
                  timeout_s: float) -> list[Completion]:
    """ยิงทุก route พร้อมกัน คืนเฉพาะ Completion ที่สำเร็จ."""
    tasks = [call_model(prov, model, prompt, timeout_s) for prov, model in routes]
    completions = await asyncio.gather(*tasks)
    return [c for c in completions if not c.is_error]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fanout.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add fusefable/fanout.py tests/test_fanout.py
git commit -m "feat: add parallel fan-out"
```

---

### Task 5: Judge (with anonymization)

**Files:**
- Create: `fusefable/judge.py`
- Test: `tests/test_judge.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_judge.py
import pytest
from fusefable.judge import build_judge_prompt, parse_judge_choice, judge
from fusefable.models import Completion


def test_build_judge_prompt_anonymizes_models():
    comps = [Completion(model="claude", text="ans1"),
             Completion(model="gpt", text="ans2")]
    prompt, labels = build_judge_prompt("question?", comps)
    assert "claude" not in prompt and "gpt" not in prompt  # ปกปิดชื่อ
    assert "Answer A" in prompt and "Answer B" in prompt
    assert labels == ["A", "B"]


def test_parse_judge_choice_extracts_letter():
    assert parse_judge_choice("The best is B because...", ["A", "B"]) == "B"


def test_parse_judge_choice_fallback_first():
    # ถ้า parse ไม่เจอ → คืน label แรก
    assert parse_judge_choice("unclear response", ["A", "B"]) == "A"


@pytest.mark.asyncio
async def test_judge_picks_completion():
    comps = [Completion(model="claude", text="ans1"),
             Completion(model="gpt", text="ans2")]

    class FakeJudgeProvider:
        async def complete(self, model, prompt):
            return Completion(model=model, text="I choose B")

    chosen, reason = await judge(FakeJudgeProvider(), "judge-model",
                                 "question?", comps, timeout_s=5)
    assert chosen.model == "gpt"          # B = ตัวที่ 2
    assert "B" in reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_judge.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# fusefable/judge.py
from __future__ import annotations
import re
from typing import Sequence
from fusefable.client import call_model
from fusefable.models import Completion
from fusefable.providers.base import Provider

_LABELS = "ABCDEFGHIJ"


def build_judge_prompt(question: str,
                       comps: Sequence[Completion]) -> tuple[str, list[str]]:
    """สร้าง prompt สำหรับ judge โดยปกปิดชื่อโมเดล (Answer A/B/C...)."""
    labels = [_LABELS[i] for i in range(len(comps))]
    blocks = [f"### Answer {label}\n{c.text}" for label, c in zip(labels, comps)]
    body = "\n\n".join(blocks)
    prompt = (
        "You are judging coding answers. Pick the single best answer.\n\n"
        f"## Question\n{question}\n\n"
        f"## Candidate Answers\n{body}\n\n"
        "Reply with the letter of the best answer first (e.g. 'B'), "
        "then one sentence why."
    )
    return prompt, labels


def parse_judge_choice(text: str, labels: list[str]) -> str:
    """ดึงตัวอักษรที่ judge เลือก; ถ้าไม่เจอคืน label แรก (fallback)."""
    match = re.search(r"\b([A-J])\b", text)
    if match and match.group(1) in labels:
        return match.group(1)
    return labels[0]


async def judge(provider: Provider, judge_model: str, question: str,
                comps: Sequence[Completion], timeout_s: float
                ) -> tuple[Completion, str]:
    """คืน (Completion ที่ถูกเลือก, เหตุผล). fallback = ตัวแรกถ้า judge พัง."""
    prompt, labels = build_judge_prompt(question, comps)
    result = await call_model(provider, judge_model, prompt, timeout_s)
    if result.is_error:
        return comps[0], f"judge failed ({result.error}); fell back to first answer"
    choice = parse_judge_choice(result.text, labels)
    idx = labels.index(choice)
    return comps[idx], result.text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_judge.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add fusefable/judge.py tests/test_judge.py
git commit -m "feat: add anonymized judge"
```

---

### Task 6: Cost estimation helper

**Files:**
- Create: `fusefable/cost.py`
- Test: `tests/test_cost.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cost.py
from fusefable.cost import estimate_cost
from fusefable.models import Completion


def test_estimate_cost_sums_tokens():
    comps = [
        Completion(model="a", text="x", prompt_tokens=1000, completion_tokens=500),
        Completion(model="b", text="y", prompt_tokens=2000, completion_tokens=1000),
    ]
    # default rate $1/1M in, $3/1M out เมื่อไม่รู้ราคาโมเดล
    cost = estimate_cost(comps, default_in=1.0, default_out=3.0)
    # (3000/1e6 * 1) + (1500/1e6 * 3) = 0.003 + 0.0045 = 0.0075
    assert round(cost, 6) == 0.0075
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cost.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# fusefable/cost.py
from __future__ import annotations
from typing import Sequence
from fusefable.models import Completion


def estimate_cost(comps: Sequence[Completion],
                  default_in: float = 1.0, default_out: float = 3.0) -> float:
    """ประมาณค่าใช้จ่ายรวม (USD) จาก usage tokens. rate = $/1M tokens."""
    total_in = sum(c.prompt_tokens for c in comps)
    total_out = sum(c.completion_tokens for c in comps)
    return total_in / 1_000_000 * default_in + total_out / 1_000_000 * default_out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cost.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add fusefable/cost.py tests/test_cost.py
git commit -m "feat: add cost estimation"
```

---

### Task 7: Config (load/validate/write)

**Files:**
- Create: `fusefable/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import os
import pytest
from fusefable.config import Config, load_config, save_config


def test_save_and_load_roundtrip(tmp_path):
    cfg = Config(
        mode="gateway",
        gateway_name="openrouter",
        gateway_base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        timeout_seconds=90,
        judge_model="deepseek/deepseek-chat",
        models=["openai/gpt-5", "anthropic/claude-opus-4.1"],
    )
    path = tmp_path / "config.yaml"
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded.gateway_name == "openrouter"
    assert loaded.models == ["openai/gpt-5", "anthropic/claude-opus-4.1"]


def test_load_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_resolve_api_key_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_KEY", "secret123")
    cfg = Config(mode="gateway", gateway_name="openrouter",
                 gateway_base_url="https://x/v1", api_key_env="MY_KEY",
                 timeout_seconds=90, judge_model="m", models=["m"])
    assert cfg.resolve_api_key() == "secret123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# fusefable/config.py
from __future__ import annotations
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml


@dataclass
class SingleProvider:
    name: str
    base_url: str
    api_key_env: str
    models: list[str] = field(default_factory=list)


@dataclass
class Config:
    mode: str                       # "gateway" | "single"
    timeout_seconds: int
    judge_model: str
    models: list[str] = field(default_factory=list)
    gateway_name: str = ""
    gateway_base_url: str = ""
    api_key_env: str = ""
    providers: list[SingleProvider] = field(default_factory=list)
    min_responses: int = 1
    budget_cap_usd: float | None = None

    def resolve_api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


def default_config_path() -> Path:
    return Path.home() / ".fusefable" / "config.yaml"


def save_config(cfg: Config, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(cfg)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def load_config(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    data = yaml.safe_load(path.read_text())
    providers = [SingleProvider(**p) for p in data.pop("providers", [])]
    return Config(providers=providers, **data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add fusefable/config.py tests/test_config.py
git commit -m "feat: add config load/save"
```

---

### Task 8: Fusion orchestrator

**Files:**
- Create: `fusefable/fusion.py`
- Test: `tests/test_fusion.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fusion.py
import pytest
from fusefable.fusion import run_fusion
from fusefable.models import Completion


class FakeProvider:
    def __init__(self, mapping):
        self.mapping = mapping   # model -> text

    async def complete(self, model, prompt):
        return Completion(model=model, text=self.mapping[model],
                          prompt_tokens=10, completion_tokens=5)


@pytest.mark.asyncio
async def test_run_fusion_end_to_end():
    prov = FakeProvider({
        "m1": "answer one", "m2": "answer two",
        "judge": "I choose B because it is clearer",
    })
    routes = [(prov, "m1"), (prov, "m2")]
    result = await run_fusion(routes, prov, "judge", "question?", timeout_s=5)
    assert result.chosen_model == "m2"        # B
    assert result.text == "answer two"
    assert result.cost_usd > 0
    assert len(result.all_completions) == 2


@pytest.mark.asyncio
async def test_run_fusion_raises_when_all_fail():
    class DeadProvider:
        async def complete(self, model, prompt):
            raise RuntimeError("dead")
    routes = [(DeadProvider(), "m1")]
    with pytest.raises(RuntimeError, match="no successful"):
        await run_fusion(routes, DeadProvider(), "judge", "q", timeout_s=5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fusion.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# fusefable/fusion.py
from __future__ import annotations
from typing import Sequence, Tuple
from fusefable.fanout import fan_out
from fusefable.judge import judge
from fusefable.cost import estimate_cost
from fusefable.models import FinalAnswer
from fusefable.providers.base import Provider

Route = Tuple[Provider, str]


async def run_fusion(routes: Sequence[Route], judge_provider: Provider,
                     judge_model: str, prompt: str, timeout_s: float) -> FinalAnswer:
    """fan-out → judge → FinalAnswer. โยน RuntimeError ถ้าไม่มีตัวไหนสำเร็จ."""
    completions = await fan_out(routes, prompt, timeout_s)
    if not completions:
        raise RuntimeError("no successful completions from any model")
    chosen, reason = await judge(judge_provider, judge_model, prompt,
                                 completions, timeout_s)
    cost = estimate_cost(completions)
    return FinalAnswer(text=chosen.text, chosen_model=chosen.model,
                       reason=reason, cost_usd=cost,
                       all_completions=list(completions))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fusion.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add fusefable/fusion.py tests/test_fusion.py
git commit -m "feat: add fusion orchestrator"
```

---

### Task 9: Setup wizard

**Files:**
- Create: `fusefable/wizard.py`
- Test: `tests/test_wizard.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_wizard.py
from fusefable.wizard import build_config_from_answers


def test_gateway_mode_builds_single_key_config():
    answers = {
        "mode": "gateway",
        "gateway_name": "openrouter",
        "gateway_base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "models": ["openai/gpt-5", "anthropic/claude-opus-4.1"],
        "judge_model": "deepseek/deepseek-chat",
        "timeout_seconds": 90,
    }
    cfg = build_config_from_answers(answers)
    assert cfg.mode == "gateway"
    assert cfg.gateway_name == "openrouter"
    assert cfg.api_key_env == "OPENROUTER_API_KEY"
    assert len(cfg.providers) == 0


def test_single_mode_builds_per_provider_config():
    answers = {
        "mode": "single",
        "providers": [
            {"name": "openai", "base_url": "https://api.openai.com/v1",
             "api_key_env": "OPENAI_API_KEY", "models": ["gpt-5"]},
            {"name": "deepseek", "base_url": "https://api.deepseek.com/v1",
             "api_key_env": "DEEPSEEK_API_KEY", "models": ["deepseek-chat"]},
        ],
        "judge_model": "deepseek-chat",
        "timeout_seconds": 90,
    }
    cfg = build_config_from_answers(answers)
    assert cfg.mode == "single"
    assert len(cfg.providers) == 2
    assert cfg.providers[0].name == "openai"
    # models รวมจากทุก provider
    assert set(cfg.models) == {"gpt-5", "deepseek-chat"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_wizard.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# fusefable/wizard.py
from __future__ import annotations
from fusefable.config import Config, SingleProvider


def build_config_from_answers(answers: dict) -> Config:
    """แปลงคำตอบจาก wizard เป็น Config (logic ล้วน — แยกจาก I/O เพื่อ test ได้)."""
    if answers["mode"] == "gateway":
        return Config(
            mode="gateway",
            gateway_name=answers["gateway_name"],
            gateway_base_url=answers["gateway_base_url"],
            api_key_env=answers["api_key_env"],
            models=answers["models"],
            judge_model=answers["judge_model"],
            timeout_seconds=answers["timeout_seconds"],
        )
    providers = [SingleProvider(**p) for p in answers["providers"]]
    all_models = [m for p in providers for m in p.models]
    return Config(
        mode="single",
        providers=providers,
        models=all_models,
        judge_model=answers["judge_model"],
        timeout_seconds=answers["timeout_seconds"],
    )


def run_wizard(prompt=input) -> Config:
    """ถาม interactive แล้วคืน Config. `prompt` ฉีดเข้าได้เพื่อ test."""
    print("=== Fuse Fable setup ===")
    print("1) AI Gateway (เช่น OpenRouter) — key เดียวเรียกทุกโมเดล")
    print("2) Provider เดี่ยว (ผสมหลายเจ้า)")
    choice = prompt("เลือก [1/2]: ").strip()

    if choice == "1":
        gw = prompt("Gateway เจ้าไหน? (เช่น openrouter): ").strip()
        base = prompt("Base URL (เช่น https://openrouter.ai/api/v1): ").strip()
        key_env = prompt("ชื่อ env var ของ API key (เช่น OPENROUTER_API_KEY): ").strip()
        models_raw = prompt("รายชื่อโมเดล คั่นด้วย comma: ").strip()
        models = [m.strip() for m in models_raw.split(",") if m.strip()]
        judge = prompt("judge model: ").strip()
        return build_config_from_answers({
            "mode": "gateway", "gateway_name": gw, "gateway_base_url": base,
            "api_key_env": key_env, "models": models, "judge_model": judge,
            "timeout_seconds": 90,
        })

    n = int(prompt("จะใช้กี่เจ้า?: ").strip())
    providers = []
    for i in range(n):
        print(f"-- เจ้าที่ {i + 1} --")
        name = prompt("  ชื่อ: ").strip()
        base = prompt("  base_url: ").strip()
        key_env = prompt("  ชื่อ env var ของ API key: ").strip()
        models_raw = prompt("  โมเดล (คั่นด้วย comma): ").strip()
        models = [m.strip() for m in models_raw.split(",") if m.strip()]
        providers.append({"name": name, "base_url": base,
                          "api_key_env": key_env, "models": models})
    judge = prompt("judge model: ").strip()
    return build_config_from_answers({
        "mode": "single", "providers": providers,
        "judge_model": judge, "timeout_seconds": 90,
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_wizard.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add fusefable/wizard.py tests/test_wizard.py
git commit -m "feat: add setup wizard"
```

---

### Task 10: Route building (Config → routes)

**Files:**
- Create: `fusefable/routing.py`
- Test: `tests/test_routing.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_routing.py
import httpx
from fusefable.config import Config, SingleProvider
from fusefable.routing import build_routes, build_judge_provider


def test_build_routes_gateway_mode(monkeypatch):
    monkeypatch.setenv("OR_KEY", "k")
    cfg = Config(mode="gateway", gateway_name="openrouter",
                 gateway_base_url="https://openrouter.ai/api/v1",
                 api_key_env="OR_KEY", timeout_seconds=90,
                 judge_model="deepseek/deepseek-chat",
                 models=["openai/gpt-5", "anthropic/claude-opus-4.1"])
    http = httpx.AsyncClient()
    routes = build_routes(cfg, http)
    assert len(routes) == 2
    assert routes[0][1] == "openai/gpt-5"          # (provider, model)


def test_build_routes_single_mode(monkeypatch):
    monkeypatch.setenv("OAI", "k1")
    monkeypatch.setenv("DS", "k2")
    cfg = Config(mode="single", timeout_seconds=90, judge_model="deepseek-chat",
                 providers=[
                     SingleProvider("openai", "https://api.openai.com/v1", "OAI", ["gpt-5"]),
                     SingleProvider("deepseek", "https://api.deepseek.com/v1", "DS", ["deepseek-chat"]),
                 ],
                 models=["gpt-5", "deepseek-chat"])
    http = httpx.AsyncClient()
    routes = build_routes(cfg, http)
    assert {r[1] for r in routes} == {"gpt-5", "deepseek-chat"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_routing.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# fusefable/routing.py
from __future__ import annotations
import os
import httpx
from fusefable.config import Config
from fusefable.models import ProviderConfig
from fusefable.providers.openai_compat import OpenAICompatProvider


def build_routes(cfg: Config, http: httpx.AsyncClient) -> list[tuple]:
    """แปลง Config → list ของ (provider, model)."""
    routes = []
    if cfg.mode == "gateway":
        pc = ProviderConfig(cfg.gateway_name, cfg.gateway_base_url,
                            os.environ.get(cfg.api_key_env, ""))
        prov = OpenAICompatProvider(pc, http)
        for model in cfg.models:
            routes.append((prov, model))
    else:
        for sp in cfg.providers:
            pc = ProviderConfig(sp.name, sp.base_url,
                                os.environ.get(sp.api_key_env, ""))
            prov = OpenAICompatProvider(pc, http)
            for model in sp.models:
                routes.append((prov, model))
    return routes


def build_judge_provider(cfg: Config, http: httpx.AsyncClient):
    """provider สำหรับ judge — ใช้ gateway หรือ provider แรกใน single mode."""
    if cfg.mode == "gateway":
        pc = ProviderConfig(cfg.gateway_name, cfg.gateway_base_url,
                            os.environ.get(cfg.api_key_env, ""))
    else:
        sp = cfg.providers[0]
        pc = ProviderConfig(sp.name, sp.base_url, os.environ.get(sp.api_key_env, ""))
    return OpenAICompatProvider(pc, http)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_routing.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add fusefable/routing.py tests/test_routing.py
git commit -m "feat: add route building from config"
```

---

### Task 11: CLI

**Files:**
- Create: `fusefable/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
from typer.testing import CliRunner
from unittest.mock import patch
from fusefable.cli import app
from fusefable.models import FinalAnswer, Completion

runner = CliRunner()


def test_ask_command_prints_answer(monkeypatch, tmp_path):
    fake = FinalAnswer(text="best answer", chosen_model="gpt-5",
                       reason="clearest", cost_usd=0.01,
                       all_completions=[Completion(model="gpt-5", text="best answer")])

    async def fake_run_fusion(*a, **k):
        return fake

    monkeypatch.setattr("fusefable.cli.run_fusion", fake_run_fusion)
    monkeypatch.setattr("fusefable.cli._load_or_die",
                        lambda: _fake_cfg())
    result = runner.invoke(app, ["ask", "write quicksort"])
    assert result.exit_code == 0
    assert "best answer" in result.stdout
    assert "gpt-5" in result.stdout


def _fake_cfg():
    from fusefable.config import Config
    return Config(mode="gateway", gateway_name="openrouter",
                  gateway_base_url="https://x/v1", api_key_env="K",
                  timeout_seconds=90, judge_model="judge", models=["gpt-5"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# fusefable/cli.py
from __future__ import annotations
import asyncio
import sys
import httpx
import typer
from fusefable.config import load_config, save_config, default_config_path, Config
from fusefable.routing import build_routes, build_judge_provider
from fusefable.fusion import run_fusion
from fusefable.wizard import run_wizard

app = typer.Typer(help="Fuse Fable — ฟิวชั่นหลาย AI เลือกคำตอบดีสุด")


def _load_or_die() -> Config:
    try:
        return load_config(default_config_path())
    except FileNotFoundError:
        typer.echo("ยังไม่ได้ตั้งค่า — รัน `fusefable config` ก่อน", err=True)
        raise typer.Exit(1)


async def _run(cfg: Config, question: str, show_all: bool):
    async with httpx.AsyncClient(timeout=None) as http:
        routes = build_routes(cfg, http)
        judge_prov = build_judge_provider(cfg, http)
        result = await run_fusion(routes, judge_prov, cfg.judge_model,
                                  question, cfg.timeout_seconds)
    if show_all:
        for c in result.all_completions:
            typer.echo(f"\n--- {c.model} ---\n{c.text}")
        typer.echo(f"\n=== Judge reason ===\n{result.reason}")
    typer.echo(f"\n=== คำตอบที่ดีที่สุด (จาก {result.chosen_model}) ===")
    typer.echo(result.text)
    typer.echo(f"\n[ประมาณค่าใช้จ่าย: ${result.cost_usd:.4f}]")


@app.command()
def ask(question: str, show_all: bool = typer.Option(False, "--show-all")):
    """ถามคำถาม → ได้คำตอบที่ดีที่สุดจากการฟิวชั่น."""
    cfg = _load_or_die()
    asyncio.run(_run(cfg, question, show_all))


@app.command()
def config():
    """ตั้งค่า provider / API key / โมเดล (setup wizard)."""
    cfg = run_wizard()
    path = default_config_path()
    save_config(cfg, path)
    typer.echo(f"บันทึกแล้วที่ {path}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: ทุก test ผ่าน

- [ ] **Step 6: Commit**

```bash
git add fusefable/cli.py tests/test_cli.py
git commit -m "feat: add CLI"
```

---

### Task 12: README + manual smoke test

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

```markdown
# Fuse Fable

ฟิวชั่นหลาย AI model พร้อมกัน แล้วเลือกคำตอบที่ดีที่สุดสำหรับงานโค้ด

## ติดตั้ง
\`\`\`bash
pip install fusefable
\`\`\`

## ตั้งค่า (ครั้งแรก)
\`\`\`bash
fusefable config
\`\`\`
- เลือก **AI Gateway** (เช่น OpenRouter) → ใส่ key เดียวพอ
- หรือ **Provider เดี่ยว** → ใส่ base_url + key ของแต่ละเจ้า

ตั้ง API key เป็น environment variable ตามชื่อที่ wizard ถาม เช่น:
\`\`\`bash
export OPENROUTER_API_KEY=sk-...
\`\`\`

## ใช้งาน
\`\`\`bash
fusefable ask "เขียนฟังก์ชัน quicksort ใน Python"
fusefable ask --show-all "..."     # ดูคำตอบทุกตัว + เหตุผล judge
\`\`\`
```

- [ ] **Step 2: Manual smoke test (ต้องมี OpenRouter key จริง)**

```bash
export OPENROUTER_API_KEY=sk-...
fusefable config          # ตั้งค่าแบบ gateway / openrouter
fusefable ask "write a Python function to reverse a string"
```
Expected: ได้คำตอบ + แสดงโมเดลที่ถูกเลือก + cost estimate

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

---

## Self-Review Notes

- **Spec coverage:** fan-out (Task 4), judge+anonymize (Task 5), timeout/error (Task 3),
  provider abstraction (Task 2), config+wizard (Task 7,9), CLI (Task 11),
  cost (Task 6), gateway-vs-single setup (Task 9,10) — ครบทุกข้อใน spec
- **Out of scope (ตาม spec §10):** Anthropic/Google native adapter, `--cheap`/`--models`
  flags, budget cap enforcement — เพิ่มได้ใน iteration ถัดไป (โครง provider/route
  รองรับไว้แล้ว)
- **Type consistency:** `Completion`, `FinalAnswer`, `ProviderConfig`, `Config`,
  `Route = (Provider, model)` ใช้ชื่อตรงกันทุก task
