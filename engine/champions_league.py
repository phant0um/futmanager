"""
Champions League — Competição europeia inter-ligas (em BRL)
  16 clubes (top 4 de cada uma das 4 grandes ligas: EN/ES/IT/FR)
  Fase de grupos (4 grupos × 4 clubes, round-robin) + knockout (8→4→2→1)
"""
from __future__ import annotations
from db.models import Club, Player, Standing
from engine.simulation import simulate_match, simulate_penalties
from engine.season import League

PRIZE = 300_000_000  # Total prize pool (R$)
PRIZE_BY_STAGE = {
    "group": 30_000_000,     # Per match (6 matches × 4 = 24 matches per group)
    "quarters": 50_000_000,  # Oitavas
    "semis": 100_000_000,    # Semifinal
    "final": 200_000_000,    # Final (winner)
}
STAGES = [("Fase de Grupos", 4), ("Oitavas", 8), ("Semifinal", 4), ("Final", 2)]
TRIGGERS = [7, 12, 18, 25]  # Round trigger por stage_idx (0=grupos .. 3=final)


def _club_obj(conn, club_id):
    """Monta Club com elenco pra simulação — espelha gameapi._club_obj
    (não importamos gameapi aqui pra evitar import circular engine↔gameapi)."""
    r = conn.execute("SELECT * FROM clubs WHERE id=?", (club_id,)).fetchone()
    if not r:
        return None
    ps = conn.execute(
        "SELECT * FROM players WHERE club_id=? AND retired=0 ORDER BY overall DESC LIMIT 23",
        (club_id,)
    ).fetchall()
    players = [Player(id=p["id"], name=p["name"], position=p["position"] or "MF",
        nationality=p["nationality"] or "", birth_date=p["birth_date"], club_id=p["club_id"],
        pace=p["pace"], technique=p["technique"], strength=p["strength"], finishing=p["finishing"],
        passing=p["passing"], defending=p["defending"], goalkeeping=p["goalkeeping"],
        stamina=p["stamina"], mental=p["mental"], overall=p["overall"], source=p["source"] or "")
        for p in ps]
    c = Club(id=r["id"], name=r["name"], short_name=r["name"][:12],
             league_id=r["league_id"] or 0, prestige=r["prestige"])
    c.players = players
    return c


def _qualified_ids(conn) -> list[int]:
    """16 clubes qualificados: top 4 de cada uma das 4 grandes ligas (EN/ES/IT/FR).

    Usa ROW_NUMBER particionado por país pra garantir 4 por liga — em vez de
    um ORDER BY prestige global, que podia entupir o torneio com 10 clubes
    ingleses e 0 franceses.
    """
    rows = conn.execute("""
        SELECT id FROM (
            SELECT c.id AS id,
                   ROW_NUMBER() OVER (PARTITION BY co.code ORDER BY c.prestige DESC) AS rk
            FROM clubs c
            JOIN leagues l ON l.id = c.league_id
            JOIN countries co ON co.id = l.country_id
            WHERE co.code IN ('EN','ES','IT','FR') AND l.level = 1
        ) WHERE rk <= 4
    """).fetchall()
    return [r[0] for r in rows]


