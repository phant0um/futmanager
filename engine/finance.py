"""
FUTMANAGER — Finance Engine
Receita (patrocínio + TV + bilheteria + premiação) − folha − multas = saldo.
Salários limitam compras: folha > receita → vai à falência, força vender.
"""
from __future__ import annotations
import sqlite3

# Base de receita por temporada (patrocínio + TV), escalado por prestígio
# Todos os valores em BRL (Real brasileiro)
SPONSOR_BASE = 440_000_000    # prestígio 100 → ~440M (€80M × 5.5)
PRIZE_POOL = 193_000_000      # distribuído por posição na liga (€35M × 5.5)
TITLE_BONUS = 138_000_000     # (€25M × 5.5)

# Bilheteria
HOME_GAMES = 19              # jogos em casa por temporada (liga 20 times)
TICKET_BASE = 193            # R$ médio por ingresso (escala com prestígio) (€35 × 5.5)

# Multa por expulsão (cartão vermelho): fração do salário ANUAL por expulsão
RED_CARD_FINE_PCT = 0.04


def wage_bill(conn, club_id: int) -> int:
    """Folha salarial anual: jogadores próprios integral + emprestados pelo %
    negociado (loan_wage_pct). Emprestados para fora não contam."""
    owned = conn.execute("""
        SELECT COALESCE(SUM(wage),0) FROM players
        WHERE club_id=? AND retired=0 AND loan_from_club IS NULL
    """, (club_id,)).fetchone()[0]
    # Emprestados para dentro: paga o % acordado (default 50 se NULL)
    loaned = conn.execute("""
        SELECT COALESCE(SUM(wage * COALESCE(loan_wage_pct,50) / 100.0),0) FROM players
        WHERE club_id=? AND retired=0 AND loan_from_club IS NOT NULL
    """, (club_id,)).fetchone()[0]
    return int(owned + loaned)


def base_ticket_price(prestige: int) -> int:
    """Preço de referência do ingresso por prestígio."""
    return int(TICKET_BASE * (0.6 + (prestige / 100) * 0.9))


def attendance_fill(prestige: int, league_pos: int, n_clubs: int,
                    ticket_price: int) -> float:
    """
    Ocupação do estádio (0-1) = base por campanha × curva de demanda do preço.
    Preço acima da referência reduz público; abaixo aumenta (até lotar).
    """
    pos_factor = (n_clubs - league_pos + 1) / n_clubs
    perf_fill = 0.55 + 0.40 * pos_factor          # campanha define base
    base = base_ticket_price(prestige)
    ratio = ticket_price / max(base, 1)
    # Elasticidade: +100% no preço → −60% na demanda; −50% → +30%
    demand_mult = max(0.20, min(1.30, 1 - 0.6 * (ratio - 1)))
    return max(0.10, min(1.0, perf_fill * demand_mult))


def stadium_revenue(capacity: int, prestige: int, league_pos: int, n_clubs: int,
                    ticket_price: int | None = None) -> int:
    """Bilheteria = capacidade × ocupação(preço,campanha) × preço × jogos casa."""
    capacity = capacity or 25_000
    if ticket_price is None:
        ticket_price = base_ticket_price(prestige)
    fill = attendance_fill(prestige, league_pos, n_clubs, ticket_price)
    return int(capacity * fill * ticket_price * HOME_GAMES)


def season_income(prestige: int, league_pos: int, n_clubs: int, won_title: bool,
                  capacity: int = 25_000, ticket_price: int | None = None) -> dict:
    """Receita: patrocínio/TV + bilheteria + premiação + bônus título."""
    sponsor = int((prestige / 100) ** 2 * SPONSOR_BASE)
    gate = stadium_revenue(capacity, prestige, league_pos, n_clubs, ticket_price)
    pos_factor = (n_clubs - league_pos + 1) / n_clubs
    prize = int(pos_factor * PRIZE_POOL)
    title = TITLE_BONUS if won_title else 0
    return {"sponsor": sponsor, "gate": gate, "prize": prize, "title": title,
            "total": sponsor + gate + prize + title}


