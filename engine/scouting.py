"""
FUTMANAGER — Scouting (olheiros)
Manda olheiro investigar um jogador: custa caixa, confirma um subconjunto de
atributos (sobrescreve a faixa do masking — engine/knowledge — com o valor
real). Quanto maior o prestígio do clube (rede/orçamento de scouting), mais
atributos confirmados e maior confiança do relatório.
Determinístico: hash(career, player, season) decide quais atributos saem
confirmados — sem RANDOM() do SQLite, mesmo padrão de incoming_offers/transfer.
"""
from __future__ import annotations
import hashlib
import json
import random

from engine.knowledge import ATTRS

# Atributos "chave" por posição — relatório prioriza o que importa pro papel
_KEY_ATTRS = {
    "GK": ("goalkeeping", "mental", "stamina"),
    "DF": ("defending", "strength", "mental"),
    "MF": ("passing", "technique", "stamina"),
    "FW": ("finishing", "pace", "technique"),
}


def _rng(career_id: int, player_id: int, season_year: int) -> random.Random:
    digest = hashlib.md5(f"scout:{career_id}:{player_id}:{season_year}".encode()).digest()
    return random.Random(digest)


def scout_cost(overall: int | None) -> int:
    """Custo da missão — cresce com a qualidade do alvo (clubes grandes
    escondem melhor seus craques, exige investigação mais cara)."""
    ovr = overall or 60
    return max(40_000, (ovr - 40) * 6_000)


def scout_quality(prestige: int | None) -> tuple[int, int]:
    """(n_attrs revelados, confiança%) — função do prestígio/orçamento do
    clube que manda o olheiro. Clube grande = rede melhor = relatório melhor."""
    prestige = prestige or 50
    n = 3 + prestige // 22       # prestígio 30→4, 60→5, 90→7 (máx 9)
    conf = min(95, 45 + prestige // 2)
    return min(len(ATTRS), n), conf


def run_scout(conn, career, player_id: int) -> dict:
    """Executa a missão, persiste relatório (merge com confirmações antigas),
    debita o custo. Retorna {ok, msg, cost, confirmed, confidence}."""
    p = conn.execute(
        "SELECT id, name, position, overall, club_id FROM players WHERE id=?",
        (player_id,)
    ).fetchone()
    if not p:
        return {"ok": False, "msg": "Jogador não encontrado."}
    if p["club_id"] == career["manager_club_id"]:
        return {"ok": False, "msg": "Já é do seu elenco — você já conhece tudo dele."}

    cost = scout_cost(p["overall"])
    if (career["money"] or 0) < cost:
        return {"ok": False, "msg": f"Caixa insuficiente — missão custa {cost:,}".replace(",", ".")}

    buyer = conn.execute("SELECT prestige FROM clubs WHERE id=?",
                         (career["manager_club_id"],)).fetchone()
    n_reveal, confidence = scout_quality(buyer["prestige"] if buyer else 50)

    rng = _rng(career["id"], player_id, career["season_year"])
    key = list(_KEY_ATTRS.get(p["position"], ()))
    rest = [a for a in ATTRS if a not in key]
    rng.shuffle(key)
    rng.shuffle(rest)
    pick = (key + rest)[:n_reveal]

    row = conn.execute(
        "SELECT confirmed_attrs FROM scout_reports WHERE career_id=? AND player_id=?",
        (career["id"], player_id)
    ).fetchone()
    prev = set(json.loads(row["confirmed_attrs"])) if row else set()
    confirmed = sorted(prev | set(pick))

    if row:
        conn.execute(
            "UPDATE scout_reports SET confirmed_attrs=?, confidence=?, created_round=? "
            "WHERE career_id=? AND player_id=?",
            (json.dumps(confirmed), confidence, career["current_round"] or 0, career["id"], player_id)
        )
    else:
        conn.execute(
            "INSERT INTO scout_reports (career_id, player_id, confirmed_attrs, confidence, created_round) "
            "VALUES (?,?,?,?,?)",
            (career["id"], player_id, json.dumps(confirmed), confidence, career["current_round"] or 0)
        )
    conn.execute("UPDATE career SET money=money-? WHERE id=?", (cost, career["id"]))
    conn.commit()
    from engine.inbox import add_message
    add_message(conn, career["id"], career["current_round"] or 0, "scout_report",
                f"🔎 Relatório de scouting — {p['name']}",
                f"{p['name']} ({p['position']}, OVR ~{p['overall']}) investigado.\n"
                f"{len(confirmed)} atributos confirmados, confiança {confidence}%.\n"
                f"Custo da missão: {cost:,}".replace(",", "."),
                ref_type="player", ref_id=player_id)
    return {"ok": True, "msg": f"Relatório de {p['name']} pronto — {len(confirmed)} atributos confirmados.",
            "cost": cost, "confirmed": confirmed, "confidence": confidence}


def confirmed_attrs(conn, career_id: int, player_id: int) -> set[str]:
    row = conn.execute(
        "SELECT confirmed_attrs FROM scout_reports WHERE career_id=? AND player_id=?",
        (career_id, player_id)
    ).fetchone()
    return set(json.loads(row["confirmed_attrs"])) if row else set()
