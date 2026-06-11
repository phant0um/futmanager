"""
FUTMANAGER — Career Mode Migration
Adiciona colunas de carreira + tabela career. Atribui idades faltantes.
Idempotente: pode rodar múltiplas vezes.
"""
from __future__ import annotations
import sqlite3
import random
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from paths import db_path


def _col_exists(conn, table, col) -> bool:
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})").fetchall())


def _add_col(conn, table, col, decl):
    if not _col_exists(conn, table, col):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        print(f"  + {table}.{col}")


def migrate(conn: sqlite3.Connection, current_year: int = 2026):
    print("Migrando schema para carreira...")

    # ── Colunas de carreira em players ───────────────────────────────
    _add_col(conn, "players", "age",       "INTEGER")
    _add_col(conn, "players", "potential", "INTEGER")
    _add_col(conn, "players", "retired",   "INTEGER DEFAULT 0")
    _add_col(conn, "players", "is_newgen", "INTEGER DEFAULT 0")
    _add_col(conn, "players", "value",     "INTEGER DEFAULT 0")
    # Contratos / salários
    _add_col(conn, "players", "wage",           "INTEGER DEFAULT 0")   # €/ano
    _add_col(conn, "players", "contract_until", "INTEGER")             # ano fim contrato
    # Disciplina
    _add_col(conn, "players", "red_cards", "INTEGER DEFAULT 0")  # expulsões na temporada
    # Empréstimos
    _add_col(conn, "players", "loan_from_club", "INTEGER")  # clube dono (se emprestado)
    _add_col(conn, "players", "loan_until",     "INTEGER")  # ano fim empréstimo
    _add_col(conn, "players", "loan_wage_pct",  "INTEGER")  # % do salário que o tomador paga
    _add_col(conn, "players", "loan_fee",       "INTEGER DEFAULT 0")  # taxa mensal de empréstimo
    # Cláusula de rescisão
    _add_col(conn, "players", "release_clause", "INTEGER")  # paga = compra forçada
    # Listas de mercado (clube disponibiliza o jogador)
    _add_col(conn, "players", "transfer_listed", "INTEGER DEFAULT 0")  # à venda
    _add_col(conn, "players", "loan_listed",     "INTEGER DEFAULT 0")  # disponível p/ empréstimo
    # Forma & condição física (rotação de elenco)
    _add_col(conn, "players", "form",    "REAL DEFAULT 1.0")      # 0.85–1.15, tendência recente
    _add_col(conn, "players", "fitness", "INTEGER DEFAULT 100")   # 0-100, condição atual
    # Renovação de contrato (evita spam de propostas no mesmo ano)
    _add_col(conn, "players", "renewal_cooldown", "INTEGER DEFAULT 0")  # ano até o qual não renegocia
    # Estádio
    _add_col(conn, "clubs", "capacity", "INTEGER")      # capacidade do estádio
    _add_col(conn, "clubs", "ticket_price", "INTEGER")  # preço atual do ingresso (€)
    _add_col(conn, "clubs", "fan_mood", "INTEGER DEFAULT 50")  # humor da torcida (0-100), afeta bilheteria
    # Estado (para estaduais brasileiros)
    _add_col(conn, "clubs", "state", "TEXT")            # SP, RJ, MG, RS...
    # Treino: foco de desenvolvimento do elenco
    _add_col(conn, "career", "training_focus", "TEXT DEFAULT 'geral'")  # geral|fisico|tecnico|finalizacao

    # ── Tabela career ────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS career (
            id              INTEGER PRIMARY KEY,
            manager_club_id INTEGER REFERENCES clubs(id),
            season_year     INTEGER NOT NULL,
            money           INTEGER DEFAULT 0,
            reputation      INTEGER DEFAULT 50,
            seasons_played  INTEGER DEFAULT 0,
            titles          INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'active',
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # Histórico de campeões por temporada
    conn.execute("""
        CREATE TABLE IF NOT EXISTS season_history (
            id          INTEGER PRIMARY KEY,
            career_id   INTEGER REFERENCES career(id),
            season_year INTEGER,
            league_id   INTEGER REFERENCES leagues(id),
            champion_id INTEGER REFERENCES clubs(id),
            manager_pos INTEGER,
            manager_pts INTEGER
        )
    """)
    # ── Classificação persistida por temporada (para a tela de tabela) ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS league_table (
            id INTEGER PRIMARY KEY,
            career_id INTEGER, season_year INTEGER, league_id INTEGER,
            club_id INTEGER, pos INTEGER, played INTEGER, wins INTEGER,
            draws INTEGER, losses INTEGER, gf INTEGER, ga INTEGER, points INTEGER
        )
    """)

    # ── Colunas de gestão (job security) ─────────────────────────────
    _add_col(conn, "career", "expectation", "INTEGER")           # meta de colocação do conselho
    _add_col(conn, "career", "warnings",    "INTEGER DEFAULT 0") # advertências do conselho
    # Escalação
    _add_col(conn, "career", "formation", "TEXT")   # ex: "4-3-3"
    _add_col(conn, "career", "lineup",    "TEXT")   # CSV de player_id (11 titulares)
    _add_col(conn, "career", "lineup_positions", "TEXT")  # JSON {player_id: [x_frac, y_frac]} posições livres no campo
    # Tática + treino
    _add_col(conn, "career", "tactic_style",   "TEXT DEFAULT 'equilibrado'")  # ofensivo|equilibrado|defensivo
    _add_col(conn, "career", "training_level", "INTEGER DEFAULT 2")            # 1-5: intensidade do CT
    # Calendário rodada a rodada
    _add_col(conn, "career", "current_round", "INTEGER DEFAULT 0")
    _add_col(conn, "career", "estadual_year", "INTEGER DEFAULT 0")  # última temp. com estadual disputado
    _add_col(conn, "career", "estadual_data", "TEXT")  # JSON: grupos/campeão do estadual da temp. atual
    _add_col(conn, "career", "declined_offers", "TEXT")  # JSON: [[player_id, club_id, season_year], ...] propostas recusadas
    _add_col(conn, "career", "notified_offers", "TEXT")  # JSON: [[player_id, club_id, season_year], ...] já avisadas na inbox (evita repost a cada rodada)
    # Inbox narrativa — cimento que reúne avisos do board, relatórios de
    # scout, propostas etc. num só lugar persistente e revisitável
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inbox_messages (
            id INTEGER PRIMARY KEY,
            career_id INTEGER, round INTEGER, kind TEXT,
            title TEXT, body TEXT, read INTEGER DEFAULT 0,
            ref_type TEXT, ref_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    # Notas rápidas sobre jogadores — reduz carga cognitiva em saves longos
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_notes (
            id INTEGER PRIMARY KEY,
            career_id INTEGER, player_id INTEGER,
            text TEXT, tag TEXT, created_round INTEGER
        )
    """)
    # Scouting — relatórios confirmam atributos (sobrescreve faixa do masking)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scout_reports (
            id INTEGER PRIMARY KEY,
            career_id INTEGER, player_id INTEGER,
            confirmed_attrs TEXT,   -- JSON: ["pace","finishing",...]
            confidence INTEGER,     -- 0-100, exibido no relatório
            created_round INTEGER,
            UNIQUE(career_id, player_id)
        )
    """)
    # Lesões reais — persistente, c/ recuperação semana a semana e cirurgia
    conn.execute("""
        CREATE TABLE IF NOT EXISTS injuries (
            id INTEGER PRIMARY KEY,
            career_id INTEGER, player_id INTEGER, club_id INTEGER,
            kind TEXT, weeks_total INTEGER, weeks_left INTEGER,
            surgery INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
            season_year INTEGER, round_occurred INTEGER
        )
    """)
    # Relações entre jogadores — squad dynamics (CM03/04). Geradas 1x por par
    # relevante (heurística: nacionalidade/idade/setor), afinidade fixa,
    # só altera leitura/coesão — não toca overall/contrato/simulação direto.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY,
            career_id INTEGER, player_a_id INTEGER, player_b_id INTEGER,
            kind TEXT,            -- amizade | rivalidade | parceria | mentoria
            affinity INTEGER,     -- -100..100
            UNIQUE(career_id, player_a_id, player_b_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fixtures (
            id INTEGER PRIMARY KEY,
            career_id INTEGER, season_year INTEGER, league_id INTEGER,
            round_idx INTEGER, home_id INTEGER, away_id INTEGER,
            played INTEGER DEFAULT 0, home_goals INTEGER, away_goals INTEGER
        )
    """)
    # Cartões por partida (para somar na classificação)
    for col in ("home_yellows", "home_reds", "away_yellows", "away_reds"):
        _add_col(conn, "fixtures", col, "INTEGER DEFAULT 0")
    # Copas mata-mata intercaladas (br=Copa do Brasil, lib=Libertadores, sul=Sul-Americana)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS copa (
            id INTEGER PRIMARY KEY,
            career_id INTEGER, season_year INTEGER, comp TEXT DEFAULT 'br',
            stage_idx INTEGER, match_idx INTEGER,
            home_id INTEGER, away_id INTEGER,
            played INTEGER DEFAULT 0, home_goals INTEGER, away_goals INTEGER, winner_id INTEGER
        )
    """)
    _add_col(conn, "copa", "comp", "TEXT DEFAULT 'br'")

    # Champions League — competição europeia inter-ligas (fase de grupos + KO)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS championships (
            id INTEGER PRIMARY KEY,
            career_id INTEGER, season_year INTEGER, comp TEXT DEFAULT 'cl',
            stage_idx INTEGER,  -- 0=groups, 1=quarters, 2=semis, 3=final
            group_id INTEGER,   -- 0-3 for groups, -1 for KO rounds
            match_idx INTEGER,
            home_id INTEGER, away_id INTEGER,
            played INTEGER DEFAULT 0, home_goals INTEGER, away_goals INTEGER, winner_id INTEGER
        )
    """)

    # ── Mercado de técnicos ──────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coaches (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            nationality TEXT,
            reputation  INTEGER DEFAULT 50,
            club_id     INTEGER REFERENCES clubs(id),  -- NULL = desempregado
            age         INTEGER DEFAULT 50,
            warnings    INTEGER DEFAULT 0,
            is_player   INTEGER DEFAULT 0,             -- 1 = gestor humano
            career_id   INTEGER,                       -- vínculo com career se humano
            retired     INTEGER DEFAULT 0
        )
    """)
    conn.commit()

    # Semeia técnicos IA (1 por clube) se ainda não existir
    seed_coaches(conn, current_year)

    # ── Atribui idade aos jogadores sem birth_date ──────────────────
    assign_ages(conn, current_year)

    # ── Calcula potencial onde falta ────────────────────────────────
    assign_potentials(conn)

    # ── Popula valores de mercado ───────────────────────────────────
    try:
        from engine.career import update_market_values
        update_market_values(conn)
        print("  ✓ valores de mercado")
    except Exception as e:
        print(f"  ⚠ valores de mercado pulados: {e}")

    # ── Salários e contratos ────────────────────────────────────────
    assign_wages_contracts(conn, current_year)

    # ── Capacidade de estádio + ingresso ────────────────────────────
    assign_stadium_capacity(conn)

    # ── Cláusulas de rescisão ───────────────────────────────────────
    assign_release_clauses(conn)

    # ── Índices — zero existiam antes (full table scan em 6k+ jogadores
    # a cada SELECT por club_id/career_id). Aditivo/idempotente, cobre os
    # WHERE mais frequentes vistos no código (grep confirmado):
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_players_club_id   ON players(club_id);
        CREATE INDEX IF NOT EXISTS idx_players_retired   ON players(retired);
        CREATE INDEX IF NOT EXISTS idx_fixtures_lookup   ON fixtures(career_id, season_year, round_idx);
        CREATE INDEX IF NOT EXISTS idx_injuries_lookup   ON injuries(career_id, player_id, status);
        CREATE INDEX IF NOT EXISTS idx_inbox_career_round ON inbox_messages(career_id, round);
        CREATE INDEX IF NOT EXISTS idx_inbox_career_read ON inbox_messages(career_id, read);
        CREATE INDEX IF NOT EXISTS idx_league_table_lookup ON league_table(career_id, league_id, season_year);
        CREATE INDEX IF NOT EXISTS idx_coaches_career    ON coaches(career_id, is_player);
        CREATE INDEX IF NOT EXISTS idx_coaches_club      ON coaches(club_id);
    """)
    conn.commit()
    print("✓ Migração completa.")


