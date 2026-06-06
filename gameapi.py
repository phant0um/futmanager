"""
FUTMANAGER — Camada de jogo (I/O-free).
Funções puras: recebem conn, devolvem dict/list. Sem HTTP, sem terminal.
Reusada por: gui/app.py (Tkinter) e web/server.py (HTTP shim).
"""
from __future__ import annotations
import sqlite3
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from paths import db_path


def conn():
    c = sqlite3.connect(db_path())
    c.row_factory = sqlite3.Row
    return c


# ─── Cores de clube (determinístico do nome) ─────────────────────────────────

def club_colors(name: str) -> dict:
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue = h % 360
    return {"primary": f"hsl({hue},65%,42%)", "accent": f"hsl({(hue+30)%360},70%,55%)",
            "hue": hue}


def club_hex(name: str) -> tuple[str, str]:
    """(primary, accent) em #rrggbb — pra Tkinter, que não aceita hsl()."""
    import colorsys
    hue = int(hashlib.md5(name.encode()).hexdigest(), 16) % 360
    def hx(h, s, l):
        r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    return hx(hue, 0.55, 0.40), hx((hue + 30) % 360, 0.62, 0.55)


def fmt_money(v: int) -> str:
    v = v or 0
    if abs(v) >= 1_000_000:
        return f"€{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"€{v/1_000:.0f}K"
    return f"€{v}"


# ─── Estado / dados ──────────────────────────────────────────────────────────

def get_active_career(c):
    return c.execute("SELECT * FROM career WHERE status='active' ORDER BY updated_at DESC LIMIT 1").fetchone()


def api_state(c):
    car = get_active_career(c)
    if not car:
        return {"has_career": False}
    club = c.execute("SELECT * FROM clubs WHERE id=?", (car["manager_club_id"],)).fetchone()
    coach = c.execute("SELECT name FROM coaches WHERE career_id=? AND is_player=1", (car["id"],)).fetchone()
    return {
        "has_career": True,
        "coach": coach["name"] if coach else "Técnico",
        "club": {"id": club["id"], "name": club["name"],
                 "prestige": club["prestige"], "colors": club_colors(club["name"])},
        "season": car["season_year"],
        "money": car["money"], "money_fmt": fmt_money(car["money"]),
        "reputation": car["reputation"], "titles": car["titles"],
        "seasons_played": car["seasons_played"],
        "expectation": car["expectation"],
        "formation": car["formation"] or "4-3-3",
        "tactic_style": car["tactic_style"] or "equilibrado",
        "training_level": car["training_level"] or 2,
        "status": car["status"],
    }


def api_squad(c):
    car = get_active_career(c)
    if not car:
        return []
    rows = c.execute("""
        SELECT id, name, position, age, overall, potential, value, wage,
               contract_until, loan_from_club
        FROM players WHERE club_id=? AND retired=0
        ORDER BY CASE position WHEN 'GK' THEN 1 WHEN 'DF' THEN 2
                               WHEN 'MF' THEN 3 WHEN 'FW' THEN 4 END, overall DESC
    """, (car["manager_club_id"],)).fetchall()
    out = []
    for p in rows:
        out.append({
            "id": p["id"], "name": p["name"], "position": p["position"] or "?",
            "age": p["age"] or 0, "overall": p["overall"], "potential": p["potential"],
            "value": p["value"], "value_fmt": fmt_money(p["value"]),
            "wage_fmt": fmt_money(p["wage"]),
            "contract": p["contract_until"], "loan": p["loan_from_club"] is not None,
        })
    return out


def api_leagues(c):
    rows = c.execute("""
        SELECT l.id, l.name, co.code as country, COUNT(cl.id) n
        FROM leagues l LEFT JOIN countries co ON co.id=l.country_id
        LEFT JOIN clubs cl ON cl.league_id=l.id
        WHERE l.level >= 1 GROUP BY l.id ORDER BY co.code
    """).fetchall()
    return [{"id": r["id"], "name": r["name"], "country": r["country"], "n": r["n"]} for r in rows]


def api_clubs(c, league_id):
    rows = c.execute("SELECT id, name, prestige FROM clubs WHERE league_id=? ORDER BY prestige DESC",
                     (league_id,)).fetchall()
    return [{"id": r["id"], "name": r["name"], "prestige": r["prestige"],
             "colors": club_colors(r["name"])} for r in rows]


