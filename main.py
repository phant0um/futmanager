#!/usr/bin/env python3
"""
FUTMANAGER — Entry point.

  python3 main.py          → servidor web local + browser   [padrão]
  python3 main.py --gui    → GUI nativa compacta (Tkinter)
  python3 main.py --cli    → modo terminal
  python3 main.py --web    → servidor web (sem auto-abrir browser)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--cli":
        from ui.cli import run
        run()
    elif arg == "--gui":
        from gui.app import main as gui_main
        gui_main()
    elif arg == "--web":
        from web.server import main as web_main
        web_main()
    else:
        from launch_web import main as web_launch_main
        web_launch_main()
