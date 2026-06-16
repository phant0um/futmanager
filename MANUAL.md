---
title: FUT BRASIL — Deployment and Feature Manual
project: brasfoot (FUT BRASIL)
stack: Python 3.12+ · SQLite · PyInstaller
updated: 2026-06-16
---

# FUT BRASIL — Deployment and Feature Manual

> Brasfoot/Elifoot clone: a season-based football manager.
> Career mode: you are the **head coach**, manage the club, set the lineup,
> watch live matches, survive the board pressure.
> Zero runtime dependencies (stdlib only). **Web frontend is the default**;
> compact Tkinter GUI as offline fallback; packs as a windowed macOS `.app`.

---

## 1. Overview

| Item | Value |
|------|-------|
| Language | Python 3.12+ (tested on 3.13) |
| Database | SQLite (`data/brasfoot.db`, ~1MB) |
| Runtime deps | **none** (pure stdlib) |
| Build deps | `pyinstaller` |
| `.app` size | ~8MB |
| Data | 9 leagues · 202 clubs · ~5,000 real players (FC26) |
| Interface | **Local web (default)** · compact GUI (`--gui`) · CLI (`--cli`) · web without auto-open (`--web`) |

---

## 2. Prerequisites

```bash
python3 --version        # 3.12 or higher
git --version            # to download OpenFootball data
```

- **Run**: Python 3 only (stdlib). No `pip install`.
- **Pack `.app`**: `python3 -m pip install pyinstaller`
- **Rebuild database**: git (clones OpenFootball repos)
- **Update players**: sofifa.com CSV (FC26) — optional

---

## 3. Deployment

### 3.1 Run directly (development)

```bash
cd /Users/michelcsasznik/Dev/projetos/brasfoot
python3 main.py            # main web mode (starts server + opens browser)
./jogar.sh                 # shortcut to main web mode
python3 main.py --gui      # compact GUI (Tkinter) — offline fallback
./jogar_gui.sh             # shortcut to compact GUI
python3 main.py --cli      # terminal mode
python3 main.py --web      # local web server (http://localhost:8765) without auto-open
```

The database is already bundled in `data/futmanager.db`. The web interface opens in the default
browser: saves screen → new/load → hub (Play · Squad · Table · Lineup · Market · Stadium & Training).
The compact GUI offers a subset of actions for offline/light usage.

### 3.2 Package as macOS `.app` (distribution)

```bash
python3 -m pip install pyinstaller         # one-time
bash scripts/build_app.sh                  # builds dist/FutManager.app (windowed)
open dist/FutManager.app                   # test (opens native GUI window, no terminal)
```

- The `.app` is **double-clickable**: opens the native GUI window directly (PyInstaller `BUNDLE`).
- The initial DB is embedded; saves go to `~/Library/Application Support/FutManager/`.
  The bundled DB is never modified — each player has an isolated save.
- **Unsigned**: on another Mac, Gatekeeper blocks → right-click → Open (first time).

### 3.3 Rebuild the database from scratch (reproducible pipeline)

```bash
bash scripts/rebuild_db.sh
```

Runs the full idempotent pipeline:
1. `import_openfootball.py --all` — clones 9 leagues (structure + fixtures)
2. `set_prestige.py` — prestige for known clubs
3. `seed_top_players.py` — ~200 real star players with attributes
4. `data/update.py` — merges FC26 CSV (sofifa) if present
5. `generate_squads.py --min 18` — fills squads with depth players
6. `migrate_career.py` — career schema + ages/values/wages/stadiums

Result: pristine `data/brasfoot.db` (no career, no newgens).

---

## 4. Project structure

```
brasfoot/
├── main.py                  # entry point
├── paths.py                 # resolves dev vs bundle paths (writable DB)
├── brasfoot.spec            # PyInstaller config
│
├── db/
│   ├── schema.sql           # base schema (clubs, players, leagues, matches)
│   ├── models.py            # dataclasses Club/Player/Standing/Match
│   └── migrate_career.py    # migration: career, coaches, lineup, stadium
│
├── engine/                  # game engine (pure logic)
│   ├── simulation.py        # match simulation (Poisson, no numpy; morale + style)
│   ├── season.py            # league round-robin + dynamic morale
│   ├── cup.py               # cups (knockout, penalties)
│   ├── live.py              # live broadcast (match + round)
│   ├── lineup.py            # formations + lineup + tactical style
│   ├── career.py            # season turnover: age, evolution, retirement, newgens, training
│   ├── transfer.py          # market: buy/sell/loan, negotiation, release clause
│   ├── finance.py           # revenue, payroll, training center, fines, attendance
│   ├── manager.py           # coach reputation, job security
│   └── coach.py             # coach market (AI + human)
│
├── ui/
│   ├── cli.py               # main menu, single match, leagues
│   └── career.py            # full career mode (hub + screens)
│
├── scripts/
│   ├── rebuild_db.sh        # full rebuild pipeline
│   ├── import_openfootball.py
│   ├── set_prestige.py
│   ├── seed_top_players.py
│   ├── generate_squads.py
│   └── build_app.sh         # pack .app
│
└── data/
    ├── brasfoot.db          # SQLite database (embedded in .app)
    ├── update.py            # merge FC26 sofifa CSV + generate attributes
    └── sources/             # OpenFootball repos + fc26_players.csv (not versioned)
```

