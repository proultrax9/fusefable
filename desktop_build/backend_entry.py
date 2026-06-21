"""PyInstaller entry — Fusion Fable HTTP backend (no GUI)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fusefable.desktop_server import main  # noqa: E402

if __name__ == "__main__":
    main()
