import fusefable.history as h


def _tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(h, "history_dir", lambda: tmp_path / "history")


def test_new_save_load_roundtrip(monkeypatch, tmp_path):
    _tmp(monkeypatch, tmp_path)
    conv = h.new_conversation("My chat", now=1000.0)
    conv["messages"].append({"role": "user", "content": "hi"})
    h.save_conversation(conv)
    got = h.load_conversation(conv["id"])
    assert got["title"] == "My chat"
    assert got["messages"][0]["content"] == "hi"


def test_list_sorted_newest_first(monkeypatch, tmp_path):
    _tmp(monkeypatch, tmp_path)
    a = h.new_conversation("old", now=10.0)
    h.save_conversation(a)
    b = h.new_conversation("new", now=99.0)
    h.save_conversation(b)
    items = h.list_conversations()
    assert [i["title"] for i in items] == ["new", "old"]


def test_delete(monkeypatch, tmp_path):
    _tmp(monkeypatch, tmp_path)
    c = h.new_conversation("x", now=1.0)
    h.save_conversation(c)
    h.delete_conversation(c["id"])
    assert h.load_conversation(c["id"]) is None


def test_derive_title_truncates():
    assert h.derive_title("hello world") == "hello world"
    assert h.derive_title("x" * 60).endswith("…")
    assert h.derive_title("") == "New chat"
