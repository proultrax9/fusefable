"""Parse และ apply การแก้ไฟล์จากคำตอบ AI (desktop agent mode).

AI ส่งบล็อก <file_edit path="...">...</file_edit> → Fuse บันทึกลงดisk อัตโนมัติ
ผู้ใช้เห็นแค่ summary สั้นๆ ไม่เห็นเนื้อหาไฟล์เต็มในแชท
"""
from __future__ import annotations
import re
from fusefable import project

FILE_EDIT_RE = re.compile(
    r'<file_edit\s+path=(["\'])(.*?)\1\s*>(.*?)</file_edit>',
    re.DOTALL | re.IGNORECASE,
)

AGENT_INSTRUCTIONS = """\
You are an coding agent inside the user's open project folder.
You can read attached project files and CREATE or MODIFY files on disk.

When the user asks you to change, fix, add, or build something in the project:
1. Output one block per changed file:
<file_edit path="relative/path/from/project/root">
...complete new file contents...
</file_edit>
2. Then write a brief summary in the user's language (1-3 sentences).

Rules:
- Use complete file contents (not a diff).
- Paths must be relative to the project root (forward slashes).
- Only change files needed for the request.
- Do not paste full file contents outside file_edit blocks."""

ENSEMBLE_EDIT_NOTE = (
    "\nIf the task requires file changes, include <file_edit path=\"...\">...</file_edit> "
    "blocks with complete file contents, then a brief summary.\n"
)


def parse_file_edits(text: str) -> list[tuple[str, str]]:
    """ดึง (path, content) จากบล็อก file_edit."""
    return [(m.group(2).strip().replace("\\", "/"), m.group(3))
            for m in FILE_EDIT_RE.finditer(text)]


def display_answer(text: str, applied_count: int = 0) -> str:
    """ตัดบล็อก file_edit ออก — เหลือ summary ให้ผู้ใช้เห็น."""
    cleaned = FILE_EDIT_RE.sub("", text).strip()
    if cleaned:
        return cleaned
    if applied_count:
        return f"อัปเดต {applied_count} ไฟล์แล้ว"
    if FILE_EDIT_RE.search(text):
        return ""
    return text.strip()


def apply_edits(root: str, edits: list[tuple[str, str]]) -> list[dict]:
    """บันทึกไฟล์ทีละตัว. คืน [{path, ok, error?}, ...]."""
    out: list[dict] = []
    for path, content in edits:
        r = project.write_file(root, path, content)
        out.append({"path": path, **r})
    return out