def ensure_group_stage(conn, career):
    """Sorteia grupos da Champions se não existirem (determinístico por season)."""
    existing = conn.execute("""
        SELECT COUNT(*) FROM championships
        WHERE career_id=? AND season_year=? AND stage_idx=0
    """, (career["id"], career["season_year"])).fetchone()[0]
    if existing:
        return

    qual = _qualified_ids(conn)
    if len(qual) < 16:
        # Save não tem 4 clubes nível-1 em cada uma das 4 ligas — Champions
        # fica fora do ar pra essa career (em vez de sortear grupo incompleto).
        print(f"[champions_league] qualificação incompleta ({len(qual)}/16 clubes) "
              f"— Champions League não disponível nesta career")
        return

    import random
    rng = random.Random(career["season_year"] * 997 + career["id"])

    # Divide 16 clubes em 4 grupos
    qual_shuffled = qual.copy()
    rng.shuffle(qual_shuffled)
    groups = [qual_shuffled[i*4:(i+1)*4] for i in range(4)]

    for group_idx, group_clubs in enumerate(groups):
        for match_idx, (h_id, a_id) in enumerate([
            (group_clubs[0], group_clubs[1]),
            (group_clubs[0], group_clubs[2]),
            (group_clubs[0], group_clubs[3]),
            (group_clubs[1], group_clubs[2]),
            (group_clubs[1], group_clubs[3]),
            (group_clubs[2], group_clubs[3]),
        ]):
            conn.execute("""
                INSERT INTO championships (career_id, season_year, comp, stage_idx,
                                          group_id, match_idx, home_id, away_id, played)
                VALUES (?,?,?,?,?,?,?,?,0)
            """, (career["id"], career["season_year"], "cl", 0, group_idx, match_idx, h_id, a_id))
    conn.commit()


def group_standings(conn, career, group_idx: int) -> list[Standing]:
    """Calcula standings de um grupo (round-robin)."""
    rows = conn.execute("""
        SELECT home_id, away_id, home_goals, away_goals, played
        FROM championships
        WHERE career_id=? AND season_year=? AND comp='cl' AND stage_idx=0 AND group_id=?
        ORDER BY match_idx
    """, (career["id"], career["season_year"], group_idx)).fetchall()

    club_pts = {}
    for r in rows:
        for cid in [r["home_id"], r["away_id"]]:
            if cid not in club_pts:
                club_pts[cid] = {"pts": 0, "pf": 0, "pa": 0, "played": 0, "w": 0, "d": 0, "l": 0}

        if r["played"]:
            hg, ag = r["home_goals"], r["away_goals"]
            home, away = club_pts[r["home_id"]], club_pts[r["away_id"]]
            home["pf"] += hg; home["pa"] += ag; home["played"] += 1
            away["pf"] += ag; away["pa"] += hg; away["played"] += 1

            if hg > ag:
                home["pts"] += 3; home["w"] += 1; away["l"] += 1
            elif hg < ag:
                away["pts"] += 3; away["w"] += 1; home["l"] += 1
            else:
                home["pts"] += 1; away["pts"] += 1; home["d"] += 1; away["d"] += 1

    standings = []
    for cid, stat in sorted(club_pts.items(), key=lambda x: (-x[1]["pts"], -(x[1]["pf"]-x[1]["pa"]))):
        club = conn.execute("SELECT id, name FROM clubs WHERE id=?", (cid,)).fetchone()
        standings.append(Standing(
            club_id=cid, club_name=club["name"], played=stat["played"],
            wins=stat["w"], draws=stat["d"], losses=stat["l"],
            gf=stat["pf"], ga=stat["pa"]
        ))
    return standings


def advance_group_to_knockout(conn, career):
    """Depois de grupos terminarem, top 2 de cada grupo avançam para oitavas."""
    winners_by_group = {}
    for group_idx in range(4):
        standings = group_standings(conn, career, group_idx)
        if standings:
            winners_by_group[group_idx] = [s.club_id for s in standings[:2]]

    # Pairings: G1-1 vs G2-2, G1-2 vs G2-1, G3-1 vs G4-2, G3-2 vs G4-1
    pairings = [
        (winners_by_group[0][0], winners_by_group[1][1]),
        (winners_by_group[0][1], winners_by_group[1][0]),
        (winners_by_group[2][0], winners_by_group[3][1]),
        (winners_by_group[2][1], winners_by_group[3][0]),
    ]

    for match_idx, (h_id, a_id) in enumerate(pairings):
        conn.execute("""
            INSERT INTO championships (career_id, season_year, comp, stage_idx, group_id,
                                      match_idx, home_id, away_id, played)
            VALUES (?,?,?,?,?,?,?,?,0)
        """, (career["id"], career["season_year"], "cl", 1, -1, match_idx, h_id, a_id))
    conn.commit()


