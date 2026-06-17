"""MCP server — เปิด Fuse Fable เป็น tool ให้ Cursor / VS Code / Claude / agent อื่นเรียก.

แยก fuse_ask_impl (logic, test ได้โดยไม่ต้องมี mcp) ออกจาก run_mcp (ตัวรัน server).
"""
from __future__ import annotations
from typing import Optional
from fusefable.config import load_config, default_config_path
from fusefable.core import fuse


async def fuse_ask_impl(question: str, models: Optional[str] = None,
                        cheap: bool = False) -> str:
    """logic ของ tool — โหลด config แล้วฟิวชั่น คืนข้อความคำตอบที่ดีสุด."""
    cfg = load_config(default_config_path())
    model_list = [m.strip() for m in models.split(",")] if models else None
    result = await fuse(cfg, question, models=model_list, cheap=cheap)
    return result.text


def run_mcp() -> None:
    """รัน MCP server ผ่าน stdio. ต้องติดตั้ง: pip install 'fusefable[mcp]'."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:  # noqa: F841
        raise SystemExit(
            "MCP ยังไม่ได้ติดตั้ง — รัน: pip install 'fusefable[mcp]'"
        )

    server = FastMCP("fusefable")

    @server.tool()
    async def fuse_ask(question: str, models: Optional[str] = None,
                       cheap: bool = False) -> str:
        """Ask multiple AI models in parallel and return the best answer.

        Args:
            question: The coding question or task.
            models: Optional comma-separated subset of models to use.
            cheap: Use the configured cheap_models subset if available.
        """
        return await fuse_ask_impl(question, models, cheap)

    server.run()
