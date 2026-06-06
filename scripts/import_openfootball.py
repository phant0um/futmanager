"""
FUTMANAGER — OpenFootball Importer
Pulls data from openfootball GitHub repos and populates SQLite.

Usage:
    python scripts/import_openfootball.py --league br --season 2025
    python scripts/import_openfootball.py --all
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import subprocess
import sys
import os
from pathlib import Path

# ─── Configuração ────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
SOURCES_DIR = DATA_DIR / "sources" / "openfootball"
DB_PATH = DATA_DIR / "futmanager.db"

# Repos OpenFootball disponíveis (verificados)
# Nota: france repo contém FR, NL, PT; brazil repo contém BR, AR
LEAGUE_REPOS = {
    "br":  "https://github.com/openfootball/brazil.git",
    "en":  "https://github.com/openfootball/england.git",
    "es":  "https://github.com/openfootball/espana.git",
    "it":  "https://github.com/openfootball/italy.git",
    "fr":  "https://github.com/openfootball/france.git",
    # NL e PT usam o mesmo repo "france"
    "nl":  "https://github.com/openfootball/france.git",
    "pt":  "https://github.com/openfootball/france.git",
    # AR usa o repo "brazil"
    "ar":  "https://github.com/openfootball/brazil.git",
    # Série B do Brasileirão (repo brazil)
    "br_b": "https://github.com/openfootball/brazil.git",
}

# Alias de pasta local: nl e pt compartilham o repo "fr"; ar e br_b compartilham "br"
REPO_LOCAL_ALIAS = {
    "nl": "fr",
    "pt": "fr",
    "ar": "br",
    "br_b": "br",
}

PLAYERS_REPO = "https://github.com/openfootball/players.git"

# file_path_tpl: path relativo dentro do repo clonado
# {season} = "2025", {s2} = "25-26", {s2prev} = "24-25"
LEAGUE_META = {
    "br": {"name": "Brasileirão Série A",   "country": "BR", "level": 1,
           "file_tpl": "brazil/{season}_br1.txt"},
    "en": {"name": "Premier League",         "country": "EN", "level": 1,
           "file_tpl": "{s2}/1-premierleague.txt"},
    "es": {"name": "La Liga",                "country": "ES", "level": 1,
           "file_tpl": "{s2}/1-liga.txt"},
    "it": {"name": "Serie A",                "country": "IT", "level": 1,
           "file_tpl": "{s2}/1-seriea.txt"},
    "fr": {"name": "Ligue 1",                "country": "FR", "level": 1,
           "file_tpl": "france/{s2}_fr1.txt"},
    "nl": {"name": "Eredivisie",             "country": "NL", "level": 1,
           "file_tpl": "netherlands/{s2}_nl1.txt"},
    "pt": {"name": "Primeira Liga",          "country": "PT", "level": 1,
           "file_tpl": "portugal/{s2}_pt1.txt"},
    "ar": {"name": "Primera División (ARG)", "country": "AR", "level": 1,
           "file_tpl": "argentina/{season}_ar1.txt"},
    "br_b": {"name": "Brasileirão Série B",  "country": "BR", "level": 2,
             "file_tpl": "brazil/{season}_br2.txt"},
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection):
    schema = (ROOT / "db" / "schema.sql").read_text()
    conn.executescript(schema)
    conn.commit()


def clone_or_pull(url: str, dest: Path):
    if dest.exists():
        print(f"  pull {dest.name}...")
        subprocess.run(["git", "-C", str(dest), "pull", "--quiet"], check=False)
    else:
        print(f"  clone {dest.name}...")
        result = subprocess.run(["git", "clone", "--depth=1", "--quiet", url, str(dest)])
        if result.returncode != 0:
            print(f"  ⚠ clone falhou para {url}")


def upsert_country(conn: sqlite3.Connection, code: str, name: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO countries(code, name) VALUES (?, ?)", (code, name)
    )
    return conn.execute("SELECT id FROM countries WHERE code=?", (code,)).fetchone()[0]


def upsert_league(conn: sqlite3.Connection, key: str, season: str) -> int:
    meta = LEAGUE_META[key]
    country_id = upsert_country(conn, meta["country"], meta["country"])
    conn.execute("""
        INSERT OR IGNORE INTO leagues(name, country_id, level, season)
        VALUES (?, ?, ?, ?)
    """, (meta["name"], country_id, meta["level"], season))
    conn.commit()
    return conn.execute(
        "SELECT id FROM leagues WHERE name=? AND season=?", (meta["name"], season)
    ).fetchone()[0]


def upsert_club(conn: sqlite3.Connection, name: str, league_id: int,
                prestige: int = 60) -> int:
    conn.execute("""
        INSERT OR IGNORE INTO clubs(name, league_id, prestige)
        VALUES (?, ?, ?)
    """, (name, league_id, prestige))
    conn.commit()
    return conn.execute(
        "SELECT id FROM clubs WHERE name=? AND league_id=?", (name, league_id)
    ).fetchone()[0]


# ─── Parsers de formato Football.TXT ─────────────────────────────────────────

import re

# Formato OpenFootball para partidas:
# "  HH:MM  Home Team Name            v Away Team Name        X-X (X-X)"
# "         Home Team Name            v Away Team Name        X-X"
# ou sem placar (jogo futuro):
# "  HH:MM  Home Team Name            v Away Team Name"

# Regex: captura home, away e placar (opcional)
# O separador entre times é sempre " v " (com espaços)
_RE_MATCH = re.compile(
    r"""
    ^\s*                          # indentação
    (?:\d{1,2}:\d{2}\s+)?        # horário opcional HH:MM
    (.+?)\s+                     # home team (greedy até 'v')
    \bv\b\s+                     # separador literal 'v'
    (.+?)                        # away team
    (?:\s+(\d+)-(\d+)            # placar X-X (opcional)
       (?:\s+\(\d+-\d+\))?       # parcial (1-0) opcional
    )?
    (?:\s+\[[\w\s]+\])?          # anotações tipo [postponed] [cancelled] — ignora
    \s*$
    """,
    re.VERBOSE,
)

_RE_MATCHDAY = re.compile(
    r"(?:Matchday|Round|Rodada|Jornada|▪\s*Matchday)\s*(\d+)",
    re.IGNORECASE,
)


def parse_football_txt(path: Path) -> dict:
    """
    Parseia formato Football.TXT do OpenFootball.
    Formato real:
        ▪ Matchday 1
          Sat Mar 29 2025
            18:30  São Paulo FC    v SC Recife          0-0
                   Cruzeiro EC     v Mirassol FC        2-1 (2-1)
    """
    clubs: set[str] = set()
    matches: list[dict] = []
    current_round = None

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            raw = line.rstrip()

            # Linha vazia ou comentário
            stripped = raw.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("="):
                continue

            # Rodada / Matchday
            md = _RE_MATCHDAY.search(stripped)
            if md:
                current_round = int(md.group(1))
                continue

            # Linha de data pura (ex: "  Sat Mar 29 2025") → ignora
            if re.match(r"^\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", raw):
                continue

            # Tenta parsear partida
            m = _RE_MATCH.match(raw)
            if not m:
                continue

            home = m.group(1).strip()
            away = m.group(2).strip()

            # Filtra lixo: times com < 2 chars ou que sejam só datas
            if len(home) < 2 or len(away) < 2:
                continue
            if re.match(r"^\d+$", home) or re.match(r"^\d+$", away):
                continue

            clubs.add(home)
            clubs.add(away)

            if m.group(3) is not None:  # tem placar
                matches.append({
                    "round": current_round,
                    "home": home,
                    "away": away,
                    "home_goals": int(m.group(3)),
                    "away_goals": int(m.group(4)),
                })

    return {"clubs": list(clubs), "matches": matches}


def _s2(season: str) -> str:
    """'2026' → '2025-26' (temporadas europeias ago-mai, full year)"""
    y = int(season)
    return f"{y-1}-{str(y)[-2:]}"


def _s2prev(season: str) -> str:
    """'2026' → '2024-25' (temporada anterior para UCL)"""
    y = int(season)
    return f"{y-2}-{str(y-1)[-2:]}"


def _resolve_file(key: str, season: str) -> Path | None:
    """
    Resolve path absoluto do arquivo de dados para a liga+temporada.
    Tenta a temporada atual e fallback para anterior se não encontrar.
    """
    meta = LEAGUE_META[key]
    local_alias = REPO_LOCAL_ALIAS.get(key, key)
    repo_dir = SOURCES_DIR / local_alias

    if not repo_dir.exists():
        return None

    tpl = meta["file_tpl"]

    def try_path(s: str, s2: str, s2p: str) -> Path | None:
        rel = tpl.replace("{season}", s).replace("{s2}", s2).replace("{s2prev}", s2p)
        p = repo_dir / rel
        return p if p.exists() else None

    # Tenta temporada atual
    p = try_path(season, _s2(season), _s2prev(season))
    if p:
        return p

    # Fallback: temporada anterior (algumas ligas atrasam upload)
    prev = str(int(season) - 1)
    p = try_path(prev, _s2(prev), _s2prev(prev))
    if p:
        print(f"  ⚠ usando temporada {prev} (arquivo {season} não encontrado)")
        return p

    return None


def import_league(conn: sqlite3.Connection, key: str, season: str):
    """Importa uma liga do OpenFootball — apenas o arquivo da temporada correta."""
    if key not in LEAGUE_REPOS:
        print(f"  Liga '{key}' não suportada.")
        return

    # Clona repo (usa alias se compartilhado)
    local_alias = REPO_LOCAL_ALIAS.get(key, key)
    repo_dir = SOURCES_DIR / local_alias
    clone_or_pull(LEAGUE_REPOS[key], repo_dir)

    txt_file = _resolve_file(key, season)
    if not txt_file:
        print(f"  ⚠ '{key}' season {season}: arquivo não encontrado.")
        return

    print(f"  Arquivo: {txt_file.relative_to(SOURCES_DIR)}")

    league_id = upsert_league(conn, key, season)
    data = parse_football_txt(txt_file)

    clubs_inserted = set()
    for club_name in data["clubs"]:
        upsert_club(conn, club_name, league_id)
        clubs_inserted.add(club_name)

    matches_inserted = 0
    for match in data["matches"]:
        home_row = conn.execute("SELECT id FROM clubs WHERE name=?", (match["home"],)).fetchone()
        away_row = conn.execute("SELECT id FROM clubs WHERE name=?", (match["away"],)).fetchone()
        if home_row and away_row:
            conn.execute("""
                INSERT OR IGNORE INTO matches(home_id, away_id, home_goals, away_goals, played)
                VALUES (?, ?, ?, ?, 1)
            """, (home_row[0], away_row[0], match["home_goals"], match["away_goals"]))
            matches_inserted += 1

    conn.commit()
    print(f"  ✓ {key}: {len(clubs_inserted)} clubes, {matches_inserted} partidas")


def import_players(conn: sqlite3.Connection):
    """Importa jogadores básicos do repo openfootball/players."""
    players_dir = SOURCES_DIR / "players"
    clone_or_pull(PLAYERS_REPO, players_dir)

    inserted = 0
    for txt_file in players_dir.rglob("*.txt"):
        import re
        with open(txt_file, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Formato: "Name, Position, DOB, Birthplace"
                # ou variações
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    name = parts[0]
                    pos_raw = parts[1].upper() if len(parts) > 1 else "MF"
                    pos_map = {"G": "GK", "D": "DF", "M": "MF", "F": "FW",
                               "GK": "GK", "DF": "DF", "MF": "MF", "FW": "FW"}
                    pos = pos_map.get(pos_raw[:2], "MF")
                    dob = parts[2] if len(parts) > 2 else None

                    conn.execute("""
                        INSERT OR IGNORE INTO players(name, position, birth_date, source)
                        VALUES (?, ?, ?, 'openfootball')
                    """, (name, pos, dob))
                    inserted += 1

    conn.commit()
    print(f"  ✓ players: {inserted} jogadores importados")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Import OpenFootball data")
    parser.add_argument("--league", choices=list(LEAGUE_REPOS.keys()),
                        help="Liga específica para importar")
    parser.add_argument("--all", action="store_true", help="Importa todas as ligas")
    parser.add_argument("--players", action="store_true", help="Importa jogadores")
    parser.add_argument("--season", default="2025", help="Temporada (ex: 2025)")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    if args.all:
        for key in LEAGUE_REPOS:
            print(f"\nImportando {key}...")
            import_league(conn, key, args.season)
    elif args.league:
        print(f"\nImportando {args.league}...")
        import_league(conn, args.league, args.season)

    if args.players:
        print("\nImportando jogadores...")
        import_players(conn)

    if not args.all and not args.league and not args.players:
        parser.print_help()

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
