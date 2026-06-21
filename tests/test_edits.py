from fusefable import edits


SAMPLE = """<file_edit path="src/main.py">
print("hello")
</file_edit>

แก้ไข main.py ให้พิมพ์ hello แล้ว"""


def test_parse_file_edits():
    got = edits.parse_file_edits(SAMPLE)
    assert len(got) == 1
    assert got[0][0] == "src/main.py"
    assert 'print("hello")' in got[0][1]


def test_parse_file_edits_single_quotes():
    text = "<file_edit path='a/b.py'>\nx=1\n</file_edit>"
    assert edits.parse_file_edits(text) == [("a/b.py", "\nx=1\n")]


def test_display_answer_strips_blocks():
    assert edits.display_answer(SAMPLE, 1) == "แก้ไข main.py ให้พิมพ์ hello แล้ว"


def test_display_answer_fallback_when_empty():
    assert edits.display_answer("<file_edit path=\"a.py\">\nx\n</file_edit>", 1) == "อัปเดต 1 ไฟล์แล้ว"


def test_apply_edits_writes_files(tmp_path):
    r = edits.apply_edits(str(tmp_path), [("nested/x.py", "ok\n")])
    assert r[0]["ok"] is True
    assert (tmp_path / "nested" / "x.py").read_text(encoding="utf-8") == "ok\n"
