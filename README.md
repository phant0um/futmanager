# ⚽ FutManager

A season-based football manager in pure Python, inspired by **Brasfoot / Elifoot**.
You are the **head coach**: build the squad, set the lineup, negotiate in the transfer market,
watch the matches live, manage stadium finances and survive the board's pressure — season after season.

> **Player names are fictional** (randomly generated). League and club structure is based on
> open data from [OpenFootball](https://github.com/openfootball) (CC0).

## Highlights

- **Web UI (default)** — clean, modern interface that runs in any browser. This is the main way to play.
- **Compact GUI** (Tkinter) — lightweight offline fallback (`--gui`) when you cannot or do not want to use a browser.
- **Terminal mode** (`--cli`) — full control via text.
- **Zero runtime dependencies** — only the Python standard library. Packs as a macOS `.app` (~11 MB).
- **Full career mode:**
  - Player evolution/regression by age (grows until ~27, plateaus, declines after 32), retirements and *newgens*
  - Transfer market with negotiation, counter-offers, release clauses, sales and loans
  - Finances: sponsorships, match-day revenue (ticket price affects attendance), prizes, wages, fines
  - Coach reputation: performance vs. board expectation → you can be sacked (and rehired by another club)
  - Lineup with formations and tactical style (attacking / balanced / defensive) + Training Center
  - Brazilian calendar: state championships (Paulistão format), Série A/B/C/D, Copa do Brasil, Libertadores and Sudamericana — all interleaved
  - Multiple *saves* (each game is an independent world)

## Run

```bash
python3 main.py          # main web mode (starts server + opens browser)
python3 main.py --web    # web server only (does not auto-open browser)
python3 main.py --gui    # compact GUI (Tkinter) - offline fallback
python3 main.py --cli    # terminal mode
```

Or use the ready-made scripts:

```bash
bash jogar.sh      # main web mode
bash jogar_gui.sh  # compact GUI
```

The initial database is already bundled in `data/futmanager.db`.

## Package as `.app` (macOS)

```bash
python3 -m pip install pyinstaller
bash scripts/build_app.sh        # builds dist/FutManager.app
open dist/FutManager.app
```

## Architecture

All game logic lives in **`gameapi.py`** — I/O-free functions that receive a SQLite
connection and return dicts. The GUI (`gui/app.py`) and the web layer (`web/server.py`)
are only presentation layers on top of the same API. Single source of truth.

```
gameapi.py        game layer (state, play, lineup, market, stadium)
engine/           simulation, season, career, finance, cups, state leagues, market
db/               models + schema migration
gui/app.py        original Tkinter GUI (kept for compatibility)
gui/compact.py    compact Tkinter GUI (offline fallback)
web/              main web frontend (default mode)
launch_web.py     launcher: starts server + opens browser
scripts/          database pipeline (rebuild, squad generation, anonymization)
```

## Rebuild the database

```bash
bash scripts/rebuild_db.sh               # clones OpenFootball, generates squads, builds the world
python3 scripts/anonymize_players.py     # ensures fictional names
```

Full details in [MANUAL.md](MANUAL.md).

---

Code license: MIT. League/club structure: OpenFootball (CC0).
