"""
FUTMANAGER — Estatísticas individuais por competição.
"""
from __future__ import annotations


STAT_KEYS = ("games", "goals", "assists", "yellows", "reds")

COMP_LABELS = {
    "league": "Brasileirão Série A",
    "estadual": "Estadual",
    "copa_br": "Copa do Brasil",
    "copa_lib": "Libertadores",
    "copa_sul": "Sul-Americana",
    "champions": "Champions League",
}


def _inc(cursor, career_id: int, season_year: int, player_id: int, club_id: int,
         comp: str, **kwargs):
    cursor.execute("""
        INSERT INTO player_comp_stats (career_id, season_year, player_id, club_id, comp, games, goals, assists, yellows, reds)
        VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 0)
        ON CONFLICT(career_id, season_year, player_id, comp) DO NOTHING
    """, (career_id, season_year, player_id, club_id, comp))
    for k, v in kwargs.items():
        if k not in STAT_KEYS or v == 0:
            continue
        cursor.execute(f"""
            UPDATE player_comp_stats SET {k} = {k} + ?
            WHERE career_id=? AND season_year=? AND player_id=? AND comp=?
        """, (v, career_id, season_year, player_id, comp))


def record_player_match(conn, career_id: int, season_year: int, comp: str,
                        club_id: int, player_id: int, goals=0, assists=0,
                        yellows=0, reds=0):
    """Registra uma participação de jogador em uma partida de competição."""
    _inc(conn, career_id, season_year, player_id, club_id, comp,
         games=1, goals=goals, assists=assists, yellows=yellows, reds=reds)


def get_top_stats(conn, career_id: int, season_year: int, comp: str,
                  limit: int = 20):
    rows = conn.execute("""
        SELECT p.name, p.position, p.overall, c.name AS club_name,
               s.goals, s.assists, s.yellows, s.reds, s.games
        FROM player_comp_stats s
        JOIN players p ON p.id = s.player_id
        JOIN clubs c ON c.id = s.club_id
        WHERE s.career_id=? AND s.season_year=? AND s.comp=?
        ORDER BY s.goals DESC, s.assists DESC, s.games ASC
        LIMIT ?
    """, (career_id, season_year, comp, limit)).fetchall()
    return [dict(r) for r in rows]