def api_table(c):
    car = get_active_career(c)
    if not car:
        return {"rows": []}
    league_id = c.execute("SELECT league_id FROM clubs WHERE id=?", (car["manager_club_id"],)).fetchone()[0]
    last = c.execute("SELECT MAX(season_year) FROM league_table WHERE career_id=? AND league_id=?",
                     (car["id"], league_id)).fetchone()[0]
    # tabela ao vivo da temporada corrente (fixtures jogadas)
    from engine import calendar as CAL
    live = CAL.standings(c, car)
    if live:
        n = len(live)
        rows = []
        for i, s in enumerate(live, 1):
            rows.append({
                "pos": i, "name": s.club_name, "club_id": s.club_id,
                "colors": club_colors(s.club_name),
                "played": s.played, "wins": s.wins, "draws": s.draws,
                "losses": s.losses, "gf": s.gf, "ga": s.ga,
                "gd": s.gf - s.ga, "points": s.points,
                "is_player": s.club_id == car["manager_club_id"],
                "zone": "cl" if i <= 4 else ("rel" if i > n - 3 else ""),
            })
        return {"rows": rows, "season": car["season_year"]}
    if not last:
        return {"rows": [], "season": None}
    rows = c.execute("""
        SELECT lt.pos, cl.name, cl.id club_id, lt.played, lt.wins, lt.draws, lt.losses,
               lt.gf, lt.ga, lt.points
        FROM league_table lt JOIN clubs cl ON cl.id=lt.club_id
        WHERE lt.career_id=? AND lt.league_id=? AND lt.season_year=? ORDER BY lt.pos
    """, (car["id"], league_id, last)).fetchall()
    n = len(rows)
    out = []
    for r in rows:
        out.append({
            "pos": r["pos"], "name": r["name"], "club_id": r["club_id"],
            "colors": club_colors(r["name"]),
            "played": r["played"], "wins": r["wins"], "draws": r["draws"],
            "losses": r["losses"], "gf": r["gf"], "ga": r["ga"],
            "gd": r["gf"] - r["ga"], "points": r["points"],
            "is_player": r["club_id"] == car["manager_club_id"],
            "zone": "cl" if r["pos"] <= 4 else ("rel" if r["pos"] > n - 3 else ""),
        })
    return {"rows": out, "season": last}


def create_career(club_id, coach_name):
    from ui.career import _money_for_prestige, get_active_career as _gac
    from engine.manager import create_player_coach, set_expectation
    import saves as SV
    coach_name = coach_name or "Técnico"

    c0 = conn()
    club = c0.execute("SELECT name, prestige FROM clubs WHERE id=?", (club_id,)).fetchone()
    season = c0.execute("SELECT MAX(season) FROM leagues").fetchone()[0]
    c0.close()
    if not club:
        return {"ok": False, "error": "clube inválido"}
    try:
        year = int(str(season)[:4])
    except (ValueError, TypeError):
        year = 2026
    money = _money_for_prestige(club["prestige"])

    SV.new_save(f"{coach_name} - {club['name']}")
    c = conn()
    c.execute("UPDATE career SET status='archived' WHERE status='active'")
    c.execute("INSERT INTO career(manager_club_id, season_year, money, reputation) VALUES (?,?,?,?)",
              (club_id, year, money, club["prestige"]))
    c.commit()
    career = _gac(c)
    create_player_coach(c, career, coach_name)
    set_expectation(c, career)
    c.close()
    return {"ok": True}


# ─── JOGAR (motor sem I/O) ────────────────────────────────────────────────────

def _club_obj(conn, club_id):
    from db.models import Club, Player
    r = conn.execute("SELECT * FROM clubs WHERE id=?", (club_id,)).fetchone()
    ps = conn.execute("SELECT * FROM players WHERE club_id=? AND retired=0 ORDER BY overall DESC LIMIT 23",
                      (club_id,)).fetchall()
    players = [Player(id=p["id"], name=p["name"], position=p["position"] or "MF",
        nationality=p["nationality"] or "", birth_date=p["birth_date"], club_id=p["club_id"],
        pace=p["pace"], technique=p["technique"], strength=p["strength"], finishing=p["finishing"],
        passing=p["passing"], defending=p["defending"], goalkeeping=p["goalkeeping"],
        stamina=p["stamina"], mental=p["mental"], overall=p["overall"], source=p["source"] or "")
        for p in ps]
    c = Club(id=r["id"], name=r["name"], short_name=r["name"][:12],
             league_id=r["league_id"] or 0, prestige=r["prestige"])
    c.players = players
    return c


