"""
FUTMANAGER — Coach Market
Todos os clubes têm técnicos com reputação. Avaliados como o gestor humano:
campanha vs expectativa → demitido vira agente livre → contratado por outro clube.
Gestor humano demitido recebe ofertas e pode continuar em outro clube.
"""
from __future__ import annotations
import sqlite3
import random
import hashlib

SACK_REP = 25
WARN_REP = 38


# ─── Tabela rápida de liga IA (sem simular partidas) ─────────────────────────

def quick_league_table(conn, league_id: int, rng: random.Random) -> list[int]:
    """
    Classificação aproximada por força do elenco + ruído.
    Retorna lista de club_id em ordem de colocação (1º primeiro).
    """
    clubs = conn.execute("SELECT id FROM clubs WHERE league_id=?", (league_id,)).fetchall()
    scored = []
    for (cid,) in clubs:
        strength = conn.execute("""
            SELECT COALESCE(AVG(overall),50) FROM (
                SELECT overall FROM players
                WHERE club_id=? AND retired=0 ORDER BY overall DESC LIMIT 16
            )
        """, (cid,)).fetchone()[0]
        score = strength + rng.gauss(0, 5.5)   # ruído de temporada
        scored.append((score, cid))
    scored.sort(reverse=True)
    return [cid for _, cid in scored]


# ─── Avaliação de reputação de técnico ───────────────────────────────────────

