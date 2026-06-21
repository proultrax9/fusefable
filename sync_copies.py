"""Sync the source-of-truth package (fusefable/) into the two self-contained folders.

The desktop app (desktop_build/) and the MCP tool (mcp_tool/) each keep their own
copy of the code. Edit the core in the root `fusefable/`, then run this to refresh
both copies with one command:

    python sync_copies.py
"""
from __future__ import annotations
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "fusefable"
TARGETS = [ROOT / "desktop_build" / "fusefable", ROOT / "mcp_tool" / "fusefable"]


def _ignore(_dir, names):
    return [n for n in names if n == "__pycache__" or n.endswith(".pyc")]


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit("root fusefable/ not found")
    for dst in TARGETS:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(SRC, dst, ignore=_ignore)
        print(f"synced -> {dst.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
