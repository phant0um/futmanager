#!/usr/bin/env python3
"""
FUTMANAGER — Launcher web primary.
Sobe servidor HTTP local e abre o navegador padrão.
Uso:  python3 launch_web.py
"""
from __future__ import annotations
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from web.server import PORT, Handler
from http.server import ThreadingHTTPServer


def _find_free_port(start: int = 8765) -> int:
    import socket
    for p in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start


def _open_browser(url: str) -> None:
    system = sys.platform
    if system == "darwin":
        import subprocess
        subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif system.startswith("linux"):
        import subprocess
        subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(url)


def _wait_for_server(url: str, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urlopen(url, timeout=1)
            return True
        except URLError:
            time.sleep(0.2)
    return False


def main() -> None:
    port = _find_free_port(PORT)
    url = f"http://127.0.0.1:{port}"
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    if not _wait_for_server(url):
        print(f"Servidor não respondeu em {url}", file=sys.stderr)
        server.shutdown()
        sys.exit(1)

    print(f"⚽ FUTMANAGER web em {url}  (Ctrl+C para sair)")
    _open_browser(url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