def _player_country_state(conn, club_id):
    state = conn.execute("SELECT state FROM clubs WHERE id=?", (club_id,)).fetchone()[0]
    cr = conn.execute("""SELECT co.code FROM clubs c JOIN leagues l ON l.id=c.league_id
        JOIN countries co ON co.id=l.country_id WHERE c.id=?""", (club_id,)).fetchone()
    return (cr[0] if cr else None), state


def api_next(conn):
    from engine import calendar as CAL, copa as COPA
    car = get_active_career(conn)
    if not car:
        return {"kind": "none"}
    cid = car["manager_club_id"]
    country, state = _player_country_state(conn, cid)
    if state and (car["estadual_year"] or 0) != car["season_year"]:
        return {"kind": "estadual", "label": "Estadual (início da temporada)"}
    CAL.ensure_fixtures(conn, car)
    cr = car["current_round"] or 0
    nr = CAL.num_rounds(conn, car)
    if country in ("BR", "AR"):
        due = COPA.due_comp(conn, car, cr)
        if due:
            comp, st = due
            pt = COPA.player_tie(conn, car, comp, st)
            return {"kind": "copa", "comp": comp, "stage": st,
                    "label": f"{COPA.COMPS[comp]['name']} — {COPA.STAGES[st][0]}"
                             + (f" vs {pt['opp_name']}" if pt else "")}
    nm = CAL.next_match(conn, car)
    if nm:
        return {"kind": "league", "round": cr, "n": nr,
                "label": f"Rodada {cr+1}/{nr} · vs {nm['opp_name']} ({nm['loc']})"}
    return {"kind": "season_end", "label": "Fim de temporada — processar entressafra"}


def api_play(conn):
    car = get_active_career(conn)
    if not car:
        return {"ok": False}
    ev = api_next(conn)
    k = ev["kind"]
    if k == "estadual":
        return _web_estadual(conn, car)
    if k == "copa":
        return _web_copa(conn, car, ev["comp"], ev["stage"])
    if k == "league":
        return _web_league_round(conn, car)
    if k == "season_end":
        return _web_finish_season(conn, car)
    return {"ok": False, "kind": k}


def _apply_player_tactics(conn, career, club):
    from ui.career import get_saved_xi
    from engine.lineup import style_mults
    _, xi = get_saved_xi(conn, career, club.players)
    club.starting_xi = xi
    club.style_atk, club.style_def = style_mults(career["tactic_style"] or "equilibrado")


def _web_league_round(conn, career):
    from engine import calendar as CAL
    from engine.simulation import simulate_match
    from engine.season import _update_morale
    cid = career["manager_club_id"]
    cr = career["current_round"] or 0
    nr = CAL.num_rounds(conn, career)
    clubs = CAL._load_league_clubs(conn, CAL.league_id_of(conn, cid))
    by_id = {c.id: c for c in clubs}
    if cid in by_id:
        _apply_player_tactics(conn, career, by_id[cid])
    for c in clubs:
        c.morale = CAL._club_morale(conn, career, c.id)
    fxs = conn.execute("""SELECT id, home_id, away_id FROM fixtures
        WHERE career_id=? AND season_year=? AND round_idx=? AND played=0""",
        (career["id"], career["season_year"], cr)).fetchall()
    your = None
    for f in fxs:
        h, a = by_id[f["home_id"]], by_id[f["away_id"]]
        r = simulate_match(h, a)
        conn.execute("UPDATE fixtures SET played=1, home_goals=?, away_goals=? WHERE id=?",
                     (r.home_goals, r.away_goals, f["id"]))
        _update_morale(h, a, r.home_goals, r.away_goals)
        if cid in (h.id, a.id):
            your = {"home": h.name, "hg": r.home_goals, "ag": r.away_goals, "away": a.name}
    conn.execute("UPDATE career SET current_round=?, updated_at=datetime('now') WHERE id=?",
                 (cr + 1, career["id"]))
    conn.commit()
    tab = CAL.standings(conn, career)
    pos = next((i for i, s in enumerate(tab, 1) if s.club_id == cid), None)
    return {"ok": True, "kind": "league", "round": cr + 1, "n": nr, "your": your,
            "pos": pos, "table": [{"pos": i, "name": s.club_name, "pts": s.points,
                                   "j": s.played, "is_player": s.club_id == cid}
                                  for i, s in enumerate(tab[:6], 1)]}


