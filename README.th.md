# Fuse Fable (ภาษาไทย)

[![PyPI](https://img.shields.io/pypi/v/fusefable)](https://pypi.org/project/fusefable/)
[![Python](https://img.shields.io/pypi/pyversions/fusefable)](https://pypi.org/project/fusefable/)
[![CI](https://github.com/proultrax9/fusefable/actions/workflows/ci.yml/badge.svg)](https://github.com/proultrax9/fusefable/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/pypi/l/fusefable)](https://github.com/proultrax9/fusefable/blob/main/LICENSE)

🌐 **ภาษา:** [English](https://github.com/proultrax9/fusefable/blob/main/README.md) · ไทย

ฟิวชั่นหลาย AI model พร้อมกัน แล้วเลือกคำตอบที่ดีที่สุดสำหรับงานโค้ด — latency ≈ x2
(ยิงทุกตัวขนานกัน + judge รอบเดียว) ไม่ใช่ x7–x15

ใช้ได้หลายรูปแบบ: **CLI**, **MCP server** (เชื่อม Cursor/VS Code/Claude), และ
**subagent/pipe** (ให้ tool หรือสคริปต์อื่นเรียก)

## ติดตั้ง
```bash
pip install fusefable            # หลัก
pip install "fusefable[mcp]"     # ถ้าจะใช้เป็น MCP server
```
หรือจาก source:
```bash
git clone https://github.com/proultrax9/fusefable.git
cd fusefable
pip install -e ".[mcp]"
```

## ตั้งค่า (ครั้งแรก)
```bash
fusefable config
```
- เลือก **AI Gateway** → ใส่ key เดียวพอ แล้วถาม "จะใช้กี่โมเดล?" → วนถามทีละตัว
  - รองรับหลายเจ้า (เติม URL อัตโนมัติ): `openrouter`, `groq`, `together`,
    `fireworks`, `deepinfra`, `novita`, `hyperbolic`, `aimlapi`, `portkey`,
    `deepseek`, `openai` — เจ้าอื่นก็ใช้ได้ แค่พิมพ์ base_url เอง
- หรือ **Provider เดี่ยว** → ถามว่าจะใช้กี่เจ้า แล้วถาม **ชนิด API** ของแต่ละเจ้า:
  - `openai_compat` — เจ้าที่เป็น OpenAI-compatible (ใส่ base_url เอง)
  - `anthropic` — Anthropic native (`/v1/messages`, เติม base_url อัตโนมัติ)
  - `google` — Google Gemini native (`generateContent`, เติม base_url อัตโนมัติ)

ตั้ง API key เป็น environment variable ตามชื่อที่ wizard ถาม:
```bash
export OPENROUTER_API_KEY=sk-...      # macOS/Linux
setx OPENROUTER_API_KEY "sk-..."      # Windows (เปิด terminal ใหม่หลังตั้ง)
```

config ถูกเก็บที่ `~/.fusefable/config.yaml`

## 1) ใช้เป็น CLI
```bash
fusefable ask "เขียนฟังก์ชัน quicksort ใน Python"
fusefable ask --show-all "..."             # ดูคำตอบทุกตัว + เหตุผล judge
fusefable ask --models gpt-5,qwen3-coder "..."   # เลือกเฉพาะบางตัว
fusefable ask --cheap "..."                # ใช้ cheap_models ใน config
ff ask "..."                                # alias สั้น
```

## 2) ใช้เป็น subagent / ต่อ pipe (ให้ tool อื่นเรียก)
```bash
fusefable ask --quiet "..."                # พิมพ์เฉพาะคำตอบ (ไม่มี header)
echo "อธิบายโค้ดนี้" | fusefable ask --quiet   # รับคำถามจาก stdin
cat bug.py | fusefable ask -q "ช่วยหาบั๊กในโค้ดนี้"
fusefable ask --json "..."                 # output JSON (answer, chosen_model, reason, cost, candidates)
```
`--json` เหมาะกับสคริปต์/agent ที่ parse ผลต่อ; `--quiet` เหมาะกับต่อ pipe

## 3) ใช้เป็น MCP server (Cursor / VS Code / Claude / agent อื่น)
รันเป็น MCP server ผ่าน stdio:
```bash
fusefable mcp
```
มี tool ชื่อ `fuse_ask(question, models?, cheap?)` ให้ client เรียก

### Cursor
`~/.cursor/mcp.json` (หรือ Settings → MCP):
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
`.vscode/mcp.json` ในโปรเจกต์:
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

> ต้องติดตั้ง `pip install "fusefable[mcp]"` และรัน `fusefable config` ไว้ก่อน
> ถ้า `fusefable` ไม่อยู่ใน PATH ของแอป ให้ใส่ path เต็ม เช่น `python -m fusefable.cli`

## บีบ prompt ลด token (Prompt compression)

ลดการใช้ token แต่คงคุณภาพคำตอบ — เหมาะกับสายที่จ่ายตรงรายเจ้า เปิดด้วย `--compress`:

```bash
fusefable ask --compress "<prompt ยาว หรือโค้ดที่ paste มา>"
# [compressed: 5200→1800 chars, ~65% saved via llm]
```

- **ชั้น 1 (lossless):** ตัด trailing space, ยุบบรรทัดว่างซ้ำ, ลบ zero-width —
  **คง indentation และช่องว่างภายในไว้ครบ** (ปลอดภัยสำหรับโค้ด)
- **ชั้น 2 (LLM):** prompt ยาวเกิน `compress_min_chars` (default 2000) ให้โมเดลถูกบีบ
  เชิงความหมาย **ครั้งเดียว** แล้วส่งไปทุกโมเดล → ประหยัด `token × จำนวนโมเดล`
- **กันคุณภาพ:** prompt สั้นข้ามชั้น 2; ถ้าผลบีบ ว่าง/ยาวกว่าเดิม/สั้นกว่า 30% ของเดิม →
  fallback ใช้ lossless; **judge ใช้คำถามเดิมเสมอ**

Config (`~/.fusefable/config.yaml`): `compress`, `compress_min_chars`, `compress_model`
(ว่าง = ใช้ judge model)

## สถาปัตยกรรม (Architecture)

```
              ทางเข้า (ใช้ core ร่วมกันตัวเดียว)
   ┌─────────────┬──────────────────┬─────────────────────┐
   │  CLI        │  pipe / subagent │  MCP server         │
   │ fusefable   │ stdin · --quiet  │ fusefable mcp       │
   │   ask "..." │      · --json    │ tool: fuse_ask()    │
   └──────┬──────┴────────┬─────────┴──────────┬──────────┘
          └───────────────┴────────────────────┘
                          │
                          ▼
                ┌───────────────────┐      ~/.fusefable/config.yaml
                │   core.fuse()     │◀──── (gateway | provider เดี่ยว,
                └─────────┬─────────┘        models, judge, timeout)
                          │
                          ▼
                ┌───────────────────┐
                │  routing          │  สร้าง (provider, model) routes
                │  + provider       │  ผ่าน factory → เลือก adapter ตาม kind
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

**ลำดับการทำงาน (request lifecycle)**
1. **ทางเข้า** — CLI, pipe/subagent, หรือ MCP tool `fuse_ask()` — ทั้งหมดวิ่งเข้า core function เดียว `core.fuse()`
2. **Routing** — config (gateway หรือ provider เดี่ยว) ถูกแปลงเป็น `(provider, model)` routes; provider **factory** เลือก adapter ตาม `kind` (`openai_compat` / `anthropic` / `google`)
3. **Fan-out** — ยิงทุกโมเดลพร้อมกันด้วย `asyncio.gather` (เวลารวม = ตัวช้าสุด); แต่ละตัวมี timeout เอง ตัวไหน timeout/พัง = ตัดทิ้ง ไม่ลากระบบช้า
4. **Judge** — ปกปิดชื่อโมเดล (Answer A/B/C...) ให้ judge เลือกที่คุณภาพล้วน ไม่ใช่ที่ยี่ห้อ; ถ้า judge พัง → fallback ตัวแรก
5. **ผลลัพธ์** — คืนคำตอบที่ดีสุด + โมเดลที่เลือก + เหตุผล + ประมาณค่าใช้จ่าย + คำตอบทุกตัว

**Components** (`fusefable/`)

| ไฟล์ | หน้าที่ |
|---|---|
| `cli.py` | Typer CLI (`ask` / `config` / `mcp`) + โหมด output |
| `mcp_server.py` | MCP server เปิด tool `fuse_ask` |
| `core.py` | `fuse()` entrypoint ที่ใช้ร่วมกัน + เลือกโมเดล |
| `config.py` | โหลด/บันทึก `config.yaml` |
| `wizard.py` | setup interactive (gateway vs เดี่ยว, ชนิด API) |
| `routing.py` | config → `(provider, model)` routes |
| `providers/factory.py` | เลือก adapter ตาม `kind` |
| `providers/openai_compat.py` · `anthropic.py` · `google.py` | provider adapters |
| `fanout.py` | fan-out ขนาน (ตัดตัวที่พัง) |
| `judge.py` | judge แบบปกปิดชื่อ |
| `fusion.py` | orchestrator: fan-out → judge → `FinalAnswer` |
| `cost.py` | ประมาณค่าใช้จ่ายจาก tokens |
| `models.py` | dataclasses: `Completion`, `FinalAnswer`, `ProviderConfig` |

## พัฒนา
```bash
pip install -e ".[dev,mcp]"
pytest -q
```

## License
MIT
