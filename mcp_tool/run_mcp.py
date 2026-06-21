"""Launcher: run FuseFable as an MCP tool (stdio) for Cursor / Claude / VS Code / Hermes.

Usage:
    pip install "fusefable[mcp]"
    python mcp_tool/run_mcp.py        # or simply: fusefable mcp

This exposes MCP tool `fuse_ask(question, models?, cheap?)` — parallel fusion
(ensemble by default) into a single answer. See mcp_tool/TOOLS.md for setup.
"""
from fusefable.mcp_server import run_mcp

if __name__ == "__main__":
    run_mcp()