---

## 5. Data pipeline

```
OpenFootball (git, CC0)  ──┐
  leagues, clubs, fixtures │
                           ├──► SQLite ──► game
FC26 sofifa (CSV scraper)  │
  24k players + attributes │
                           │
Algorithmic generator ─────┘
  fills thin squads
```

| Source | Provides | How |
|--------|----------|-----|
| OpenFootball | League structure, clubs, real fixtures | `import_openfootball.py` (git clone) |
| FC26 sofifa | Names + real attributes (~24k players) | browser JS scraper → `fc26_players.csv` |
| seed_top_players | ~200 hand-tuned stars | `seed_top_players.py` |
| generator | Squad depth (reserves) | `generate_squads.py` |

### Update players (new FC season)

1. On sofifa.com (logged in), run the JS scraper → download `fc26_players.csv`
2. Save it to `data/sources/fc26_players.csv`
3. `python3 data/update.py --skip-openfootball --skip-top-seed`
4. `python3 db/migrate_career.py` (recalculates values/wages)

---

## 6. Built-in features

### 6.1 Main menu (`ui/cli.py`)

| # | Function |
|---|----------|
| 1 | **Career mode** (core game) |
| 2 | View available leagues |
| 3 | Simulate a standalone season |
| 4 | Quick match (with optional **live watch**) |
| 5 | View standings |
| 6 | View players of a club |
| 7 | Update database (dev) |

### 6.2 Career mode — hub (`ui/career.py`)

```
1 Squad            5 🎟️  Stadium & Training
2 📋 Lineup         6 📊 Standings
3 ▶️  Play season    7 🔍 Search club (squads)
4 💰 Market         8 Scout · 9 History
```

#### Lineup + tactics (`engine/lineup.py`)
- 7 formations: 4-4-2, 4-3-3, 4-2-3-1, 3-5-2, 5-3-2, 3-4-3, 4-5-1
- Auto-pick best 11 by position; swap starter ↔ reserve
- The 11 starters define attack/defense ratings for simulation
- **Tactical style** `[e]`:
  - Attacking (+12% attack / −10% defense) — more goals for and against
  - Balanced — neutral
  - Defensive (−14% attack / +12% defense) — locks down against stronger teams
- **Squad limits**: 30 players max; bench limited to 12 reserves

#### Play season (`engine/season.py` + `engine/live.py`)
- Home-and-away round-robin (38 rounds / 20 clubs)
- **Live watch**: full-round broadcast (~2min)
  - Goal/card/injury feed for every match, minute-by-minute
  - Your match with extra detail; final score + stadium name
  - `[Enter]` watch · `[p]` scores only · `[s]` simulate rest
- Live results feed the standings
- **Cups** (after the league) — `engine/cup.py`:
  - National Cup (16 clubs from your league) + Continental Cup (16 best worldwide)
  - Knockout with penalties on draw; prize money, reputation, titles
  - Your campaign: Round of 16 → Quarter → Semi → Final → CHAMPION 🏆

#### Stadium & Training (`engine/finance.py` + `engine/career.py`)
- **Ticket price**: edit price → changes attendance (demand curve) → changes match-day revenue
- **Training Center**: level 1-5, cost €2.5M×level/year
  - Level >2 accelerates your squad's evolution; <2 saves money

#### Transfer market (`engine/transfer.py`)
- **Buy**: filter by position/price; **negotiation** (offer → counter-offer → accept)
- **Release clause**: paying it forces an instant buy
- **Sell**: AI club offers; selling an **idol** (OVR≥82) costs reputation
- **Loan IN**: no fee, propose % of wage + monthly fee; AI accepts if it covers costs
- **Loan OUT**: frees wage; player returns after 1 season
- Squad limits: 30 players, bench 12

#### Stadium and tickets (`engine/finance.py`)
- Edit ticket price → changes attendance (demand curve) → changes match-day revenue
- Live projection: attendance % + crowd + yearly revenue
- There is an optimal price (expensive = empty, cheap = full but little money)

