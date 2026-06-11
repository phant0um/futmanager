"""
FUTMANAGER — Career Mode Engine
Progressão de temporadas: envelhecimento, desenvolvimento, aposentadorias, newgens.
"""
from __future__ import annotations
import sqlite3
import random
import hashlib
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Pools de nomes por país (reusa do gerador de squads)
try:
    from scripts.generate_squads import NAMES_BY_COUNTRY, _get_names
except Exception:
    NAMES_BY_COUNTRY = {"default": ["Alex","Bruno","Carlos","David","Emil","Franco"]}
    def _get_names(country, n, seed):
        import random as _r
        pool = NAMES_BY_COUNTRY.get(country, NAMES_BY_COUNTRY["default"])
        rng = _r.Random(seed)
        return [rng.choice(pool) for _ in range(n)]


# ─── Constantes de carreira ──────────────────────────────────────────────────

PEAK_AGE = 27
NEWGENS_PER_CLUB = (3, 5)        # min, max por temporada
NEWGEN_AGE = (16, 18)

ATTR_COLS = ["pace", "technique", "strength", "finishing",
             "passing", "defending", "goalkeeping", "stamina", "mental"]


# ─── Distribuição de potencial dos newgens ───────────────────────────────────

def _roll_potential(rng: random.Random) -> int:
    """Distribuição enviesada: maioria medíocre, raros craques."""
    r = rng.random()
    if r < 0.60:
        return rng.randint(45, 60)   # comum
    elif r < 0.88:
        return rng.randint(60, 72)   # bom
    elif r < 0.98:
        return rng.randint(72, 82)   # titular
    else:
        return rng.randint(82, 92)   # wonderkid


# ─── Desenvolvimento de atributos ────────────────────────────────────────────

def _growth_factor(age: int) -> float:
    """
    Curva de carreira:
      cresce até 27 (pico) → estável 28-31 → declina a partir de 32.
    """
    if age <= 18:   return 1.0     # joia: cresce rápido
    if age <= 21:   return 0.8
    if age <= 24:   return 0.5
    if age <= 27:   return 0.25    # ainda subindo até o pico (27)
    if age <= 31:   return 0.0     # platô (28-31): estável
    if age <= 34:   return -0.5    # 32-34: declínio leve
    if age <= 37:   return -1.0    # 35-37: declínio acentuado
    return -1.6                    # 38+: queda forte


# Foco de treino → atributos beneficiados com bônus extra de crescimento
TRAINING_FOCUS_ATTRS = {
    "fisico":      ("pace", "strength", "stamina"),
    "tecnico":     ("technique", "passing", "defending"),
    "finalizacao": ("finishing", "technique", "mental"),
    "geral":       tuple(ATTR_COLS),   # sem viés — comportamento padrão
}


