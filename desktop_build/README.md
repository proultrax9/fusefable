# Fusion Fable — Desktop App (.exe)

Cursor-style desktop: **Electron + Monaco Editor** UI, **Python** fusion backend.

## Quick start (dev)

```bash
# terminal 1 — backend
python desktop_build/backend_entry.py

# terminal 2 — UI (needs Node 18+)
cd desktop_build/electron && npm install && npm start
```

## Build portable .exe (Windows)

```bash
pip install pyinstaller
python desktop_build/build_desktop.py
```

Output: **`desktop_build/dist-electron/Fusion Fable.exe`**

Includes embedded `FusionFableBackend.exe` (Python fusion engine).

## Layout (like Cursor)

```
[Activity] [Explorer] | [Agent Chat — full center] | [Editor — right on file click]
```

- Drag panel borders to resize
- Single-click file → Monaco editor on the right
- Chat + `Plan, @ for context…` composer

## Legacy PyWebView build

Still available: `python desktop_build/build_exe.py` → `dist/Fusion Fable.exe`

## ไทย

- **Electron** = หน้าตาเหมือน Cursor (Monaco editor จริง)
- **Python backend** = fusion AI + แก้ไฟล์อัตโนมัติ
- สร้าง exe: `python desktop_build/build_desktop.py`
