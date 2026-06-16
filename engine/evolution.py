"""
FUTMANAGER — Player Evolution (mid-season ticks)
Evolução periódica por idade, potencial, minutagem e status de estrela.
Roda a cada N rodadas, não só no fim da temporada.
"""
from __future__ import annotations
import random


def assign_star_players(conn, seed: int | None = None):
    """
    Marca 1–3 jogadores por clube como star_player=1.
    Clubes maiores (prestígio alto) podem ter até 3; pequenos, 1.
    Critério: melhores overall do elenco, com bônus de potencial pra jovens.
    """
    rng = random.Random(seed) if seed else random.Random()
    clubs = conn.execute(
        "SELECT id, prestige FROM clubs"
    ).fetchall()

    for cid, prestige in clubs:
        players = conn.execute("""
            SELECT id, overall, potential, age
            FROM players WHERE club_id=? AND retired=0
            ORDER BY (overall * 2 + (potential or overall) - age) DESC
        """, (cid,)).fetchall()

        if not players:
            continue

        n_stars = rng.randint(1, 3)
        if (prestige or 50) < 45:
            n_stars = 1
        elif (prestige or 50) > 75:
            n_stars = rng.randint(2, 3)

        stars = players[:n_stars]
        for pid, *_ in stars:
            # Bônus de potencial e fama pra estrelas
            conn.execute("""
                UPDATE players SET star_player=1,
                    potential = MIN(99, potential + ?),
                    fame = fame + ?
                WHERE id=?
            """, (rng.randint(3, 10), rng.randint(10, 25), pid))

        # Limpa estrelas antigas (se re-roda)
        star_ids = {s[0] for s in stars}
        conn.execute("""
            UPDATE players SET star_player=0
            WHERE club_id=? AND id NOT IN ({}) AND star_player=1
        """.format(",".join(str(i) for i in star_ids) if star_ids else "0"),
        (cid,))

    conn.commit()


def _growth_factor(age: int) -> float:
    """Curva de carreira adaptada para ticks periódicos."""
    if age <= 18:   return 1.8
    if age <= 21:   return 1.2
    if age <= 25:   return 0.8
    if age <= 27:   return 0.4
    if age <= 31:   return 0.0
    if age <= 34:   return -0.8
    return -1.5


def evolve_players(conn, round_idx: int, season_year: int, seed: int | None = None):
    """
    Evolução periódica — roda a cada X rodadas (sugerido: 3 rodadas).
    Base: idade + gap potencial-overall + minutagem + bônus estrela.
    """
    rng = random.Random(seed if seed is not None else round_idx * 997 + season_year)

    players = conn.execute("""
        SELECT id, age, overall, potential, star_player, minutes_played,
               pace, technique, strength, finishing, passing,
               defending, goalkeeping, stamina, mental
        FROM players WHERE retired = 0
    """).fetchall()

    ATTRS = ["pace", "technique", "strength", "finishing",
             "passing", "defending", "goalkeeping", "stamina", "mental"]

    for p in players:
        pid = p["id"]
        age = p["age"] or 25
        overall = p["overall"] or 60
        potential = p["potential"] or overall
        star = p["star_player"] or 0
        mins = p["minutes_played"] or 0

        if age > 34:
            continue

        growth = _growth_factor(age)
        if growth <= 0:
            continue

        gap = max(0, potential - overall)
        crescimento = growth + (gap / 8.0)

        if star:
            crescimento *= 1.5

        # Minutos jogados na temporada (90min por jogo)
        games_approx = max(0, mins) / 90.0
        crescimento *= (games_approx / 20.0 + 0.5)

        if crescimento < 0.1:
            continue

        delta = round(crescimento + rng.uniform(-0.3, 0.5))
        delta = max(0, min(delta, gap))
        if delta == 0:
            continue

        # Aplica nos atributos com 40% de chance cada
        updates = {}
        for attr in ATTRS:
            if rng.random() < 0.4:
                cur = p[attr] or 50
                updates[attr] = max(20, min(99, cur + delta))

        if updates:
            set_clause = ", ".join(f"{k}=?" for k in updates)
            vals = list(updates.values())
            conn.execute(
                f"UPDATE players SET overall=MIN(99, overall+?), {set_clause} WHERE id=?",
                (delta, *vals, pid)
            )

    conn.commit()


def tick_weekly_finance(conn, club_id: int):
    """
    Tick semanal de finanças: salários + bilheteria parcial.
    Chamado a cada rodada simulada.
    """
    from engine.finance import wage_bill
    wages = wage_bill(conn, club_id)
    weekly_wage = wages // 38  # salário semanal estimado (~38 rodadas)

    # Bilheteria parcial: 1 jogo em casa a cada 2 rodadas (aproximação)
    # Não aplicamos aqui pois precisaríamos saber se é jogo em casa;
    # o season_end já consolida. Tick semanal deduz salários.
    conn.execute("""
        UPDATE career SET money = money - ?
        WHERE manager_club_id = ? AND status = 'active'
    """, (weekly_wage, club_id))
    conn.commit()
