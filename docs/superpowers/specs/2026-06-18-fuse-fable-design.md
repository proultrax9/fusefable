# Fuse Fable — Design Spec

วันที่: 2026-06-18

## 1. ภาพรวม (Overview)

**Fuse Fable** เป็น CLI tool ที่ "ฟิวชั่น" คำตอบจากหลาย AI model พร้อมกัน
แล้วใช้ judge เลือกคำตอบที่ดีที่สุดสำหรับงานโค้ดดิ้ง — เป้าหมายคือได้คุณภาพ
สูงสุดในเวลาตอบสนองที่ไวที่สุด (latency ประมาณ x2 ไม่ใช่ x7–x15)

**แนวคิดหลัก:** ในเมื่อโมเดลที่แรงที่สุด (เช่น Fable 5) ยังไม่เปิด/แพง การยิง
หลายโมเดลพร้อมกันแล้วคัดตัวที่ดีสุด ให้ผลลัพธ์ที่เข้าใกล้โมเดลระดับบนได้ในราคา
ที่คุมได้

**กลุ่มเป้าหมาย:** แจกฟรี (open-source) — ใครใช้ provider เจ้าไหนก็เสียบได้
ผู้พัฒนาเอง (เจ้าของโปรเจกต์) ใช้ OpenRouter เป็นหลัก

## 2. สถาปัตยกรรม (Architecture)

```
ผู้ใช้พิมพ์ prompt
      │
      ▼
fan-out (asyncio.gather)  ─── ยิง N โมเดลพร้อมกัน, latency = ตัวช้าสุด (~x1)
      │
   ┌──┴──┬─────┬─────┬─────┬─────┬─────┐
   ▼     ▼     ▼     ▼     ▼     ▼     ▼
 Claude GPT Gemini DeepSeek Kimi GLM Qwen
   │     │     │     │     │     │     │
   └─────┴─────┴─────┴─────┴─────┴─────┘
      │  คำตอบทั้งหมด (ปกปิดชื่อ → A, B, C, ...)
      ▼
judge (1 รอบ)  ─── เลือกตัวที่ดีสุด (+x1)
      │
      ▼
คำตอบที่ดีที่สุด (stream ออกมา)

รวม latency ≈ x2 (ตัวช้าสุด + judge)
```

### หลักการสำคัญ 3 ข้อ
1. **fan-out ด้วย `asyncio.gather`** — request ทุกตัววิ่งขนานกัน เวลารวม = ตัวช้าสุด
   ไม่ใช่ผลบวก
2. **Timeout headroom = x2** — มี hard cap timeout (default 90s) ถ้าตัวไหนช้า/พัง
   ก็ทิ้ง ไม่ลากทั้งระบบช้า
3. **Judge รอบเดียว** — ปกปิดชื่อโมเดลก่อนส่งให้ judge เพื่อตัดสินที่คุณภาพล้วน
   (กัน bias เข้าข้างตัวเองเมื่อ judge เป็นหนึ่งในผู้แข่ง)

## 3. โครงสร้างไฟล์ (Components)

```
fusefable/
├── config.py        # โหลด/validate config.yaml
├── providers/
│   ├── base.py      # interface กลาง: async def complete(model, prompt) -> Completion
│   ├── openrouter.py# default — 1 key เรียกได้ทุกโมเดล (OpenAI-compatible)
│   ├── openai.py    # OpenAI native (OpenAI-compatible)
│   ├── anthropic.py # Claude native (format เฉพาะ)
│   └── google.py    # Gemini native (format เฉพาะ)
├── client.py        # เรียก 1 โมเดล (async) + จับ error/timeout → Completion | None
├── fanout.py        # ยิง N โมเดลพร้อมกันด้วย asyncio.gather
├── judge.py         # ส่งคำตอบ(ปกปิดชื่อ)ให้ judge เลือกตัวดีสุด → index
├── fusion.py        # orchestrator: prompt → คำตอบสุดท้าย
└── main.py          # CLI (typer/click)
```

### หน้าที่ของแต่ละ unit
| ไฟล์ | หน้าที่เดียว | input → output |
|---|---|---|
| `providers/base.py` | นิยาม interface | — |
| `providers/*.py` | คุยกับ provider จริง | (model, prompt) → text + usage |
| `client.py` | ยิง 1 โมเดล + timeout/error | (provider, model, prompt) → Completion \| None |
| `fanout.py` | ยิง N ตัวขนาน | prompt → list[Completion] (เฉพาะที่สำเร็จ) |
| `judge.py` | ตัดสิน | list[Completion] → index ตัวที่ดีสุด + เหตุผล |
| `fusion.py` | รวมร่าง | prompt → FinalAnswer |
| `main.py` | CLI | argv → stdout |

## 4. การจัดการ Error / Timeout

1. **Per-model timeout** — `asyncio.wait_for(..., timeout=config.timeout_seconds)`
   ตัวไหนช้าเกิน = ตัดทิ้ง
2. **`return_exceptions=True`** ใน `gather` — ตัวหนึ่งพัง อีกตัวยังเดินต่อ
3. **Graceful degradation** — ถ้าได้คำตอบ ≥1 ตัว ก็ judge ได้ ไม่ต้องครบทุกตัว
4. **Judge fallback** — ถ้า judge พัง → คืนคำตอบจากโมเดลแรกในลิสต์ที่สำเร็จ
   (เช่น Claude) ไม่ให้ทั้งระบบล่ม
5. **Streaming ที่ judge** — judge stream คำตอบสุดท้ายออกมาทันที ลดความรู้สึกว่าช้า

