# Fuse Fable

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

## How it works
1. **Fan-out** — every model is called concurrently via `asyncio` (total time = slowest model).
2. Any model that times out or fails is dropped — it never slows the whole run.
3. **Judge** — model names are anonymized (Answer A/B/C...) and a judge model picks the best.
4. Returns the best answer plus an estimated cost.

## Development
```bash
pip install -e ".[dev,mcp]"
pytest -q
```

## License
MIT
