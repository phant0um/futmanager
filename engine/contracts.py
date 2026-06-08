"""
FUTMANAGER — Contratos & Renegociação Salarial
Mesma lógica de "pedido → contraproposta → aceita/recusa" do mercado de
transferências (engine/transfer.py), aplicada à renovação de contrato do
PRÓPRIO elenco. Determinístico por (jogador, temporada).
"""
from __future__ import annotations
import random

EXPIRY_WINDOW = 2          # avisa quando faltam <= N anos pro fim do contrato
COOLDOWN_YEARS = 1         # após proposta recusada/fechada, espera N anos p/ negociar de novo


def _seed_for(player_id: int, season: int) -> int:
    return (player_id * 53 + season * 13) % (2**31)


def expiring_players(conn, club_id: int, season_year: int, within: int = EXPIRY_WINDOW) -> list:
    """Jogadores do elenco com contrato terminando em <= `within` anos
    (e fora do cooldown de renegociação)."""
    return conn.execute("""
        SELECT id, name, position, age, overall, potential, value, wage,
               contract_until, form, fitness,
               pace, technique, strength, finishing, passing, defending, stamina
        FROM players
        WHERE club_id=? AND retired=0 AND loan_from_club IS NULL
          AND contract_until IS NOT NULL AND contract_until <= ?
          AND COALESCE(renewal_cooldown, 0) <= ?
        ORDER BY contract_until ASC, overall DESC
    """, (club_id, season_year + within, season_year)).fetchall()


def _player_demand(conn, player_id: int, career) -> tuple[int, int]:
    """(salário pretendido, anos pretendidos) — análogo a asking_and_clause.
    Cresce com overall/forma/moral; cai se o jogador está velho ou o time vai mal."""
    p = conn.execute(
        "SELECT wage, overall, age, form FROM players WHERE id=?", (player_id,)
    ).fetchone()
    rng = random.Random(_seed_for(player_id, career["season_year"]))
    base = max(p["wage"] or 80_000, int((p["overall"] or 60) ** 2 * 35))
    form = p["form"] if p["form"] is not None else 1.0
    mood = 0.85 + 0.3 * max(0.0, min(1.0, (form - 0.85) / 0.30))   # forma 0.85→0.85x, 1.15→1.15x
    demand_wage = int(base * mood * rng.uniform(0.95, 1.15))
    age = p["age"] or 25
    years = 4 if age <= 23 else (3 if age <= 29 else (2 if age <= 33 else 1))
    return demand_wage, years


def evaluate_renewal_offer(offer_wage: int, offer_years: int, demand_wage: int,
                           demand_years: int, player_form: float, club_money: int,
                           wage_bill: int) -> tuple[str, dict]:
    """
    Avalia proposta de renovação — espelha evaluate_offer (transfer.py):
      'accept'  → proposta atende ou supera a pretensão
      'counter' → contraproposta (wage, years) no meio-termo
      'reject'  → proposta longe demais do que o jogador quer
    Clube com caixa apertado (folha alta vs caixa) deixa o jogador mais flexível;
    jogador em baixa de forma também cede um pouco.
    """
    flex = 1.0
    if player_form < 0.95:
        flex -= 0.05
    if club_money < wage_bill:                      # clube no vermelho — jogador entende
        flex -= 0.05
    threshold = demand_wage * max(0.85, flex)

    if offer_wage >= demand_wage and offer_years >= demand_years:
        return "accept", {"wage": offer_wage, "years": offer_years}
    if offer_wage >= threshold * 0.92:
        cw = int((offer_wage + demand_wage) / 2)
        cy = max(offer_years, demand_years - 1, 1)
        return "counter", {"wage": cw, "years": cy}
    return "reject", {"wage": demand_wage, "years": demand_years}


def renew_contract(conn, career, player_id: int, wage: int, years: int) -> tuple[bool, str]:
    """Fecha o novo contrato — espelha buy_player_at (commit direto)."""
    p = conn.execute(
        "SELECT id, name, club_id, retired FROM players WHERE id=?", (player_id,)
    ).fetchone()
    if not p or p["retired"] or p["club_id"] != career["manager_club_id"]:
        return False, "Jogador não está no seu elenco."
    new_until = career["season_year"] + max(1, years)
    conn.execute("""UPDATE players SET wage=?, contract_until=?, renewal_cooldown=?
                    WHERE id=?""",
                 (int(wage), new_until, career["season_year"] + COOLDOWN_YEARS, player_id))
    conn.commit()
    return True, f"✅ {p['name']} renovou até {new_until} por €{wage/1e6:.2f}M/ano"


def let_expire(conn, career, player_id: int) -> tuple[bool, str]:
    """Decide não renovar — jogador sai como agente livre ao fim da temporada
    (marcado com cooldown pra não voltar a aparecer na lista)."""
    p = conn.execute("SELECT id, name, club_id FROM players WHERE id=?", (player_id,)).fetchone()
    if not p or p["club_id"] != career["manager_club_id"]:
        return False, "Jogador não está no seu elenco."
    conn.execute("UPDATE players SET renewal_cooldown=? WHERE id=?",
                 (career["season_year"] + COOLDOWN_YEARS, player_id))
    conn.commit()
    return True, f"{p['name']} vai sair como agente livre ao fim do contrato."
