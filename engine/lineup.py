"""
FUTMANAGER — Escalação (formação + 11 titulares)
Formações definem nº de DF/MF/FW (GK sempre 1). Auto-monta o melhor 11
respeitando a formação; jogador pode trocar titular por reserva.
"""
from __future__ import annotations

# nome → (DF, MF, FW); GK implícito = 1
FORMATIONS = {
    "4-4-2":   (4, 4, 2),
    "4-3-3":   (4, 3, 3),
    "4-2-3-1": (4, 5, 1),
    "3-5-2":   (3, 5, 2),
    "5-3-2":   (5, 3, 2),
    "3-4-3":   (3, 4, 3),
    "4-5-1":   (4, 5, 1),
}

DEFAULT_FORMATION = "4-3-3"

# Estilo tático → (mult_ataque, mult_defesa)
STYLES = {
    "ofensivo":    (1.12, 0.90),   # mais gols pró e contra
    "equilibrado": (1.00, 1.00),
    "defensivo":   (0.86, 1.12),   # trava o jogo
}

def style_mults(style: str) -> tuple:
    return STYLES.get(style, STYLES["equilibrado"])


def formation_slots(formation: str) -> dict:
    df, mf, fw = FORMATIONS.get(formation, FORMATIONS[DEFAULT_FORMATION])
    return {"GK": 1, "DF": df, "MF": mf, "FW": fw}


def fatigue_penalty(overall: int, fitness: int) -> float:
    """Rating efetivo para escalar: titular cansado vale menos — incentiva rotação.
    fitness 100 → rating cheio; fitness baixo → desconta até 30%."""
    fitness = max(0, min(100, fitness if fitness is not None else 100))
    return overall * (0.7 + 0.3 * fitness / 100)


def auto_lineup(players: list, formation: str) -> list:
    """Melhor 11 por posição respeitando a formação (pondera fadiga — joga
    quem rende mais agora, não só o de maior OVR no papel). Preenche faltas com sobras."""
    slots = formation_slots(formation)
    by_pos = {"GK": [], "DF": [], "MF": [], "FW": []}
    rank = lambda x: fatigue_penalty(x.overall, getattr(x, "fitness", 100))
    for p in sorted(players, key=rank, reverse=True):
        by_pos.get(p.position, by_pos["MF"]).append(p)

    xi, used = [], set()
    for pos, n in slots.items():
        for p in by_pos.get(pos, [])[:n]:
            xi.append(p); used.add(p.id)

    # Completa se faltou (posição sem jogadores suficientes)
    if len(xi) < 11:
        rest = sorted([p for p in players if p.id not in used],
                      key=rank, reverse=True)
        for p in rest:
            if len(xi) >= 11:
                break
            xi.append(p); used.add(p.id)
    return xi[:11]


def validate_lineup(xi: list, formation: str) -> tuple[bool, str]:
    """Verifica 11 jogadores e ao menos 1 GK."""
    if len(xi) != 11:
        return False, f"Escalação precisa de 11 (tem {len(xi)})."
    if not any(p.position == "GK" for p in xi):
        return False, "Sem goleiro na escalação."
    return True, "ok"
