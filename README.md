# Fuse Fable

[![PyPI](https://img.shields.io/pypi/v/fusefable)](https://pypi.org/project/fusefable/)
[![Python](https://img.shields.io/pypi/pyversions/fusefable)](https://pypi.org/project/fusefable/)
[![CI](https://github.com/proultrax9/fusefable/actions/workflows/ci.yml/badge.svg)](https://github.com/proultrax9/fusefable/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/pypi/l/fusefable)](https://github.com/proultrax9/fusefable/blob/main/LICENSE)

🌐 **Languages:** English · [ไทย (Thai)](https://github.com/proultrax9/fusefable/blob/main/README.th.md)

Fan out a coding prompt to many AI models **in parallel**, then let a judge pick the
single best answer — total latency ≈ **x2** (slowest model + one judge pass), not x7–x15.

Works three ways: as a **CLI**, as an **MCP server** (connect Cursor / VS Code / Claude),
and as a **subagent / pipe** (callable by other tools and scripts).

## Install
```bash
pip install fusefable            # core
pip install "fusefable[mcp]"     # if you want the MCP server
```
From source:
```bash
git clone https://github.com/proultrax9/fusefable.git
cd fusefable
pip install -e ".[mcp]"
```

## Setup (first run)
```bash
fusefable config
```
- Choose **AI Gateway** → one key for everything, then it asks "how many models?" and
  prompts for each one.
  - Known gateways (base URL auto-filled): `openrouter`, `groq`, `together`,
    `fireworks`, `deepinfra`, `novita`, `hyperbolic`, `aimlapi`, `portkey`,
    `deepseek`, `openai` — any other works too, just type its base URL.
- Or **Single providers** → it asks how many, then the **API kind** of each:
  - `openai_compat` — any OpenAI-compatible endpoint (you provide the base URL)
  - `anthropic` — Anthropic native (`/v1/messages`, base URL auto-filled)
  - `google` — Google Gemini native (`generateContent`, base URL auto-filled)

Set your API key as an environment variable named as the wizard asks:
```bash
export OPENROUTER_API_KEY=sk-...      # macOS/Linux
setx OPENROUTER_API_KEY "sk-..."      # Windows (open a new terminal afterwards)
```

Config is stored at `~/.fusefable/config.yaml`.

## 1) Use as a CLI
```bash
fusefable ask "Write a quicksort function in Python"
fusefable ask --show-all "..."                   # show every answer + judge reason
fusefable ask --models gpt-5,qwen3-coder "..."   # restrict to specific models
fusefable ask --cheap "..."                      # use cheap_models from config
ff ask "..."                                      # short alias
```

## 2) Use as a subagent / in a pipe
```bash
fusefable ask --quiet "..."                # print only the answer (no headers)
echo "Explain this code" | fusefable ask --quiet   # read the prompt from stdin
cat bug.py | fusefable ask -q "Find the bug in this code"
fusefable ask --json "..."                 # JSON output: answer, chosen_model, reason, cost, candidates
```
`--json` is ideal for scripts/agents that parse the result; `--quiet` is ideal for piping.

## 3) Use as an MCP server (Cursor / VS Code / Claude / other agents)
Run as an MCP server over stdio:
```bash
fusefable mcp
```
Exposes a tool `fuse_ask(question, models?, cheap?)` for any MCP client.

### Cursor
`~/.cursor/mcp.json` (or Settings → MCP):
```json
{
  "mcpServers": {
    "fusefable": {
      "command": "fusefable",
      "args": ["mcp"],
      "env": { "OPENROUTER_API_KEY": "sk-..." }
    }
  }
}
```

### VS Code (Copilot / MCP-compatible extension)
`.vscode/mcp.json` in your project:
```json
{
  "servers": {
    "fusefable": {
      "command": "fusefable",
      "args": ["mcp"],
      "env": { "OPENROUTER_API_KEY": "sk-..." }
    }
  }
}
```

### Claude Desktop
`claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "fusefable": {
      "command": "fusefable",
      "args": ["mcp"],
      "env": { "OPENROUTER_API_KEY": "sk-..." }
    }
  }
}
```

> Requires `pip install "fusefable[mcp]"` and a completed `fusefable config`.
> If `fusefable` isn't on the app's PATH, use a full path such as `python -m fusefable.cli`.

## Ensemble, cache & budget

```bash
fusefable ask --ensemble "..."     # merge all answers into one (vs picking one)
fusefable ask --cache "..."        # reuse the answer for an identical question
fusefable ask --no-cache "..."     # force a fresh run
```

- **Ensemble mode** (`--ensemble`, config `fusion_mode: ensemble`): instead of the judge
  picking one answer, a model synthesizes a single answer combining the strengths of all
  candidates (anonymized). Falls back to the first answer if synthesis fails.
- **Cache** (`--cache`, config `cache: true`, `cache_ttl_seconds`): identical question +
  same models/mode/compression returns the stored answer instantly with no API calls
  (`cached, $0`). Stored in `~/.fusefable/cache/`. `cache_ttl_seconds: 0` = never expires.
- **Budget cap** (config `budget_cap_usd`, `budget_action: warn|stop`): before firing,
  the run estimates cost. If it exceeds the cap — `warn` prints a warning and continues,
  `stop` aborts before spending anything.

## Prompt compression (save tokens)

Reduce token usage while keeping answer quality — useful when you pay per-provider
directly. Two tiers, opt-in via `--compress`:

```bash
fusefable ask --compress "<long prompt or pasted code>"
# [compressed: 5200→1800 chars, ~65% saved via llm]
```

- **Tier 1 (lossless):** trims trailing whitespace, collapses blank lines, strips
  zero-width chars — keeps indentation and inner spacing intact (safe for code).
- **Tier 2 (LLM):** for prompts above `compress_min_chars` (default 2000), a cheap
  model compresses semantically — **once**, then the compressed prompt is sent to all
  models, so you save `tokens × number-of-models`.
- **Quality guards:** prompts under the threshold skip the LLM; if the compressed
  result is empty, longer, or under 30% of the original, it falls back to the lossless
  text. The judge always sees the **original** question.

Config (`~/.fusefable/config.yaml`): `compress`, `compress_min_chars`, `compress_model`
(empty = reuse the judge model).

## Architecture

```
              ENTRYPOINTS (one shared core)
   ┌─────────────┬──────────────────┬─────────────────────┐
   │  CLI        │  pipe / subagent │  MCP server         │
   │ fusefable   │ stdin · --quiet  │ fusefable mcp       │
   │   ask "..." │      · --json    │ tool: fuse_ask()    │
   └──────┬──────┴────────┬─────────┴──────────┬──────────┘
          └───────────────┴────────────────────┘
                          │
                          ▼
                ┌───────────────────┐      ~/.fusefable/config.yaml
                │   core.fuse()     │◀──── (gateway | single providers,
                └─────────┬─────────┘        models, judge, timeout)
                          │
                          ▼
                ┌───────────────────┐
                │  routing          │  build (provider, model) routes
                │  + provider       │  via factory → pick adapter by kind
                │    factory        │
                └─────────┬─────────┘
                          ▼
        ┌──────────────  FAN-OUT (asyncio.gather)  ──────────────┐
        │   ทุกตัวยิงพร้อมกัน · per-model timeout · ตัวพัง = ตัดทิ้ง       │
        │                                                         │
        ▼            ▼              ▼                ▼            ▼
   ┌─────────┐ ┌──────────┐  ┌────────────┐   ┌──────────┐  ┌────────┐
   │ openai_ │ │ anthropic│  │  google    │   │ openai_  │  │  ...   │
   │ compat  │ │ native   │  │  native    │   │ compat   │  │        │
   │(gateway)│ │/v1/msgs  │  │generateCont│   │          │  │        │
   └────┬────┘ └────┬─────┘  └─────┬──────┘   └────┬─────┘  └───┬────┘
        └───────────┴──────────────┴───────────────┴───────────┘
                          │  Completion[] (สำเร็จเท่านั้น)
                          ▼
                ┌───────────────────┐
                │  judge            │  ปกปิดชื่อ → Answer A/B/C...
                │  (anonymized)     │  ให้ judge model เลือกตัวดีสุด
                └─────────┬─────────┘  (พัง → fallback ตัวแรก)
                          ▼
                ┌───────────────────┐
                │  FinalAnswer      │  text · chosen_model · reason
                │  (+ cost estimate)│  · cost_usd · candidates
                └───────────────────┘
```

**Request lifecycle**
1. **Entrypoint** — CLI, a pipe/subagent call, or the MCP tool `fuse_ask()` — all funnel into one core function `core.fuse()`.
2. **Routing** — config (gateway or single providers) is turned into `(provider, model)` routes; a provider **factory** picks the right adapter per `kind` (`openai_compat` / `anthropic` / `google`).
3. **Fan-out** — every model is called concurrently via `asyncio.gather` (total time = slowest model). Each call has its own timeout; any model that times out or errors is dropped and never slows the run.
4. **Judge** — model names are anonymized (Answer A/B/C...) so the judge picks on quality alone, not by brand; if the judge fails it falls back to the first answer.
5. **Result** — returns the best answer with the chosen model, the judge's reason, an estimated cost, and all candidates.

**Components** (`fusefable/`)

| File | Responsibility |
|---|---|
| `cli.py` | Typer CLI (`ask` / `config` / `mcp`), output modes |
| `mcp_server.py` | MCP server exposing the `fuse_ask` tool |
| `core.py` | shared `fuse()` entrypoint + model selection |
| `config.py` | load/save `config.yaml` |
| `wizard.py` | interactive setup (gateway vs single, API kind) |
| `routing.py` | config → `(provider, model)` routes |
| `providers/factory.py` | pick adapter by `kind` |
| `providers/openai_compat.py` · `anthropic.py` · `google.py` | provider adapters |
| `fanout.py` | parallel fan-out (drops failures) |
| `judge.py` | anonymized judging |
| `fusion.py` | orchestrator: fan-out → judge → `FinalAnswer` |
| `cost.py` | token-based cost estimate |
| `models.py` | dataclasses: `Completion`, `FinalAnswer`, `ProviderConfig` |

## Development
```bash
pip install -e ".[dev,mcp]"
pytest -q
```

## License
MIT
