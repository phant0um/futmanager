"""
FUTMANAGER — Relações entre jogadores (squad dynamics, CM03/04)
GDD: "relações precisam ser jogáveis, não flavor text" — afinidades reais
entre companheiros de elenco, com efeito pequeno e mensurável na coesão
(modificador na partida, mesma escala/lugar de `morale`), sem tocar
overall/contrato/simulação de transferências.

Determinístico — gerado 1x por par relevante (heurística: nacionalidade/
idade/setor tático), seed por hash(career, par ordenado). Escopo: só
elenco do técnico humano (custo de I/O em 14k+ jogadores de IA não
compensa — mesmo corte de `injury`/`scouting`).
"""
from __future__ import annotations
import hashlib
import random

KIND_LABELS = {
    "amizade": "🤝 Amizade", "parceria": "⚡ Parceria de campo",
    "rivalidade": "⚔️ Rivalidade", "mentoria": "🎓 Mentoria",
}

# setor tático por posição — pares do mesmo setor têm mais chance de vínculo
SECTOR = {"GK": "def", "DF": "def", "MF": "mid", "FW": "att"}

MAX_PAIRS_PER_PLAYER = 3   # evita N² (elenco de 25+ → ruído visual)


def _seed_for(career_id: int, a: int, b: int) -> int:
    lo, hi = (a, b) if a < b else (b, a)
    return int(hashlib.md5(f"relationship:{career_id}:{lo}:{hi}".encode()).hexdigest(), 16) % (2**31)


def _candidate_score(rng: random.Random, pa: dict, pb: dict) -> float:
    """Quanto maior, mais provável formar vínculo — heurística simples e
    explicável: mesma nacionalidade, idade próxima, mesmo setor tático."""
    score = rng.uniform(0.0, 1.0)
    if pa["nationality"] and pa["nationality"] == pb["nationality"]:
        score += 0.6
    if abs((pa["age"] or 25) - (pb["age"] or 25)) <= 3:
        score += 0.3
    if SECTOR.get(pa["position"]) == SECTOR.get(pb["position"]):
        score += 0.25
    return score


def _roll_kind_and_affinity(rng: random.Random, pa: dict, pb: dict) -> tuple[str, int]:
    """Define tipo de vínculo + intensidade (-100..100). Mentoria pede gap
    de idade relevante (veterano formando jovem); resto é aleatório
    ponderado — vida de vestiário tem mais afinidade que conflito."""
    age_gap = (pa["age"] or 25) - (pb["age"] or 25)
    if abs(age_gap) >= 8:
        return "mentoria", rng.randint(40, 85)
    roll = rng.random()
    if roll < 0.45:
        return "amizade", rng.randint(35, 90)
    if roll < 0.75:
        return "parceria", rng.randint(30, 80)
    return "rivalidade", -rng.randint(20, 75)


def seed_relationships(conn, career, club_id: int) -> int:
    """Gera (se ainda não existir) relações pro elenco de `club_id`. Idempotente
    — usa UNIQUE(career_id, player_a_id, player_b_id) + INSERT OR IGNORE.
    Retorna nº de pares criados (0 se já existia ou elenco pequeno demais)."""
    existing = conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE career_id=?", (career["id"],)
    ).fetchone()[0]
    if existing:
        return 0

    squad = conn.execute(
        "SELECT id, name, position, age, nationality FROM players "
        "WHERE club_id=? AND retired=0", (club_id,)
    ).fetchall()
    if len(squad) < 2:
        return 0
    players = [dict(p) for p in squad]

    created = 0
    pair_count = {p["id"]: 0 for p in players}
    pairs = []
    for i, pa in enumerate(players):
        for pb in players[i + 1:]:
            seed = _seed_for(career["id"], pa["id"], pb["id"])
            rng = random.Random(seed)
            pairs.append((_candidate_score(rng, pa, pb), pa, pb, seed))
    pairs.sort(key=lambda t: -t[0])

    for score, pa, pb, seed in pairs:
        if score < 0.9:
            continue
        if pair_count[pa["id"]] >= MAX_PAIRS_PER_PLAYER or pair_count[pb["id"]] >= MAX_PAIRS_PER_PLAYER:
            continue
        rng = random.Random(seed ^ 0x5EED)
        kind, affinity = _roll_kind_and_affinity(rng, pa, pb)
        conn.execute(
            "INSERT OR IGNORE INTO relationships (career_id, player_a_id, player_b_id, kind, affinity) "
            "VALUES (?,?,?,?,?)",
            (career["id"], pa["id"], pb["id"], kind, affinity)
        )
        pair_count[pa["id"]] += 1
        pair_count[pb["id"]] += 1
        created += 1
    conn.commit()
    return created


def notable_relations(conn, career, player_id: int) -> list[dict]:
    """Lista vínculos de um jogador, com nome do parceiro/rival — pro perfil."""
    # 1 query com JOIN — era 1 SELECT extra por vínculo (N+1)
    rows = conn.execute("""
        SELECT r.kind, r.affinity,
               CASE WHEN r.player_a_id=? THEN r.player_b_id ELSE r.player_a_id END AS other_id,
               p.name AS other_name
        FROM relationships r
        JOIN players p
          ON p.id = (CASE WHEN r.player_a_id=? THEN r.player_b_id ELSE r.player_a_id END)
        WHERE r.career_id=? AND (r.player_a_id=? OR r.player_b_id=?)
        ORDER BY ABS(r.affinity) DESC
    """, (player_id, player_id, career["id"], player_id, player_id)).fetchall()
    return [{
        "kind": r["kind"], "label": KIND_LABELS.get(r["kind"], r["kind"]),
        "affinity": r["affinity"], "other_id": r["other_id"], "other_name": r["other_name"],
    } for r in rows]


def unit_cohesion(conn, career, player_ids: list[int]) -> float:
    """Modificador agregado de coesão pro XI (ou setor) — pequeno, multiplicativo,
    mesma escala de `morale` (0.85–1.15). Pares positivos juntos no XI somam,
    rivais juntos subtraem; gente de fora (sem vínculo mapeado) é neutra."""
    if len(player_ids) < 2:
        return 1.0
    ids = set(player_ids)
    rows = conn.execute("""
        SELECT player_a_id, player_b_id, affinity FROM relationships
        WHERE career_id=? AND player_a_id IN ({}) AND player_b_id IN ({})
    """.format(",".join("?" * len(ids)), ",".join("?" * len(ids))),
        (career["id"], *ids, *ids)).fetchall()
    if not rows:
        return 1.0
    total = sum(r["affinity"] for r in rows if r["player_a_id"] in ids and r["player_b_id"] in ids)
    avg = total / max(1, len(rows))
    # normaliza afinidade média (-100..100) pra faixa ±5%
    return max(0.95, min(1.05, 1.0 + (avg / 100.0) * 0.05))
