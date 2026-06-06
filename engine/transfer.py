"""
FUTMANAGER — Transfer Market Engine
Comprar/vender jogadores usando orçamento (€). IA aceita vendas a prêmio.
"""
from __future__ import annotations
import random
import sqlite3

# Limites de elenco
MIN_SQUAD = 16
MAX_SQUAD = 32

# Prêmio de compra: clube vendedor cobra acima do valor de mercado
BUY_PREMIUM = (1.05, 1.35)
# Desconto de venda: você recebe abaixo do valor de mercado
SELL_DISCOUNT = (0.75, 0.95)


def _seed_for(player_id: int, career_id: int, season: int) -> int:
    return (player_id * 31 + career_id * 17 + season) % (2**31)


def buy_price(value: int, player_id: int, career_id: int, season: int) -> int:
    """Preço determinístico de compra (mesmo jogador, mesmo preço na janela)."""
    rng = random.Random(_seed_for(player_id, career_id, season))
    return int((value or 1_000_000) * rng.uniform(*BUY_PREMIUM))


def sell_price(value: int, player_id: int, career_id: int, season: int) -> int:
    rng = random.Random(_seed_for(player_id, career_id, season) + 7)
    return int((value or 500_000) * rng.uniform(*SELL_DISCOUNT))


def squad_size(conn, club_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM players WHERE club_id=? AND retired=0", (club_id,)
    ).fetchone()[0]


def list_market(conn, manager_club_id: int, position: str | None = None,
                max_price: int | None = None, min_ovr: int = 0,
                max_ovr: int = 99, limit: int = 40) -> list:
    """Jogadores compráveis (fora do seu clube, não aposentados)."""
    q = """
        SELECT p.id, p.name, p.position, p.age, p.overall, p.potential,
               p.value, c.name as club, c.id as club_id
        FROM players p
        JOIN clubs c ON c.id = p.club_id
        WHERE p.retired = 0
          AND p.club_id != ?
          AND p.overall BETWEEN ? AND ?
    """
    params = [manager_club_id, min_ovr, max_ovr]
    if position:
        q += " AND p.position = ?"
        params.append(position)
    if max_price:
        q += " AND p.value <= ?"
        params.append(max_price)
    q += " ORDER BY p.overall DESC, p.potential DESC LIMIT ?"
    params.append(limit)
    return conn.execute(q, params).fetchall()


def asking_and_clause(conn, player_id: int, career) -> tuple[int, int]:
    """Preço pedido pelo clube vendedor e cláusula de rescisão."""
    p = conn.execute(
        "SELECT value, release_clause FROM players WHERE id=?", (player_id,)
    ).fetchone()
    asking = buy_price(p["value"], player_id, career["id"], career["season_year"])
    clause = p["release_clause"] or int((p["value"] or 1_000_000) * 2.2)
    return asking, clause


def evaluate_offer(offer: int, asking: int, clause: int) -> tuple[str, int]:
    """
    Avalia oferta de compra.
    Retorna (resultado, contraproposta):
      'clause'  → cláusula atingida, venda forçada
      'accept'  → aceita pela oferta
      'counter' → contraproposta (valor)
      'reject'  → recusada
    """
    if offer >= clause:
        return "clause", clause
    if offer >= asking:
        return "accept", offer
    if offer >= asking * 0.85:
        # Contrapropõe no meio-termo entre oferta e pedido
        counter = int((offer + asking) / 2)
        return "counter", counter
    return "reject", asking


def buy_player_at(conn, career, player_id: int, price: int) -> tuple[bool, str]:
    """Finaliza compra a um preço acordado."""
    club_id = career["manager_club_id"]
    if squad_size(conn, club_id) >= MAX_SQUAD:
        return False, f"Elenco cheio (máx {MAX_SQUAD})."
    p = conn.execute(
        "SELECT id, name, club_id, retired FROM players WHERE id=?", (player_id,)
    ).fetchone()
    if not p or p["retired"]:
        return False, "Jogador indisponível."
    if p["club_id"] == club_id:
        return False, "Jogador já é seu."
    if price > career["money"]:
        return False, f"Sem caixa. Custo €{price/1e6:.1f}M, você tem €{career['money']/1e6:.1f}M."

    from_club = p["club_id"]
    conn.execute("UPDATE players SET club_id=? WHERE id=?", (club_id, player_id))
    conn.execute("UPDATE career SET money = money - ? WHERE id=?", (price, career["id"]))
    conn.execute("""
        INSERT INTO transfers(player_id, from_club, to_club, fee) VALUES (?,?,?,?)
    """, (player_id, from_club, club_id, price))
    conn.commit()
    return True, f"✅ {p['name']} contratado por €{price/1e6:.1f}M"