def _web_copa(conn, career, comp, st):
    from engine import copa as COPA
    cid = career["manager_club_id"]
    ids = set()
    for r in conn.execute("""SELECT home_id, away_id FROM copa WHERE career_id=? AND season_year=?
            AND comp=? AND stage_idx=? AND played=0""",
            (career["id"], career["season_year"], comp, st)).fetchall():
        ids.add(r["home_id"]); ids.add(r["away_id"])
    by_id = {i: _club_obj(conn, i) for i in ids}
    if cid in by_id:
        _apply_player_tactics(conn, career, by_id[cid])
    lines, winners = COPA.play_stage(conn, career, comp, st, by_id)
    champ = COPA.champion_id(conn, career, comp)
    out = {"ok": True, "kind": "copa", "comp_name": COPA.COMPS[comp]["name"],
           "stage": COPA.STAGES[st][0], "lines": lines, "champion": None}
    if champ:
        out["champion"] = conn.execute("SELECT name FROM clubs WHERE id=?", (champ,)).fetchone()[0]
        if champ == cid:
            conn.execute("UPDATE career SET money=money+?, reputation=MIN(100,reputation+6), titles=titles+1 WHERE id=?",
                         (COPA.COMPS[comp]["prize"], career["id"]))
            out["won"] = True
    else:
        if any(w == cid for _, w in winners):
            conn.execute("UPDATE career SET money=money+4000000 WHERE id=?", (career["id"],))
            out["advanced"] = True
        elif COPA.player_tie(conn, career, comp, st) is None and cid in ids:
            out["eliminated"] = True
    conn.commit()
    return out


def _web_estadual(conn, career):
    from engine.estadual import run_estadual
    from ui.career import _load_state_clubs, _STATE_NAMES
    cid = career["manager_club_id"]
    state = conn.execute("SELECT state FROM clubs WHERE id=?", (cid,)).fetchone()[0]
    clubs = _load_state_clubs(conn, state)
    my = next((c for c in clubs if c.id == cid), None)
    if my:
        _apply_player_tactics(conn, career, my)
    res = run_estadual(state, clubs, watch_club_id=cid)
    prize = 0
    if res.player_champion:
        prize = 8_000_000
        conn.execute("UPDATE career SET money=money+?, reputation=MIN(100,reputation+4), titles=titles+1 WHERE id=?",
                     (prize, career["id"]))
    elif res.player_stage in ("Final", "Semifinais"):
        prize = 2_500_000
        conn.execute("UPDATE career SET money=money+? WHERE id=?", (prize, career["id"]))
    conn.execute("UPDATE career SET estadual_year=? WHERE id=?", (career["season_year"], career["id"]))
    conn.commit()
    return {"ok": True, "kind": "estadual", "name": _STATE_NAMES.get(state, f"Estadual {state}"),
            "groups": res.group_tables, "log": res.log[-2:],
            "champion": res.champion.name if res.champion else "?",
            "player_stage": res.player_stage, "prize": prize}


