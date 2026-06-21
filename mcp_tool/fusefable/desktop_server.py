"""HTTP API for Fusion Fable desktop shell (Electron / any UI).

Wraps the same logic as fusefable.desktop.Api — no pywebview required.
"""
from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import unquote

from fusefable.desktop import Api, _load_or_default


def _test_models(api: Api) -> dict:
    """ทดสอบยิงโมเดลทีละตัว — ใช้ debug ใน Settings."""
    import asyncio
    import httpx
    from fusefable.routing import build_routes
    from fusefable.client import call_model

    cfg = api.cfg
    out = []

    async def run():
        async with httpx.AsyncClient(timeout=60) as http:
            routes = build_routes(cfg, http)
            for prov, model in routes:
                c = await call_model(prov, model, "Reply with exactly: OK", 60)
                out.append({
                    "model": model,
                    "ok": not c.is_error,
                    "error": c.error if c.is_error else "",
                    "sample": (c.text or "")[:80] if not c.is_error else "",
                })

    asyncio.run(run())
    ok_n = sum(1 for r in out if r["ok"])
    return {"results": out, "ok": ok_n, "total": len(out)}


def _json_response(handler: BaseHTTPRequestHandler, status: int, data: object) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


class DesktopHandler(BaseHTTPRequestHandler):
    api: Api

    def log_message(self, fmt: str, *args) -> None:  # noqa: ARG002
        pass

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def do_GET(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        if path == "/api/health":
            return _json_response(self, 200, {"ok": True})
        if path == "/api/status":
            return _json_response(self, 200, self.api.get_status())
        if path == "/api/test_models":
            return _json_response(self, 200, _test_models(self.api))
        if path == "/api/conversations":
            return _json_response(self, 200, self.api.list_conversations())
        m = re.fullmatch(r"/api/conversations/([^/]+)", path)
        if m:
            conv = self.api.load_conversation(m.group(1))
            return _json_response(self, 200, conv)
        _json_response(self, 404, {"error": "not found"})

    def do_DELETE(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        m = re.fullmatch(r"/api/conversations/([^/]+)", path)
        if m:
            self.api.delete_conversation(m.group(1))
            return _json_response(self, 200, {"ok": True})
        _json_response(self, 404, {"error": "not found"})

    def do_POST(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        body = self._read_json()
        try:
            if path == "/api/ask":
                return _json_response(self, 200, self.api.ask(body))
            if path == "/api/list_files":
                return _json_response(self, 200, self.api.list_files(body["path"]))
            if path == "/api/read_context":
                return _json_response(self, 200, self.api.read_context(body))
            if path == "/api/open_file":
                return _json_response(self, 200, self.api.open_file(body))
            if path == "/api/read_image":
                return _json_response(self, 200, self.api.read_image(body))
            if path == "/api/save_file":
                return _json_response(self, 200, self.api.save_file(body))
            if path == "/api/settings":
                return _json_response(self, 200, self.api.save_settings(body))
            if path == "/api/open_project":
                root = body.get("path", "")
                if not root:
                    return _json_response(self, 400, {"error": "path required"})
                listed = self.api.list_files(root)
                if listed.get("error"):
                    return _json_response(self, 400, listed)
                return _json_response(self, 200, {"path": root, "files": listed.get("files", [])})
        except Exception as e:  # noqa: BLE001
            return _json_response(self, 500, {"error": str(e)})
        _json_response(self, 404, {"error": "not found"})


def run_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    cfg = _load_or_default()
    api = Api(cfg)
    DesktopHandler.api = api
    server = ThreadingHTTPServer((host, port), DesktopHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Fusion Fable desktop API server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    cfg = _load_or_default()
    DesktopHandler.api = Api(cfg)
    server = ThreadingHTTPServer((args.host, args.port), DesktopHandler)
    print(f"Fusion Fable API http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
