"""
FUTMANAGER — Data Models
Thin wrappers over SQLite rows. No ORM overhead.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Country:
    id: int
    code: str
    name: str


@dataclass
class League:
    id: int
    name: str
    country_id: int
    level: int
    season: str


@dataclass
class Club:
    id: int
    name: str
    short_name: str
    league_id: int
    prestige: int = 50
    stadium: str = ""
    founded: Optional[int] = None
    source_id: Optional[str] = None

    # carregado em runtime, não no DB direto
    players: list["Player"] = field(default_factory=list)
    starting_xi: list["Player"] = field(default_factory=list)  # escalação (se vazio, usa top-11)
    morale: float = 1.0      # 0.85–1.15 — sobe com vitórias, cai com derrotas
    cohesion: float = 1.0    # 0.95–1.05 — afinidade entre titulares (squad dynamics)
    style_atk: float = 1.0   # mentalidade: multiplicador de ataque
    style_def: float = 1.0   # mentalidade: multiplicador de defesa

    @property
    def lineup(self) -> list["Player"]:
        """11 que jogam: escalação salva, ou top-11 por overall."""
        if self.starting_xi:
            return self.starting_xi
        return sorted(self.players, key=lambda p: p.overall, reverse=True)[:11]

    @property
    def bench(self) -> list["Player"]:
        xi_ids = {p.id for p in self.lineup}
        return [p for p in self.players if p.id not in xi_ids]

    @property
    def attack_rating(self) -> float:
        fwd = [p for p in self.lineup if p.position in ("FW", "MF")]
        if not fwd:
            return 50.0
        return sum(p.attack_score * p.condition_mult for p in fwd) / len(fwd)

    @property
    def defense_rating(self) -> float:
        defs = [p for p in self.lineup if p.position in ("DF", "GK")]
        if not defs:
            return 50.0
        return sum(p.defense_score * p.condition_mult for p in defs) / len(defs)

    @property
    def overall_rating(self) -> float:
        if not self.players:
            return float(self.prestige)
        return sum(p.overall for p in self.players) / len(self.players)


@dataclass
class Player:
    id: int
    name: str
    position: str           # GK | DF | MF | FW
    nationality: str
    birth_date: Optional[str]
    club_id: Optional[int]

    # Atributos (1–99)
    pace: int = 50
    technique: int = 50
    strength: int = 50
    finishing: int = 50
    passing: int = 50
    defending: int = 50
    goalkeeping: int = 50
    stamina: int = 50
    mental: int = 50

    overall: int = 50
    source: str = "generated"

    # Carreira / rotação
    age: int = 0
    wage: int = 0
    contract_until: Optional[int] = None
    form: float = 1.0       # 0.85–1.15 — tendência recente (gols, vitórias)
    fitness: int = 100      # 0-100 — condição física atual (cai jogando, recupera descansando)

    @property
    def condition_mult(self) -> float:
        """Combina forma + condição física num único multiplicador de desempenho."""
        fit_mult = 0.85 + 0.15 * max(0, min(100, self.fitness)) / 100
        return max(0.7, min(1.2, self.form * fit_mult))

    @property
    def attack_score(self) -> float:
        """Contribuição ofensiva ponderada por posição."""
        if self.position == "FW":
            return self.finishing * 0.4 + self.technique * 0.25 + self.pace * 0.2 + self.passing * 0.15
        if self.position == "MF":
            return self.passing * 0.35 + self.technique * 0.3 + self.finishing * 0.2 + self.mental * 0.15
        if self.position == "DF":
            return self.passing * 0.4 + self.strength * 0.3 + self.mental * 0.3
        return self.goalkeeping * 0.1  # GK

    @property
    def defense_score(self) -> float:
        """Contribuição defensiva ponderada por posição."""
        if self.position == "GK":
            return self.goalkeeping * 0.7 + self.mental * 0.2 + self.strength * 0.1
        if self.position == "DF":
            return self.defending * 0.45 + self.strength * 0.25 + self.pace * 0.15 + self.mental * 0.15
        if self.position == "MF":
            return self.defending * 0.35 + self.mental * 0.3 + self.strength * 0.2 + self.stamina * 0.15
        return self.pace * 0.3 + self.mental * 0.3 + self.technique * 0.4  # FW defending

    @staticmethod
    def calc_overall(pos: str, attrs: dict) -> int:
        """Calcula overall ponderado por posição."""
        weights = {
            "GK": {"goalkeeping": 0.5, "mental": 0.2, "strength": 0.15, "pace": 0.15},
            "DF": {"defending": 0.4, "strength": 0.2, "pace": 0.15, "mental": 0.15, "passing": 0.1},
            "MF": {"passing": 0.3, "technique": 0.25, "mental": 0.2, "stamina": 0.15, "defending": 0.1},
            "FW": {"finishing": 0.35, "technique": 0.25, "pace": 0.2, "strength": 0.1, "mental": 0.1},
        }
        w = weights.get(pos, weights["MF"])
        score = sum(attrs.get(attr, 50) * weight for attr, weight in w.items())
        return max(1, min(99, round(score)))


@dataclass
class Match:
    id: int
    round_id: int
    home_id: int
    away_id: int
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    played: bool = False

    @property
    def result(self) -> Optional[str]:
        if not self.played:
            return None
        if self.home_goals > self.away_goals:
            return "home"
        if self.away_goals > self.home_goals:
            return "away"
        return "draw"


@dataclass
class Standing:
    club_id: int
    club_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    gf: int = 0
    ga: int = 0
    yellows: int = 0
    reds: int = 0

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def gd(self) -> int:
        return self.gf - self.ga

    def update(self, scored: int, conceded: int, yellows: int = 0, reds: int = 0):
        self.played += 1
        self.gf += scored
        self.ga += conceded
        self.yellows += yellows
        self.reds += reds
        if scored > conceded:
            self.wins += 1
        elif scored == conceded:
            self.draws += 1
        else:
            self.losses += 1