def _web_finish_season(conn, career):
    from engine import calendar as CAL
    from engine.finance import apply_season_finances, roll_red_cards
    from engine.manager import season_reputation, set_expectation, sync_player_coach
    from engine.career import advance_season
    cid = career["manager_club_id"]
    league_id = CAL.league_id_of(conn, cid)
    table = CAL.standings(conn, career)
    n = len(table)
    manager_pos = next((i for i, s in enumerate(table, 1) if s.club_id == cid), n)
    champion = table[0]
    won_title = champion.club_id == cid

    conn.execute("""INSERT INTO season_history(career_id, season_year, league_id, champion_id, manager_pos, manager_pts)
        VALUES (?,?,?,?,?,?)""", (career["id"], career["season_year"], league_id, champion.club_id,
        manager_pos, next((s.points for s in table if s.club_id == cid), 0)))
    conn.execute("DELETE FROM league_table WHERE career_id=? AND league_id=?", (career["id"], league_id))
    for pos, s in enumerate(table, 1):
        conn.execute("""INSERT INTO league_table(career_id, season_year, league_id, club_id, pos,
            played, wins, draws, losses, gf, ga, points) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (career["id"], career["season_year"], league_id, s.club_id, pos,
             s.played, s.wins, s.draws, s.losses, s.gf, s.ga, s.points))
    conn.commit()

    roll_red_cards(conn, cid, seed=career["season_year"] * 7 + cid)
    fin = apply_season_finances(conn, career, manager_pos, n, won_title)
    career = get_active_career(conn)
    rep = season_reputation(conn, career, manager_pos, n, won_title, fin)
    career = get_active_career(conn)

    sacked = rep["sacked"]
    rehired = None
    if sacked:
        from engine.coach import offers_for_player, fill_vacancies
        import random
        conn.execute("UPDATE career SET seasons_played=seasons_played+1 WHERE id=?", (career["id"],))
        conn.commit(); career = get_active_career(conn)
        offers = offers_for_player(conn, rep["new_rep"], cid)
        if offers:
            ch = offers[0]
            conn.execute("UPDATE career SET manager_club_id=?, reputation=?, warnings=0 WHERE id=?",
                         (ch["club_id"], min(100, rep["new_rep"] + 8), career["id"]))
            conn.commit(); career = get_active_career(conn)
            from engine.manager import occupy_club
            occupy_club(conn, ch["club_id"]); sync_player_coach(conn, career)
            fill_vacancies(conn, ch["club_id"], random.Random(career["season_year"]))
            set_expectation(conn, career)
            rehired = ch["name"]
        else:
            conn.execute("UPDATE career SET status='sacked' WHERE id=?", (career["id"],))
            conn.commit(); career = get_active_career(conn); sync_player_coach(conn, career)
        report = advance_season(conn, career["season_year"], manager_club_id=cid,
                                training_level=career["training_level"] or 2)
        conn.execute("UPDATE career SET season_year=?, current_round=0 WHERE id=?", (report.year, career["id"]))
        conn.execute("DELETE FROM fixtures WHERE career_id=?", (career["id"],))
        conn.execute("DELETE FROM copa WHERE career_id=?", (career["id"],))
        conn.commit()
        return {"ok": True, "kind": "season_end", "champion": champion.club_name,
                "pos": manager_pos, "won_title": won_title, "fin": fin, "rep": rep,
                "sacked": True, "rehired": rehired}

    conn.execute("UPDATE players SET contract_until=? WHERE club_id=? AND contract_until<=?",
                 (career["season_year"] + 3, cid, career["season_year"]))
    conn.commit()
    report = advance_season(conn, career["season_year"], manager_club_id=cid,
                            training_level=career["training_level"] or 2)
    conn.execute("""UPDATE career SET season_year=?, seasons_played=seasons_played+1,
        titles=titles+?, current_round=0 WHERE id=?""",
        (report.year, 1 if won_title else 0, career["id"]))
    conn.execute("DELETE FROM fixtures WHERE career_id=? AND season_year<?", (career["id"], report.year))
    conn.execute("DELETE FROM copa WHERE career_id=? AND season_year<?", (career["id"], report.year))
    conn.commit()
    career = get_active_career(conn)
    set_expectation(conn, career)
    return {"ok": True, "kind": "season_end", "champion": champion.club_name,
            "pos": manager_pos, "won_title": won_title, "fin": fin, "rep": rep,
            "sacked": False, "newgens": report.newgens_created}


# ─── Saves ─────────────────────────────────────────────────────────────────────

def api_saves():
    import saves as SV
    return SV.list_saves()


def save_load(slug):
    import saves as SV
    return {"ok": SV.load_save(slug)}


def save_delete(slug):
    import saves as SV
    return {"ok": SV.delete_save(slug)}


# ─── Escalação ─────────────────────────────────────────────────────────────────

def api_lineup(c):
    from ui.career import get_saved_xi, _load_squad_players
    from engine.lineup import FORMATIONS, validate_lineup
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    squad = _load_squad_players(c, car["manager_club_id"])
    formation, xi = get_saved_xi(c, car, squad)
    xi_ids = {p.id for p in xi}
    ok, msg = validate_lineup(xi, formation)

    def pj(p, on):
        return {"id": p.id, "name": p.name, "pos": p.position, "ovr": p.overall,
                "age": getattr(p, "age", 0) or 0, "on": on}
    xi_out = [pj(p, True) for p in xi]
    bench = [pj(p, False) for p in squad if p.id not in xi_ids]
    avg = round(sum(p.overall for p in xi) / 11, 1) if len(xi) == 11 else 0
    return {"ok": True, "formation": formation, "formations": list(FORMATIONS.keys()),
            "style": car["tactic_style"] or "equilibrado",
            "xi": xi_out, "bench": bench, "avg": avg, "valid": ok, "msg": msg}


def save_lineup(c, formation, style, xi_ids):
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    ids = ",".join(str(i) for i in xi_ids)
    c.execute("UPDATE career SET formation=?, tactic_style=?, lineup=? WHERE id=?",
              (formation, style, ids, car["id"]))
    c.commit()
    return {"ok": True}


def auto_lineup_ids(c, formation):
    """11 ids auto pra uma formação (usado ao trocar formação na GUI)."""
    from ui.career import _load_squad_players
    from engine.lineup import auto_lineup
    car = get_active_career(c)
    squad = _load_squad_players(c, car["manager_club_id"])
    return [p.id for p in auto_lineup(squad, formation)]


# ─── Estádio & CT ──────────────────────────────────────────────────────────────

def api_stadium(c):
    from engine.finance import base_ticket_price, attendance_fill, stadium_revenue
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    club = c.execute("SELECT name, prestige, capacity, ticket_price FROM clubs WHERE id=?",
                     (car["manager_club_id"],)).fetchone()
    last = c.execute("SELECT manager_pos FROM season_history WHERE career_id=? ORDER BY season_year DESC LIMIT 1",
                     (car["id"],)).fetchone()
    pos = last["manager_pos"] if last and last["manager_pos"] else 10
    n = 20
    base = base_ticket_price(club["prestige"])
    price = club["ticket_price"] or base
    fill = attendance_fill(club["prestige"], pos, n, price)
    rev = stadium_revenue(club["capacity"], club["prestige"], pos, n, price)
    tl = car["training_level"] or 2
    return {"ok": True, "capacity": club["capacity"] or 0, "base": base, "price": price,
            "fill": round(fill * 100), "public": int((club["capacity"] or 0) * fill),
            "revenue": rev, "revenue_fmt": fmt_money(rev),
            "training": tl, "training_cost": tl * 2_500_000,
            "training_cost_fmt": fmt_money(tl * 2_500_000)}


def save_stadium(c, price, training):
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    price = max(5, min(300, int(price)))
    training = max(1, min(5, int(training)))
    c.execute("UPDATE clubs SET ticket_price=? WHERE id=?", (price, car["manager_club_id"]))
    c.execute("UPDATE career SET training_level=? WHERE id=?", (training, car["id"]))
    c.commit()
    return {"ok": True}


# ─── Mercado de transferências ──────────────────────────────────────────────────

def api_market(c, position=None, max_price=None, min_ovr=0):
    from engine.transfer import list_market, asking_and_clause
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    rows = list_market(c, car["manager_club_id"], position=position or None,
                       max_price=max_price, min_ovr=min_ovr, limit=60)
    out = []
    for r in rows:
        asking, clause = asking_and_clause(c, r["id"], car)
        out.append({"id": r["id"], "name": r["name"], "pos": r["position"] or "?",
                    "age": r["age"] or 0, "ovr": r["overall"], "pot": r["potential"],
                    "club": r["club"], "value": r["value"], "value_fmt": fmt_money(r["value"]),
                    "asking": asking, "asking_fmt": fmt_money(asking),
                    "clause": clause, "clause_fmt": fmt_money(clause)})
    return {"ok": True, "players": out, "money": car["money"], "money_fmt": fmt_money(car["money"])}


def api_offer(c, player_id, offer):
    """Faz oferta. Retorna resultado da negociação (accept/clause/counter/reject)."""
    from engine.transfer import asking_and_clause, evaluate_offer
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    asking, clause = asking_and_clause(c, player_id, car)
    result, val = evaluate_offer(int(offer), asking, clause)
    return {"ok": True, "result": result, "value": val, "value_fmt": fmt_money(val),
            "asking": asking, "clause": clause}


def api_buy(c, player_id, price):
    from engine.transfer import buy_player_at
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "sem carreira"}
    ok, msg = buy_player_at(c, car, player_id, int(price))
    return {"ok": ok, "msg": msg}


def api_sell(c, player_id):
    from engine.transfer import sell_player
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "sem carreira"}
    ok, msg = sell_player(c, car, player_id)
    return {"ok": ok, "msg": msg}
