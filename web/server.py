"""
FUTMANAGER — Web Frontend (HTTP + API JSON). Shim sobre gameapi.
Lógica de jogo vive em gameapi.py (compartilhada com a GUI Tkinter).
Uso:  python3 web/server.py   → abre http://localhost:8765
"""
from __future__ import annotations
import json
import sys
import webbrowser
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import gameapi as G
from gameapi import (conn, api_state, api_squad, api_leagues, api_clubs, api_table,
                     api_next, api_play, create_career, api_saves, save_load, save_delete)

STATIC = Path(__file__).parent / "static"
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, ctype):
        if not path.exists():
            self.send_response(404); self.end_headers(); return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        q = parse_qs(u.query)
        c = conn()
        try:
            if p in ("/", "/index.html"):
                return self._file(STATIC / "index.html", "text/html; charset=utf-8")
            if p == "/style.css":
                return self._file(STATIC / "style.css", "text/css")
            if p == "/app.js":
                return self._file(STATIC / "app.js", "application/javascript")
            if p == "/api/state":
                return self._json(api_state(c))
            if p == "/api/squad":
                return self._json(api_squad(c))
            if p == "/api/leagues":
                return self._json(api_leagues(c))
            if p == "/api/clubs":
                return self._json(api_clubs(c, int(q.get("league", [0])[0])))
            if p == "/api/table":
                return self._json(api_table(c))
            if p == "/api/saves":
                return self._json(api_saves())
            if p == "/api/next":
                return self._json(api_next(c))
            self.send_response(404); self.end_headers()
        finally:
            c.close()

    def do_POST(self):
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if u.path == "/api/career/new":
            return self._json(create_career(int(body.get("club_id")), body.get("coach_name", "")))
        if u.path == "/api/save/load":
            return self._json(save_load(body.get("slug")))
        if u.path == "/api/save/delete":
            return self._json(save_delete(body.get("slug")))
        if u.path == "/api/play":
            c = conn()
            try:
                return self._json(api_play(c))
            finally:
                c.close()
        self.send_response(404); self.end_headers()


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"⚽ FUTMANAGER web em {url}  (Ctrl+C para sair)")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando.")
        srv.shutdown()


if __name__ == "__main__":
    main()
