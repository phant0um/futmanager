#!/bin/bash
# FUTMANAGER — abre a GUI nativa (Tkinter) sem empacotar.
cd "$(dirname "$0")"
exec python3 main.py "$@"
