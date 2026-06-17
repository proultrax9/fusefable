# Fuse Fable

ฟิวชั่นหลาย AI model พร้อมกัน แล้วเลือกคำตอบที่ดีที่สุดสำหรับงานโค้ด — latency ≈ x2
(ยิงทุกตัวขนานกัน + judge รอบเดียว) ไม่ใช่ x7–x15

## ติดตั้ง
```bash
pip install fusefable
```
หรือจาก source:
```bash
pip install -e .
```

## ตั้งค่า (ครั้งแรก)
```bash
fusefable config
```
- เลือก **AI Gateway** → ใส่ key เดียวพอ แล้วถามว่าจะใช้กี่โมเดล + ทีละตัว
  - รองรับหลายเจ้า (เติม URL อัตโนมัติ): `openrouter`, `groq`, `together`,
    `fireworks`, `deepinfra`, `novita`, `hyperbolic`, `aimlapi`, `portkey`,
    `deepseek`, `openai` — เจ้าอื่นก็ใช้ได้ แค่พิมพ์ base_url เอง
- หรือ **Provider เดี่ยว** → ถามว่าจะใช้กี่เจ้า แล้วใส่ base_url + ชื่อ env ของ key ของแต่ละเจ้า

ตั้ง API key เป็น environment variable ตามชื่อที่ wizard ถาม เช่น:
```bash
export OPENROUTER_API_KEY=sk-...
```

## ใช้งาน
```bash
fusefable ask "เขียนฟังก์ชัน quicksort ใน Python"
fusefable ask --show-all "..."     # ดูคำตอบทุกตัว + เหตุผล judge
ff ask "..."                        # alias สั้น
```

## ทำงานยังไง
1. **fan-out** — ยิงทุกโมเดลพร้อมกันด้วย `asyncio` (เวลารวม = ตัวช้าสุด)
2. ตัวไหน timeout/พัง → ตัดทิ้ง ไม่ลากระบบช้า
3. **judge** — ปกปิดชื่อโมเดล (Answer A/B/C...) แล้วให้โมเดล judge เลือกตัวดีสุด
4. คืนคำตอบที่ดีที่สุด + ประมาณค่าใช้จ่าย

## พัฒนา
```bash
pip install -e ".[dev]"
pytest -q
```
