from fusefable import project


def _mkproject(tmp_path):
    (tmp_path / "a.py").write_text("print('a')", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("x=1", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("//x", encoding="utf-8")
    (tmp_path / "img.png").write_bytes(b"\x89PNG\x00\x00data")
    return tmp_path


def test_list_files_skips_ignored_dirs(tmp_path):
    _mkproject(tmp_path)
    files = project.list_files(str(tmp_path))
    paths = [f["path"] for f in files]
    assert "a.py" in paths and "sub/b.py" in paths
    assert not any(".git" in p for p in paths)
    assert not any("node_modules" in p for p in paths)
    png = [f for f in files if f["path"] == "img.png"][0]
    assert png["binary"] is True


def test_read_files_concatenates_with_headers(tmp_path):
    _mkproject(tmp_path)
    r = project.read_files(str(tmp_path), ["a.py", "sub/b.py"])
    assert "### a.py" in r["context"]
    assert "print('a')" in r["context"]
    assert "### sub/b.py" in r["context"]
    assert set(r["included"]) == {"a.py", "sub/b.py"}
    assert r["truncated"] is False


def test_read_files_skips_binary(tmp_path):
    _mkproject(tmp_path)
    r = project.read_files(str(tmp_path), ["img.png", "a.py"])
    assert r["included"] == ["a.py"]
    assert any(s["path"] == "img.png" for s in r["skipped"])


def test_read_files_respects_cap(tmp_path):
    big = "x" * 5000
    (tmp_path / "big.txt").write_text(big, encoding="utf-8")
    (tmp_path / "small.txt").write_text("hi", encoding="utf-8")
    r = project.read_files(str(tmp_path), ["big.txt", "small.txt"], total_cap=1000)
    assert r["truncated"] is True
    assert "big.txt" not in r["included"]   # เกิน cap ถูกข้าม


def test_read_files_rejects_binary_junk_without_null(tmp_path):
    # ไฟล์ที่ไม่ใช่ utf-8 และมี control char เยอะ (แต่ไม่มี null byte) → ต้องถูกข้าม
    (tmp_path / "blob.dat").write_bytes(bytes(range(1, 9)) * 600)
    r = project.read_files(str(tmp_path), ["blob.dat"])
    assert r["included"] == []
    assert any(s["path"] == "blob.dat" for s in r["skipped"])


def test_open_file_returns_content(tmp_path):
    (tmp_path / "a.py").write_text("print('hi')", encoding="utf-8")
    r = project.open_file(str(tmp_path), "a.py")
    assert r["content"] == "print('hi')"
    assert r["readonly"] is False


def test_open_file_binary_and_traversal(tmp_path):
    (tmp_path / "img.png").write_bytes(b"\x89PNG\x00")
    assert project.open_file(str(tmp_path), "img.png")["error"] == "binary"
    assert "outside" in project.open_file(str(tmp_path), "../x.txt")["error"]


def test_list_files_marks_image(tmp_path):
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n")
    (tmp_path / "a.py").write_text("x=1", encoding="utf-8")
    files = {f["path"]: f for f in project.list_files(str(tmp_path))}
    assert files["logo.png"]["image"] is True and files["logo.png"]["binary"] is True
    assert files["a.py"]["image"] is False


def test_read_image_returns_data_uri(tmp_path):
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    r = project.read_image(str(tmp_path), "logo.png")
    assert r["data_uri"].startswith("data:image/png;base64,")


def test_read_image_rejects_non_image_and_traversal(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    assert project.read_image(str(tmp_path), "a.py")["error"] == "not an image"
    assert "outside" in project.read_image(str(tmp_path), "../x.png")["error"]


def test_write_file_roundtrip_and_guard(tmp_path):
    (tmp_path / "a.py").write_text("old", encoding="utf-8")
    assert project.write_file(str(tmp_path), "a.py", "new content")["ok"] is True
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "new content"
    assert project.write_file(str(tmp_path), "../evil.txt", "x")["ok"] is False


def test_write_file_creates_parent_dirs(tmp_path):
    assert project.write_file(str(tmp_path), "deep/nested.py", "x")["ok"] is True
    assert (tmp_path / "deep" / "nested.py").read_text(encoding="utf-8") == "x"


def test_pick_context_paths_small_project():
    paths = ["a.py", "b.py"]
    assert project.pick_context_paths(paths) == ["a.py", "b.py"]


def test_pick_context_paths_prioritizes_open_and_mentioned():
    paths = [f"f{i}.py" for i in range(50)]
    paths.extend(["README.md", "main.py"])
    got = project.pick_context_paths(paths, open_path="f49.py", mentioned=["f10.py"], max_files=5)
    assert "f10.py" in got and "f49.py" in got and "README.md" in got
    assert len(got) == 5


def test_read_files_uses_overrides(tmp_path):
    (tmp_path / "a.py").write_text("on disk", encoding="utf-8")
    r = project.read_files(str(tmp_path), ["a.py"], overrides={"a.py": "from editor"})
    assert "from editor" in r["context"]
    assert "on disk" not in r["context"]
    _mkproject(tmp_path)
    r = project.read_files(str(tmp_path), ["../secret.txt"])
    assert r["included"] == []
    assert any("outside" in s["reason"] for s in r["skipped"])