#### Standings / Search club (management page)
- Full persisted standings (P/W/D/L/GF/GA/GD), zones 🟢/🔴, ◀ you
- Search any club → coach, stadium, full squad, values

### 6.3 Economy (`engine/finance.py`)

At the end of each season:

```
REVENUE = sponsorship/TV (prestige) + match-day revenue (price × attendance)
          + prize money (position) + title bonus + cup prizes
EXPENSE = payroll + training center + loan fees + red-card fines
BALANCE = REVENUE − EXPENSE  →  cash
```

- Negative cash = warning (must sell)
- Wages + training center limit purchases (high payroll = unsustainable)
- Fine per red card (4% of yearly wage per sending-off)

### 6.4 Morale (`engine/season.py`)

- Each club has **morale 0.85–1.15** that affects attack
- Wins raise morale, losses lower it; regresses to the mean over time
- Propagates between rounds — good form yields more goals (and vice versa)

### 6.5 Season turnover (`engine/career.py`)

The off-season processes the whole world:
1. **Aging**: everyone +1 year
2. **Evolution/regression**: grows until 27 (peak) → plateau 28-31 → declines from 32
   (age curve × potential; club training center gives evolution bonus to your squad)
3. **Retirements**: by age+position (GK up to 43, outfield up to 40)
4. **Newgens**: ~800/season worldwide, skewed potential (2% wonderkids POT 82-92)
5. **Contracts**: expired auto-renew (AI); yours you decide (renew/release)
6. **Loans**: expired return to owner club
7. **Market values** recalculated

### 6.6 Coach career (`engine/manager.py` + `engine/coach.py`)

- **You are the coach** (single human role, no separate "manager")
- **Reputation 0-100**, changes by:
  - Campaign vs. board target (±20)
  - Title (+12), relegation (−15)
  - Financial health (±)
  - Selling idols (−)
- **Job security**: reputation <38 = warning (2 = sacked); <25 = sacked immediately
- **Coach market**: 202 AI coaches + you, same rules
  - Sacked (AI or human) → free agent → rehired
  - **When you are sacked you receive offers** (scaled by reputation): continue at another club or end
  - Coach carousel every season

---

## 7. Recommended usage flow

```
1. python3 main.py
2. Career mode → New career
3. Choose league + club + coach name
4. 📋 Lineup: formation, 11 starters and tactical style
5. 💰 Market: strengthen (negotiate/clause/loan)
6. 🎟️  Stadium & Training: ticket price + training level
7. ▶️  Play season (live watch or simulate) + cups
8. Renew contracts · review balance · reputation
9. Repeat: build a dynasty without getting sacked
```

---

## 8. Database schema (main tables)

| Table | Content |
|-------|---------|
| `leagues` / `clubs` / `players` | structure + squads |
| `countries` | league countries |
| `matches` / `rounds` / `seasons` | fixtures and calendar |
| `career` | coach save (club, year, cash, reputation, formation, lineup, tactic, training) |
| `coaches` | coaches (AI + human `is_player=1`) |
| `season_history` | champions + final position per season |
| `league_table` | persisted standings (table screen) |
| `transfers` | transfer history |

Key `players` columns: `overall`, `potential`, `age`, `wage`, `contract_until`,
`value`, `release_clause`, `loan_from_club`, `red_cards`, `is_newgen`, `retired`.

Key `career` columns: `formation`, `lineup`, `tactic_style`, `training_level`,
`expectation`, `warnings`. In `clubs`: `prestige`, `capacity`, `ticket_price`.

---

## 9. Troubleshooting

| Problem | Solution |
|---------|----------|
| "Database not found" | `bash scripts/rebuild_db.sh` |
| `.app` won't open on another Mac | Right-click → Open (Gatekeeper) |
| Update DB inside `.app` | not available in bundle; use dev version |
| Broken career | save is in `~/Library/Application Support/BrasfootClone/`; delete to restart |
| Rebuild is slow | `import_openfootball` clones repos (first run ~1min) |
| Want new data | download `fc26_players.csv` → `data/update.py` |

---

## 10. Technical summary

FUT BRASIL is a complete manager: season-based career, lineup + tactical style,
transfer market with negotiation/clause/loan, economy (payroll/attendance/training/fines/cups),
dynamic morale, training, national and continental cups, living world (peak-27/decline-32,
newgens, retirements), coach market with job security, and live match broadcast.
All in Python stdlib, reproducible SQLite database via pipeline,
distributable as an 8MB `.app`.

**Ready-to-use deployment:** `python3 main.py` (dev) or
`PyInstaller + build_app.sh` (`.app`). Database included.
