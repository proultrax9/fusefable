def test_web_module_imports_and_has_html():
    import fusefable.web as web
    assert "Fusion Fable" in web.INDEX_HTML
    assert "workbench" in web.INDEX_HTML
    assert "panelChat" in web.INDEX_HTML
    assert "panelEditor" in web.INDEX_HTML
    assert "sashExplorer" in web.INDEX_HTML
    assert "\x00" not in web.INDEX_HTML
    assert "pywebview.api" in web.INDEX_HTML


def test_web_source_has_no_null_bytes():
    import fusefable.web as web
    raw = open(web.__file__, "rb").read()
    assert raw.count(b"\x00") == 0
