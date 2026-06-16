"""
FUTMANAGER — Live Match Broadcast
Simula partida minuto a minuto e narra em ~2min reais.
Eventos: gols, cartões (amarelo/vermelho), contusões → substituição.
O placar gerado É o resultado oficial (alimenta a classificação).
"""
from __future__ import annotations
import random
import time
from dataclasses import dataclass, field

from engine.simulation import _expected_goals, _poisson, HOME_ADVANTAGE


@dataclass
class LiveEvent:
    minute: int
    kind: str        # goal | yellow | red | injury | half | full | kick
    team: str        # 'H' | 'A' | ''
    text: str


@dataclass
class LiveResult:
    home_id: int
    away_id: int
    home_goals: int
    away_goals: int
    home_scorers: list = field(default_factory=list)
    away_scorers: list = field(default_factory=list)
    home_scorer_ids: list = field(default_factory=list)
    away_scorer_ids: list = field(default_factory=list)
    yellows: dict = field(default_factory=dict)   # {player_id: club_id}
    reds: dict = field(default_factory=dict)        # {player_name: club_id} -> manter compat
    injuries: list = field(default_factory=list)    # [{player_id, name, club_id}]
    events: list = field(default_factory=list)

    @property
    def winner(self):
        if self.home_goals > self.away_goals: return self.home_id
        if self.away_goals > self.home_goals: return self.away_id
        return None

    def player_goals(self, player_id: int) -> int:
        return self.home_scorer_ids.count(player_id) + self.away_scorer_ids.count(player_id)

    def player_cards(self, player_id: int, color: str) -> int:
        if color == "yellow":
            return 1 if player_id in self.yellows else 0
        return 1 if player_id in self.reds else 0


_PREFIXES = {"cr","se","fc","ec","sc","ac","ca","rb","afc","ss","as","sl",
             "rc","cf","us","ogc","losc","ssc","acf","bc"}

def abbr(name: str) -> str:
    """Sigla de 3 letras a partir da parte significativa do nome."""
    toks = [t for t in name.split() if t]
    # Pula prefixo de sigla (CR, SE, FC...)
    while toks and toks[0].lower().strip(".") in _PREFIXES:
        toks.pop(0)
    if not toks:
        toks = name.split()
    base = toks[0] if toks else name
    return base[:3].upper()


def _starters_bench(club):
    """11 titulares (escalação salva ou top-11) + reservas."""
    return club.lineup, club.bench


def _weighted_player(players, attr="finishing"):
    if not players:
        return None
    weights = [max(1, getattr(p, attr, 50)) for p in players]
    return random.choices(players, weights=weights, k=1)[0]


# ── Lances "de cor" — não mudam placar, só dão vida ao minuto a minuto ──
_CHANCE_TEMPLATES = (
    ("⚡ Chute de {a} de fora da área, {gk} defende", "finishing", "goalkeeping"),
    ("🧤 Cabeceio de {a}, {gk} espalma escanteio", "finishing", "goalkeeping"),
    ("🚩 Escanteio cobrado, zaga afasta no susto", None, None),
    ("🔀 Jogada construída por {a}, {b} chuta por cima do gol", "passing", "finishing"),
    ("🛡️  {a} corta lance perigoso na entrada da área", "defending", None),
    ("🎯 {a} arrisca de longe, bola passa raspando a trave", "technique", None),
    ("🏃 Contra-ataque puxado por {a}, mas a zaga se recompõe", "pace", None),
    ("🧱 Bola na área, {gk} sai bem e afasta o perigo", "goalkeeping", None),
    ("⚽ {a} driblou dois marcadores e cruzou, ninguém alcançou", "technique", None),
)


def _chances(home, away, h_start, a_start) -> list[LiveEvent]:
    """Gera ~6-10 lances de texto sem gol — pesa pela força ofensiva relativa,
    escolhe protagonista por atributo (cai pra finishing se faltar)."""
    h_atk = getattr(home, "attack_rating", 50) * getattr(home, "morale", 1.0)
    a_atk = getattr(away, "attack_rating", 50) * getattr(away, "morale", 1.0)
    total = h_atk + a_atk or 1
    n = random.randint(6, 10)
    evs = []
    for _ in range(n):
        home_side = random.random() < (h_atk / total)
        starters, gk_pool, short = (h_start, a_start, abbr(home.name)) if home_side \
            else (a_start, h_start, abbr(away.name))
        team = "H" if home_side else "A"
        tmpl, attr_a, attr_b = random.choice(_CHANCE_TEMPLATES)
        a = _weighted_player([p for p in starters if p.position in ("FW", "MF")] or starters,
                             attr_a or "overall")
        b = _weighted_player([p for p in starters if p.position in ("MF", "FW")] or starters,
                             attr_b or "overall")
        gk = next((p for p in gk_pool if p.position == "GK"), None)
        text = tmpl.format(
            a=a.name if a else "?", b=b.name if b else "?",
            gk=gk.name if gk else "goleiro", short=short,
        )
        evs.append(LiveEvent(random.randint(2, 88), "chance", team, f"{text} ({short})"))
    return evs


