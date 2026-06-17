---
title: FutManager — Deployment and Feature Manual
project: futmanager (brasfoot)
stack: Python 3.12+ · SQLite · PyInstaller
updated: 2026-06-17
---

# FutManager — Deployment and Feature Manual

> Brasfoot/Elifoot-inspired season-based football manager.
> You are the **head coach**, build the squad, set the lineup,
> watch live matches, negotiate transfers and survive the board pressure.
> Zero runtime dependencies (stdlib only). **Web UI is the default and recommended mode**;
> compact Tkinter GUI as an offline fallback; CLI for terminal users; packs as a macOS `.app`.

---

## 1. Overview

| Item | Value |
|------|-------|
| Language | Python 3.12+ (tested on 3.13) |
| Database | SQLite (`data/futmanager.db`) |
| Runtime deps | **none** (pure stdlib) |
| Build deps | `pyinstaller` (optional, for `.app`) |
| `.app` size | ~11 MB |
| Data | 9 leagues · 202 clubs · fictional players |
| Interface | **Local web (default)** · compact GUI (`--gui`) · CLI (`--cli`) · web without auto-open (`--web`) |

---

## 2. Prerequisites

```bash
python3 --version        # 3.12 or higher
```

- **Run**: Python 3 only (stdlib). No `pip install`.
- **Pack `.app`**: `python3 -m pip install pyinstaller`
- **Rebuild database**: git (clones OpenFootball data)

---

## 3. Deployment

### 3.1 Run directly (development)

```bash
cd /path/to/brasfoot
python3 main.py            # main web mode (starts server + opens browser)
python3 main.py --web      # local web server (http://localhost:8765) without auto-open
python3 main.py --gui      # compact GUI (Tkinter) — offline fallback
python3 main.py --cli      # terminal mode
```

Use the bundled helper scripts:

```bash
bash jogar.sh            # main web mode
bash jogar_gui.sh        # compact GUI
```

The database is already bundled in `data/futmanager.db`.
The web interface opens in the default browser: saves screen → new/load → hub
(Play · Squad · Table · Lineup · Market · Stadium & Training · Inbox · Scout · Search · History).
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
3. `seed_top_players.py` — star players with attributes
4. `data/update.py` — merges FC26 CSV (sofifa) if present
5. `generate_squads.py --min 18` — fills squads with depth players
6. `migrate_career.py` — career schema + ages/values/wages/stadiums

Result: pristine `data/futmanager.db` (no career, no newgens).

---

## 4. Project structure

```
brasfoot/
├── main.py                  # entry point
├── paths.py                 # resolves dev vs bundle paths (writable DB)
├── futmanager.spec          # PyInstaller config
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
│   ├── coach.py             # coach market (AI + human)
│   └── scouting.py          # scout search and negotiation
│
├── ui/
│   ├── cli.py               # main menu, single match, leagues
│   └── career.py            # full career mode (hub + screens)
│
├── web/                     # default frontend
│   ├── server.py            # HTTP + JSON API shim
│   └── static/              # HTML/CSS/JS app
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
    ├── futmanager.db        # SQLite database (embedded in .app)
    ├── update.py            # merge FC26 sofifa CSV + generate attributes
    └── sources/             # OpenFootball repos + fc26_players.csv (not versioned)
```

---

## 5. Built-in features

### 5.1 Career mode — hub

```
1 Squad            5 Stadium & Training
2 Lineup           6 Standings
3 Play season      7 Search club (squads)
4 Market           8 Scout · 9 History · 10 Inbox (offers)
```

#### Lineup + tactics (`engine/lineup.py`)
- 23 formations; auto-pick best 11 by position; swap starter ↔ reserve
- The 11 starters define attack/defense ratings for simulation
- **Tactical style**:
  - Attacking (+12% attack / −10% defense) — more goals for and against
  - Balanced — neutral
  - Defensive (−14% attack / +12% defense) — locks down against stronger teams
- **Squad limits**: 30 players max; bench limited to 12 reserves

#### Play season (`engine/season.py` + `engine/live.py`)
- Home-and-away round-robin (38 rounds / 20 clubs)
- **Live watch**: full-round broadcast
  - Goal/card/injury feed for every match, minute-by-minute
  - Your match with extra detail; final score + stadium name
- Live results feed the standings
- **Cups** (after the league) — `engine/cup.py`:
  - National Cup (16 clubs from your league) + Continental Cup (16 best worldwide)
  - Knockout with penalties on draw; prize money, reputation, titles
  - Your campaign: Round of 16 → Quarter → Semi → Final → CHAMPION 🏆

