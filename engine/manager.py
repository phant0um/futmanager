"""
FUTMANAGER — Manager Reputation & Job Security
Gestor tem reputação (0-100). Varia por campanha vs expectativa, finanças,
venda de ídolos. Reputação baixa → advertência → demissão.
"""
from __future__ import annotations
import sqlite3

# Limiares de demissão
SACK_REP = 25          # abaixo disso: demissão imediata
WARN_REP = 38          # abaixo disso: advertência (2 = demissão)
IDOL_OVERALL = 82      # vender jogador >= isso = ídolo (revolta torcida)
IDOL_REP_HIT = 4       # perda de reputação por ídolo vendido


def expected_finish(conn, club_id: int, league_id: int) -> int:
    """
    Meta de colocação = posto do clube no ranking de prestígio da liga.
    Real Madrid (maior prestígio) → espera-se 1º; lanterna de prestígio → último.
    """
    rows = conn.execute("""
        SELECT id FROM clubs WHERE league_id=? ORDER BY prestige DESC, id
    """, (league_id,)).fetchall()
    for i, r in enumerate(rows, 1):
        if r[0] == club_id:
            return i
    return max(1, len(rows) // 2)


def idol_sale_penalty(conn, career, player_overall: int) -> int:
    """Aplica perda de reputação ao vender ídolo. Retorna o hit (0 se não-ídolo)."""
    if player_overall is None or player_overall < IDOL_OVERALL:
        return 0
    # Quanto melhor, maior a revolta
    hit = IDOL_REP_HIT + (player_overall - IDOL_OVERALL) // 2
    new_rep = max(0, (career["reputation"] or 50) - hit)
    conn.execute("UPDATE career SET reputation=? WHERE id=?", (new_rep, career["id"]))
    conn.execute(
        "UPDATE coaches SET reputation=? WHERE career_id=? AND is_player=1",
        (new_rep, career["id"])
    )
    conn.commit()
    return hit


def season_reputation(conn, career, actual_pos: int, n_clubs: int,
                      won_title: bool, fin: dict) -> dict:
    """
    Calcula e aplica variação de reputação ao fim da temporada.
    Retorna relatório {delta, reasons[], new_rep, sacked, warned, expectation}.
    """
    expectation = career["expectation"]
    if expectation is None:
        expectation = max(1, n_clubs // 2)

    reasons = []
    delta = 0

    # 1. Campanha vs expectativa (fator principal)
    diff = expectation - actual_pos     # positivo = melhor que esperado
    perf = max(-20, min(20, round(diff * 1.6)))
    delta += perf
    if diff >= 3:
        reasons.append(f"📈 Superou a meta ({actual_pos}º vs meta {expectation}º): +{perf}")
    elif diff <= -3:
        reasons.append(f"📉 Frustrou a meta ({actual_pos}º vs meta {expectation}º): {perf}")
    else:
        reasons.append(f"➖ Campanha dentro do esperado ({actual_pos}º): {perf:+d}")

    # 2. Título
    if won_title:
        delta += 12
        reasons.append("🏆 Título conquistado: +12")

    # 3. Rebaixamento (zona = 3 últimos)
    if actual_pos > n_clubs - 3:
        delta -= 15
        reasons.append("⬇️ Zona de rebaixamento: -15")

    # 4. Saúde financeira
    if fin.get("bankrupt"):
        delta -= 10
        reasons.append("💸 Caixa negativo: -10")
    elif fin.get("net", 0) > 0 and fin.get("money_after", 0) > 20_000_000:
        delta += 2
        reasons.append("💰 Finanças saudáveis: +2")

    old_rep = career["reputation"] or 50
    new_rep = max(0, min(100, old_rep + delta))
    conn.execute("UPDATE career SET reputation=? WHERE id=?", (new_rep, career["id"]))

    # 5. Job security
    warnings = career["warnings"] or 0
    sacked = False
    warned = False
    if new_rep < SACK_REP:
        sacked = True
    elif new_rep < WARN_REP:
        warnings += 1
        warned = True
        if warnings >= 2:
            sacked = True
    else:
        warnings = 0   # reseta advertências em temporada boa

    conn.execute("UPDATE career SET warnings=? WHERE id=?", (warnings, career["id"]))
    if sacked:
        conn.execute("UPDATE career SET status='sacked' WHERE id=?", (career["id"],))
    # Espelha reputação no registro de técnico do humano
    conn.execute(
        "UPDATE coaches SET reputation=?, warnings=? WHERE career_id=? AND is_player=1",
        (new_rep, warnings, career["id"])
    )
    conn.commit()

    return {
        "delta": delta, "reasons": reasons, "old_rep": old_rep, "new_rep": new_rep,
        "sacked": sacked, "warned": warned, "warnings": warnings,
        "expectation": expectation,
    }


def occupy_club(conn, club_id: int):
    """Libera o técnico IA do clube (o humano assume como técnico)."""
    conn.execute(
        "UPDATE coaches SET club_id=NULL, warnings=0 WHERE club_id=? AND is_player=0",
        (club_id,)
    )
    conn.commit()


def create_player_coach(conn, career, name: str):
    """Cria o registro de técnico do humano (is_player=1) no clube atual."""
    occupy_club(conn, career["manager_club_id"])
    # Idade inicial aleatória plausível
    conn.execute("""
        INSERT INTO coaches(name, nationality, reputation, club_id, age, is_player, career_id)
        VALUES (?, ?, ?, ?, ?, 1, ?)
    """, (name, "—", career["reputation"] or 50, career["manager_club_id"],
          45, career["id"]))
    conn.commit()


def sync_player_coach(conn, career):
    """Mantém o registro de técnico do humano coerente (clube + reputação + status)."""
    row = conn.execute(
        "SELECT id FROM coaches WHERE career_id=? AND is_player=1", (career["id"],)
    ).fetchone()
    if not row:
        return
    active = (career["status"] == "active")
    conn.execute("""
        UPDATE coaches SET club_id=?, reputation=?, retired=? WHERE id=?
    """, (career["manager_club_id"] if active else None,
          career["reputation"] or 50, 0 if active else 1, row[0]))
    conn.commit()


def player_coach_name(conn, career) -> str:
    row = conn.execute(
        "SELECT name FROM coaches WHERE career_id=? AND is_player=1", (career["id"],)
    ).fetchone()
    return row[0] if row else "Técnico"


def set_expectation(conn, career):
    """Define a meta do conselho para a temporada atual."""
    club_id = career["manager_club_id"]
    league_id = conn.execute("SELECT league_id FROM clubs WHERE id=?", (club_id,)).fetchone()[0]
    exp = expected_finish(conn, club_id, league_id)
    conn.execute("UPDATE career SET expectation=? WHERE id=?", (exp, career["id"]))
    conn.commit()
    return exp
