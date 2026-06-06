"""
FUTMANAGER — Copas (mata-mata)
Torneios eliminatórios: Copa Nacional (clubes da liga) e Copa Continental
(melhores do mundo). Empate → pênaltis. Reusa o motor de partida.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from engine.simulation import simulate_match, simulate_penalties

STAGE_NAMES = {16: "Oitavas", 8: "Quartas", 4: "Semifinal", 2: "Final"}


@dataclass
class CupResult:
    name: str
    champion = None
    runner_up = None
    player_stage: str = "—"      # até onde o clube do jogador foi
    player_champion: bool = False
    log: list = field(default_factory=list)   # linhas de resultado por fase


def _largest_pow2(n: int) -> int:
    p = 1
    while p * 2 <= n:
        p *= 2
    return p


def _seed_bracket(clubs: list) -> list:
    """Chaveamento por seed: 1×N, 2×N-1… (melhores evitam-se cedo)."""
    n = len(clubs)
    pairs = []
    for i in range(n // 2):
        pairs.append((clubs[i], clubs[n - 1 - i]))
    return pairs


def run_cup(name: str, clubs: list, watch_club_id=None, on_match=None) -> CupResult:
    """
    clubs: ordenados por força/colocação (melhor primeiro).
    on_match(home, away) -> result : opcional, p/ transmitir jogo do jogador.
    """
    res = CupResult(name=name)
    size = _largest_pow2(len(clubs))
    remaining = clubs[:size]            # top-N entram
    res.player_stage = "Não classificado" if not any(c.id == watch_club_id for c in remaining) else "Fase de grupos"

    while len(remaining) > 1:
        stage = STAGE_NAMES.get(len(remaining), f"Rodada de {len(remaining)}")
        pairs = _seed_bracket(remaining)
        winners = []
        stage_lines = [f"  ── {name} · {stage} ──"]
        for home, away in pairs:
            is_player = watch_club_id in (home.id, away.id)
            if is_player and on_match:
                r = on_match(home, away)
            else:
                r = simulate_match(home, away)
            hg, ag = r.home_goals, r.away_goals
            extra = ""
            if hg == ag:
                hp, ap = simulate_penalties(home, away)
                winner = home if hp >= ap else away
                extra = f" ({hp}-{ap} pên)"
            else:
                winner = home if hg > ag else away
            winners.append(winner)
            mark = " ◀" if is_player else ""
            stage_lines.append(f"     {home.name} {hg}-{ag} {away.name}{extra} → {winner.name}{mark}")
            if is_player and watch_club_id != winner.id:
                res.player_stage = stage   # eliminado nesta fase
        res.log.append("\n".join(stage_lines))
        remaining = winners

    champ = remaining[0]
    res.champion = champ
    if watch_club_id == champ.id:
        res.player_champion = True
        res.player_stage = "CAMPEÃO 🏆"
    return res
