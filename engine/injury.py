"""
FUTMANAGER — Lesões reais (não cosméticas)
Hoje `engine/live.py` só gera "🚑 contusão → troca" como flavor de texto.
Aqui a contusão vira mecânica persistente: tipo + tempo de recuperação,
queda de fitness, decisão de cirurgia (acelera mas custa caro e tem risco).
Aplicado só ao elenco do técnico humano — IA não precisa de gestão médica
(balanceamento e custo de I/O em 14k+ jogadores não compensa o ganho).
Determinístico via hash(career, player, round) — sem RANDOM() do SQLite.
"""
from __future__ import annotations
import hashlib
import random

# (nome, semanas mín, semanas máx, gravidade, queda de fitness)
INJURY_TYPES = (
    ("Lesão muscular",      1,  3, "leve",  25),
    ("Estiramento",         1,  2, "leve",  20),
    ("Entorse de tornozelo",2,  4, "leve",  30),
    ("Lesão no joelho",     4,  8, "média", 50),
    ("Lesão no tendão",     3,  6, "média", 45),
    ("Fratura",             8, 16, "grave", 70),
)

SURGERY_CUT = 0.45          # cirurgia reduz ~45% do tempo restante
SURGERY_RISK = 0.12         # chance de complicação (some semanas voltam)
SURGERY_BASE_COST = 180_000


def _rng(career_id: int, player_id: int, round_no: int, salt: str = "") -> random.Random:
    digest = hashlib.md5(f"injury:{salt}:{career_id}:{player_id}:{round_no}".encode()).digest()
    return random.Random(digest)


def roll_injury(career_id: int, player_id: int, round_no: int) -> dict:
    rng = _rng(career_id, player_id, round_no)
    name, lo, hi, severity, drop = rng.choice(INJURY_TYPES)
    weeks = rng.randint(lo, hi)
    return {"kind": name, "weeks": weeks, "severity": severity, "fitness_drop": drop}


def record_injury(conn, career, player_id: int, club_id: int, round_no: int) -> dict:
    """Persiste a lesão + aplica queda de fitness. Chamado só pro elenco do
    técnico humano (ver play_round_live)."""
    info = roll_injury(career["id"], player_id, round_no)
    conn.execute("""
        INSERT INTO injuries (career_id, player_id, club_id, kind, weeks_total,
                              weeks_left, status, season_year, round_occurred)
        VALUES (?,?,?,?,?,?, 'active', ?, ?)
    """, (career["id"], player_id, club_id, info["kind"], info["weeks"], info["weeks"],
          career["season_year"], round_no))
    conn.execute("UPDATE players SET fitness = MAX(15, fitness - ?) WHERE id=?",
                 (info["fitness_drop"], player_id))
    conn.commit()
    return info


def active_injury(conn, career_id: int, player_id: int) -> dict | None:
    row = conn.execute("""
        SELECT id, kind, weeks_total, weeks_left, surgery, status
        FROM injuries WHERE career_id=? AND player_id=? AND status='active'
        ORDER BY id DESC LIMIT 1
    """, (career_id, player_id)).fetchone()
    return dict(row) if row else None


def process_recoveries(conn, career) -> list[dict]:
    """Chamado 1x por rodada simulada (≈ 1 semana) — avança recuperação de
    todas as lesões ativas da carreira. Quem zera volta (status='recovered',
    fitness sobe pra 'apto mas precisa rodar'). Retorna recuperados nesta chamada."""
    rows = conn.execute("""
        SELECT i.id, i.player_id, i.weeks_left, p.name
        FROM injuries i JOIN players p ON p.id = i.player_id
        WHERE i.career_id=? AND i.status='active'
    """, (career["id"],)).fetchall()
    recovered = []
    for r in rows:
        left = r["weeks_left"] - 1
        if left <= 0:
            conn.execute("UPDATE injuries SET weeks_left=0, status='recovered' WHERE id=?", (r["id"],))
            conn.execute("UPDATE players SET fitness = MAX(fitness, 65) WHERE id=?", (r["player_id"],))
            recovered.append({"player_id": r["player_id"], "name": r["name"]})
        else:
            conn.execute("UPDATE injuries SET weeks_left=? WHERE id=?", (left, r["id"]))
    if rows:
        conn.commit()
    return recovered


def surgery_offer(weeks_left: int, severity: str) -> dict:
    """Oferta de cirurgia — pura. Acelera recuperação, custa caro, risco de
    complicação (sai pior do que entrou)."""
    mult = {"leve": 1.0, "média": 1.6, "grave": 2.4}.get(severity, 1.0)
    cost = int(SURGERY_BASE_COST * mult * max(1, weeks_left))
    weeks_after = max(1, int(weeks_left * (1 - SURGERY_CUT)))
    return {"cost": cost, "weeks_after": weeks_after,
            "risk_pct": int(SURGERY_RISK * 100), "weeks_saved": weeks_left - weeks_after}


def decide_surgery(conn, career, injury_id: int) -> dict:
    """Aplica a cirurgia: debita custo, recalcula semanas restantes
    (com chance determinística de complicação que adiciona semanas)."""
    inj = conn.execute("SELECT * FROM injuries WHERE id=? AND career_id=? AND status='active'",
                       (injury_id, career["id"])).fetchone()
    if not inj:
        return {"ok": False, "msg": "Lesão não encontrada ou já resolvida."}
    if inj["surgery"]:
        return {"ok": False, "msg": "Já operado nesta lesão."}
    offer = surgery_offer(inj["weeks_left"], _severity_of(inj["kind"]))
    if (career["money"] or 0) < offer["cost"]:
        return {"ok": False, "msg": f"Caixa insuficiente — cirurgia custa {offer['cost']:,}".replace(",", ".")}

    rng = _rng(career["id"], inj["player_id"], inj["round_occurred"], salt="surgery")
    complication = rng.random() < SURGERY_RISK
    weeks = offer["weeks_after"] + (rng.randint(2, 5) if complication else 0)
    conn.execute("UPDATE injuries SET surgery=1, weeks_total=?, weeks_left=? WHERE id=?",
                 (weeks, weeks, injury_id))
    conn.execute("UPDATE career SET money = money - ? WHERE id=?", (offer["cost"], career["id"]))
    conn.commit()
    return {"ok": True, "complication": complication, "weeks_after": weeks, "cost": offer["cost"]}


def _severity_of(kind: str) -> str:
    for name, _, _, severity, _ in INJURY_TYPES:
        if name == kind:
            return severity
    return "leve"