def roll_red_cards(conn, club_id: int, seed: int | None = None):
    """
    Gera expulsões da temporada para o elenco (estatístico por posição).
    Zagueiros/meias levam mais vermelhos que atacantes/goleiros.
    """
    import random
    rng = random.Random(seed)
    # Lambda Poisson por posição ao longo de ~38 jogos
    lam = {"GK": 0.03, "DF": 0.30, "MF": 0.20, "FW": 0.10}
    players = conn.execute(
        "SELECT id, position FROM players WHERE club_id=? AND retired=0", (club_id,)
    ).fetchall()
    for pid, pos in players:
        l = lam.get(pos or "MF", 0.15)
        # Poisson simples (Knuth) — lambda baixo
        import math
        L = math.exp(-l); k = 0; p = 1.0
        while True:
            k += 1; p *= rng.random()
            if p <= L:
                break
        reds = k - 1
        if reds > 0:
            conn.execute("UPDATE players SET red_cards=? WHERE id=?", (reds, pid))
    conn.commit()


def red_card_fines(conn, club_id: int) -> tuple[int, list]:
    """
    Multa por expulsões da temporada: % do salário anual por cartão vermelho.
    Retorna (total_multa, lista_infratores).
    """
    rows = conn.execute("""
        SELECT name, wage, red_cards FROM players
        WHERE club_id=? AND retired=0 AND COALESCE(red_cards,0) > 0
        ORDER BY red_cards DESC
    """, (club_id,)).fetchall()
    total = 0
    offenders = []
    for name, wage, reds in rows:
        fine = int((wage or 0) * RED_CARD_FINE_PCT * reds)
        total += fine
        offenders.append({"name": name, "reds": reds, "fine": fine})
    return total, offenders


def loan_fees_expense(conn, club_id: int) -> int:
    """Taxas mensais de empréstimos de jogadores tomados (×12)."""
    rows = conn.execute("""
        SELECT loan_fee FROM players
        WHERE club_id=? AND retired=0 AND loan_from_club IS NOT NULL
    """, (club_id,)).fetchall()
    return int(sum((r[0] or 0) * 12 for r in rows))


def apply_season_finances(conn, career, league_pos: int, n_clubs: int,
                          won_title: bool) -> dict:
    """
    Aplica receita − folha ao caixa. Retorna relatório financeiro.
    """
    club = conn.execute("SELECT prestige, capacity, ticket_price FROM clubs WHERE id=?",
                        (career["manager_club_id"],)).fetchone()
    prestige = club[0] if club else 60
    capacity = club[1] if club else 25_000
    ticket_price = club[2] if club and club[2] else base_ticket_price(prestige)

    cid = career["manager_club_id"]
    income = season_income(prestige, league_pos, n_clubs, won_title, capacity, ticket_price)
    wages = wage_bill(conn, cid)
    fines, offenders = red_card_fines(conn, cid)
    loan_fees = loan_fees_expense(conn, cid)
    # Custo do CT: nível × R$13.75M/temporada (€2.5M × 5.5, nível 2 = baseline)
    training_cost = (career["training_level"] or 2) * 13_750_000
    net = income["total"] - wages - fines - loan_fees - training_cost

    new_money = career["money"] + net
    conn.execute("UPDATE career SET money=? WHERE id=?", (new_money, career["id"]))
    # Zera expulsões da temporada (multa já aplicada)
    conn.execute("UPDATE players SET red_cards=0 WHERE club_id=?", (cid,))
    conn.commit()

    return {
        "sponsor": income["sponsor"],
        "gate": income["gate"],
        "prize": income["prize"],
        "title": income["title"],
        "income_total": income["total"],
        "wages": wages,
        "fines": fines,
        "offenders": offenders,
        "loan_fees": loan_fees,
        "training_cost": training_cost,
        "net": net,
        "money_before": career["money"],
        "money_after": new_money,
        "bankrupt": new_money < 0,
    }
