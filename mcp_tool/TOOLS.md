# Fuse Fable — MCP Tools

เอกสารนี้สำหรับฝั่ง **MCP tool** (`mcp_tool/`) — ให้ Cursor / Claude / Hermes เรียก fusion AI ผ่าน tool เดียว  
**ไม่มีแก้ไฟล์โปรเจกต** (แก้ไฟล์ใช้ Desktop `.exe` ใน `desktop_build/`)

---

## Tool ที่มี

### `fuse_ask`

ยิงคำถามไปหลายโมเดลพร้อมกัน → **ensemble synthesize** เป็นคำตอบเดียว (ตาม `fusion_mode` ใน config)

| พารามิเตอร์ | ชนิด | คำอธิบาย |
|-------------|------|----------|
| `question` | string | คำถาม / งาน coding (บังคับ) |
| `models` | string? | จำกัดโมเดล เช่น `openai/gpt-5.5,anthropic/claude-opus-4.8` (ว่าง = ใช้ทุกตัวใน config) |
| `cheap` | bool | ใช้ `cheap_models` ใน config ถ้ามี (default `false`) |

**คืนค่า:** ข้อความคำตอบสุดท้าย (string เท่านั้น — ไม่มี metadata)

**ตัวอย่างที่ agent ควรเรียก:**
```
fuse_ask(question="อธิบายว่าโปรเจกตนี้ทำอะไร และแนะนำจุดเริ่มอ่านโค้ด")
```

---

## ติดตั้ง + รัน

```bash
pip install "fusefable[mcp]"
fusefable config          # wizard ครั้งแรก (หรือแก้ config.yaml เอง)
fusefable mcp             # รัน MCP server (stdio)
```

จาก repo นี้โดยตรง:

```bash
python mcp_tool/run_mcp.py
```

---

## เชื่อม Cursor / Hermes

ดู [`mcp-config.example.json`](mcp-config.example.json)

**ติดตั้ง global (แนะนำ):**
```json
{
  "mcpServers": {
    "fusefable": {
      "command": "fusefable",
      "args": ["mcp"]
    }
  }
}
```

**รันจาก repo นี้ (Windows — แก้ path ให้ตรงเครื่องคุณ):**
```json
{
  "mcpServers": {
    "fusefable": {
      "command": "python",
      "args": ["C:/Users/User/Desktop/Project Fable 5 Fusion/mcp_tool/run_mcp.py"]
    }
  }
}
```

| Client | ที่วาง config |
|--------|----------------|
| **Cursor** | Settings → MCP หรือ `%USERPROFILE%\.cursor\mcp.json` |
| **Claude Desktop** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Hermes / agent อื่น** | MCP servers ใน config ของ agent |

หลัง save → **restart client** → จะเห็น tool `fuse_ask`

---

## Config แนะนำ (OpenRouter — 3 ตัว top tier)

ไฟล์: **`%USERPROFILE%\.fusefable\config.yaml`**

```yaml
mode: gateway
gateway_name: openrouter
gateway_base_url: https://openrouter.ai/api/v1
api_key: "sk-or-v1-..."          # key จาก openrouter.ai/keys
models:
  - openai/gpt-5.5
  - anthropic/claude-opus-4.8
  - google/gemini-3.1-pro-preview   # ต้องมี -preview บน OpenRouter
judge_model: anthropic/claude-opus-4.8
fusion_mode: ensemble              # สังเคราะห์คำตอบใหม่ (ไม่ใช่เลือกตัวเดียว)
min_responses: 3                   # รอครบ 3 ตัวแล้ว synthesize
timeout_seconds: 45
cache: true
compress: false                    # ปิดสำหรับแชททั่วไป
```

**Models ช่องเดียว (Settings Desktop / wizard):**
```
openai/gpt-5.5, anthropic/claude-opus-4.8, google/gemini-3.1-pro-preview
```

---

## Desktop vs MCP

| | **MCP (`fuse_ask`)** | **Desktop (.exe)** |
|--|----------------------|---------------------|
| ใช้จาก | Cursor, Claude, Hermes | Fusion Fable app |
| คำตอบ | ข้อความอย่างเดียว | แชท + แก้ไฟล์อัตโนมัติ |
| โปรเจกต / ไฟล์ | ไม่มี explorer | เปิดโฟลเดอร์ + agent แก้ไฟล์ |
| config | `~/.fusefable/config.yaml` | ไฟล์เดียวกัน |

---

## แก้ปัญหา

### `no successful completions from any model`

มักเกิดจาก **ทุกโมเดลล้มเหลว** — ดูข้อความต่อท้าย (เช่น `401 Unauthorized`)

| อาการ | แก้ |
|--------|-----|
| **401 Unauthorized** | สร้าง API key ใหม่ที่ [openrouter.ai/keys](https://openrouter.ai/keys) → วางใน `api_key` → ตรวจ credits |
| **model not found** | ตรวจ slug ที่ [openrouter.ai/models](https://openrouter.ai/models) — Gemini ใช้ `google/gemini-3.1-pro-preview` |
| **timeout** | เพิ่ม `timeout_seconds` ใน config หรือถามสั้นลง |
| key มีช่องว่าง / copy ไม่ครบ | วาง key ใหม่ทั้งก้อน ไม่มี space หัวท้าย |

**ทดสอบ key เร็ว (PowerShell):**
```powershell
curl https://openrouter.ai/api/v1/chat/completions `
  -H "Authorization: Bearer YOUR_KEY" `
  -H "Content-Type: application/json" `
  -d "{\"model\":\"openai/gpt-5.5\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}"
```

### MCP ไม่ขึ้นใน Cursor

- `fusefable` ต้องอยู่บน PATH (`pip install fusefable`) หรือใช้ `python` + path ไป `run_mcp.py`
- restart Cursor หลังแก้ `mcp.json`
- ดู MCP logs ใน Cursor Settings

### แก้ config แล้วยังไม่เปลี่ยน

- MCP โหลด config ทุกครั้งที่เรียก `fuse_ask` — ไม่ต้อง restart server สำหรับเปลี่ยน model/key
- ถ้าแก้โค้ดใน repo → รัน `python sync_copies.py` แล้ว restart MCP client

---

## Sync โค้ดจาก root

แก้ที่ `fusefable/` (root) แล้ว:

```bash
python sync_copies.py
```

จะ copy ไป `mcp_tool/fusefable/` และ `desktop_build/fusefable/`

---

## ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | หน้าที่ |
|------|---------|
| `TOOLS.md` | เอกสาร tool นี้ |
| `README.md` | ภาพรวมสั้นๆ |
| `run_mcp.py` | launcher MCP |
| `mcp-config.example.json` | ตัวอย่าง config client |
| `fusefable/mcp_server.py` | ลงทะเบียน `fuse_ask` |