def build_timeline(home, away) -> LiveResult:
    """Gera todos os eventos da partida com minutos, ordenados."""
    h_start, h_bench = _starters_bench(home)
    a_start, a_bench = _starters_bench(away)

    # ── Gols (Poisson) — moral + estilo tático afetam ataque/defesa ──
    hm = getattr(home, "morale", 1.0); am = getattr(away, "morale", 1.0)
    h_sa = getattr(home, "style_atk", 1.0); h_sd = getattr(home, "style_def", 1.0)
    a_sa = getattr(away, "style_atk", 1.0); a_sd = getattr(away, "style_def", 1.0)
    lam_h = _expected_goals(home.attack_rating * hm * h_sa, away.defense_rating * a_sd, home=True)
    lam_a = _expected_goals(away.attack_rating * am * a_sa, home.defense_rating * h_sd, home=False)
    gh, ga = _poisson(lam_h), _poisson(lam_a)

    res = LiveResult(home_id=home.id, away_id=away.id, home_goals=gh, away_goals=ga)
    evs: list[LiveEvent] = []

    def goal_scorer(starters):
        atk = [p for p in starters if p.position in ("FW", "MF")] or starters
        return _weighted_player(atk, "finishing")

    for _ in range(gh):
        s = goal_scorer(h_start)
        if s:
            res.home_scorers.append(s.name)
            res.home_scorer_ids.append(s.id)
            evs.append(LiveEvent(random.randint(1, 90), "goal", "H", f"⚽ GOL do {abbr(home.name)}! {s.name}"))
        else:
            res.home_scorers.append("?")
            res.home_scorer_ids.append(None)
    for _ in range(ga):
        s = goal_scorer(a_start)
        if s:
            res.away_scorers.append(s.name)
            res.away_scorer_ids.append(s.id)
            evs.append(LiveEvent(random.randint(1, 90), "goal", "A", f"⚽ GOL do {abbr(away.name)}! {s.name}"))
        else:
            res.away_scorers.append("?")
            res.away_scorer_ids.append(None)

    # ── Cartões amarelos (~1.8/time) ──
    for team, starters, short, club_id in (("H", h_start, abbr(home.name), home.id), ("A", a_start, abbr(away.name), away.id)):
        n = _poisson(1.8)
        for _ in range(min(n, 5)):
            p = _weighted_player([x for x in starters if x.position in ("DF", "MF")] or starters, "strength")
            if p:
                res.yellows[p.id] = club_id
                evs.append(LiveEvent(random.randint(1, 90), "yellow", team,
                                     f"🟨 Amarelo p/ {p.name} ({short})"))

    # ── Cartões vermelhos (~7%/time) ──
    for team, starters, short, club_id in (("H", h_start, abbr(home.name), home.id), ("A", a_start, abbr(away.name), away.id)):
        if random.random() < 0.07:
            p = random.choice([x for x in starters if x.position in ("DF", "MF")] or starters)
            res.reds[p.name] = club_id
            res.reds[p.id] = club_id  # também por id para stats
            evs.append(LiveEvent(random.randint(20, 90), "red", team,
                                 f"🟥 VERMELHO! {p.name} ({short}) expulso"))

    # ── Contusões → substituição (~12%/time) ──
    for team, starters, bench, short in (("H", h_start, h_bench, abbr(home.name)),
                                          ("A", a_start, a_bench, abbr(away.name))):
        if random.random() < 0.12 and bench:
            out = random.choice(starters)
            inn = bench[0]
            evs.append(LiveEvent(random.randint(10, 85), "injury", team,
                                 f"🚑 Contusão: {out.name} sai, entra {inn.name} ({short})"))
            res.injuries.append({"player_id": out.id, "name": out.name,
                                 "club_id": home.id if team == "H" else away.id})

    # ── Lances sem gol — preenchem minutos vazios, dão clima ──
    evs.extend(_chances(home, away, h_start, a_start))

    # ── Marcos do jogo ──
    evs.append(LiveEvent(0, "kick", "", f"🔵 Bola rolando: {home.name} x {away.name}"))
    evs.append(LiveEvent(45, "half", "", "⏸️  Intervalo"))
    evs.append(LiveEvent(90, "full", "", "🔚 Fim de jogo"))

    evs.sort(key=lambda e: (e.minute, 0 if e.kind == "kick" else 1))
    res.events = evs
    return res


