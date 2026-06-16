#!/bin/bash
# FUTMANAGER — modo web principal (sobe servidor + abre navegador)
cd "$(dirname "$0")"
exec python3 launch_web.py "$@"