#### Stadium & Training (`engine/finance.py` + `engine/career.py`)
- **Ticket price**: edit price → changes attendance (demand curve) → changes match-day revenue
- **Training Center**: level 1-5, cost scales with level
  - Higher level accelerates your squad's evolution; lower level saves money

#### Transfer market (`engine/transfer.py`)
- **Buy**: filter by position/price/overall; **negotiation** (offer → counter-offer → accept)
- **Release clause**: paying it forces an instant buy
- **Sell**: AI clubs send offers; selling an **idol** (high OVR) costs reputation
- **Loan IN**: no fee, propose wage share; AI accepts if it covers costs
- **Loan OUT**: frees wage; player returns after 1 season
- **Inbox**: view and respond to offers received for your listed players
- Squad limits: 30 players, bench 12

#### Search club and standings
- Full persisted standings (P/W/D/L/GF/GA/GD), zones, your position highlighted
- Search any club → coach, stadium, full squad, values

### 5.2 Economy (`engine/finance.py`)

At the end of each season:

```
REVENUE = sponsorship/TV (prestige) + match-day revenue (price × attendance)
          + prize money (position) + title bonus + cup prizes
EXPENSE = payroll + training center + loan fees + red-card fines
BALANCE = REVENUE − EXPENSE  →  cash
```

- Negative cash = warning (must sell)
- Wages + training center limit purchases (high payroll = unsustainable)
- Fine per red card (percentage of yearly wage per sending-off)

### 5.3 Morale (`engine/season.py`)

- Each club has **morale 0.85–1.15** that affects attack
- Wins raise morale, losses lower it; regresses to the mean over time
- Propagates between rounds — good form yields more goals (and vice versa)

### 5.4 Season turnover (`engine/career.py`)

The off-season processes the whole world:
1. **Aging**: everyone +1 year
2. **Evolution/regression**: grows until 27 (peak) → plateau 28-31 → declines from 32
   (age curve × potential; club training center gives evolution bonus to your squad)
3. **Retirements**: by age+position (GK up to 43, outfield up to 40)
4. **Newgens**: new players every season, skewed potential
5. **Contracts**: expired auto-renew (AI); yours you decide (renew/release)
6. **Loans**: expired return to owner club
7. **Market values** recalculated

### 5.5 Coach career (`engine/manager.py` + `engine/coach.py`)

- **You are the coach** (single human role, no separate "manager")
- **Reputation 0-100**, changes by:
  - Campaign vs. board target
  - Title / relegation
  - Financial health
  - Selling idols
- **Job security**: low reputation triggers warnings, then sacking
- **Coach market**: AI coaches + you, same rules
  - Sacked (AI or human) → free agent → rehired
  - **When you are sacked you receive offers** scaled by reputation
  - Coach carousel every season

---

## 6. Recommended usage flow

```
1. python3 main.py
2. Career mode → New career
3. Choose league + club + coach name
4. Lineup: formation, 11 starters and tactical style
5. Market: strengthen (negotiate/clause/loan)
6. Stadium & Training: ticket price + training level
7. Play season (live watch or simulate) + cups
8. Renew contracts · review balance · reputation
9. Repeat: build a dynasty without getting sacked
```

---

## 7. Database schema (main tables)

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

## 8. Troubleshooting

| Problem | Solution |
|---------|----------|
| "Database not found" | `bash scripts/rebuild_db.sh` |
| `.app` won't open on another Mac | Right-click → Open (Gatekeeper) |
| Update DB inside `.app` | not available in bundle; use dev version |
| Broken career | saves are in `~/Library/Application Support/FutManager/`; delete to restart |
| Rebuild is slow | `import_openfootball` clones repos (first run ~1min) |
| Want new data | download `fc26_players.csv` → `data/update.py` |

---

## 9. Technical summary

FutManager is a complete manager: season-based career, lineup + tactical style,
transfer market with negotiation/clause/loan, economy (payroll/attendance/training/fines/cups),
dynamic morale, training, national and continental cups, living world (peak-27/decline-32,
newgens, retirements), coach market with job security, and live match broadcast.
All in Python stdlib, reproducible SQLite database via pipeline,
distributable as an ~11 MB `.app`.

**Ready-to-use deployment:** `python3 main.py` (dev) or
`PyInstaller + build_app.sh` (`.app`). Database included.