def broadcast(res: LiveResult, home, away, spm: float = 1.3):
    """
    Narra a partida. spm = segundos por minuto simulado (90×spm ≈ duração real).
    spm=0 → instantâneo (testes). Placar corrente atualizado a cada gol.
    """
    hg = ag = 0
    HSHORT, ASHORT = abbr(home.name), abbr(away.name)
    by_min: dict[int, list] = {}
    for e in res.events:
        by_min.setdefault(e.minute, []).append(e)

    print(f"\n  {'═'*52}")
    print(f"  📺  AO VIVO — {home.name}  x  {away.name}")
    print(f"  {'═'*52}")

    for minute in range(0, 91):
        if spm > 0:
            time.sleep(spm)
        for e in by_min.get(minute, []):
            if e.kind == "goal":
                if e.team == "H": hg += 1
                else: ag += 1
                print(f"  {minute:>2}'  {e.text}   [{HSHORT} {hg}-{ag} {ASHORT}]")
            elif e.kind == "kick":
                print(f"   0'  {e.text}")
            elif e.kind == "half":
                print(f"  45'  {e.text}   [{HSHORT} {hg}-{ag} {ASHORT}]")
                if spm > 0:
                    time.sleep(spm * 2)
            elif e.kind == "full":
                print(f"  90'  {e.text}")
            elif e.kind == "chance":
                print(f"  {minute:>2}'  {e.text}")
            else:
                print(f"  {minute:>2}'  {e.text}")

    print(f"\n  {'─'*52}")
    print(f"  PLACAR FINAL: {home.name} {res.home_goals} x {res.away_goals} {away.name}")
    print(f"  {'─'*52}")
    return res


def play_live(home, away, spm: float = 1.3) -> LiveResult:
    res = build_timeline(home, away)
    broadcast(res, home, away, spm)
    return res


# ─── Estádios (gerados deterministicamente) ──────────────────────────────────

_STADIUM_WORDS = ["Arena", "Estádio", "Arena", "Estádio"]

def stadium_name(club) -> str:
    base = abbr(club.name)
    word = _STADIUM_WORDS[club.id % len(_STADIUM_WORDS)]
    # nome a partir da parte significativa
    toks = [t for t in club.name.split() if t.lower().strip(".") not in _PREFIXES]
    core = toks[0] if toks else club.name
    return f"{word} {core}"


# ─── Rodada ao vivo (vários jogos simultâneos) ───────────────────────────────

def matchday_timeline(pairs) -> list:
    """Gera timelines de todos os confrontos da rodada.
    pairs: lista de (home_club, away_club). Retorna [(home, away, LiveResult)]."""
    return [(h, a, build_timeline(h, a)) for h, a in pairs]


def narrate_matchday(items, player_club_id, spm: float = 1.0) -> dict:
    """
    Narra a rodada inteira ao vivo: feed de gols/expulsões de todos os jogos,
    placar consolidado nos intervalos. Jogo do humano com detalhe extra.
    Retorna {(home_id,away_id): LiveResult}.
    """
    # estado de placar por jogo
    score = {i: [0, 0] for i in range(len(items))}
    by_min = {}  # minute → list of (idx, event)
    for idx, (h, a, res) in enumerate(items):
        for e in res.events:
            by_min.setdefault(e.minute, []).append((idx, e))

    def scoreboard(title):
        print(f"\n  ── {title} ──")
        for idx, (h, a, res) in enumerate(items):
            hs, as_ = score[idx]
            star = " ◀" if player_club_id in (h.id, a.id) else ""
            print(f"     {abbr(h.name)} {hs}-{as_} {abbr(a.name)}  ·  {stadium_name(h)}{star}")

    print(f"\n  {'═'*54}")
    print(f"  📺  RODADA AO VIVO  ({len(items)} jogos)")
    print(f"  {'═'*54}")
    scoreboard("Bola rolando")

    for minute in range(0, 91):
        if spm > 0:
            time.sleep(spm)
        for idx, e in by_min.get(minute, []):
            h, a, res = items[idx]
            is_player = player_club_id in (h.id, a.id)
            if e.kind == "goal":
                if e.team == "H": score[idx][0] += 1
                else: score[idx][1] += 1
                hs, as_ = score[idx]
                tag = " ◀" if is_player else ""
                print(f"  {minute:>2}'  ⚽ {abbr(h.name)} {hs}-{as_} {abbr(a.name)}  ({e.text.split('! ')[-1]}){tag}")
            elif e.kind == "red":
                print(f"  {minute:>2}'  🟥 {e.text}")
            elif is_player and e.kind in ("yellow", "injury", "chance"):
                print(f"  {minute:>2}'  {e.text}")
        if minute == 45:
            scoreboard("Intervalo")
            if spm > 0:
                time.sleep(spm * 2)

    scoreboard("FIM DA RODADA")
    return {(h.id, a.id): res for (h, a, res) in items}
