#!/bin/bash
# FUTMANAGER — modo desktop compacto (Tkinter) - fallback offline
cd "$(dirname "$0")"
exec python3 main.py --gui "$@"
