"""อ่านไฟล์ในโปรเจกต์เป็น context ให้ AI ฟิวชั่นช่วยกันอ่าน.

list_files: ไล่ไฟล์ในโฟลเดอร์ (ข้าม .git/node_modules/binary ฯลฯ)
read_files: รวมเนื้อหาไฟล์ที่เลือกเป็น context เดียว โดยมี cap ขนาดรวม (คุม token/cost)
"""
from __future__ import annotations
import base64
import os
from pathlib import Path

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg"}
_IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
               ".ico": "image/x-icon", ".svg": "image/svg+xml"}
IMAGE_CAP = 6_000_000   # รูปใหญ่กว่านี้ไม่พรีวิว

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".pytest_cache", ".idea", ".vscode", ".mypy_cache", ".ruff_cache",
    ".next", ".cache", "site-packages",
}
# นามสกุลที่เดาว่าเป็น binary (ข้ามไม่อ่าน)
BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".exe", ".dll", ".so", ".dylib", ".bin", ".pyc", ".woff", ".woff2",
    ".ttf", ".otf", ".mp3", ".mp4", ".mov", ".wav", ".jar", ".class",
}
DEFAULT_CAP = 200_000          # ขนาดรวมสูงสุดของ context (bytes) ~50k tokens
PER_FILE_CAP = 60_000          # ต่อไฟล์
CONTEXT_MAX_FILES = 40         # โปรเจกตใหญ่ → ส่งเฉพาะไฟล์สำคัญ + ที่เปิด + @mention

PRIORITY_FILENAMES = frozenset({
    "README.md", "README.th.md", "pyproject.toml", "package.json",
    "Cargo.toml", "go.mod", "requirements.txt", "setup.py",
    "main.py", "app.py", "index.ts", "index.js", "index.tsx",
})

def _is_binary_name(name: str) -> bool:
    return Path(name).suffix.lower() in BINARY_EXT


def _is_image_name(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_EXT


def list_files(root: str, max_files: int = 3000) -> list[dict]:
    """คืนรายการไฟล์ (relative path + size + binary) เรียงตาม path. ข้ามโฟลเดอร์ที่ ignore."""
    root_p = Path(root)
    out: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in IGNORE_DIRS and not d.endswith(".egg-info")]
        for fn in filenames:
            full = Path(dirpath) / fn
            try:
                size = full.stat().st_size
            except OSError:
                continue
            rel = str(full.relative_to(root_p)).replace("\\", "/")
            out.append({"path": rel, "size": size,
                        "binary": _is_binary_name(fn) or _is_image_name(fn),
                        "image": _is_image_name(fn)})
            if len(out) >= max_files:
                out.sort(key=lambda x: x["path"])
                return out
    out.sort(key=lambda x: x["path"])
    return out


