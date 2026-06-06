-- Brasfoot Clone — SQLite Schema
-- v1.0 — 2026-06-02

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ─── ESTRUTURA ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS countries (
    id      INTEGER PRIMARY KEY,
    code    TEXT UNIQUE NOT NULL,  -- BR, ES, EN...
    name    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leagues (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    country_id INTEGER REFERENCES countries(id),
    level      INTEGER DEFAULT 1,  -- 1=primeira divisão
    season     TEXT NOT NULL        -- "2025-26"
);

CREATE TABLE IF NOT EXISTS clubs (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    short_name  TEXT,
    league_id   INTEGER REFERENCES leagues(id),
    prestige    INTEGER DEFAULT 50 CHECK(prestige BETWEEN 1 AND 100),
    stadium     TEXT,
    founded     INTEGER,
    source_id   TEXT   -- ID externo (OpenFootball, etc.)
);

-- ─── JOGADORES ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS players (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    position    TEXT CHECK(position IN ('GK','DF','MF','FW')),
    nationality TEXT,
    birth_date  TEXT,
    club_id     INTEGER REFERENCES clubs(id),

    -- Atributos (1–99, escala FIFA/EA)
    pace        INTEGER DEFAULT 50 CHECK(pace BETWEEN 1 AND 99),
    technique   INTEGER DEFAULT 50 CHECK(technique BETWEEN 1 AND 99),
    strength    INTEGER DEFAULT 50 CHECK(strength BETWEEN 1 AND 99),
    finishing   INTEGER DEFAULT 50 CHECK(finishing BETWEEN 1 AND 99),
    passing     INTEGER DEFAULT 50 CHECK(passing BETWEEN 1 AND 99),
    defending   INTEGER DEFAULT 50 CHECK(defending BETWEEN 1 AND 99),
    goalkeeping INTEGER DEFAULT 50 CHECK(goalkeeping BETWEEN 1 AND 99),
    stamina     INTEGER DEFAULT 50 CHECK(stamina BETWEEN 1 AND 99),
    mental      INTEGER DEFAULT 50 CHECK(mental BETWEEN 1 AND 99),

    -- Overall calculado (trigger atualiza)
    overall     INTEGER DEFAULT 50,

    -- Metadata
    source      TEXT,   -- "fc25_kaggle" | "openfootball" | "generated"
    source_id   TEXT,
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- ─── TEMPORADA ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS seasons (
    id         INTEGER PRIMARY KEY,
    league_id  INTEGER REFERENCES leagues(id),
    year       TEXT NOT NULL,
    status     TEXT DEFAULT 'active' CHECK(status IN ('active','finished'))
);

CREATE TABLE IF NOT EXISTS rounds (
    id        INTEGER PRIMARY KEY,
    season_id INTEGER REFERENCES seasons(id),
    number    INTEGER NOT NULL,
    name      TEXT   -- "Rodada 1", "Semifinal", etc.
);

CREATE TABLE IF NOT EXISTS matches (
    id         INTEGER PRIMARY KEY,
    round_id   INTEGER REFERENCES rounds(id),
    home_id    INTEGER REFERENCES clubs(id),
    away_id    INTEGER REFERENCES clubs(id),
    home_goals INTEGER,
    away_goals INTEGER,
    played     INTEGER DEFAULT 0,
    played_at  TEXT
);

-- ─── TABELA DE CLASSIFICAÇÃO ──────────────────────────────────
CREATE TABLE IF NOT EXISTS standings (
    id         INTEGER PRIMARY KEY,
    season_id  INTEGER REFERENCES seasons(id),
    club_id    INTEGER REFERENCES clubs(id),
    played     INTEGER DEFAULT 0,
    wins       INTEGER DEFAULT 0,
    draws      INTEGER DEFAULT 0,
    losses     INTEGER DEFAULT 0,
    gf         INTEGER DEFAULT 0,  -- gols feitos
    ga         INTEGER DEFAULT 0,  -- gols sofridos
    points     INTEGER DEFAULT 0,
    UNIQUE(season_id, club_id)
);

-- ─── TRANSFERÊNCIAS ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transfers (
    id         INTEGER PRIMARY KEY,
    player_id  INTEGER REFERENCES players(id),
    from_club  INTEGER REFERENCES clubs(id),
    to_club    INTEGER REFERENCES clubs(id),
    season_id  INTEGER REFERENCES seasons(id),
    fee        INTEGER DEFAULT 0,
    date       TEXT DEFAULT (date('now'))
);

-- ─── ÍNDICES ──────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_players_club    ON players(club_id);
CREATE INDEX IF NOT EXISTS idx_players_pos     ON players(position);
CREATE INDEX IF NOT EXISTS idx_matches_round   ON matches(round_id);
CREATE INDEX IF NOT EXISTS idx_standings_season ON standings(season_id);
