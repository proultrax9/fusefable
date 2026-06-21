def test_desktop_server_health():
    import threading
    from fusefable.desktop_server import run_server
    import urllib.request
    import json

    srv = run_server("127.0.0.1", 0)
    port = srv.server_address[1]
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as r:
            data = json.loads(r.read().decode())
        assert data.get("ok") is True
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=2) as r:
            st = json.loads(r.read().decode())
        assert "configured" in st
    finally:
        srv.shutdown()
