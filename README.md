# Fuse Fable

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

## ทำงานยังไง
1. **fan-out** — ยิงทุกโมเดลพร้อมกันด้วย `asyncio` (เวลารวม = ตัวช้าสุด)
2. ตัวไหน timeout/พัง → ตัดทิ้ง ไม่ลากระบบช้า
3. **judge** — ปกปิดชื่อโมเดล (Answer A/B/C...) แล้วให้โมเดล judge เลือกตัวดีสุด
4. คืนคำตอบที่ดีที่สุด + ประมาณค่าใช้จ่าย

## พัฒนา
```bash
pip install -e ".[dev,mcp]"
pytest -q
```

## License
MIT
