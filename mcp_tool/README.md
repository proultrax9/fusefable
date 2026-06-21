# FuseFable — MCP Tool

Use FuseFable as an **MCP server** so Cursor, Claude Desktop, VS Code, Hermes, etc. can call **`fuse_ask`** — parallel multi-model fusion → one synthesized answer.

> Full tool reference, recommended models, and troubleshooting: **[TOOLS.md](TOOLS.md)**

This folder is the **MCP deployment**. The desktop app (Cursor-like UI + file editing) lives in [`../desktop_build/`](../desktop_build/). Core code: [`../fusefable/`](../fusefable/) → sync with `python sync_copies.py`.

---

## Quick start

```bash
pip install "fusefable[mcp]"
fusefable config
fusefable mcp
# or: python mcp_tool/run_mcp.py
```

Connect clients with [`mcp-config.example.json`](mcp-config.example.json) → restart client → use `fuse_ask`.

---

## ไทย (สั้นๆ)

- Tool เดียว: **`fuse_ask(question, models?, cheap?)`** — fusion หลาย AI → คำตอบเดียว
- Config: `%USERPROFILE%\.fusefable\config.yaml` (ร่วมกับ Desktop)
- รายละเอียด model แนะนำ + แก้ 401: ดู **[TOOLS.md](TOOLS.md)**
