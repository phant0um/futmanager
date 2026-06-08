"""
FUTMANAGER — Campeonatos Estaduais (regulamento Paulistão)
16 clubes · 4 grupos de 4 · cada clube joga os 12 de OUTROS grupos ·
top 2 de cada grupo → quartas → semi → final (mata-mata, pênaltis no empate).
Todos os estaduais usam este formato.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from db.models import Standing
from engine.simulation import simulate_match, simulate_penalties


@dataclass
class EstadualResult:
    state: str
    champion = None
    player_stage: str = "—"
    player_champion: bool = False
    group_tables: dict = field(default_factory=dict)
    log: list = field(default_factory=list)


def _make_groups(clubs):
    """4 grupos de 4, distribuídos por força (seeding em serpentina)."""
    ordered = sorted(clubs, key=lambda c: c.prestige, reverse=True)[:16]
    groups = [[], [], [], []]
    for i, c in enumerate(ordered):
        # serpentina: 0,1,2,3,3,2,1,0,...
        g = i % 8
        gi = g if g < 4 else 7 - g
        groups[gi].append(c)
    return groups


def run_estadual(state: str, clubs: list, watch_club_id=None) -> EstadualResult:
    res = EstadualResult(state=state)
    if len(clubs) < 8:
        res.player_stage = "Sem estadual (poucos clubes)"
        return res

    groups = _make_groups(clubs)
    in_play = [c for g in groups for c in g]
    by_id = {c.id: c for c in in_play}
    group_of = {}
    for gi, g in enumerate(groups):
        for c in g:
            group_of[c.id] = gi

    # Fase de grupos: cada confronto entre clubes de grupos diferentes (1 jogo)
    tab = {c.id: Standing(club_id=c.id, club_name=c.name) for c in in_play}
    for i in range(len(in_play)):
        for j in range(i + 1, len(in_play)):
            a, b = in_play[i], in_play[j]
            if group_of[a.id] == group_of[b.id]:
                continue  # mesmo grupo não se enfrenta
            r = simulate_match(a, b)
            tab[a.id].update(r.home_goals, r.away_goals)
            tab[b.id].update(r.away_goals, r.home_goals)

    # Classificação por grupo + 2 melhores avançam
    advancers = {}   # group -> [1º, 2º]
    for gi, g in enumerate(groups):
        ranked = sorted(g, key=lambda c: (tab[c.id].points, tab[c.id].gd, tab[c.id].gf), reverse=True)
        res.group_tables[chr(65 + gi)] = [
            {"name": c.name, "pts": tab[c.id].points, "gd": tab[c.id].gd,
             "is_player": c.id == watch_club_id} for c in ranked]
        advancers[gi] = ranked[:2]

    if watch_club_id in by_id:
        adv_ids = {c.id for pair in advancers.values() for c in pair}
        res.player_stage = "Fase de grupos" if watch_club_id not in adv_ids else "Quartas"
        if watch_club_id not in adv_ids:
            res.champion = _knockout(advancers, res, watch_club_id)
            return res

    res.champion = _knockout(advancers, res, watch_club_id)
    return res


def _schedule_matchdays(pairs):
    """Empacota confrontos em rodadas (nenhum clube joga 2x na mesma rodada)."""
    remaining = list(pairs)
    matchdays = []
    while remaining:
        used, md, leftover = set(), [], []
        for h, a in remaining:
            if h.id not in used and a.id not in used:
                md.append((h, a)); used.add(h.id); used.add(a.id)
            else:
                leftover.append((h, a))
        matchdays.append(md)
        remaining = leftover
    return matchdays


def run_estadual_live(state: str, clubs: list, watch_club_id=None):
    """
    Igual ao run_estadual, mas devolve as RODADAS com timelines minuto-a-minuto
    (fase de grupos rodada a rodada + mata-mata), para a GUI animar todos os jogos.
    Retorna (matchdays, result) onde matchdays = [{'label':..., 'matches':[LiveResult-like]}].
    """
    from engine.live import build_timeline, abbr, stadium_name
    from engine.simulation import simulate_penalties

    res = EstadualResult(state=state)
    if len(clubs) < 8:
        res.player_stage = "Sem estadual (poucos clubes)"
        return [], res

    groups = _make_groups(clubs)
    in_play = [c for g in groups for c in g]
    group_of = {c.id: gi for gi, g in enumerate(groups) for c in g}
    tab = {c.id: Standing(club_id=c.id, club_name=c.name) for c in in_play}

    def ser(h, a, lr, pens=None, winner=None):
        d = {"home": h.name, "away": a.name, "h_abbr": abbr(h.name), "a_abbr": abbr(a.name),
             "hg": lr.home_goals, "ag": lr.away_goals, "stadium": stadium_name(h),
             "is_player": watch_club_id in (h.id, a.id),
             "events": [{"m": e.minute, "kind": e.kind, "team": e.team, "text": e.text}
                        for e in lr.events]}
        if pens:
            d["pens"] = pens; d["winner"] = winner
        return d

    matchdays = []

    # ── Fase de grupos (cada clube enfrenta os 12 de outros grupos), rodada a rodada
    pairs = [(in_play[i], in_play[j])
             for i in range(len(in_play)) for j in range(i + 1, len(in_play))
             if group_of[in_play[i].id] != group_of[in_play[j].id]]
    for ri, md in enumerate(_schedule_matchdays(pairs), 1):
        sm = []
        for h, a in md:
            lr = build_timeline(h, a)
            tab[h.id].update(lr.home_goals, lr.away_goals)
            tab[a.id].update(lr.away_goals, lr.home_goals)
            sm.append(ser(h, a, lr))
        sm.sort(key=lambda m: 0 if m["is_player"] else 1)
        matchdays.append({"label": f"Fase de grupos — rodada {ri}", "matches": sm})

    # ── Classificação por grupo + 2 avançam
    advancers = {}
    for gi, g in enumerate(groups):
        ranked = sorted(g, key=lambda c: (tab[c.id].points, tab[c.id].gd, tab[c.id].gf), reverse=True)
        res.group_tables[chr(65 + gi)] = [
            {"name": c.name, "pts": tab[c.id].points, "gd": tab[c.id].gd,
             "is_player": c.id == watch_club_id} for c in ranked]
        advancers[gi] = ranked[:2]

    adv_ids = {c.id for pair in advancers.values() for c in pair}
    if watch_club_id and watch_club_id in group_of:
        res.player_stage = "Fase de grupos" if watch_club_id not in adv_ids else "Quartas"

    # ── Mata-mata, rodada a rodada
    A1, A2 = advancers[0]; B1, B2 = advancers[1]
    C1, C2 = advancers[2]; D1, D2 = advancers[3]
    remaining_pairs = [(A1, B2), (B1, A2), (C1, D2), (D1, C2)]
    stage_names = ["Quartas de Final", "Semifinais", "Final"]
    stage_i = 0
    while True:
        sm, winners = [], []
        for h, a in remaining_pairs:
            lr = build_timeline(h, a)
            if lr.home_goals == lr.away_goals:
                hp, ap = simulate_penalties(h, a)
                w = h if hp >= ap else a
                sm.append(ser(h, a, lr, pens=(hp, ap), winner=w.name))
            else:
                w = h if lr.home_goals > lr.away_goals else a
                sm.append(ser(h, a, lr))
            winners.append(w)
            if watch_club_id in (h.id, a.id) and w.id != watch_club_id:
                res.player_stage = stage_names[min(stage_i, 2)]
        sm.sort(key=lambda m: 0 if m["is_player"] else 1)
        matchdays.append({"label": stage_names[min(stage_i, 2)], "matches": sm})
        if len(winners) == 1:
            res.champion = winners[0]
            if watch_club_id == winners[0].id:
                res.player_champion = True
                res.player_stage = "CAMPEÃO 🏆"
            break
        remaining_pairs = list(zip(winners[::2], winners[1::2]))
        stage_i += 1

    return matchdays, res


def _knockout(advancers, res, watch_club_id):
    """Quartas (1A×2B, 1B×2A, 1C×2D, 1D×2C) → semi → final."""
    A1, A2 = advancers[0]; B1, B2 = advancers[1]
    C1, C2 = advancers[2]; D1, D2 = advancers[3]
    quarters = [(A1, B2), (B1, A2), (C1, D2), (D1, C2)]

    def play_tie(h, a):
        r = simulate_match(h, a)
        if r.home_goals == r.away_goals:
            hp, ap = simulate_penalties(h, a)
            w = h if hp >= ap else a
            extra = f" ({hp}-{ap} pên)"
        else:
            w = h if r.home_goals > r.away_goals else a
            extra = ""
        return w, f"{h.name} {r.home_goals}-{r.away_goals} {a.name}{extra} → {w.name}"

    stage_names = ["Quartas de Final", "Semifinais", "Final"]
    remaining_pairs = quarters
    stage_i = 0
    while True:
        winners = []
        lines = [f"  ── {stage_names[min(stage_i,2)]} ──"]
        for h, a in remaining_pairs:
            w, line = play_tie(h, a)
            is_p = watch_club_id in (h.id, a.id)
            lines.append(f"     {line}" + (" ◀" if is_p else ""))
            if is_p and w.id != watch_club_id:
                res.player_stage = stage_names[min(stage_i, 2)]
            winners.append(w)
        res.log.append("\n".join(lines))
        if len(winners) == 1:
            champ = winners[0]
            if watch_club_id == champ.id:
                res.player_champion = True
                res.player_stage = "CAMPEÃO 🏆"
            return champ
        remaining_pairs = list(zip(winners[::2], winners[1::2]))
        stage_i += 1
