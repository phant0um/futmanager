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
                     api_next, api_play, create_career, api_saves, save_load, save_delete,
                     api_set_market_status, api_player_detail, api_lineup, save_lineup, auto_lineup_ids,
                     play_round_live, api_finance, api_stadium, save_stadium, api_market,
                     api_buy, api_player_terms, api_finalize_transfer, api_incoming_offers,
                     api_respond_offer, api_search_clubs, api_club_squad, api_scout_players,
                     api_match_history, api_table_by_comp, get_active_career)

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
            if p == "/api/lineup":
                return self._json(api_lineup(c))
            if p == "/api/leagues":
                return self._json(api_leagues(c))
            if p == "/api/clubs":
                return self._json(api_clubs(c, int(q.get("league", [0])[0])))
            if p == "/api/table":
                return self._json(api_table_by_comp(c, q.get("comp", ["league"])[0]))
            if p == "/api/player_stats":
                from engine.stats import get_top_stats
                car = get_active_career(c)
                return self._json({"players": get_top_stats(c, car["season_year"], q.get("comp", ["league"])[0],
                                                              int(q.get("limit", ["20"])[0])),
                                   "comp": q.get("comp", ["league"])[0],
                                   "season": car["season_year"] if car else 0})
            if p == "/api/saves":
                return self._json(api_saves())
            if p == "/api/next":
                return self._json(api_next(c))
            if p == "/api/finance":
                return self._json(api_finance(c))
            if p == "/api/stadium":
                return self._json(api_stadium(c))
            if p == "/api/market":
                return self._json(api_market(c, position=q.get("position", [None])[0],
                                            max_price=int(q["max_price"][0]) if q.get("max_price") else None,
                                            min_ovr=int(q.get("min_ovr", [0])[0]),
                                            max_ovr=int(q.get("max_ovr", [99])[0]),
                                            only_transfer=bool(q.get("only_transfer", [False])[0]),
                                            limit=int(q.get("limit", [200])[0])))
            if p == "/api/search-clubs":
                return self._json(api_search_clubs(c, q.get("term", [""])[0]))
            if p == "/api/club-squad":
                return self._json(api_club_squad(c, int(q["id"][0])))
            if p == "/api/scout":
                return self._json(api_scout_players(c, min_ovr=int(q.get("min_ovr", [60])[0]),
                                                    max_ovr=int(q.get("max_ovr", [99])[0]),
                                                    position=q.get("position", [None])[0],
                                                    max_price=int(q["max_price"][0]) if q.get("max_price") else None,
                                                    max_age=int(q.get("max_age", [40])[0]),
                                                    nationality=q.get("nationality", [None])[0],
                                                    sort_by=q.get("sort_by", ["pot"])[0],
                                                    limit=int(q.get("limit", [100])[0])))
            if p == "/api/history":
                return self._json(api_match_history(c, limit=int(q.get("limit", [30])[0])))
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
        if u.path == "/api/play/live":
            c = conn()
            try:
                return self._json(play_round_live(c))
            finally:
                c.close()
        if u.path == "/api/stadium/save":
            c = conn()
            try:
                return self._json(save_stadium(c, body.get("price"), body.get("training"), body.get("focus")))
            finally:
                c.close()
        if u.path == "/api/market/buy":
            c = conn()
            try:
                return self._json(api_buy(c, int(body.get("player_id")), int(body.get("price"))))
            finally:
                c.close()
        if u.path == "/api/market/terms":
            c = conn()
            try:
                return self._json(api_player_terms(c, int(body.get("player_id")), int(body.get("fee"))))
            finally:
                c.close()
        if u.path == "/api/market/finalize":
            c = conn()
            try:
                return self._json(api_finalize_transfer(c, int(body.get("player_id")), int(body.get("fee"), int(body.get("wage")))))
            finally:
                c.close()
        if u.path == "/api/market/respond":
            c = conn()
            try:
                return self._json(api_respond_offer(c, int(body.get("player_id")), int(body.get("club_id")), body.get("accept")))
            finally:
                c.close()
        if u.path == "/api/play":
            c = conn()
            try:
                return self._json(api_play(c))
            finally:
                c.close()
        if u.path == "/api/player/market":
            c = conn()
            try:
                return self._json(api_set_market_status(c, int(body.get("player_id")), body.get("status", "none")))
            finally:
                c.close()
        if u.path == "/api/lineup/save":
            c = conn()
            try:
                return self._json(save_lineup(c, body.get("formation"), body.get("style"),
                                              body.get("xi", []), body.get("positions", {})))
            finally:
                c.close()
        if u.path == "/api/lineup/auto":
            c = conn()
            try:
                xi = auto_lineup_ids(c, body.get("formation"),
                                     skip_fatigue_above=body.get("skip_fatigue_above"),
                                     skip_form_below=body.get("skip_form_below"))
                return self._json({"ok": True, "xi": xi})
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
