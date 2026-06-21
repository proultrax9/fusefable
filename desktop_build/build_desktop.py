"""Build Fusion Fable desktop — Electron UI + Python backend exe.

Steps:
  1. PyInstaller → desktop_build/dist/FusionFableBackend.exe
  2. npm install + electron-builder → desktop_build/dist-electron/Fusion Fable.exe

Requires: pip install pyinstaller, Node.js 18+
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def run(cmd: list[str], cwd: str | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=cwd or HERE)


def build_backend() -> None:
    run([
        sys.executable, "-m", "PyInstaller",
        os.path.join(HERE, "backend_entry.py"),
        "--name", "FusionFableBackend",
        "--onefile",
        "--noconsole",
        "--paths", HERE,
        "--collect-submodules", "fusefable",
        "--hidden-import", "fusefable.desktop",
        "--hidden-import", "fusefable.desktop_server",
        "--distpath", os.path.join(HERE, "dist"),
        "--workpath", os.path.join(HERE, "build-backend"),
        "--specpath", HERE,
        "--noconfirm",
        "--clean",
    ])


def build_electron() -> None:
    electron_dir = os.path.join(HERE, "electron")
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    env = os.environ.copy()
    env["CSC_IDENTITY_AUTO_DISCOVERY"] = "false"
    run([npm, "install"], cwd=electron_dir)
    print("+", npm, "run", "build", flush=True)
    subprocess.check_call([npm, "run", "build"], cwd=electron_dir, env=env)


def main() -> None:
    # sync from root if script exists
    sync = os.path.join(ROOT, "sync_copies.py")
    if os.path.isfile(sync):
        run([sys.executable, sync], cwd=ROOT)
    build_backend()
    build_electron()
    out = os.path.join(HERE, "dist-electron", "Fusion Fable.exe")
    print(f"\nDone: {out}", flush=True)


if __name__ == "__main__":
    main()
