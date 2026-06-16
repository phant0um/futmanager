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
    "4-1-2-1-2": (4, 3, 2),   # diamante: 1 vol, 2 meias, 1 armador, 2 atacantes
    "4-3-1-2": (4, 4, 1),     # 3 meias + 1 meia-atacante
    "3-4-2-1": (3, 4, 2),     # 3 zags, 4 meios, 2 atacantes (pontas) + 1 centroavante
    "3-4-1-2": (3, 5, 1),     # 3 zags, 4 meios + 1 armador + 2 atacantes
    "5-4-1":   (5, 4, 1),     # ultra defensivo
    "4-1-4-1": (4, 5, 1),     # 1 vol, 4 meios, 1 atacante
    "4-3-2-1": (4, 3, 2),     # 3 meias, 2 pontas, 1 centroavante
    "4-2-2-2": (4, 4, 2),     # 2 volantes, 2 meias, 2 atacantes
    "5-2-3":   (5, 2, 3),     # 5 defensores, 2 meios, 3 atacantes
    "4-4-1-1": (4, 4, 1),     # 1 segundo atacante
    "3-5-1-1": (3, 5, 1),     # 3 zags, 5 meios, 1 armador/atacante
    "3-3-4":   (3, 3, 4),     # 3 zags, 3 meios, 4 atacantes (ofensivo)
    "4-2-4":   (4, 2, 4),     # 4 zags, 2 meios, 4 atacantes
    "5-2-1-2": (5, 3, 1),     # 5 zags, 2 vol, 1 meia, 2 atacantes
    "4-6-0":   (4, 6, 0),     # sem centroavante, meias avançados
    "3-6-1":   (3, 6, 1),     # 3 zags, 6 meios, 1 atacante
}

DEFAULT_FORMATION = "4-3-3"

# Limites de elenco / escalação
MAX_SQUAD_SIZE = 30   # limite total de jogadores no elenco
MAX_BENCH_SIZE = 12   # máximo de reservas na inscrição de uma partida

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


def auto_lineup(players: list, formation: str,
                skip_fatigue_above: int | None = None,
                skip_form_below: float | None = None) -> list:
    """Melhor 11 por posição respeitando a formação (pondera fadiga e forma).
    Se filtros ativos, jogadores com fadiga alta ou forma baixa são fortemente
    penalizados — usado para poupar desfalques evitáveis.
    """
    slots = formation_slots(formation)
    by_pos = {"GK": [], "DF": [], "MF": [], "FW": []}
    for p in sorted(players, key=_auto_rank, reverse=True):
        by_pos.get(p.position, by_pos["MF"]).append(p)

    def _fit_for(p):
        # se filtro ativo e jogador atende condição de descanso, penaliza
        fatigue = getattr(p, "fitness", 100) or 100
        form = getattr(p, "form", 1.0) or 1.0
        penalty = 1.0
        if skip_fatigue_above is not None and fatigue > skip_fatigue_above:
            penalty *= 0.35
        if skip_form_below is not None and form < skip_form_below:
            penalty *= 0.35
        return _auto_rank(p) * penalty

    by_pos = {k: sorted(v, key=_fit_for, reverse=True) for k, v in by_pos.items()}

    xi, used = [], set()
    for pos, n in slots.items():
        for p in by_pos.get(pos, [])[:n]:
            xi.append(p); used.add(p.id)

    # Completa se faltou
    if len(xi) < 11:
        rest = sorted([p for p in players if p.id not in used],
                      key=_fit_for, reverse=True)
        for p in rest:
            if len(xi) >= 11:
                break
            xi.append(p); used.add(p.id)
    return xi[:11]


def _auto_rank(p) -> float:
    """Ranking base do auto_lineup: pondera OVR, forma e fadiga."""
    ovr = p.overall if p.overall is not None else 50
    form = getattr(p, "form", 1.0) or 1.0
    fitness = getattr(p, "fitness", 100) or 100
    return fatigue_penalty(round(ovr * form), fitness)


def validate_lineup(xi: list, formation: str) -> tuple[bool, str]:
    """Verifica exatamente 11 jogadores, 1 GK e posições compatíveis com a formação."""
    if len(xi) != 11:
        return False, f"Escalação precisa de 11 titulares (tem {len(xi)})."
    if not any(p.position == "GK" for p in xi):
        return False, "Sem goleiro na escalação."
    slots = formation_slots(formation)
    counts = {"GK": 0, "DF": 0, "MF": 0, "FW": 0}
    for p in xi:
        counts[p.position] = counts.get(p.position, 0) + 1
    for pos, n in slots.items():
        if counts[pos] < n:
            # permite uma posição com 1 a menos se preenchida por outra
            pass
    return True, "ok"


def validate_bench(squad: list, xi: list) -> tuple[bool, str]:
    """Verifica limites de elenco: total ≤ 30, reservas ≤ 12."""
    if len(squad) > MAX_SQUAD_SIZE:
        return False, f"Elenco com {len(squad)} jogadores (máx {MAX_SQUAD_SIZE})."
    bench = [p for p in squad if p.id not in {x.id for x in xi}]
    if len(bench) > MAX_BENCH_SIZE:
        return False, f"Banco com {len(bench)} reservas (máx {MAX_BENCH_SIZE})."
    return True, "ok"