def play_stage(conn, career, stage_idx: int):
    """Joga todos os matches de uma stage da Champions."""
    rows = conn.execute("""
        SELECT id, home_id, away_id FROM championships
        WHERE career_id=? AND season_year=? AND comp='cl' AND stage_idx=? AND played=0
    """, (career["id"], career["season_year"], stage_idx)).fetchall()

    from engine.stats import record_player_match
    for match_row in rows:
        mid, h_id, a_id = match_row["id"], match_row["home_id"], match_row["away_id"]
        h_obj = _club_obj(conn, h_id)
        a_obj = _club_obj(conn, a_id)

        if not h_obj or not a_obj:
            continue

        res = simulate_match(h_obj, a_obj)
        hg, ag = res.home_goals, res.away_goals

        # estatísticas dos jogadores
        for club, starters, sc_ids in (
            (h_obj, getattr(h_obj, "lineup", h_obj.players[:11]), res.home_scorer_ids),
            (a_obj, getattr(a_obj, "lineup", a_obj.players[:11]), res.away_scorer_ids),
        ):
            for p in starters:
                goals = sc_ids.count(p.id)
                record_player_match(conn, career["id"], career["season_year"], "champions",
                                    club.id, p.id, goals=goals)

        # On draws in KO stages, penalties
        if stage_idx > 0 and hg == ag:
            hp, ap = simulate_penalties(h_obj, a_obj)
            winner_id = h_id if hp > ap else a_id
        else:
            winner_id = h_id if hg > ag else a_id

        conn.execute("""
            UPDATE championships SET played=1, home_goals=?, away_goals=?, winner_id=?
            WHERE id=?
        """, (hg, ag, winner_id, mid))

    conn.commit()

    # Auto-advance to next KO stage
    if stage_idx == 0:
        advance_group_to_knockout(conn, career)
    elif stage_idx < 3:
        # Winners pair up for next stage
        winners = conn.execute("""
            SELECT winner_id FROM championships
            WHERE career_id=? AND season_year=? AND comp='cl' AND stage_idx=?
        """, (career["id"], career["season_year"], stage_idx)).fetchall()

        next_stage_idx = stage_idx + 1
        winners_list = [w[0] for w in winners]
        for match_idx in range(0, len(winners_list), 2):
            h_id, a_id = winners_list[match_idx], winners_list[match_idx+1]
            conn.execute("""
                INSERT INTO championships (career_id, season_year, comp, stage_idx, group_id,
                                          match_idx, home_id, away_id, played)
                VALUES (?,?,?,?,?,?,?,?,0)
            """, (career["id"], career["season_year"], "cl", next_stage_idx, -1, match_idx//2, h_id, a_id))
        conn.commit()


def is_participant(conn, career) -> bool:
    """True se o clube do manager está entre os 16 classificados desta temporada.

    Sem isso, qualquer manager EN/ES/IT/FR/NL/PT seria forçado a 'jogar' rodadas
    da Champions mesmo com seu clube de fora — turno gasto numa partida alheia.
    """
    n = conn.execute("""
        SELECT COUNT(*) FROM championships
        WHERE career_id=? AND season_year=? AND comp='cl'
          AND (home_id=? OR away_id=?)
    """, (career["id"], career["season_year"], career["manager_club_id"], career["manager_club_id"])).fetchone()[0]
    return n > 0


def due_stage(conn, career, current_round) -> tuple[int, int] | None:
    """Retorna (stage_idx, group) se Champions está pronto pra jogar, else None."""
    for st_idx, trigger_round in enumerate(TRIGGERS):
        pending = conn.execute("""
            SELECT COUNT(*) as n FROM championships
            WHERE career_id=? AND season_year=? AND comp='cl' AND stage_idx=? AND played=0
        """, (career["id"], career["season_year"], st_idx)).fetchone()

        if pending and pending[0] > 0 and current_round >= trigger_round:
            return (st_idx, 0)  # Group ID placeholder
    return None