def assign_stadium_capacity(conn: sqlite3.Connection):
    """Capacidade + preço base de ingresso ≈ prestígio. Só preenche onde NULL."""
    rows = conn.execute(
        "SELECT id, prestige FROM clubs WHERE capacity IS NULL OR ticket_price IS NULL"
    ).fetchall()
    for cid, prest in rows:
        prest = prest or 60
        cap = int(12_000 + (prest / 100) ** 2.5 * 75_000)
        cap = int(cap * (0.9 + (cid % 20) / 100))
        # Preço base de ingresso escala com prestígio (€21-€66)
        ticket = int(35 * (0.6 + (prest / 100) * 0.9))
        conn.execute("UPDATE clubs SET capacity=?, ticket_price=? WHERE id=?",
                     (cap, ticket, cid))
    conn.commit()
    print(f"  ✓ capacidade + preço de ingresso")


def seed_coaches(conn: sqlite3.Connection, current_year: int):
    """Cria 1 técnico IA por clube que ainda não tem. Reputação ≈ prestígio."""
    existing = conn.execute("SELECT COUNT(*) FROM coaches").fetchone()[0]
    if existing > 0:
        return

    import sys
    sys.path.insert(0, str(ROOT))
    try:
        from scripts.generate_squads import _get_names, _full_name
    except Exception:
        _full_name = None

    clubs = conn.execute("""
        SELECT c.id, c.prestige, COALESCE(co.code,'default') as country
        FROM clubs c
        LEFT JOIN leagues l ON l.id=c.league_id
        LEFT JOIN countries co ON co.id=l.country_id
    """).fetchall()

    n = 0
    for cid, prest, country in clubs:
        seed = int(hashlib.md5(f"coach:{cid}".encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        if _full_name:
            first = _get_names(country, 1, seed)[0]
            name = _full_name(country, first, rng)
        else:
            name = f"Técnico {cid}"
        rep = max(20, min(95, (prest or 60) + rng.randint(-8, 8)))
        age = rng.randint(38, 64)
        conn.execute("""
            INSERT INTO coaches(name, nationality, reputation, club_id, age)
            VALUES (?,?,?,?,?)
        """, (name, country, rep, cid, age))
        n += 1
    conn.commit()
    print(f"  ✓ {n} técnicos IA semeados")


def assign_release_clauses(conn: sqlite3.Connection):
    """Cláusula de rescisão ≈ valor × 1.5-2.5 (melhores → multiplicador maior)."""
    rows = conn.execute(
        "SELECT id, value, overall FROM players WHERE release_clause IS NULL AND retired=0"
    ).fetchall()
    for pid, value, ovr in rows:
        value = value or 5_500_000  # Base value in BRL (€1M × 5.5)
        ovr = ovr or 60
        # Craques têm cláusula mais alta (mais difícil tirar)
        mult = 1.5 + (ovr / 100) * 1.0  # ovr 60→2.1, 90→2.4
        mult += random.uniform(-0.2, 0.3)
        conn.execute("UPDATE players SET release_clause=? WHERE id=?",
                     (int(value * mult), pid))
    conn.commit()
    print(f"  ✓ cláusulas de rescisão")


def assign_wages_contracts(conn: sqlite3.Connection, current_year: int):
    """
    Salário ≈ fração do valor de mercado (€/ano). Contrato 1-5 anos.
    Idempotente: só preenche onde wage=0.
    """
    rows = conn.execute(
        "SELECT id, value, overall, age FROM players WHERE COALESCE(wage,0)=0 AND retired=0"
    ).fetchall()
    for pid, value, ovr, age in rows:
        value = value or 5_500_000  # Base value in BRL (€1M × 5.5)
        # Salário anual ~10-15% do valor (ratio típico futebol)
        wage = int(value * random.uniform(0.10, 0.15))
        wage = max(275_000, wage)  # piso em BRL (€50k × 5.5)
        # Contrato: jovens contratos mais longos, veteranos curtos
        age = age or 25
        if age <= 23:
            dur = random.randint(3, 5)
        elif age <= 30:
            dur = random.randint(2, 4)
        else:
            dur = random.randint(1, 2)
        conn.execute(
            "UPDATE players SET wage=?, contract_until=? WHERE id=?",
            (wage, current_year + dur, pid)
        )
    conn.commit()
    print(f"  ✓ salários e contratos")


def assign_ages(conn: sqlite3.Connection, current_year: int):
    """Deriva idade de birth_date; atribui idade plausível aos sem data."""
    # 1. Quem tem birth_date → calcula
    conn.execute("""
        UPDATE players
        SET age = ? - CAST(substr(birth_date, 1, 4) AS INTEGER)
        WHERE birth_date IS NOT NULL AND age IS NULL
    """, (current_year,))

    # 2. Sem birth_date → atribui por overall (craques tendem a estar no pico)
    rows = conn.execute(
        "SELECT id, overall FROM players WHERE age IS NULL"
    ).fetchall()
    for pid, ovr in rows:
        ovr = ovr or 60
        # Jogadores melhores: distribuição centrada no pico (24-30)
        # Piores/jovens: mais espalhado
        if ovr >= 80:
            age = random.randint(23, 31)
        elif ovr >= 70:
            age = random.choice([19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33])
        else:
            age = random.randint(17, 34)
        conn.execute("UPDATE players SET age=? WHERE id=?", (age, pid))

    # Sanidade: clampa idades absurdas
    conn.execute("UPDATE players SET age=16 WHERE age < 16")
    conn.execute("UPDATE players SET age=42 WHERE age > 42")
    conn.commit()
    print(f"  ✓ idades atribuídas")


def assign_potentials(conn: sqlite3.Connection):
    """
    Potencial = overall máximo que o jogador atingirá.
    Jovens têm gap (vão crescer); veteranos potencial ≈ overall atual.
    """
    rows = conn.execute(
        "SELECT id, overall, age FROM players WHERE potential IS NULL"
    ).fetchall()
    for pid, ovr, age in rows:
        ovr = ovr or 60
        age = age or 25
        if age <= 20:
            # Jovem: potencial pode ser bem maior
            gap = random.randint(3, 18)
        elif age <= 24:
            gap = random.randint(1, 8)
        elif age <= 28:
            gap = random.randint(0, 3)
        else:
            gap = 0  # veterano já no teto
        potential = min(99, ovr + gap)
        conn.execute("UPDATE players SET potential=? WHERE id=?", (potential, pid))
    conn.commit()
    print(f"  ✓ potenciais calculados")


if __name__ == "__main__":
    conn = sqlite3.connect(db_path())
    migrate(conn)
    conn.close()
