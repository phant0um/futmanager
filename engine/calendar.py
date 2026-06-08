"""
FUTMANAGER — Calendário (rodada a rodada)
Persiste o fixture da liga por save/temporada. Permite jogar UMA rodada por vez,
voltando à tela de gestão entre os jogos (loop clássico Brasfoot).
"""
from __future__ import annotations
import sqlite3
from db.models import Club, Player, Standing


def _load_league_clubs(conn, league_id):
    rows = conn.execute("SELECT * FROM clubs WHERE league_id=?", (league_id,)).fetchall()
    clubs = []
    for r in rows:
        prows = conn.execute(
            "SELECT * FROM players WHERE club_id=? AND retired=0 ORDER BY overall DESC LIMIT 23",
            (r["id"],)).fetchall()
        players = [Player(
            id=p["id"], name=p["name"], position=p["position"] or "MF",
            nationality=p["nationality"] or "", birth_date=p["birth_date"],
            club_id=p["club_id"], pace=p["pace"], technique=p["technique"],
            strength=p["strength"], finishing=p["finishing"], passing=p["passing"],
            defending=p["defending"], goalkeeping=p["goalkeeping"],
            stamina=p["stamina"], mental=p["mental"], overall=p["overall"],
            source=p["source"] or "", age=p["age"] or 0,
            form=p["form"] if p["form"] is not None else 1.0,
            fitness=p["fitness"] if p["fitness"] is not None else 100,
            ) for p in prows]
        c = Club(id=r["id"], name=r["name"], short_name=r["name"][:12],
                 league_id=r["league_id"], prestige=r["prestige"])
        c.players = players
        clubs.append(c)
    return clubs


def league_id_of(conn, club_id):
    return conn.execute("SELECT league_id FROM clubs WHERE id=?", (club_id,)).fetchone()[0]


def ensure_fixtures(conn, career):
    """Gera e persiste o fixture da liga se ainda não existir para a temporada."""
    cid = career["manager_club_id"]
    season = career["season_year"]
    n = conn.execute(
        "SELECT COUNT(*) FROM fixtures WHERE career_id=? AND season_year=?",
        (career["id"], season)).fetchone()[0]
    if n > 0:
        return
    from engine.season import League
    lid = league_id_of(conn, cid)
    clubs = _load_league_clubs(conn, lid)
    league = League("L", clubs, str(season))
    for ri, pairs in enumerate(league.rounds):
        for home, away in pairs:
            conn.execute("""
                INSERT INTO fixtures(career_id, season_year, league_id, round_idx,
                    home_id, away_id, played) VALUES (?,?,?,?,?,?,0)
            """, (career["id"], season, lid, ri, home.id, away.id))
    conn.commit()


def num_rounds(conn, career):
    return (conn.execute(
        "SELECT MAX(round_idx) FROM fixtures WHERE career_id=? AND season_year=?",
        (career["id"], career["season_year"])).fetchone()[0] or -1) + 1


def next_match(conn, career):
    """Próximo jogo do clube do jogador: (round_idx, 'casa'|'fora', opp_id, opp_name) ou None."""
    cid = career["manager_club_id"]
    ri = career["current_round"] or 0
    row = conn.execute("""
        SELECT round_idx, home_id, away_id FROM fixtures
        WHERE career_id=? AND season_year=? AND round_idx>=? AND played=0
          AND (home_id=? OR away_id=?)
        ORDER BY round_idx LIMIT 1
    """, (career["id"], career["season_year"], ri, cid, cid)).fetchone()
    if not row:
        return None
    if row["home_id"] == cid:
        opp = row["away_id"]; loc = "casa"
    else:
        opp = row["home_id"]; loc = "fora"
    name = conn.execute("SELECT name FROM clubs WHERE id=?", (opp,)).fetchone()[0]
    return {"round": row["round_idx"], "loc": loc, "opp_id": opp, "opp_name": name}


def _club_morale(conn, career, club_id) -> float:
    """Moral a partir dos últimos 5 resultados da temporada (forma)."""
    rows = conn.execute("""
        SELECT home_id, away_id, home_goals, away_goals FROM fixtures
        WHERE career_id=? AND season_year=? AND played=1
          AND (home_id=? OR away_id=?)
        ORDER BY round_idx DESC LIMIT 5
    """, (career["id"], career["season_year"], club_id, club_id)).fetchall()
    m = 1.0
    for r in rows:
        gf, ga = (r["home_goals"], r["away_goals"]) if r["home_id"] == club_id else (r["away_goals"], r["home_goals"])
        if gf > ga: m += 0.03
        elif gf < ga: m -= 0.03
    return max(0.85, min(1.15, m))


def _update_player_condition(conn, club):
    """Atualiza forma + fadiga do elenco após uma rodada (só persiste p/ clubes
    carregados via _load_league_clubs — em geral só o do manager, p/ minimizar writes).
    Titulares cansam (conforme stamina); reservas recuperam. Forma sobe/desce com
    desempenho do time e regride à média — mesmo idioma de _update_morale."""
    xi_ids = {p.id for p in club.lineup}
    won = club.morale > 1.0  # aproximação: time em boa fase joga melhor e ganha mais
    for p in club.players:
        if p.id in xi_ids:
            drain = max(2, 9 - (p.stamina or 50) // 12)
            fitness = max(15, (p.fitness or 100) - drain)
            target = 1.04 if won else 0.985
        else:
            fitness = min(100, (p.fitness or 100) + 14)
            target = p.form or 1.0
        form = (p.form or 1.0) + (target - (p.form or 1.0)) * 0.25
        form = max(0.85, min(1.15, form))
        conn.execute("UPDATE players SET form=?, fitness=? WHERE id=?",
                     (round(form, 3), int(fitness), p.id))


def standings(conn, career):
    """Classificação da temporada corrente a partir das partidas já jogadas."""
    lid = league_id_of(conn, career["manager_club_id"])
    clubs = conn.execute("SELECT id, name FROM clubs WHERE league_id=?", (lid,)).fetchall()
    tab = {r["id"]: Standing(club_id=r["id"], club_name=r["name"]) for r in clubs}
    rows = conn.execute("""
        SELECT home_id, away_id, home_goals, away_goals,
               COALESCE(home_yellows,0) hy, COALESCE(home_reds,0) hr,
               COALESCE(away_yellows,0) ay, COALESCE(away_reds,0) ar
        FROM fixtures
        WHERE career_id=? AND season_year=? AND played=1
    """, (career["id"], career["season_year"])).fetchall()
    for r in rows:
        if r["home_id"] in tab:
            tab[r["home_id"]].update(r["home_goals"], r["away_goals"], r["hy"], r["hr"])
        if r["away_id"] in tab:
            tab[r["away_id"]].update(r["away_goals"], r["home_goals"], r["ay"], r["ar"])
    return sorted(tab.values(), key=lambda s: (s.points, s.gd, s.gf), reverse=True)
