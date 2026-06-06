"""
FUTMANAGER — CLI Interface (Fase 1)
Terminal-based UI for the football manager game.
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from paths import db_path, is_frozen


def _load_engine():
    from engine.season import League
    from engine.simulation import simulate_match
    from db.models import Club, Player
    return League, simulate_match, Club, Player


def _get_conn():
    if not db_path().exists():
        print("❌ Database não encontrada. Rode: python data/update.py")
        sys.exit(1)
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


# ─── Telas ───────────────────────────────────────────────────────────────────

def clear():
    import os
    os.system("clear" if os.name != "nt" else "cls")


def header(title: str):
    print(f"\n{'━'*55}")
    print(f"  ⚽  FUTMANAGER — {title}")
    print(f"{'━'*55}")


def menu_principal() -> str:
    header("MENU PRINCIPAL")
    print("""
  1. ⚽  MODO CARREIRA  (gerir clube por temporadas)
  ──────────────────────────────────────────
  2. Ver ligas disponíveis
  3. Simular temporada (avulsa)
  4. Simular partida rápida
  5. Ver classificação
  6. Ver jogadores de um clube
  7. Atualizar database
  0. Sair
""")
    return input("  Opção: ").strip()


def listar_ligas(conn: sqlite3.Connection):
    header("LIGAS")
    rows = conn.execute("""
        SELECT l.id, l.name, l.season, c.name as country,
               COUNT(cl.id) as n_clubs
        FROM leagues l
        LEFT JOIN countries c ON c.id = l.country_id
        LEFT JOIN clubs cl ON cl.league_id = l.id
        GROUP BY l.id
        ORDER BY c.name, l.level
    """).fetchall()

    if not rows:
        print("\n  Nenhuma liga encontrada. Rode: python data/update.py --skip-kaggle")
        return

    print(f"\n  {'ID':>4}  {'Liga':<30} {'País':<5} {'Temp':<7} {'Clubes':>6}")
    print(f"  {'─'*55}")
    for r in rows:
        print(f"  {r['id']:>4}  {r['name']:<30} {r['country']:<5} {r['season']:<7} {r['n_clubs']:>6}")


def _load_clubs_for_league(conn: sqlite3.Connection, league_id: int):
    """Carrega clubes com elencos para simulação."""
    League, simulate_match, Club, Player = _load_engine()

    clubs_rows = conn.execute(
        "SELECT * FROM clubs WHERE league_id=?", (league_id,)
    ).fetchall()

    clubs = []
    for r in clubs_rows:
        players_rows = conn.execute(
            "SELECT * FROM players WHERE club_id=?", (r["id"],)
        ).fetchall()

        players = [Player(
            id=p["id"], name=p["name"], position=p["position"] or "MF",
            nationality=p["nationality"] or "", birth_date=p["birth_date"],
            club_id=p["club_id"],
            pace=p["pace"], technique=p["technique"], strength=p["strength"],
            finishing=p["finishing"], passing=p["passing"], defending=p["defending"],
            goalkeeping=p["goalkeeping"], stamina=p["stamina"], mental=p["mental"],
            overall=p["overall"], source=p["source"] or "generated",
        ) for p in players_rows]

        club = Club(
            id=r["id"], name=r["name"],
            short_name=r["short_name"] or r["name"][:3].upper(),
            league_id=r["league_id"], prestige=r["prestige"],
        )
        club.players = players

        # Se clube sem jogadores, gera mock
        if not players:
            club = _mock_club(club, League, Player)

        clubs.append(club)

    return clubs, League


def _mock_club(club, League, Player):
    """Gera elenco mock para clubes sem jogadores na DB."""
    import random, hashlib
    positions = ["GK"] + ["DF"]*4 + ["MF"]*4 + ["FW"]*3
    players = []
    for i, pos in enumerate(positions):
        pid = int(hashlib.md5(f"{club.id}:{i}".encode()).hexdigest(), 16) % 100000
        rng = random.Random(pid)
        base = club.prestige
        p = Player(
            id=pid, name=f"Jogador {i+1}", position=pos,
            nationality="BR", birth_date="1998-01-01",
            club_id=club.id,
            pace=rng.randint(base-15, base+15),
            technique=rng.randint(base-15, base+15),
            strength=rng.randint(base-10, base+10),
            finishing=rng.randint(base-15, base+15),
            passing=rng.randint(base-15, base+15),
            defending=rng.randint(base-10, base+10),
            goalkeeping=rng.randint(base-15, base+15) if pos == "GK" else 30,
            stamina=rng.randint(base-10, base+10),
            mental=rng.randint(base-10, base+10),
            overall=base + rng.randint(-10, 10),
        )
        players.append(p)
    club.players = players
    return club


def simular_temporada(conn: sqlite3.Connection):
    header("SIMULAR TEMPORADA")
    listar_ligas(conn)
    try:
        league_id = int(input("\n  ID da liga: ").strip())
    except ValueError:
        return

    league_row = conn.execute("SELECT * FROM leagues WHERE id=?", (league_id,)).fetchone()
    if not league_row:
        print("  Liga não encontrada.")
        return

    clubs, LeagueEngine = _load_clubs_for_league(conn, league_id)
    if len(clubs) < 2:
        print(f"  Poucos clubes ({len(clubs)}). Importe dados primeiro.")
        return

    print(f"\n  Liga: {league_row['name']} | {len(clubs)} clubes")
    print("  Simulando temporada completa...")

    league = LeagueEngine(league_row["name"], clubs, league_row["season"])
    league.simulate_all()
    league.print_table()

    top3 = league.top(3)
    rel = league.bottom(3)
    print(f"  🏆 Campeão: {top3[0].club_name}")
    print(f"  🥈 2º: {top3[1].club_name}")
    print(f"  🥉 3º: {top3[2].club_name}")
    print(f"\n  ⬇️  Rebaixados: {', '.join(s.club_name for s in rel)}")


def partida_rapida(conn: sqlite3.Connection):
    header("PARTIDA RÁPIDA")
    _, simulate_match, Club, Player = _load_engine()

    listar_ligas(conn)
    try:
        league_id = int(input("\n  ID da liga: ").strip())
    except ValueError:
        return

    clubs, _ = _load_clubs_for_league(conn, league_id)
    if len(clubs) < 2:
        print("  Poucos clubes.")
        return

    print("\n  Clubes disponíveis:")
    for i, c in enumerate(clubs[:20], 1):
        print(f"  {i:>2}. {c.name}")

    try:
        hi = int(input("\n  Nº time da casa: ").strip()) - 1
        ai = int(input("  Nº time visitante: ").strip()) - 1
        home = clubs[hi]
        away = clubs[ai]
    except (ValueError, IndexError):
        print("  Seleção inválida.")
        return

    modo = input("\n  [Enter] resultado rápido   ·   [a] assistir ao vivo: ").strip().lower()
    if modo == "a":
        from engine.live import play_live
        play_live(home, away, spm=1.3)
        return

    result = simulate_match(home, away)
    print(f"\n  {'─'*45}")
    print(f"  {home.name:<20} {result.home_goals} x {result.away_goals}  {away.name}")
    print(f"  {'─'*45}")
    for event in result.events:
        print(f"  {event}")
    print(f"  {'─'*45}")


def ver_classificacao(conn: sqlite3.Connection):
    header("CLASSIFICAÇÃO")
    listar_ligas(conn)
    try:
        league_id = int(input("\n  ID da liga: ").strip())
    except ValueError:
        return

    rows = conn.execute("""
        SELECT cl.name, s.played, s.wins, s.draws, s.losses,
               s.gf, s.ga, s.points
        FROM standings s
        JOIN clubs cl ON cl.id = s.club_id
        WHERE cl.league_id = ?
        ORDER BY s.points DESC, (s.gf - s.ga) DESC
    """, (league_id,)).fetchall()

    if not rows:
        print("\n  Nenhuma classificação. Simule uma temporada primeiro.")
        return

    print(f"\n  {'#':>2}  {'Clube':<25} {'J':>3} {'V':>3} {'E':>3} {'D':>3} {'GP':>3} {'GC':>3} {'Pts':>4}")
    print(f"  {'─'*55}")
    for i, r in enumerate(rows, 1):
        gd = r["gf"] - r["ga"]
        print(f"  {i:>2}. {r['name']:<25} {r['played']:>3} {r['wins']:>3} "
              f"{r['draws']:>3} {r['losses']:>3} {r['gf']:>3} {r['ga']:>3} {r['points']:>4}")


def ver_jogadores(conn: sqlite3.Connection):
    header("ELENCO DE CLUBE")
    query = input("  Nome do clube (parcial): ").strip()
    if not query:
        return

    matches = conn.execute(
        "SELECT id, name FROM clubs WHERE name LIKE ? ORDER BY name LIMIT 10",
        (f"%{query}%",)
    ).fetchall()

    if not matches:
        print("  Clube não encontrado.")
        return
    if len(matches) == 1:
        club_id = matches[0]["id"]
    else:
        print()
        for i, m in enumerate(matches, 1):
            print(f"  {i}. {m['name']}")
        try:
            idx = int(input("\n  Escolha: ").strip()) - 1
            club_id = matches[idx]["id"]
        except (ValueError, IndexError):
            return

    club = conn.execute("SELECT * FROM clubs WHERE id=?", (club_id,)).fetchone()
    if not club:
        print("  Clube não encontrado.")
        return

    players = conn.execute("""
        SELECT name, position, nationality, overall,
               pace, technique, finishing, passing, defending
        FROM players WHERE club_id=?
        ORDER BY CASE position WHEN 'GK' THEN 1 WHEN 'DF' THEN 2
                               WHEN 'MF' THEN 3 WHEN 'FW' THEN 4 END,
                 overall DESC
    """, (club_id,)).fetchall()

    print(f"\n  {club['name']} (prestige: {club['prestige']})")
    print(f"\n  {'Nome':<25} {'Pos':<4} {'Nac':<4} {'OVR':>4} {'PAC':>4} {'TEC':>4} {'FIN':>4} {'PAS':>4} {'DEF':>4}")
    print(f"  {'─'*65}")
    for p in players:
        print(f"  {p['name']:<25} {p['position'] or '?':<4} {(p['nationality'] or '?')[:3]:<4} "
              f"{p['overall']:>4} {p['pace']:>4} {p['technique']:>4} "
              f"{p['finishing']:>4} {p['passing']:>4} {p['defending']:>4}")


# ─── Main Loop ───────────────────────────────────────────────────────────────

def run():
    conn = _get_conn()
    while True:
        clear()
        choice = menu_principal()
        if choice == "1":
            from ui.career import run_career
            run_career()
        elif choice == "2":
            listar_ligas(conn)
            input("\n  Enter para continuar...")
        elif choice == "3":
            simular_temporada(conn)
            input("\n  Enter para continuar...")
        elif choice == "4":
            partida_rapida(conn)
            input("\n  Enter para continuar...")
        elif choice == "5":
            ver_classificacao(conn)
            input("\n  Enter para continuar...")
        elif choice == "6":
            ver_jogadores(conn)
            input("\n  Enter para continuar...")
        elif choice == "7":
            if is_frozen():
                print("\n  Atualização de database indisponível na versão empacotada.")
                print("  Use a versão de desenvolvimento (python data/update.py).")
            else:
                import subprocess
                subprocess.run([sys.executable, str(ROOT / "data" / "update.py")])
            input("\n  Enter para continuar...")
        elif choice == "0":
            print("\n  Até logo!\n")
            break
        else:
            print("  Opção inválida.")