### กลยุทธ์ timeout (default)
**รอครบทุกตัว แต่มี hard cap** (default 90s) — เหมาะกับงานโค้ดที่ไม่อยากตัดตัวเก่งทิ้ง
ปรับเป็นโหมด "พอได้ N ตัวก็ judge เลย" ได้ผ่าน config (`min_responses`)

## 5. Provider Abstraction (สำหรับแจกฟรี)

- ทุก provider implement `base.py` → `fanout.py` ไม่รู้ว่าข้างใต้เป็นเจ้าไหน
- เจ้าที่เป็น **OpenAI-compatible** (OpenRouter, OpenAI, DeepSeek, GLM, Together ฯลฯ)
  ใช้ adapter เดียวกัน ต่างแค่ `base_url`
- เจ้าที่ format ต่าง (Anthropic, Google) ทำ adapter เฉพาะ
- รองรับ **mixed mode**: ผสม provider หลายเจ้าในคำถามเดียว
  (เช่น Claude จาก Anthropic ตรง + ที่เหลือจาก OpenRouter)

## 6. Config (config.yaml)

```yaml
provider: openrouter          # openrouter | openai | anthropic | google | mixed
api_key_env: OPENROUTER_API_KEY
timeout_seconds: 90
min_responses: 1              # judge เริ่มเมื่อได้คำตอบครบ N ตัว
budget_cap_usd: null          # คุมค่าใช้จ่ายต่อคำถาม (null = ไม่จำกัด)
judge_model: deepseek/deepseek-chat
models:
  - anthropic/claude-opus-4.1
  - openai/gpt-5
  - google/gemini-2.5-pro
  - deepseek/deepseek-chat
  - moonshotai/kimi-k2
  - z-ai/glm-4.6
  - qwen/qwen3-coder
# โหมด mixed: ระบุ provider ต่อโมเดลได้
# models:
#   - {provider: anthropic, model: claude-opus-4.1}
#   - {provider: openrouter, model: deepseek/deepseek-chat}
```

> หมายเหตุ: ชื่อโมเดลด้านบนเป็นตัวอย่าง — ปรับตามชื่อจริงบน OpenRouter ตอน implement

## 7. CLI

```bash
fusefable "เขียนฟังก์ชัน quicksort ใน Python"   # ใช้งานพื้นฐาน
ff "..."                                          # alias สั้น
fusefable --show-all "..."                        # ดูคำตอบทุกตัว + เหตุผล judge
fusefable --models claude,gpt,qwen "..."          # เลือกเฉพาะบางตัว
fusefable --cheap "..."                           # โหมดประหยัด (ยิงเฉพาะโมเดลถูก)
fusefable config                                  # ตั้งค่า key / โมเดล
```

## 7.1 Setup Wizard (รันครั้งแรก / `fusefable config`)

ถามแบบ interactive เพื่อให้คนอื่นตั้งค่าได้ง่าย ไม่ต้องแก้ yaml เอง:

```
ขั้นที่ 1: คุณใช้แบบไหน?
  [1] AI Gateway (เช่น OpenRouter)  ← key เดียวเรียกได้ทุกโมเดล
  [2] Provider เดี่ยว (ผสมหลายเจ้า)

── ถ้าเลือก [1] AI Gateway ──
  > Gateway เจ้าไหน? (openrouter / ...)
  > ใส่ API key:  ______
  → จบ! ใช้ key เดียวกับทุกโมเดล

── ถ้าเลือก [2] Provider เดี่ยว ──
  > จะใช้กี่เจ้า? (เช่น 3)
  วนถามทีละเจ้า:
    > เจ้าที่ 1 ชื่อ/base_url:  ______
    > API key ของเจ้านี้:      ______
    > เจ้าที่ 2 ...
  → บันทึกแต่ละเจ้าพร้อม key แยกกัน
```

ผลลัพธ์: เขียนลง `config.yaml` + เก็บ key ใน env/ไฟล์ลับ (ไม่ commit)
- โหมด gateway → `provider: <gateway>`, `api_key_env: ...` ตัวเดียว
- โหมด เดี่ยว → `provider: mixed` + รายการ provider พร้อม base_url/key แยก

## 8. งบประมาณ (Cost)

- ค่าใช้จ่าย/คำถาม ≈ ผลรวม N โมเดล + judge 1 รอบ
- `--cheap` mode: ยิงเฉพาะ 3–4 โมเดลถูก → ถูกลง ~70%
- แสดง **cost estimate** ท้ายผลลัพธ์ (คำนวณจาก usage tokens)
- **budget cap** ใน config กันบิลบาน

## 9. เทคโนโลยี

- **ภาษา:** Python 3.10+
- **Async:** `asyncio` + `httpx` (async HTTP)
- **CLI:** `typer` (หรือ `click`)
- **Config:** `pyyaml`
- **Anthropic provider (ถ้าทำ native):** `anthropic` SDK
- **แจกจ่าย:** `pip install fusefable`

## 10. ขอบเขต (Scope) — YAGNI

**ทำในเวอร์ชันแรก:**
- fan-out + judge + CLI พื้นฐาน
- OpenRouter provider (default) + OpenAI-compatible adapter
- timeout/error handling, cost estimate, `--show-all`, `--cheap`

**ยังไม่ทำ (ไว้ทีหลัง):**
- Anthropic/Google native adapter (เริ่มจาก OpenRouter ก่อน เพราะครอบคลุมทุกโมเดลแล้ว)
- Web UI / API server
- Caching คำตอบ
- โหมด vote/ensemble แบบรวมคำตอบ (เริ่มจาก "เลือก 1 ตัวดีสุด" ก่อน)
```