def sell_player(conn, career, player_id: int) -> tuple[bool, str]:
    """Vende jogador para clube IA. Retorna (sucesso, mensagem)."""
    club_id = career["manager_club_id"]

    if squad_size(conn, club_id) <= MIN_SQUAD:
        return False, f"Elenco no mínimo ({MIN_SQUAD}). Não pode vender."

    p = conn.execute(
        "SELECT id, name, value, overall, club_id, retired FROM players WHERE id=?", (player_id,)
    ).fetchone()
    if not p or p["retired"] or p["club_id"] != club_id:
        return False, "Jogador não está no seu elenco."

    price = sell_price(p["value"], player_id, career["id"], career["season_year"])

    # Encontra comprador IA: clube que pode "pagar" — prestígio compatível com o OVR
    buyer = _find_ai_buyer(conn, club_id, p["overall"])
    conn.execute("UPDATE players SET club_id=? WHERE id=?", (buyer, player_id))
    conn.execute("UPDATE career SET money = money + ? WHERE id=?", (price, career["id"]))
    conn.execute("""
        INSERT INTO transfers(player_id, from_club, to_club, fee)
        VALUES (?,?,?,?)
    """, (player_id, club_id, buyer, price))
    conn.commit()
    return True, f"✅ {p['name']} vendido por €{price/1e6:.1f}M"


def _find_ai_buyer(conn, exclude_club: int, overall: int) -> int:
    """Clube IA plausível para receber jogador vendido (prestígio ~ overall)."""
    row = conn.execute("""
        SELECT id FROM clubs
        WHERE id != ?
        ORDER BY ABS(prestige - ?) + ABS(RANDOM() % 15)
        LIMIT 1
    """, (exclude_club, overall)).fetchone()
    return row[0] if row else exclude_club


# ─── Empréstimos ─────────────────────────────────────────────────────────────

def loan_min_coverage(overall: int) -> int:
    """% mínimo de cobertura (salário+taxa) que o clube dono exige."""
    if overall >= 85: return 95
    if overall >= 80: return 85
    if overall >= 75: return 70
    if overall >= 70: return 55
    return 40


def loan_in_evaluate(wage: int, overall: int, wage_pct: int, monthly_fee: int) -> tuple[bool, int, int]:
    """
    Avalia proposta. Retorna (aceita, cobertura_oferecida_%, minimo_exigido_%).
    Cobertura = % salário bancado + (taxa anual / salário).
    """
    wage = max(wage, 1)
    fee_as_pct = (monthly_fee * 12) / wage * 100
    offered = wage_pct + fee_as_pct
    required = loan_min_coverage(overall)
    return offered >= required, int(offered), required


def loan_in(conn, career, player_id: int, season_year: int,
            wage_pct: int = 50, monthly_fee: int = 0) -> tuple[bool, str]:
    """
    Propõe empréstimo: você banca wage_pct% do salário + taxa mensal ao dono.
    Clube dono aceita se a cobertura total atingir o mínimo (por qualidade).
    """
    club_id = career["manager_club_id"]
    if squad_size(conn, club_id) >= MAX_SQUAD:
        return False, f"Elenco cheio (máx {MAX_SQUAD})."

    p = conn.execute(
        "SELECT id, name, overall, wage, club_id, retired, loan_from_club FROM players WHERE id=?",
        (player_id,)
    ).fetchone()
    if not p or p["retired"]:
        return False, "Jogador indisponível."
    if p["club_id"] == club_id:
        return False, "Jogador já é seu."
    if p["loan_from_club"] is not None:
        return False, "Jogador já está emprestado."

    accept, offered, required = loan_in_evaluate(
        p["wage"] or 0, p["overall"] or 60, wage_pct, monthly_fee
    )
    if not accept:
        return False, (f"❌ {p['name']}: proposta recusada. "
                       f"Cobertura {offered}% < exigido {required}%. Ofereça mais.")

    origin = p["club_id"]
    conn.execute("""
        UPDATE players SET club_id=?, loan_from_club=?, loan_until=?,
                           loan_wage_pct=?, loan_fee=? WHERE id=?
    """, (club_id, origin, season_year + 1, wage_pct, monthly_fee, player_id))
    conn.commit()
    yr_cost = int((p["wage"] or 0) * wage_pct / 100 + monthly_fee * 12)
    return True, (f"✅ {p['name']} emprestado até {season_year+1} "
                  f"(banca {wage_pct}% salário + {monthly_fee/1e3:.0f}K/mês = ~{yr_cost/1e6:.1f}M/ano)")


def loan_out(conn, career, player_id: int, season_year: int) -> tuple[bool, str]:
    """Empresta seu jogador a clube IA por 1 temporada. Libera salário."""
    club_id = career["manager_club_id"]
    if squad_size(conn, club_id) <= MIN_SQUAD:
        return False, f"Elenco no mínimo ({MIN_SQUAD})."

    p = conn.execute(
        "SELECT id, name, overall, club_id, retired, loan_from_club FROM players WHERE id=?", (player_id,)
    ).fetchone()
    if not p or p["retired"] or p["club_id"] != club_id:
        return False, "Jogador não está no seu elenco."
    if p["loan_from_club"] is not None:
        return False, "Esse jogador já está emprestado a você (não pode reemprestar)."

    dest = _find_ai_buyer(conn, club_id, p["overall"])
    conn.execute("""
        UPDATE players SET club_id=?, loan_from_club=?, loan_until=? WHERE id=?
    """, (dest, club_id, season_year + 1, player_id))
    conn.commit()
    return True, f"✅ {p['name']} emprestado até {season_year+1} (salário liberado)"