def _prestige_rank(conn, club_id: int, league_id: int) -> int:
    rows = conn.execute(
        "SELECT id FROM clubs WHERE league_id=? ORDER BY prestige DESC, id", (league_id,)
    ).fetchall()
    for i, r in enumerate(rows, 1):
        if r[0] == club_id:
            return i
    return max(1, len(rows) // 2)


def _rep_delta(expected: int, actual: int, n_clubs: int, won_title: bool) -> int:
    diff = expected - actual
    d = max(-20, min(20, round(diff * 1.6)))
    if won_title:
        d += 12
    if actual > n_clubs - 3:
        d -= 15
    return d


def evaluate_ai_coaches(conn, player_club_id: int, finishes: dict) -> list[dict]:
    """
    Avalia técnicos IA com base nas colocações (finishes: {club_id: (pos, n_clubs)}).
    Sacaneia reputação, demite os fracos (club_id → NULL).
    Retorna lista de demitidos.
    """
    sacked = []
    coaches = conn.execute("""
        SELECT co.id, co.name, co.reputation, co.warnings, co.club_id, c.league_id
        FROM coaches co JOIN clubs c ON c.id=co.club_id
        WHERE co.is_player=0 AND co.retired=0 AND co.club_id IS NOT NULL
    """).fetchall()

    for coid, name, rep, warns, club_id, league_id in coaches:
        if club_id == player_club_id:
            continue  # clube do humano não tem técnico IA
        if club_id not in finishes:
            continue
        pos, n_clubs = finishes[club_id]
        expected = _prestige_rank(conn, club_id, league_id)
        won = (pos == 1)
        delta = _rep_delta(expected, pos, n_clubs, won)
        new_rep = max(0, min(100, (rep or 50) + delta))
        warns = warns or 0

        fire = False
        if new_rep < SACK_REP:
            fire = True
        elif new_rep < WARN_REP:
            warns += 1
            if warns >= 2:
                fire = True
        else:
            warns = 0

        if fire:
            conn.execute("UPDATE coaches SET reputation=?, warnings=0, club_id=NULL WHERE id=?",
                         (new_rep, coid))
            sacked.append({"id": coid, "name": name, "rep": new_rep, "club_id": club_id})
        else:
            conn.execute("UPDATE coaches SET reputation=?, warnings=? WHERE id=?",
                         (new_rep, warns, coid))
    conn.commit()
    return sacked


# ─── Mercado: preenche vagas ─────────────────────────────────────────────────

_COACH_FIRST = ["Carlos","Luis","Jorge","Pep","Carlo","Jürgen","Diego","Marcelo",
                "Antonio","Fernando","Roberto","José","Thomas","Mikel","Xabi",
                "Hansi","Unai","Erik","Simone","Massimiliano","Ange","Rúben"]
_COACH_LAST = ["Silva","Guardiola","Ancelotti","Klopp","Simeone","Mourinho",
               "Alonso","Flick","Arteta","Conte","Inzaghi","Gasperini","Amorim",
               "Slot","Emery","Tuchel","Motta","Postecoglou","Marsch","De Zerbi"]


def _new_coach(conn, country: str, target_rep: int, rng: random.Random) -> int:
    name = f"{rng.choice(_COACH_FIRST)} {rng.choice(_COACH_LAST)}"
    rep = max(25, min(80, target_rep + rng.randint(-6, 4)))
    age = rng.randint(36, 60)
    cur = conn.execute("""
        INSERT INTO coaches(name, nationality, reputation, club_id, age)
        VALUES (?,?,?,NULL,?)
    """, (name, country, rep, age))
    return cur.lastrowid


def fill_vacancies(conn, player_club_id: int, rng: random.Random) -> list[dict]:
    """
    Clubes sem técnico contratam. Clubes maiores escolhem primeiro e pegam
    os técnicos livres de maior reputação. Vagas sobrando → técnico newgen.
    Retorna contratações [{coach, club, rep}].
    """
    # Clubes com vaga (sem técnico ativo) — exceto clube do humano
    vacant = conn.execute("""
        SELECT c.id, c.name, c.prestige, COALESCE(co.code,'default') country
        FROM clubs c
        LEFT JOIN leagues l ON l.id=c.league_id
        LEFT JOIN countries co ON co.id=l.country_id
        WHERE c.id != ?
          AND NOT EXISTS (
            SELECT 1 FROM coaches k WHERE k.club_id=c.id AND k.retired=0
          )
    """, (player_club_id,)).fetchall()
    # Maiores primeiro
    vacant.sort(key=lambda r: -(r[2] or 0))

    hires = []
    for club_id, club_name, prestige, country in vacant:
        # Melhor técnico livre cuja reputação não exceda muito o teto do clube
        free = conn.execute("""
            SELECT id, name, reputation FROM coaches
            WHERE club_id IS NULL AND retired=0 AND is_player=0
            ORDER BY reputation DESC LIMIT 1
        """).fetchone()
        if free:
            coid, cname, crep = free
            conn.execute("UPDATE coaches SET club_id=?, warnings=0 WHERE id=?",
                         (club_id, coid))
            hires.append({"coach": cname, "club": club_name, "rep": crep})
        else:
            # Sem livres → gera newgen técnico
            coid = _new_coach(conn, country, (prestige or 60) - 5, rng)
            row = conn.execute("SELECT name, reputation FROM coaches WHERE id=?", (coid,)).fetchone()
            conn.execute("UPDATE coaches SET club_id=? WHERE id=?", (club_id, coid))
            hires.append({"coach": row[0], "club": club_name, "rep": row[1]})
    conn.commit()
    return hires


# ─── Ofertas para o gestor humano demitido ──────────────────────────────────

def offers_for_player(conn, player_reputation: int, player_club_id: int) -> list[dict]:
    """
    Clubes interessados no gestor humano demitido. Um clube oferece se:
      - o técnico atual dele é PIOR que o gestor (gestor é upgrade), e
      - o prestígio do clube não está muito acima do nível do gestor.
    Aceitar a proposta substitui o técnico atual (que vai para o mercado).
    """
    rows = conn.execute("""
        SELECT c.id, c.name, c.prestige,
               (SELECT k.reputation FROM coaches k
                WHERE k.club_id=c.id AND k.retired=0 LIMIT 1) as coach_rep
        FROM clubs c
        WHERE c.id != ?
    """, (player_club_id,)).fetchall()

    offers = []
    for cid, name, prest, coach_rep in rows:
        prest = prest or 60
        coach_rep = coach_rep if coach_rep is not None else 50
        # Gestor precisa ser upgrade E o clube não muito acima do seu nível
        if player_reputation > coach_rep + 2 and prest <= player_reputation + 18:
            offers.append({"club_id": cid, "name": name, "prestige": prest,
                           "coach_rep": coach_rep})
    # Melhores clubes (maior prestígio) primeiro
    offers.sort(key=lambda o: -o["prestige"])
    return offers[:8]