def develop_player(conn, player_row, rng: random.Random, train_bonus: float = 0.0,
                   focus: str = "geral"):
    """
    Atualiza overall e atributos conforme idade + potencial.
    train_bonus: ganho extra de desenvolvimento (treino do clube do jogador).
    focus: foco do CT — favorece crescimento de um grupo de atributos
           (geral|fisico|tecnico|finalizacao). Só vale para jogadores em
           crescimento (factor > 0) — veteranos não "aprendem" mais com treino.
    """
    pid, age, overall, potential, pos = player_row
    overall = overall or 60
    potential = potential or overall
    factor = _growth_factor(age)
    biased = set(TRAINING_FOCUS_ATTRS.get(focus, ATTR_COLS))
    # bônus de foco escala com o quanto o jogador ainda cresce — treino não
    # transforma veterano em craque
    focus_bonus = train_bonus * 0.6 * max(0.0, factor)

    if factor > 0:
        # Cresce em direção ao potencial; quanto mais perto, mais devagar
        gap = potential - overall
        if gap <= 0:
            delta = 0
        else:
            # ganho proporcional ao gap + ruído + treino
            delta = round(factor * (1.5 + gap * 0.25) + train_bonus + rng.uniform(-0.5, 1.0))
            delta = max(0, min(delta, gap))
    elif factor < 0:
        # Declina; veteranos perdem mais
        delta = round(factor * rng.uniform(1.0, 2.5))
    else:
        delta = 0

    if delta == 0 and focus_bonus <= 0:
        return

    new_overall = max(35, min(99, overall + delta))

    # Aplica delta proporcional aos atributos (mantém perfil da posição);
    # atributos do foco do CT recebem um extra
    # Busca todos atributos de uma vez (era 1 SELECT por atributo — 9 round-trips
    # por jogador × 6k+ jogadores no fim de temporada)
    cur_row = conn.execute(
        f"SELECT {', '.join(ATTR_COLS)} FROM players WHERE id=?", (pid,)
    ).fetchone()
    updates = {}
    for col in ATTR_COLS:
        cur = cur_row[col] or 50
        # Atributos seguem o delta com leve variação
        adj = delta + rng.choice([-1, 0, 0, 1])
        if col in biased:
            adj += round(focus_bonus + rng.uniform(0, 0.5))
        updates[col] = max(20, min(99, cur + adj))

    set_clause = ", ".join(f"{c}=?" for c in ATTR_COLS)
    conn.execute(
        f"UPDATE players SET overall=?, {set_clause} WHERE id=?",
        (new_overall, *[updates[c] for c in ATTR_COLS], pid)
    )


# ─── Aposentadorias ──────────────────────────────────────────────────────────

def _retire_probability(age: int, pos: str) -> float:
    """Probabilidade de aposentar nesta temporada."""
    # GK aposenta mais tarde
    base_start = 37 if pos == "GK" else 34
    force_age = 43 if pos == "GK" else 40

    if age < base_start:
        return 0.0
    if age >= force_age:
        return 1.0
    # Ramp linear entre base_start e force_age
    span = force_age - base_start
    return (age - base_start) / span * 0.7 + 0.1


def process_retirements(conn, rng: random.Random) -> list[dict]:
    """Aposenta jogadores. Retorna lista de aposentados (notáveis)."""
    players = conn.execute("""
        SELECT id, name, age, position, overall, club_id
        FROM players WHERE retired = 0 AND age >= 33
    """).fetchall()

    retired = []
    for pid, name, age, pos, overall, club_id in players:
        prob = _retire_probability(age, pos or "MF")
        if rng.random() < prob:
            conn.execute(
                "UPDATE players SET retired=1, club_id=NULL WHERE id=?", (pid,)
            )
            if overall and overall >= 75:  # só reporta notáveis
                retired.append({"name": name, "age": age, "overall": overall,
                                "club_id": club_id})
    return retired


# ─── Geração de newgens ──────────────────────────────────────────────────────

# Distribuição de posições num elenco jovem
NEWGEN_POSITIONS = ["GK", "DF", "DF", "MF", "MF", "FW"]


