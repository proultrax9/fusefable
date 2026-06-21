"""MCP server — เปิด Fuse Fable เป็น tool ให้ Cursor / VS Code / Claude / agent อื่นเรียก.

แยก fuse_ask_impl (logic, test ได้โดยไม่ต้องมี mcp) ออกจาก run_mcp (ตัวรัน server).
"""
from __future__ import annotations
from typing import Optional
from fusefable.config import load_config, default_config_path
from fusefable.core import fuse


async def fuse_ask_impl(question: str, models: Optional[str] = None,
                        cheap: bool = False) -> str:
    """โหลด config → fuse → คืนข้อความคำตอบ (ensemble/judge ตาม config)."""
    cfg = load_config(default_config_path())
    model_list = [m.strip() for m in models.split(",") if m.strip()] if models else None
    try:
        result = await fuse(cfg, question, models=model_list, cheap=cheap)
        return result.text
    except Exception as e:  # noqa: BLE001 — ส่ง error กลับ agent ให้อ่านได้
        return f"[fusefable error] {e}"


def build_server():
    """สร้าง FastMCP server + ลงทะเบียน tool fuse_ask. ต้องมี mcp ติดตั้ง."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("fusefable")

    @server.tool()
    async def fuse_ask(question: str, models: Optional[str] = None,
                       cheap: bool = False) -> str:
        """Fan out to multiple AI models (OpenRouter etc.) and return one fused answer.

        Uses ~/.fusefable/config.yaml — default fusion_mode=ensemble synthesizes
        a new answer from all models (not pick-one judge).

        Args:
            question: Coding question or task (required).
            models: Optional comma-separated model slugs, e.g.
                "openai/gpt-5.5,anthropic/claude-opus-4.8,google/gemini-3.1-pro-preview"
            cheap: If true, use cheap_models from config when set.

        Returns:
            Final answer text. On failure, returns a line starting with [fusefable error].
        """
        return await fuse_ask_impl(question, models, cheap)

    return server


def run_mcp() -> None:
    """รัน MCP server ผ่าน stdio. ต้องติดตั้ง: pip install 'fusefable[mcp]'."""
    try:
        server = build_server()
    except ImportError:
        raise SystemExit("MCP ยังไม่ได้ติดตั้ง — รัน: pip install 'fusefable[mcp]'")
    server.run()
