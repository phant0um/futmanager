"""
FUTMANAGER — Gerência de saves (múltiplos jogos)
Cada save = 1 arquivo .db (cópia do mundo template). Permite vários jogos
independentes: a evolução do mundo de um save não afeta os outros.
"""
from __future__ import annotations
import re
import shutil
import sqlite3
from pathlib import Path

import paths


def _slug(name: str) -> str:
    s = re.sub(r"[^\w\- ]", "", name).strip().replace(" ", "_")
    return (s or "save")[:40]


def new_save(label: str) -> str:
    """Cria save: copia o template do mundo → saves/<slug>.db. Ativa-o. Retorna slug."""
    slug = _slug(label)
    dest = paths.saves_dir() / f"{slug}.db"
    n = 1
    base = slug
    while dest.exists():
        n += 1
        slug = f"{base}_{n}"
        dest = paths.saves_dir() / f"{slug}.db"
    shutil.copy2(paths.template_db(), dest)
    paths.set_active_save(slug)
    return slug


def list_saves() -> list[dict]:
    """Lista saves com metadados (clube, técnico, temporada, reputação)."""
    out = []
    active = paths.active_save_name()
    for f in sorted(paths.saves_dir().glob("*.db")):
        slug = f.stem
        meta = {"slug": slug, "active": slug == active, "mtime": f.stat().st_mtime,
                "club": "?", "coach": "?", "season": "?", "reputation": "?",
                "titles": 0, "seasons_played": 0}
        try:
            c = sqlite3.connect(f)
            c.row_factory = sqlite3.Row
            car = c.execute(
                "SELECT * FROM career WHERE status IN ('active','sacked') ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
            if car:
                club = c.execute("SELECT name FROM clubs WHERE id=?", (car["manager_club_id"],)).fetchone()
                coach = c.execute("SELECT name FROM coaches WHERE career_id=? AND is_player=1",
                                  (car["id"],)).fetchone()
                meta.update({
                    "club": club["name"] if club else "?",
                    "coach": coach["name"] if coach else "?",
                    "season": car["season_year"],
                    "reputation": car["reputation"],
                    "titles": car["titles"],
                    "seasons_played": car["seasons_played"],
                    "status": car["status"],
                })
            c.close()
        except Exception:
            pass
        out.append(meta)
    out.sort(key=lambda m: m["mtime"], reverse=True)
    return out


def load_save(slug: str) -> bool:
    if (paths.saves_dir() / f"{slug}.db").exists():
        paths.set_active_save(slug)
        return True
    return False


def delete_save(slug: str) -> bool:
    f = paths.saves_dir() / f"{slug}.db"
    if f.exists():
        f.unlink()
        if paths.active_save_name() == slug:
            paths.set_active_save(None)
        return True
    return False


def active_save() -> str | None:
    return paths.active_save_name()