def _read_text(path: Path) -> str | None:
    """อ่านไฟล์เป็น text; คืน None ถ้าเป็น binary/อ่านไม่ได้."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw[:1024]:          # มี null byte = binary
        return None
    text = None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except Exception:  # noqa: BLE001
            return None
    # heuristic กัน binary junk: ถ้า control char เยอะ (เกิน 5%) ถือว่าไม่ใช่ text
    # (ยกเว้น \t \n \r \x0b \x0c)
    sample = text[:4096]
    if sample:
        ctrl = sum(1 for ch in sample
                   if ord(ch) < 0x09 or (0x0E <= ord(ch) < 0x20))
        if ctrl / len(sample) > 0.05:
            return None
    return text


EDIT_CAP = 400_000   # ไฟล์ใหญ่กว่านี้ → เปิดอ่านได้แต่แก้ไม่ได้ (readonly)


def _within(root: str, rel_path: str):
    """คืน Path เต็มถ้าอยู่ในโปรเจกต์จริง; ไม่งั้น None (กัน path traversal/symlink)."""
    root_p = Path(root)
    full = root_p / rel_path
    try:
        full.resolve().relative_to(root_p.resolve())
    except (ValueError, OSError):
        return None
    return full


def open_file(root: str, rel_path: str) -> dict:
    """เปิดไฟล์เพื่ออ่าน/แก้. คืน {content, truncated, readonly} หรือ {error}."""
    full = _within(root, rel_path)
    if full is None:
        return {"error": "outside project"}
    if not full.is_file():
        return {"error": "not a file"}
    if _is_binary_name(rel_path):
        return {"error": "binary"}
    text = _read_text(full)
    if text is None:
        return {"error": "binary"}
    if len(text) > EDIT_CAP:
        return {"content": text[:EDIT_CAP], "truncated": True, "readonly": True}
    return {"content": text, "truncated": False, "readonly": False}


def read_image(root: str, rel_path: str) -> dict:
    """อ่านรูปเป็น base64 data URI สำหรับพรีวิว. คืน {data_uri} หรือ {error}."""
    full = _within(root, rel_path)
    if full is None:
        return {"error": "outside project"}
    if not full.is_file():
        return {"error": "not a file"}
    if not _is_image_name(rel_path):
        return {"error": "not an image"}
    try:
        raw = full.read_bytes()
    except OSError as e:
        return {"error": str(e)}
    if len(raw) > IMAGE_CAP:
        return {"error": "image too large to preview"}
    mime = _IMAGE_MIME.get(Path(rel_path).suffix.lower(), "application/octet-stream")
    b64 = base64.b64encode(raw).decode("ascii")
    return {"data_uri": f"data:{mime};base64,{b64}", "size": len(raw)}


def write_file(root: str, rel_path: str, content: str) -> dict:
    """บันทึกไฟล์ (utf-8). คืน {ok} หรือ {ok:False, error}."""
    full = _within(root, rel_path)
    if full is None:
        return {"ok": False, "error": "outside project"}
    if _is_binary_name(rel_path):
        return {"ok": False, "error": "binary file"}
    try:
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return {"ok": True}
    except OSError as e:
        return {"ok": False, "error": str(e)}


def pick_context_paths(rel_paths: list[str],
                       open_path: str = "",
                       mentioned: list[str] | None = None,
                       max_files: int = CONTEXT_MAX_FILES) -> list[str]:
    """เลือกไฟล์ที่ส่งให้ AI — โปรเจกตเล็กส่งทั้งหมด, ใหญ่ส่งไฟล์สำคัญ + ที่เปิด + @mention."""
    text_paths = sorted(set(rel_paths))
    if len(text_paths) <= max_files:
        return text_paths
    chosen: list[str] = []
    seen: set[str] = set()

    def add(p: str) -> None:
        if p and p in rel_paths and p not in seen:
            seen.add(p)
            chosen.append(p)

    for p in mentioned or []:
        add(p)
    if open_path:
        add(open_path)
    for p in text_paths:
        if Path(p).name in PRIORITY_FILENAMES:
            add(p)
    for p in text_paths:
        add(p)
        if len(chosen) >= max_files:
            break
    return chosen[:max_files]


def read_files(root: str, rel_paths: list[str],
               total_cap: int = DEFAULT_CAP,
               per_file_cap: int = PER_FILE_CAP,
               overrides: dict[str, str] | None = None) -> dict:
    """รวมเนื้อหาไฟล์ที่เลือกเป็น context เดียว (มี cap). คืน dict สรุปผล.

    คืน: {context, included:[...], skipped:[{path,reason}], truncated, chars}
    """
    overrides = overrides or {}
    root_p = Path(root)
    parts: list[str] = []
    included: list[str] = []
    skipped: list[dict] = []
    used = 0
    truncated = False

    for rel in rel_paths:
        full = (root_p / rel)
        try:
            full_resolved = full.resolve()
            full_resolved.relative_to(root_p.resolve())   # กัน path traversal
        except (ValueError, OSError):
            skipped.append({"path": rel, "reason": "outside project"})
            continue
        if _is_binary_name(rel):
            skipped.append({"path": rel, "reason": "binary"})
            continue
        if rel in overrides:
            text = overrides[rel]
        else:
            text = _read_text(full)
            if text is None:
                skipped.append({"path": rel, "reason": "binary/unreadable"})
                continue
        if len(text) > per_file_cap:
            text = text[:per_file_cap] + "\n…(truncated)…"
            truncated = True
        block = f"### {rel}\n{text}\n"
        if used + len(block) > total_cap:
            truncated = True
            skipped.append({"path": rel, "reason": "cap reached"})
            continue
        parts.append(block)
        used += len(block)
        included.append(rel)

    return {
        "context": "\n".join(parts),
        "included": included,
        "skipped": skipped,
        "truncated": truncated,
        "chars": used,
    }