def generate_newgens(conn, season_year: int, rng: random.Random) -> int:
    """Gera novos jovens para cada clube. Retorna total criado."""
    clubs = conn.execute("""
        SELECT c.id, c.name, c.prestige, COALESCE(co.code,'default') as country
        FROM clubs c
        LEFT JOIN leagues l ON l.id = c.league_id
        LEFT JOIN countries co ON co.id = l.country_id
    """).fetchall()

    total = 0
    for club_id, club_name, prestige, country in clubs:
        n = rng.randint(*NEWGENS_PER_CLUB)
        for i in range(n):
            seed = int(hashlib.md5(
                f"newgen:{season_year}:{club_id}:{i}".encode()
            ).hexdigest(), 16) % (2**32)
            prng = random.Random(seed)

            pos = prng.choice(NEWGEN_POSITIONS)
            age = prng.randint(*NEWGEN_AGE)
            potential = _roll_potential(prng)
            # Clubes de maior prestígio atraem jovens ligeiramente melhores
            potential = min(99, potential + (prestige - 60) // 15)

            # Overall atual: jovem cru, bem abaixo do potencial
            overall = max(40, potential - prng.randint(8, 22))

            name = _get_names(country, 1, seed)[0] + " " + _last_name(country, prng)

            attrs = _newgen_attributes(pos, overall, prng)
            # Salário modesto de jovem + contrato longo (3-5 anos)
            wage = max(40_000, int(overall ** 2 * 30))
            contract_until = season_year + prng.randint(3, 5)
            conn.execute("""
                INSERT INTO players(
                    name, position, nationality, age, club_id,
                    pace, technique, strength, finishing, passing,
                    defending, goalkeeping, stamina, mental,
                    overall, potential, wage, contract_until,
                    is_newgen, retired, source
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,0,'newgen')
            """, (
                name, pos, country, age, club_id,
                attrs["pace"], attrs["technique"], attrs["strength"],
                attrs["finishing"], attrs["passing"], attrs["defending"],
                attrs["goalkeeping"], attrs["stamina"], attrs["mental"],
                overall, potential, wage, contract_until,
            ))
            total += 1
    return total


# Sobrenomes por país para newgens (variação)
_LAST_NAMES = {
    "BR": ["Silva","Santos","Oliveira","Souza","Costa","Pereira","Lima","Almeida","Rocha","Ferreira"],
    "EN": ["Smith","Jones","Taylor","Brown","Wilson","Walker","White","Hughes","Green","Hall"],
    "ES": ["García","Martínez","López","Sánchez","Pérez","Gómez","Ruiz","Torres","Romero","Navarro"],
    "DE": ["Müller","Schmidt","Weber","Wagner","Becker","Hoffmann","Koch","Richter","Klein","Wolf"],
    "IT": ["Rossi","Russo","Ferrari","Esposito","Bianchi","Romano","Greco","Conti","Marino","Costa"],
    "FR": ["Martin","Bernard","Dubois","Thomas","Robert","Petit","Durand","Leroy","Moreau","Simon"],
    "PT": ["Silva","Santos","Ferreira","Pereira","Costa","Carvalho","Sousa","Gomes","Lopes","Marques"],
    "NL": ["Jansen","Visser","Bakker","Smit","Meijer","Mulder","Bos","Vos","Peters","Hendriks"],
    "AR": ["González","Rodríguez","Fernández","López","Martínez","Pérez","García","Díaz","Romero","Sosa"],
    "default": ["Silva","Smith","García","Rossi","Martin","Jansen","Costa","Müller"],
}

def _last_name(country: str, rng: random.Random) -> str:
    pool = _LAST_NAMES.get(country, _LAST_NAMES["default"])
    return rng.choice(pool)


def _newgen_attributes(pos: str, overall: int, rng: random.Random) -> dict:
    """Atributos coerentes com posição, centrados no overall."""
    def a(center_offset: int, spread: int = 8) -> int:
        return max(20, min(99, overall + center_offset + rng.randint(-spread, spread)))

    profiles = {
        "GK": {"goalkeeping": a(6), "defending": a(-12), "strength": a(-4),
               "mental": a(-2), "pace": a(-16), "technique": a(-12),
               "finishing": a(-25), "passing": a(-8), "stamina": a(-4)},
        "DF": {"defending": a(6), "strength": a(3), "mental": a(0), "pace": a(-2),
               "passing": a(-6), "technique": a(-10), "finishing": a(-16),
               "stamina": a(0), "goalkeeping": a(-30)},
        "MF": {"passing": a(5), "technique": a(3), "mental": a(2), "stamina": a(3),
               "defending": a(-4), "pace": a(-2), "finishing": a(-4),
               "strength": a(-4), "goalkeeping": a(-30)},
        "FW": {"finishing": a(6), "pace": a(5), "technique": a(3), "strength": a(-2),
               "mental": a(-2), "passing": a(-4), "defending": a(-14),
               "stamina": a(-2), "goalkeeping": a(-30)},
    }
    return profiles.get(pos, profiles["MF"])


# ─── Valor de mercado ────────────────────────────────────────────────────────

def update_market_values(conn):
    """Calcula valor de mercado (R$) baseado em overall, idade, potencial.
    Recalcula também a cláusula de rescisão (proporcional ao novo valor) —
    senão fica presa na escala antiga (assign_release_clauses só roda 1x,
    em cima do value pré-conversão BRL)."""
    import random
    players = conn.execute(
        "SELECT id, overall, age, potential FROM players WHERE retired=0"
    ).fetchall()
    for pid, ovr, age, pot in players:
        ovr = ovr or 60
        age = age or 25
        pot = pot or ovr
        # Base exponencial no overall (€80M × 5.5 = R$440M)
        base = (ovr / 100) ** 4 * 440_000_000
        # Fator idade (jovens valem mais)
        if age <= 21:   age_f = 1.4
        elif age <= 25: age_f = 1.2
        elif age <= 29: age_f = 1.0
        elif age <= 32: age_f = 0.6
        else:           age_f = 0.25
        # Bônus potencial
        pot_f = 1 + max(0, pot - ovr) * 0.04
        value = int(base * age_f * pot_f)
        # Cláusula ≈ valor × 1.5-2.5 (craques têm cláusula mais alta)
        rng = random.Random(pid)
        clause_mult = 1.5 + (ovr / 100) * 1.0 + rng.uniform(-0.2, 0.3)
        clause = int(value * clause_mult)
        conn.execute("UPDATE players SET value=?, release_clause=? WHERE id=?",
                     (value, clause, pid))
    conn.commit()


# ─── Acesso & queda (Brasileirão A↔B↔C↔D) ────────────────────────────────────

PROMO_RELEGATION_N = 4   # 4 sobem / 4 caem entre divisões adjacentes (regra real)


def apply_promotion_relegation(conn, season_year: int, manager_club_id: int,
                               manager_league_id: int, manager_table: list) -> dict | None:
    """
    Acesso/queda entre Brasileirão A-B-C-D ao fim da temporada: os 4 últimos de
    cada divisão trocam de lugar com os 4 primeiros da divisão de baixo (mesmo
    formato do Brasileirão real). A divisão D não tem queda (não existe nível
    abaixo no jogo).

    A liga do técnico usa a tabela já simulada (`manager_table`); as demais
    — que não rodam rodada-a-rodada na carreira — são simuladas inteiras em
    memória (sem persistir fixtures) só para apurar a classificação final.

    Retorna {'promoted': bool, 'league_name': str} se o clube do jogador mudou
    de divisão, senão None.
    """
    from engine.season import League
    from engine.calendar import _load_league_clubs

    leagues = conn.execute("""
        SELECT l.id, l.level, l.name FROM leagues l
        JOIN countries co ON co.id=l.country_id
        WHERE co.code='BR' AND l.level BETWEEN 1 AND 4
        ORDER BY l.level
    """).fetchall()
    by_level = {lg["level"]: lg for lg in leagues}
    if len(by_level) < 2:
        return None

    tables = {}
    for lg in leagues:
        lid, level = lg["id"], lg["level"]
        if lid == manager_league_id:
            tables[level] = manager_table
            continue
        clubs = _load_league_clubs(conn, lid)
        if len(clubs) < 2 * PROMO_RELEGATION_N:
            tables[level] = None
            continue
        lgobj = League("L", clubs, str(season_year))
        lgobj.simulate_all()
        tables[level] = lgobj.get_table()

    moves = {}  # club_id -> novo league_id
    for lvl in sorted(by_level)[:-1]:
        up_tab, down_tab = tables.get(lvl), tables.get(lvl + 1)
        if not up_tab or not down_tab:
            continue
        for s in up_tab[-PROMO_RELEGATION_N:]:
            moves[s.club_id] = by_level[lvl + 1]["id"]
        for s in down_tab[:PROMO_RELEGATION_N]:
            moves[s.club_id] = by_level[lvl]["id"]

    for club_id, new_lid in moves.items():
        conn.execute("UPDATE clubs SET league_id=? WHERE id=?", (new_lid, club_id))
    conn.commit()

    if manager_club_id in moves:
        new_lid = moves[manager_club_id]
        levels = {lg["id"]: lg["level"] for lg in leagues}
        names = {lg["id"]: lg["name"] for lg in leagues}
        return {"promoted": levels[new_lid] < levels[manager_league_id],
                "league_name": names[new_lid]}
    return None


# ─── Transição de temporada (orquestrador) ───────────────────────────────────

@dataclass
class SeasonReport:
    year: int
    retired_notable: list
    newgens_created: int
    top_newgens: list
    ai_transfers: int


def advance_season(conn, season_year: int, seed: int | None = None,
                   manager_club_id: int | None = None,
                   training_level: int = 2, training_focus: str = "geral") -> SeasonReport:
    """
    Avança uma temporada completa:
      age+1 → develop → retire → newgens → market values
    manager_club_id: clube do jogador — excluído do auto-renew de contratos.
    training_level (1-5): intensidade do CT — desenvolve mais o elenco do jogador.
    training_focus: geral|fisico|tecnico|finalizacao — direciona quais atributos
                    crescem mais com o treino do clube do jogador.
    """
    rng = random.Random(seed if seed is not None else random.randint(0, 2**31))

    # 1. Envelhece todos os ativos
    conn.execute("UPDATE players SET age = age + 1 WHERE retired = 0")

    # 2. Desenvolve atributos (treino dá bônus + foco ao clube do jogador)
    train_bonus = max(0.0, (training_level - 2) * 0.6)   # nível 2 = neutro
    players = conn.execute("""
        SELECT id, age, overall, potential, position, club_id
        FROM players WHERE retired = 0
    """).fetchall()
    for p in players:
        mine = bool(manager_club_id and p[5] == manager_club_id)
        bonus = train_bonus if mine else 0.0
        f = training_focus if mine else "geral"
        develop_player(conn, p[:5], rng, train_bonus=bonus, focus=f)
    conn.commit()

    # 3. Aposentadorias
    retired = process_retirements(conn, rng)
    conn.commit()

    # 4. Newgens
    n_newgens = generate_newgens(conn, season_year + 1, rng)
    conn.commit()

    # 5. Valores de mercado
    update_market_values(conn)

    # 5b. Janela de transferências IA — clubes grandes assediam jovens dos
    #     pequenos, fortalece elencos rivais ao longo das temporadas (dificuldade)
    from engine.transfer import ai_transfer_window
    n_ai_transfers = ai_transfer_window(conn, manager_club_id or -1, rng)

    # 6. Retorna empréstimos vencidos ao clube dono
    new_year = season_year + 1
    conn.execute("""
        UPDATE players
        SET club_id = loan_from_club, loan_from_club = NULL, loan_until = NULL
        WHERE loan_from_club IS NOT NULL AND loan_until <= ?
    """, (new_year,))

    # 7. Auto-renova contratos IA vencidos (mantém mundo estável; +3 anos, +8% salário)
    #    EXCLUI clube do manager — essas renovações são decididas na UI.
    if manager_club_id is not None:
        conn.execute("""
            UPDATE players
            SET contract_until = ? + 3, wage = CAST(wage * 1.08 AS INTEGER)
            WHERE retired = 0 AND contract_until IS NOT NULL AND contract_until <= ?
              AND (club_id IS NULL OR club_id != ?)
        """, (new_year, new_year, manager_club_id))
    else:
        conn.execute("""
            UPDATE players
            SET contract_until = ? + 3, wage = CAST(wage * 1.08 AS INTEGER)
            WHERE retired = 0 AND contract_until IS NOT NULL AND contract_until <= ?
        """, (new_year, new_year))
    conn.commit()

    # Top newgens criados (para scout report)
    top_newgens = conn.execute("""
        SELECT p.name, p.position, p.age, p.overall, p.potential, c.name as club
        FROM players p LEFT JOIN clubs c ON c.id = p.club_id
        WHERE p.is_newgen = 1 AND p.potential >= 78
        ORDER BY p.potential DESC LIMIT 15
    """).fetchall()

    return SeasonReport(
        year=season_year + 1,
        retired_notable=retired,
        newgens_created=n_newgens,
        top_newgens=top_newgens,
        ai_transfers=n_ai_transfers,
    )
