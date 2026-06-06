#!/usr/bin/env python3
"""
FUTMANAGER — Entry point.

  python3 main.py          → GUI nativa (Tkinter)   [padrão]
  python3 main.py --cli    → modo terminal
  python3 main.py --web    → servidor web local + browser
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--cli":
        from ui.cli import run
        run()
    elif arg == "--web":
        from web.server import main as web_main
        web_main()
    else:
        from gui.app import main as gui_main
        gui_main()
