"""
FUTMANAGER — Season & League Engine
Round-robin schedule, standings, promotion/relegation.
"""
from __future__ import annotations
import itertools
import random
from typing import Optional
from db.models import Club, Match, Standing
from engine.simulation import simulate_match, MatchResult

# ─── Moral ───────────────────────────────────────────────────────────────────
MORALE_MIN, MORALE_MAX = 0.85, 1.15

def _update_morale(home: Club, away: Club, hg: int, ag: int):
    """Vitória sobe moral, derrota desce. Sempre regride à média (1.0)."""
    def adj(club, delta):
        m = getattr(club, "morale", 1.0)
        m += delta
        m += (1.0 - m) * 0.15           # regressão à média
        club.morale = max(MORALE_MIN, min(MORALE_MAX, m))
    if hg > ag:
        adj(home, +0.05); adj(away, -0.05)
    elif ag > hg:
        adj(home, -0.05); adj(away, +0.05)
    else:
        adj(home, +0.01); adj(away, +0.01)  # empate quase neutro


class League:
    """
    Motor de temporada: gera calendário, simula rodadas, mantém classificação.
    """

    def __init__(self, name: str, clubs: list[Club], season: str = "2025-26"):
        self.name = name
        self.clubs = clubs
        self.season = season
        self.rounds: list[list[tuple[Club, Club]]] = []
        self.results: list[MatchResult] = []
        self.standings: dict[int, Standing] = {
            c.id: Standing(club_id=c.id, club_name=c.name)
            for c in clubs
        }
        self._club_map: dict[int, Club] = {c.id: c for c in clubs}

        self._generate_schedule()

    def _generate_schedule(self):
        """Gera calendário round-robin (ida e volta)."""
        n = len(self.clubs)
        if n % 2 != 0:
            # Adiciona bye se ímpar
            self.clubs.append(Club(id=-1, name="BYE", short_name="BYE",
                                   league_id=-1, prestige=1))
            n += 1

        clubs = self.clubs[:]
        random.shuffle(clubs)  # aleatoriza ordem

        rounds_single = []
        for round_num in range(n - 1):
            pairs = []
            for i in range(n // 2):
                home = clubs[i]
                away = clubs[n - 1 - i]
                if home.id != -1 and away.id != -1:
                    pairs.append((home, away))
            rounds_single.append(pairs)
            clubs = [clubs[0]] + [clubs[-1]] + clubs[1:-1]

        # Ida e volta (inverte mandos na segunda metade)
        self.rounds = rounds_single + [
            [(away, home) for home, away in round_]
            for round_ in rounds_single
        ]

    def simulate_round(self, round_index: int, watch_club_id=None, on_watch=None,
                       on_round=False, on_round_results=None) -> list[MatchResult]:
        """
        Simula todas as partidas de uma rodada.
        Se watch_club_id + on_watch dados, a partida desse clube usa on_watch(home,away)
        para obter o resultado (ex.: transmissão ao vivo). Demais: simulate_match.
        """
        if round_index >= len(self.rounds):
            raise IndexError(f"Rodada {round_index + 1} não existe.")

        round_results = []
        for home, away in self.rounds[round_index]:
            if on_round and on_round_results is not None:
                result = on_round_results[(home.id, away.id)]
            elif on_watch and watch_club_id in (home.id, away.id):
                result = on_watch(home, away)
            else:
                result = simulate_match(home, away)
            self.results.append(result)
            round_results.append(result)

            self.standings[home.id].update(result.home_goals, result.away_goals)
            self.standings[away.id].update(result.away_goals, result.home_goals)
            _update_morale(home, away, result.home_goals, result.away_goals)

        return round_results

    def player_round_index(self, club_id: int) -> dict:
        """Mapa round_index → adversário do clube (para saber quando ele joga)."""
        sched = {}
        for ri, pairs in enumerate(self.rounds):
            for home, away in pairs:
                if home.id == club_id:
                    sched[ri] = ("casa", away)
                elif away.id == club_id:
                    sched[ri] = ("fora", home)
        return sched

    def simulate_all(self) -> list[list[MatchResult]]:
        """Simula temporada completa."""
        all_results = []
        for i in range(len(self.rounds)):
            all_results.append(self.simulate_round(i))
        return all_results

    def get_table(self) -> list[Standing]:
        """Retorna classificação ordenada."""
        return sorted(
            self.standings.values(),
            key=lambda s: (s.points, s.gd, s.gf),
            reverse=True,
        )

    def top(self, n: int) -> list[Standing]:
        return self.get_table()[:n]

    def bottom(self, n: int) -> list[Standing]:
        return self.get_table()[-n:]

    def print_table(self):
        table = self.get_table()
        print(f"\n{'='*65}")
        print(f"  {self.name} — {self.season}")
        print(f"{'='*65}")
        print(f"  {'#':>2}  {'Clube':<25} {'P':>3} {'J':>3} {'V':>3} {'E':>3} {'D':>3} {'GP':>3} {'GC':>3} {'SG':>4} {'Pts':>4}")
        print(f"  {'-'*62}")
        for i, s in enumerate(table, 1):
            print(
                f"  {i:>2}. {s.club_name:<25} "
                f"{s.played:>3} {s.wins:>3} {s.draws:>3} {s.losses:>3} "
                f"{s.gf:>3} {s.ga:>3} {s.gd:>+4} {s.points:>4}"
            )
        print(f"{'='*65}\n")


class KnockoutStage:
    """
    Fase eliminatória (mata-mata).
    Suporte a: oitavas, quartas, semi, final.
    """

    def __init__(self, clubs: list[Club], stage_name: str = "Playoffs"):
        assert len(clubs) >= 2 and (len(clubs) & (len(clubs) - 1)) == 0, \
            "Knockout precisa de potência de 2 (2, 4, 8, 16...)"
        self.clubs = clubs
        self.stage_name = stage_name
        self.bracket: list[tuple[Club, Club]] = list(zip(clubs[::2], clubs[1::2]))
        self.winner: Optional[Club] = None

    def simulate_stage(self) -> list[Club]:
        """Simula rodada eliminatória, retorna vencedores."""
        from engine.simulation import simulate_penalties
        winners = []
        print(f"\n{'─'*40}")
        print(f"  {self.stage_name}")
        print(f"{'─'*40}")
        for home, away in self.bracket:
            result = simulate_match(home, away)
            if result.winner is not None:
                winner_club = home if result.winner == home.id else away
            else:
                # Empate → pênaltis
                hp, ap = simulate_penalties(home, away)
                winner_club = home if hp >= ap else away
                print(f"  {home.name} {result.home_goals}({hp}) x ({ap}){result.away_goals} {away.name} → {winner_club.name}")
                winners.append(winner_club)
                continue

            print(f"  {home.name} {result.home_goals} x {result.away_goals} {away.name} → {winner_club.name}")
            winners.append(winner_club)

        return winners

    def run_tournament(self) -> Club:
        """Roda torneio completo até campeão."""
        remaining = list(self.clubs)
        stage_names = {
            16: "Oitavas de Final",
            8: "Quartas de Final",
            4: "Semifinais",
            2: "Final",
        }

        while len(remaining) > 1:
            name = stage_names.get(len(remaining), f"Rodada de {len(remaining)}")
            stage = KnockoutStage(remaining, name)
            remaining = stage.simulate_stage()

        self.winner = remaining[0]
        print(f"\n🏆 Campeão: {self.winner.name}")
        return self.winner
