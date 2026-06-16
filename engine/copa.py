"""
FUTMANAGER — Copas mata-mata intercaladas no calendário
  br  = Copa do Brasil      (16 clubes BR)
  lib = Libertadores        (16 melhores da América do Sul: BR+AR)
  sul = Sul-Americana       (clubes sul-americanos 17º-32º por prestígio)
16 clubes · Oitavas → Quartas → Semi → Final. Cada fase entre rodadas da liga.
"""
from __future__ import annotations
from db.models import Club, Player
from engine.simulation import simulate_match, simulate_penalties

STAGES = [("Oitavas de Final", 16), ("Quartas de Final", 8),
          ("Semifinal", 4), ("Final", 2)]

# Config por competição: nome + rodadas-gatilho (após qual rodada cada fase joga)
# Valores em BRL (Real brasileiro)
COMPS = {
    "br":  {"name": "Copa do Brasil",  "triggers": [4, 13, 22, 31], "prize": 165_000_000},
    "lib": {"name": "Libertadores",    "triggers": [6, 15, 24, 33], "prize": 248_000_000},
    "sul": {"name": "Sul-Americana",   "triggers": [8, 17, 26, 35], "prize": 121_000_000},
}
ALL_COMPS = ["br", "lib", "sul"]


def _qualified_ids(conn, comp):
    """16 clubes classificados para a competição (por prestígio)."""
    if comp == "br":
        rows = conn.execute("""
            SELECT c.id FROM clubs c JOIN leagues l ON l.id=c.league_id
            JOIN countries co ON co.id=l.country_id
            WHERE co.code='BR' AND l.level<=2
            ORDER BY c.prestige DESC, c.id LIMIT 16
        """).fetchall()
        return [r[0] for r in rows]
    # Sul-americanos (BR + AR) por prestígio
    sa = conn.execute("""
        SELECT c.id FROM clubs c JOIN leagues l ON l.id=c.league_id
        JOIN countries co ON co.id=l.country_id
        WHERE co.code IN ('BR','AR') AND l.level<=1
        ORDER BY c.prestige DESC, c.id LIMIT 32
    """).fetchall()
    ids = [r[0] for r in sa]
    if comp == "lib":
        return ids[:16]
    if comp == "sul":
        return ids[16:32]
    return []


def ensure_comp(conn, career, comp):
    """Sorteia o chaveamento da competição se ainda não existir na temporada."""
    n = conn.execute("SELECT COUNT(*) FROM copa WHERE career_id=? AND season_year=? AND comp=?",
                     (career["id"], career["season_year"], comp)).fetchone()[0]
    if n > 0:
        return
    ids = _qualified_ids(conn, comp)
    if len(ids) < 16:
        return
    for mi in range(8):
        conn.execute("""
            INSERT INTO copa(career_id, season_year, comp, stage_idx, match_idx,
                home_id, away_id, played) VALUES (?,?,?,0,?,?,?,0)
        """, (career["id"], career["season_year"], comp, mi, ids[mi], ids[15 - mi]))
    conn.commit()


def player_in_comp(conn, career, comp):
    cid = career["manager_club_id"]
    return conn.execute("""
        SELECT 1 FROM copa WHERE career_id=? AND season_year=? AND comp=?
          AND (home_id=? OR away_id=?) LIMIT 1
    """, (career["id"], career["season_year"], comp, cid, cid)).fetchone() is not None


def pending_stage(conn, career, comp):
    row = conn.execute("""
        SELECT MIN(stage_idx) FROM copa
        WHERE career_id=? AND season_year=? AND comp=? AND played=0
    """, (career["id"], career["season_year"], comp)).fetchone()
    return row[0]


def champion_id(conn, career, comp):
    row = conn.execute("""
        SELECT winner_id FROM copa WHERE career_id=? AND season_year=? AND comp=?
          AND stage_idx=? AND played=1
    """, (career["id"], career["season_year"], comp, len(STAGES) - 1)).fetchone()
    return row[0] if row else None


def player_tie(conn, career, comp, stage_idx):
    cid = career["manager_club_id"]
    row = conn.execute("""
        SELECT home_id, away_id FROM copa
        WHERE career_id=? AND season_year=? AND comp=? AND stage_idx=? AND played=0
          AND (home_id=? OR away_id=?)
    """, (career["id"], career["season_year"], comp, stage_idx, cid, cid)).fetchone()
    if not row:
        return None
    opp = row["away_id"] if row["home_id"] == cid else row["home_id"]
    name = conn.execute("SELECT name FROM clubs WHERE id=?", (opp,)).fetchone()[0]
    return {"opp_id": opp, "opp_name": name}


def play_stage(conn, career, comp, stage_idx, by_id, on_match=None):
    ties = conn.execute("""
        SELECT id, match_idx, home_id, away_id FROM copa
        WHERE career_id=? AND season_year=? AND comp=? AND stage_idx=? AND played=0
        ORDER BY match_idx
    """, (career["id"], career["season_year"], comp, stage_idx)).fetchall()
    cid = career["manager_club_id"]
    lines, winners = [], []
    from engine.stats import record_player_match
    for t in ties:
        h, a = by_id[t["home_id"]], by_id[t["away_id"]]
        is_player = cid in (h.id, a.id)
        r = on_match(h, a) if (is_player and on_match) else simulate_match(h, a)
        # cartões fictícios p/ jogadores de IA (só registramos gols de forma simples)
        for club, starters, sc_ids in (
            (h, getattr(h, "lineup", h.players[:11]), r.home_scorer_ids),
            (a, getattr(a, "lineup", a.players[:11]), r.away_scorer_ids),
        ):
            for p in starters:
                goals = sc_ids.count(p.id)
                record_player_match(conn, career["id"], career["season_year"], f"copa_{comp}",
                                    club.id, p.id, goals=goals)
        if r.home_goals == r.away_goals:
            hp, ap = simulate_penalties(h, a)
            w = h if hp >= ap else a
            extra = f" ({hp}-{ap} pên)"
        else:
            w = h if r.home_goals > r.away_goals else a
            extra = ""
        conn.execute("UPDATE copa SET played=1, home_goals=?, away_goals=?, winner_id=? WHERE id=?",
                     (r.home_goals, r.away_goals, w.id, t["id"]))
        winners.append((t["match_idx"], w.id))
        mk = " ◀" if is_player else ""
        lines.append(f"     {h.name} {r.home_goals}-{r.away_goals} {a.name}{extra} → {w.name}{mk}")

    if stage_idx + 1 < len(STAGES):
        winners.sort()
        wids = [wid for _, wid in winners]
        for mi in range(len(wids) // 2):
            conn.execute("""
                INSERT INTO copa(career_id, season_year, comp, stage_idx, match_idx,
                    home_id, away_id, played) VALUES (?,?,?,?,?,?,?,0)
            """, (career["id"], career["season_year"], comp, stage_idx + 1, mi,
                  wids[mi * 2], wids[mi * 2 + 1]))
    conn.commit()
    return lines, winners


def due_comp(conn, career, current_round):
    """Primeira competição com fase liberada (gatilho<=rodada) p/ o clube do jogador."""
    for comp in ALL_COMPS:
        ensure_comp(conn, career, comp)
        if not player_in_comp(conn, career, comp):
            continue
        st = pending_stage(conn, career, comp)
        if st is not None and current_round >= COMPS[comp]["triggers"][st]:
            return comp, st
    return None
