"""
FUTMANAGER — Match Simulation Engine
Poisson-based probabilistic match simulator.
"""
from __future__ import annotations
import math
import random
from dataclasses import dataclass
from typing import Optional
from db.models import Club, Match


def _poisson(lam: float) -> int:
    """
    Amostra de distribuição de Poisson — algoritmo de Knuth.
    Substitui numpy.random.poisson (zero dependências externas).
    """
    if lam <= 0:
        return 0
    if lam > 30:
        # Aproximação normal para lambda alto (evita underflow do exp)
        val = round(random.gauss(lam, math.sqrt(lam)))
        return max(0, val)
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1


# Fator de vantagem em casa (histórico futebol mundial ~1.3)
HOME_ADVANTAGE = 1.25

# Constante de escala: converte rating médio em gols esperados por jogo
# Rating 75 atacante vs Rating 75 defesa → ~1.5 gols esperados (média mundial)
SCALE_FACTOR = 0.022  # calibrado: avg ~1.3 gols/time/jogo (média Brasileirão)


@dataclass
class MatchResult:
    home_id: int
    away_id: int
    home_goals: int
    away_goals: int
    home_scorers: list[str]
    away_scorers: list[str]
    events: list[str]       # log textual da partida

    @property
    def winner(self) -> Optional[int]:
        if self.home_goals > self.away_goals:
            return self.home_id
        if self.away_goals > self.home_goals:
            return self.away_id
        return None

    @property
    def summary(self) -> str:
        return f"{self.home_goals} x {self.away_goals}"


def _expected_goals(attack: float, defense: float, home: bool) -> float:
    """
    Calcula gols esperados (lambda para Poisson).
    attack e defense: ratings 1–99.
    """
    ratio = attack / max(defense, 1.0)
    base = ratio * SCALE_FACTOR * 50  # normaliza para escala de gols
    if home:
        base *= HOME_ADVANTAGE
    # clamp entre 0.2 (time muito ruim) e 5.0 (goleada absurda)
    return max(0.2, min(5.0, base))


def _pick_scorers(club: Club, n_goals: int) -> list[str]:
    """Seleciona marcadores de gols probabilisticamente por finishing."""
    candidates = [p for p in club.players if p.position in ("FW", "MF")]
    if not candidates:
        candidates = club.players
    if not candidates:
        return [f"Jogador desconhecido"] * n_goals

    weights = [max(1, p.finishing) for p in candidates]
    total = sum(weights)
    probs = [w / total for w in weights]

    scorers = []
    for _ in range(n_goals):
        scorer = random.choices(candidates, weights=probs, k=1)[0]
        scorers.append(scorer.name)
    return scorers


def simulate_match(home: Club, away: Club, verbose: bool = False) -> MatchResult:
    """
    Simula uma partida entre dois clubes.
    Usa distribuição de Poisson para gols.
    """
    # Ratings de ataque e defesa
    home_atk = home.attack_rating
    away_atk = away.attack_rating
    home_def = home.defense_rating
    away_def = away.defense_rating

    # Moral/forma — atacante embalado rende mais
    home_morale = getattr(home, "morale", 1.0)
    away_morale = getattr(away, "morale", 1.0)
    # Coesão do XI (squad dynamics — afinidade entre titulares, 0.95–1.05)
    home_cohesion = getattr(home, "cohesion", 1.0)
    away_cohesion = getattr(away, "cohesion", 1.0)
    # Estilo tático — ofensivo sobe ataque/baixa defesa; defensivo o inverso
    h_satk = getattr(home, "style_atk", 1.0); h_sdef = getattr(home, "style_def", 1.0)
    a_satk = getattr(away, "style_atk", 1.0); a_sdef = getattr(away, "style_def", 1.0)

    # Lambda (gols esperados)
    lam_home = _expected_goals(home_atk * home_morale * home_cohesion * h_satk,
                               away_def * a_sdef, home=True)
    lam_away = _expected_goals(away_atk * away_morale * away_cohesion * a_satk,
                               home_def * h_sdef, home=False)

    # Simula gols via Poisson
    home_goals = _poisson(lam_home)
    away_goals = _poisson(lam_away)

    # Marcadores
    home_scorers = _pick_scorers(home, home_goals)
    away_scorers = _pick_scorers(away, away_goals)

    # Log de eventos
    events = _generate_events(
        home.name, away.name,
        home_goals, away_goals,
        home_scorers, away_scorers
    )

    return MatchResult(
        home_id=home.id,
        away_id=away.id,
        home_goals=home_goals,
        away_goals=away_goals,
        home_scorers=home_scorers,
        away_scorers=away_scorers,
        events=events,
    )


def _generate_events(
    home_name: str, away_name: str,
    home_goals: int, away_goals: int,
    home_scorers: list[str], away_scorers: list[str]
) -> list[str]:
    """Gera log de eventos da partida com minutos aleatórios."""
    events = []
    # Distribui gols em minutos aleatórios (1–90)
    goal_minutes = sorted(random.sample(range(1, 91), min(home_goals + away_goals, 40)))

    hi, ai = 0, 0
    total = home_goals + away_goals

    for i, minute in enumerate(goal_minutes[:total]):
        # Alterna gols proporcionalmente
        home_share = home_goals / max(total, 1)
        if hi < home_goals and (ai >= away_goals or random.random() < home_share):
            events.append(f"⚽ {minute}' {home_scorers[hi]} ({home_name})")
            hi += 1
        elif ai < away_goals:
            events.append(f"⚽ {minute}' {away_scorers[ai]} ({away_name})")
            ai += 1

    # Preenche restantes
    while hi < home_goals:
        minute = random.randint(1, 90)
        events.append(f"⚽ {minute}' {home_scorers[hi]} ({home_name})")
        hi += 1
    while ai < away_goals:
        minute = random.randint(1, 90)
        events.append(f"⚽ {minute}' {away_scorers[ai]} ({away_name})")
        ai += 1

    events.sort(key=lambda e: int(e.split("'")[0].split(" ")[-1]) if "'" in e else 0)
    return events


def simulate_penalties(home: Club, away: Club) -> tuple[int, int]:
    """
    Simula disputa de pênaltis (5 cobranças por lado).
    Retorna (home_pen, away_pen).
    """
    def penalty_score(club: Club) -> int:
        gk = next((p for p in club.players if p.position == "GK"), None)
        gk_rating = gk.goalkeeping if gk else 50
        shots = 5
        goals = 0
        for _ in range(shots):
            # 75% base de conversão, afetada por GK
            save_prob = (gk_rating - 50) / 200  # ±25%
            if random.random() > (0.25 + save_prob):
                goals += 1
        return goals

    return penalty_score(home), penalty_score(away)
