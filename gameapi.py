"""
FUTMANAGER — Camada de jogo (I/O-free).
Funções puras: recebem conn, devolvem dict/list. Sem HTTP, sem terminal.
Reusada por: gui/app.py (Tkinter) e web/server.py (HTTP shim).
"""
from __future__ import annotations
import sqlite3
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from paths import db_path


def conn():
    c = sqlite3.connect(db_path())
    c.row_factory = sqlite3.Row
    _ensure_player_columns(c)
    return c


def _ensure_player_columns(c):
    """Migra colunas novas se o save foi criado antes delas."""
    cols = {r[1] for r in c.execute("PRAGMA table_info(players)").fetchall()}
    if 'star_player' not in cols:
        c.execute("ALTER TABLE players ADD COLUMN star_player INTEGER DEFAULT 0")
    if 'minutes_played' not in cols:
        c.execute("ALTER TABLE players ADD COLUMN minutes_played INTEGER DEFAULT 0")
    if 'fame' not in cols:
        c.execute("ALTER TABLE players ADD COLUMN fame INTEGER DEFAULT 0")
    if 'potential' not in cols:
        c.execute("ALTER TABLE players ADD COLUMN potential INTEGER DEFAULT 0")
    c.commit()


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
    """Formata valores monetários em BRL (Real brasileiro)."""
    v = v or 0
    if abs(v) >= 1_000_000:
        return f"R$ {v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"R$ {v/1_000:.0f}K"
    return f"R$ {v}"


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
    from engine.knowledge import cm_role
    rows = c.execute("""
        SELECT id, name, position, age, overall, potential, value, wage,
               contract_until, loan_from_club, form, fitness,
               pace, technique, strength, finishing, passing, defending, stamina,
               star_player, transfer_listed, loan_listed
        FROM players WHERE club_id=? AND retired=0
        ORDER BY CASE position WHEN 'GK' THEN 1 WHEN 'DF' THEN 2
                               WHEN 'MF' THEN 3 WHEN 'FW' THEN 4 END, overall DESC
    """, (car["manager_club_id"],)).fetchall()
    out = []
    for p in rows:
        role, role_label = cm_role(p["position"], dict(p))
        out.append({
            "id": p["id"], "name": p["name"], "position": p["position"] or "?",
            "role": role, "role_label": role_label,
            "age": p["age"] or 0, "overall": p["overall"], "potential": p["potential"],
            "value": p["value"], "value_fmt": fmt_money(p["value"]),
            "wage_fmt": fmt_money(p["wage"]),
            "contract": p["contract_until"], "loan": p["loan_from_club"] is not None,
            "fitness": p["fitness"] if p["fitness"] is not None else 100,
            "form": round(p["form"] if p["form"] is not None else 1.0, 2),
            "star_player": bool(p["star_player"]) if "star_player" in p.keys() else False,
            "transfer_listed": bool(p["transfer_listed"]) if "transfer_listed" in p.keys() else False,
            "loan_listed": bool(p["loan_listed"]) if "loan_listed" in p.keys() else False,
        })
    return out


def api_player_detail(c, player_id):
    """Perfil completo de 1 jogador — atributos passam pelo masking
    (engine/knowledge): elenco próprio e listados veem tudo, resto vê
    faixa/oculto conforme prestígio do clube do técnico."""
    from engine.knowledge import known_attrs, ATTRS, ATTR_LABELS, cm_role
    from engine.scouting import confirmed_attrs, scout_cost
    car = get_active_career(c)
    p = c.execute("""
        SELECT p.*, cl.name club_name, cl.prestige club_prestige
        FROM players p LEFT JOIN clubs cl ON cl.id = p.club_id
        WHERE p.id=?
    """, (player_id,)).fetchone()
    if not p:
        return None
    is_own = bool(car and p["club_id"] == car["manager_club_id"])
    is_listed = bool(p["transfer_listed"] or p["loan_listed"])
    buyer_prestige = None
    if car:
        row = c.execute("SELECT prestige FROM clubs WHERE id=?", (car["manager_club_id"],)).fetchone()
        buyer_prestige = row["prestige"] if row else None
    raw = {a: p[a] for a in ATTRS}
    role, role_label = cm_role(p["position"], raw)
    confirmed = confirmed_attrs(c, car["id"], player_id) if car else set()
    masked = known_attrs(raw, car["id"] if car else 0, player_id,
                         is_own=is_own, is_listed=is_listed, prestige=buyer_prestige,
                         confirmed=confirmed)
    attrs = [{"key": a, "label": ATTR_LABELS[a], "value": masked[a],
              "known": masked[a] != "?", "confirmed": a in confirmed} for a in ATTRS]
    relations = []
    training = None
    if car and is_own:
        from engine.relationships import notable_relations
        from engine.training_feedback import training_summary
        relations = notable_relations(c, car, player_id)
        training = training_summary(c, car, player_id)
    injury = None
    if car and is_own:
        from engine.injury import active_injury, surgery_offer, _severity_of
        inj = active_injury(c, car["id"], player_id)
        if inj:
            offer = surgery_offer(inj["weeks_left"], _severity_of(inj["kind"]))
            injury = {**inj,
                      "can_surgery": not inj["surgery"],
                      "surgery_cost": offer["cost"], "surgery_cost_fmt": fmt_money(offer["cost"]),
                      "surgery_weeks_after": offer["weeks_after"],
                      "surgery_risk_pct": offer["risk_pct"],
                      "surgery_weeks_saved": offer["weeks_saved"]}
    return {
        "can_scout": bool(car) and not is_own,
        "scout_cost": scout_cost(p["overall"]),
        "scout_cost_fmt": fmt_money(scout_cost(p["overall"])),
        "id": p["id"], "name": p["name"], "position": p["position"] or "?",
        "role": role, "role_label": role_label,
        "age": p["age"] or 0, "nationality": p["nationality"],
        "overall": p["overall"], "potential": p["potential"],
        "club_id": p["club_id"], "club_name": p["club_name"] or "—",
        "value": p["value"], "value_fmt": fmt_money(p["value"]),
        "wage": p["wage"], "wage_fmt": fmt_money(p["wage"]),
        "contract": p["contract_until"],
        "fitness": p["fitness"] if p["fitness"] is not None else 100,
        "form": round(p["form"] if p["form"] is not None else 1.0, 2),
        "transfer_listed": bool(p["transfer_listed"]),
        "loan_listed": bool(p["loan_listed"]),
        "is_own": is_own, "attrs": attrs, "injury": injury, "relations": relations,
        "training": training,
    }


def api_decide_surgery(c, injury_id):
    """Aceita oferta de cirurgia pra lesão ativa — debita custo, recalcula
    prazo (com risco determinístico de complicação)."""
    from engine.injury import decide_surgery
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "Sem carreira ativa."}
    r = decide_surgery(c, car, injury_id)
    if not r.get("ok"):
        return r
    msg = f"🏥 Cirurgia realizada — novo prazo: {r['weeks_after']} semanas. Custo: {fmt_money(r['cost'])}."
    if r["complication"]:
        msg += "\n⚠️ Complicação no pós-operatório — recuperação demorou mais que o previsto."
    return {"ok": True, "msg": msg}


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


def api_scout_player(c, player_id):
    """Manda olheiro investigar — confirma atributos (custa caixa)."""
    from engine.scouting import run_scout
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "Sem carreira ativa."}
    return run_scout(c, car, player_id)


def api_inbox(c):
    """Lista mensagens da inbox (mais recente primeiro) + contagem de não-lidas."""
    from engine.inbox import list_messages, unread_count, KIND_LABELS
    car = get_active_career(c)
    if not car:
        return {"messages": [], "unread": 0}
    msgs = list_messages(c, car["id"])
    for m in msgs:
        m["kind_label"] = KIND_LABELS.get(m["kind"], m["kind"])
    return {"messages": msgs, "unread": unread_count(c, car["id"])}


def api_inbox_mark_read(c, message_id=None):
    from engine.inbox import mark_read
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    mark_read(c, car["id"], message_id)
    return {"ok": True}


def api_player_notes(c, player_id):
    car = get_active_career(c)
    if not car:
        return []
    rows = c.execute(
        "SELECT id, text, tag, created_round FROM player_notes "
        "WHERE career_id=? AND player_id=? ORDER BY id DESC",
        (car["id"], player_id)
    ).fetchall()
    return [dict(r) for r in rows]


def api_add_note(c, player_id, text, tag=None):
    car = get_active_career(c)
    if not car or not text.strip():
        return {"ok": False}
    c.execute("INSERT INTO player_notes (career_id, player_id, text, tag, created_round) "
              "VALUES (?,?,?,?,?)", (car["id"], player_id, text.strip(), tag, car["current_round"] or 0))
    c.commit()
    return {"ok": True}


def api_delete_note(c, note_id):
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    c.execute("DELETE FROM player_notes WHERE id=? AND career_id=?", (note_id, car["id"]))
    c.commit()
    return {"ok": True}


def api_set_transfer_listed(c, player_id, listed: bool):
    """Liga/desliga jogador do próprio elenco na lista de transferências
    (público — passa a ser visto por outros clubes sem masking)."""
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "Sem carreira ativa."}
    p = c.execute("SELECT club_id FROM players WHERE id=?", (player_id,)).fetchone()
    if not p or p["club_id"] != car["manager_club_id"]:
        return {"ok": False, "msg": "Jogador não é do seu elenco."}
    c.execute("UPDATE players SET transfer_listed=? WHERE id=?", (1 if listed else 0, player_id))
    c.commit()
    return {"ok": True, "listed": listed}


def api_set_loan_listed(c, player_id, listed: bool):
    """Liga/desliga jogador do próprio elenco disponível por empréstimo."""
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "Sem carreira ativa."}
    p = c.execute("SELECT club_id FROM players WHERE id=?", (player_id,)).fetchone()
    if not p or p["club_id"] != car["manager_club_id"]:
        return {"ok": False, "msg": "Jogador não é do seu elenco."}
    c.execute("UPDATE players SET loan_listed=? WHERE id=?", (1 if listed else 0, player_id))
    c.commit()
    return {"ok": True, "listed": listed}


def api_set_market_status(c, player_id, status):
    """
    Define disponibilidade do jogador no mercado.
    status: 'none' | 'sale' | 'loan'
    """
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "Sem carreira ativa."}
    p = c.execute("SELECT club_id FROM players WHERE id=?", (player_id,)).fetchone()
    if not p or p["club_id"] != car["manager_club_id"]:
        return {"ok": False, "msg": "Jogador não é do seu elenco."}
    if status == "sale":
        c.execute("UPDATE players SET transfer_listed=1, loan_listed=0 WHERE id=?", (player_id,))
    elif status == "loan":
        c.execute("UPDATE players SET transfer_listed=0, loan_listed=1 WHERE id=?", (player_id,))
    else:
        c.execute("UPDATE players SET transfer_listed=0, loan_listed=0 WHERE id=?", (player_id,))
    c.commit()
    return {"ok": True, "status": status}


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
                "yellows": s.yellows, "reds": s.reds,
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


def api_competitions(c):
    """Lista competições disponíveis pra exibir na Classificação (a partir
    do estado real da carreira — Brasileirão sempre, Estadual se já disputado
    nesta temporada, copas se o clube do gestor está classificado)."""
    car = get_active_career(c)
    if not car:
        return []
    from engine.copa import COMPS, ALL_COMPS, ensure_comp, player_in_comp
    out = [{"key": "brasileirao", "label": "Brasileirão"}]
    if (car["estadual_year"] or 0) == car["season_year"] and car["estadual_data"]:
        out.append({"key": "estadual", "label": "Estadual"})
    for comp in ALL_COMPS:
        ensure_comp(c, car, comp)
        if player_in_comp(c, car, comp):
            out.append({"key": f"copa_{comp}", "label": COMPS[comp]["name"]})
    return out


def api_estadual_table(conn):
    """Classificação dos grupos do estadual jogado nesta temporada."""
    import json
    car = get_active_career(conn)
    if not car:
        return {"rows": [], "groups": {}, "comp": "estadual", "season": 0, "name": "Estadual"}
    if (car["estadual_year"] or 0) == car["season_year"] and car["estadual_data"]:
        d = json.loads(car["estadual_data"])
        return {"groups": d.get("groups", {}), "champion": d.get("champion"),
                "comp": "estadual", "season": car["season_year"], "name": d.get("name", "Estadual")}
    return {"rows": [], "groups": {}, "comp": "estadual", "season": car["season_year"], "name": "Estadual"}


def api_copa_bracket(conn, comp):
    """Chaveamento (mata-mata) da copa — compatível com api_table_by_comp."""
    car = get_active_career(conn)
    if not car:
        return {"rows": [], "comp": f"copa_{comp}", "season": 0, "name": "Copa"}
    from engine.copa import COMPS, STAGES, ensure_comp
    ensure_comp(conn, car, comp)
    cid = car["manager_club_id"]
    rows = conn.execute("""
        SELECT cp.stage_idx, cp.match_idx, cp.home_id, cp.away_id, cp.played,
               cp.home_goals, cp.away_goals, cp.winner_id, h.name home_name, a.name away_name
        FROM copa cp JOIN clubs h ON h.id=cp.home_id JOIN clubs a ON a.id=cp.away_id
        WHERE cp.career_id=? AND cp.season_year=? AND cp.comp=?
        ORDER BY cp.stage_idx, cp.match_idx
    """, (car["id"], car["season_year"], comp)).fetchall()
    stages = []
    for si, (stage_name, _) in enumerate(STAGES):
        matches = [r for r in rows if r["stage_idx"] == si]
        if not matches:
            continue
        out = []
        for r in matches:
            out.append({
                "home": r["home_name"], "away": r["away_name"],
                "home_id": r["home_id"], "away_id": r["away_id"],
                "played": bool(r["played"]),
                "hg": r["home_goals"], "ag": r["away_goals"],
                "score": f"{r['home_goals']}-{r['away_goals']}" if r["played"] else "—",
                "winner": (r["home_name"] if r["winner_id"] == r["home_id"] else r["away_name"]) if r["played"] else None,
                "is_player": cid in (r["home_id"], r["away_id"]),
                "stage_name": stage_name,
            })
        stages.append({"name": stage_name, "matches": out})
    return {"rows": [m for s in stages for m in s["matches"]], "stages": stages,
            "comp": f"copa_{comp}", "season": car["season_year"], "name": COMPS[comp]["name"]}


def create_career(club_id, coach_name):
    from ui.career import _money_for_prestige, get_active_career as _gac
    from engine.manager import create_player_coach, set_expectation
    from engine.lineup import MAX_SQUAD_SIZE
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

    # Ajusta elenco inicial ao limite de 30 (remove os piores excedentes, protege goleiros)
    _trim_squad_to_limit(c, club_id, MAX_SQUAD_SIZE)

    career = _gac(c)
    create_player_coach(c, career, coach_name)
    set_expectation(c, career)
    _assign_stars_on_new_career(c, career)
    c.close()
    return {"ok": True}


def _trim_squad_to_limit(c, club_id, limit):
    total = c.execute("SELECT COUNT(*) FROM players WHERE club_id=? AND retired=0", (club_id,)).fetchone()[0]
    if total <= limit:
        return
    # protege goleiros: mantém os 2 melhores
    keep_gk = {r["id"] for r in c.execute(
        "SELECT id FROM players WHERE club_id=? AND retired=0 AND position='GK' ORDER BY overall DESC LIMIT 2",
        (club_id,)).fetchall()}
    n_remove = total - limit
    # remove os piores excedentes, começando pelos mais velhos de menor overall, nunca goleiros protegidos
    rows = c.execute("""
        SELECT id, position, overall FROM players
        WHERE club_id=? AND retired=0 AND id NOT IN ({}) AND position<>'GK'
        ORDER BY overall ASC, age DESC
        LIMIT ?
    """.format(",".join(str(i) for i in keep_gk) if keep_gk else "0"),
        (club_id, n_remove)).fetchall()
    ids = [r["id"] for r in rows]
    if ids:
        c.execute("DELETE FROM players WHERE id IN ({})".format(",".join("?"*len(ids))), ids)
        c.commit()


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


STAR_EVERY_ROUNDS = 3  # evolução + tick financeiro a cada 3 rodadas


def _maybe_midseason_tick(conn, career, round_played):
    """
    Tick de meia-temporada: evolução periódica + finanças semanais.
    Roda a cada STAR_EVERY_ROUNDS rodadas jogadas.
    """
    from engine.evolution import evolve_players, tick_weekly_finance
    if round_played > 0 and round_played % STAR_EVERY_ROUNDS == 0:
        evolve_players(conn, round_played, career["season_year"])
    tick_weekly_finance(conn, career["manager_club_id"])


def _assign_stars_on_new_career(conn, career):
    """Marca estrelas no elenco do técnico humano quando carreira é criada."""
    from engine.evolution import assign_star_players
    assign_star_players(conn, seed=career["season_year"] * 7 + career["manager_club_id"])



def _player_country_state(conn, club_id):
    state = conn.execute("SELECT state FROM clubs WHERE id=?", (club_id,)).fetchone()[0]
    cr = conn.execute("""SELECT co.code FROM clubs c JOIN leagues l ON l.id=c.league_id
        JOIN countries co ON co.id=l.country_id WHERE c.id=?""", (club_id,)).fetchone()
    return (cr[0] if cr else None), state


def api_next(conn):
    from engine import calendar as CAL, copa as COPA, champions_league as CL
    car = get_active_career(conn)
    if not car:
        return {"kind": "none"}
    cid = car["manager_club_id"]
    country, state = _player_country_state(conn, cid)
    CAL.ensure_fixtures(conn, car)
    cr = car["current_round"] or 0
    nr = CAL.num_rounds(conn, car)

    # Check for Champions League (European manager)
    if country in ("EN", "ES", "IT", "FR", "NL", "PT"):
        CL.ensure_group_stage(conn, car)
        cl_due = CL.due_stage(conn, car, cr) if CL.is_participant(conn, car) else None
        if cl_due:
            st_idx, gid = cl_due
            stage_name = CL.STAGES[st_idx][0] if st_idx < len(CL.STAGES) else "Desconhecido"
            return {"kind": "champions", "stage": st_idx,
                    "label": f"Champions League — {stage_name}"}

    # Check for Copa (South American)
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
                "label": f"Brasileirão Série A — Rodada {cr+1}/{nr} · vs {nm['opp_name']} ({nm['loc']})"}
    return {"kind": "season_end", "label": "Fim de temporada — processar entressafra"}


def api_advance(conn):
    """Botão JOGAR: avança a semana, processando Brasileirão e eventuais copas/champions pendentes."""
    car = get_active_career(conn)
    if not car:
        return {"ok": False}
    out = {"ok": True, "kind": "advance", "results": []}

    # 1) rodada do Brasileirão
    ev = api_next(conn)
    if ev["kind"] == "league":
        out["results"].append(_web_league_round(conn, car))
        car = get_active_career(conn)
    elif ev["kind"] == "season_end":
        return _web_finish_season(conn, car)

    cr = (car["current_round"] or 0)
    country, state = _player_country_state(conn, car["manager_club_id"])

    # 2) copas mata-mata intercaladas
    from engine import copa as COPA
    for comp in COPA.ALL_COMPS:
        COPA.ensure_comp(conn, car, comp)
        if not COPA.player_in_comp(conn, car, comp):
            continue
        st = COPA.pending_stage(conn, car, comp)
        if st is not None and cr - 1 >= COPA.COMPS[comp]["triggers"][st]:
            out["results"].append(_web_copa(conn, car, comp, st))

    # 3) Champions League (fase de grupos / mata-mata)
    from engine import champions_league as CL
    if CL.is_participant(conn, car):
        CL.ensure_group_stage(conn, car)
        due = CL.due_stage(conn, car, cr - 1)
        if due:
            st_idx, _ = due
            out["results"].append(_web_champions(conn, car, st_idx))

    conn.commit()
    return out


def api_play(conn):
    """Alias legado para manter compatibilidade com endpoints antigos."""
    return api_advance(conn)


def _apply_player_tactics(conn, career, club):
    from ui.career import get_saved_xi
    from engine.lineup import style_mults
    from engine.relationships import seed_relationships, unit_cohesion
    _, xi = get_saved_xi(conn, career, club.players)
    club.starting_xi = xi
    club.style_atk, club.style_def = style_mults(career["tactic_style"] or "equilibrado")
    # Squad dynamics — só elenco do técnico humano (custo de I/O em 14k+
    # jogadores de IA não compensa, mesmo corte de injury/scouting).
    seed_relationships(conn, career, club.id)
    club.cohesion = unit_cohesion(conn, career, [p.id for p in xi])


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
            CAL._update_player_condition(conn, by_id[cid])
    conn.execute("UPDATE career SET current_round=?, updated_at=datetime('now') WHERE id=?",
                 (cr + 1, career["id"]))
    conn.commit()
    _maybe_midseason_tick(conn, career, cr + 1)
    fresh = get_active_career(conn)
    _notify_incoming_offers(conn, fresh)
    _notify_media(conn, fresh, your)  # era `career` (stale current_round) — divergia
                                      # do round usado por _notify_incoming_offers/medical (cr+1)
    tab = CAL.standings(conn, career)
    pos = next((i for i, s in enumerate(tab, 1) if s.club_id == cid), None)
    return {"ok": True, "kind": "league", "round": cr + 1, "n": nr, "your": your,
            "pos": pos, "table": [{"pos": i, "name": s.club_name, "pts": s.points,
                                   "j": s.played, "is_player": s.club_id == cid}
                                  for i, s in enumerate(tab[:6], 1)]}


def _count_cards(res):
    """(hy, hr, ay, ar) a partir dos eventos da partida."""
    hy = sum(1 for e in res.events if e.kind == "yellow" and e.team == "H")
    ay = sum(1 for e in res.events if e.kind == "yellow" and e.team == "A")
    hr = sum(1 for e in res.events if e.kind == "red" and e.team == "H")
    ar = sum(1 for e in res.events if e.kind == "red" and e.team == "A")
    return hy, hr, ay, ar


def _serialize_match(h, a, res, player_id):
    from engine.live import abbr, stadium_name
    return {
        "home": h.name, "away": a.name,
        "h_abbr": abbr(h.name), "a_abbr": abbr(a.name),
        "hg": res.home_goals, "ag": res.away_goals,
        "stadium": stadium_name(h),
        "is_player": player_id in (h.id, a.id),
        "events": [{"m": e.minute, "kind": e.kind, "team": e.team, "text": e.text}
                   for e in res.events],
    }


def play_round_live(conn):
    """Joga a rodada da liga ao vivo: gera timeline de TODOS os jogos, grava
    placar+cartões+moral, avança a rodada e devolve os jogos serializados para
    a GUI animar minuto a minuto. (Resultado já é definitivo no banco.)"""
    from engine import calendar as CAL
    from engine.live import build_timeline
    from engine.season import _update_morale
    career = get_active_career(conn)
    if not career:
        return {"ok": False}
    cid = career["manager_club_id"]
    CAL.ensure_fixtures(conn, career)
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
    from engine import injury as INJ
    matches = []
    from engine.stats import record_player_match
    for f in fxs:
        h, a = by_id[f["home_id"]], by_id[f["away_id"]]
        res = build_timeline(h, a)
        hy, hr, ay, ar = _count_cards(res)
        conn.execute("""UPDATE fixtures SET played=1, home_goals=?, away_goals=?,
            home_yellows=?, home_reds=?, away_yellows=?, away_reds=? WHERE id=?""",
            (res.home_goals, res.away_goals, hy, hr, ay, ar, f["id"]))
        _update_morale(h, a, res.home_goals, res.away_goals)
        # estatísticas dos jogadores (todos os titulares + gols/cartões)
        for club, starters, opp_starters, sc_ids in (
            (h, getattr(h, "lineup", h.players[:11]), a.players, res.home_scorer_ids),
            (a, getattr(a, "lineup", a.players[:11]), h.players, res.away_scorer_ids),
        ):
            for p in starters:
                goals = sc_ids.count(p.id)
                yellows = 1 if p.id in res.yellows else 0
                reds = 1 if p.id in res.reds else 0
                record_player_match(conn, career["id"], career["season_year"], "league",
                                    club.id, p.id, goals=goals, yellows=yellows, reds=reds)
        if cid in (h.id, a.id):
            CAL._update_player_condition(conn, by_id[cid])
            # Lesão real só pro elenco do técnico humano (custo/balanço de
            # gerir 14k+ jogadores de IA não compensa o ganho)
            for inj in res.injuries:
                if inj["club_id"] == cid and not INJ.active_injury(conn, career["id"], inj["player_id"]):
                    info = INJ.record_injury(conn, career, inj["player_id"], cid, cr + 1)
                    from engine.inbox import add_message
                    add_message(conn, career["id"], cr + 1, "medical",
                                f"🚑 Lesão — {inj['name']}",
                                f"{inj['name']} sofreu {info['kind'].lower()} durante a partida.\n"
                                f"Previsão de recuperação: {info['weeks']} semanas (gravidade {info['severity']}).\n"
                                f"Condição física caiu {info['fitness_drop']} pontos.",
                                ref_type="player", ref_id=inj["player_id"])
        matches.append(_serialize_match(h, a, res, cid))
    # Recuperação semana a semana — avança 1 rodada = 1 semana
    for rec in INJ.process_recoveries(conn, career):
        from engine.inbox import add_message
        add_message(conn, career["id"], cr + 1, "medical",
                    f"✅ Recuperado — {rec['name']}",
                    f"{rec['name']} concluiu a recuperação e está liberado para retornar aos treinos.",
                    ref_type="player", ref_id=rec["player_id"])
    conn.execute("UPDATE career SET current_round=?, updated_at=datetime('now') WHERE id=?",
                 (cr + 1, career["id"]))
    conn.commit()
    _maybe_midseason_tick(conn, career, cr + 1)
    fresh = get_active_career(conn)
    _notify_incoming_offers(conn, fresh)
    your_match = next((m for m in matches if m["is_player"]), None)
    if your_match:
        _notify_media(conn, fresh, {"home": your_match["home"], "away": your_match["away"],
                                    "hg": your_match["hg"], "ag": your_match["ag"]})
    # ordena: jogo do humano primeiro
    matches.sort(key=lambda m: 0 if m["is_player"] else 1)
    return {"ok": True, "kind": "round_live", "round": cr + 1, "n": nr,
            "matches": matches, "table": _full_table(conn, career, cid)}


def _full_table(conn, career, cid):
    from engine import calendar as CAL
    tab = CAL.standings(conn, career)
    n = len(tab)
    return [{"pos": i, "name": s.club_name, "club_id": s.club_id,
             "played": s.played, "wins": s.wins, "draws": s.draws, "losses": s.losses,
             "gf": s.gf, "ga": s.ga, "gd": s.gd, "points": s.points,
             "yellows": s.yellows, "reds": s.reds,
             "is_player": s.club_id == cid,
             "zone": "cl" if i <= 4 else ("rel" if i > n - 3 else "")}
            for i, s in enumerate(tab, 1)]


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
            conn.execute("UPDATE career SET money=money+220****0000 WHERE id=?", (career["id"],))
            out["advanced"] = True
        elif COPA.player_tie(conn, career, comp, st) is None and cid in ids:
            out["eliminated"] = True
    conn.commit()
    return out


def _save_estadual_data(conn, career, name, res):
    """Persiste grupos/campeão do estadual — sem isso, o resultado só existia
    na tela de resumo do momento em que foi jogado (sumia ao navegar)."""
    import json
    data = {"name": name, "groups": res.group_tables,
            "champion": res.champion.name if res.champion else None,
            "player_stage": res.player_stage}
    conn.execute("UPDATE career SET estadual_data=? WHERE id=?",
                 (json.dumps(data), career["id"]))


def play_estadual_live(conn):
    """Roda o estadual inteiro produzindo as rodadas com timelines (grupos +
    mata-mata) para a GUI animar todos os jogos. Grava prêmio/reputação/ano."""
    from engine.estadual import run_estadual_live
    from ui.career import _load_state_clubs, _STATE_NAMES
    career = get_active_career(conn)
    if not career:
        return {"ok": False}
    cid = career["manager_club_id"]
    state = conn.execute("SELECT state FROM clubs WHERE id=?", (cid,)).fetchone()[0]
    clubs = _load_state_clubs(conn, state)
    my = next((c for c in clubs if c.id == cid), None)
    if my:
        _apply_player_tactics(conn, career, my)
    matchdays, res = run_estadual_live(state, clubs, watch_club_id=cid)
    prize = 0
    if res.player_champion:
        prize = 44_000_000  # €8M × 5.5
        conn.execute("UPDATE career SET money=money+?, reputation=MIN(100,reputation+4), titles=titles+1 WHERE id=?",
                     (prize, career["id"]))
    elif res.player_stage in ("Final", "Semifinais"):
        prize = 13_750_000  # €2.5M × 5.5
        conn.execute("UPDATE career SET money=money+? WHERE id=?", (prize, career["id"]))
    conn.execute("UPDATE career SET estadual_year=? WHERE id=?", (career["season_year"], career["id"]))
    _save_estadual_data(conn, career, _STATE_NAMES.get(state, f"Estadual {state}"), res)
    conn.commit()
    return {"ok": True, "kind": "estadual_live",
            "name": _STATE_NAMES.get(state, f"Estadual {state}"),
            "matchdays": matchdays,
            "groups": res.group_tables,
            "champion": res.champion.name if res.champion else "?",
            "player_stage": res.player_stage, "prize": prize}


def play_copa_live(conn):
    """Joga a fase de copa devida ao vivo (todas as partidas com timeline),
    grava resultados, semeia a próxima fase e devolve as partidas p/ animar."""
    from engine import copa as COPA
    from engine.live import build_timeline, abbr, stadium_name
    from engine.simulation import simulate_penalties
    career = get_active_career(conn)
    if not career:
        return {"ok": False}
    ev = api_next(conn)
    if ev.get("kind") != "copa":
        return {"ok": False, "kind": ev.get("kind")}
    comp, st = ev["comp"], ev["stage"]
    cid = career["manager_club_id"]
    ties = conn.execute("""SELECT id, match_idx, home_id, away_id FROM copa
        WHERE career_id=? AND season_year=? AND comp=? AND stage_idx=? AND played=0
        ORDER BY match_idx""", (career["id"], career["season_year"], comp, st)).fetchall()
    ids = {t["home_id"] for t in ties} | {t["away_id"] for t in ties}
    by_id = {i: _club_obj(conn, i) for i in ids}
    if cid in by_id:
        _apply_player_tactics(conn, career, by_id[cid])

    matches, winners = [], []
    for t in ties:
        h, a = by_id[t["home_id"]], by_id[t["away_id"]]
        lr = build_timeline(h, a)
        m = {"home": h.name, "away": a.name, "h_abbr": abbr(h.name), "a_abbr": abbr(a.name),
             "hg": lr.home_goals, "ag": lr.away_goals, "stadium": stadium_name(h),
             "is_player": cid in (h.id, a.id),
             "events": [{"m": e.minute, "kind": e.kind, "team": e.team, "text": e.text}
                        for e in lr.events]}
        if lr.home_goals == lr.away_goals:
            hp, ap = simulate_penalties(h, a)
            w = h if hp >= ap else a
            m["pens"] = (hp, ap); m["winner"] = w.name
        else:
            w = h if lr.home_goals > lr.away_goals else a
        conn.execute("UPDATE copa SET played=1, home_goals=?, away_goals=?, winner_id=? WHERE id=?",
                     (lr.home_goals, lr.away_goals, w.id, t["id"]))
        winners.append((t["match_idx"], w.id))
        matches.append(m)
    # semeia próxima fase
    if st + 1 < len(COPA.STAGES):
        winners.sort()
        wids = [wid for _, wid in winners]
        for mi in range(len(wids) // 2):
            conn.execute("""INSERT INTO copa(career_id, season_year, comp, stage_idx, match_idx,
                home_id, away_id, played) VALUES (?,?,?,?,?,?,?,0)""",
                (career["id"], career["season_year"], comp, st + 1, mi, wids[mi*2], wids[mi*2+1]))
    conn.commit()

    matches.sort(key=lambda x: 0 if x["is_player"] else 1)
    champ = COPA.champion_id(conn, career, comp)
    out = {"ok": True, "kind": "copa_live", "comp_name": COPA.COMPS[comp]["name"],
           "stage": COPA.STAGES[st][0], "matches": matches, "champion": None}
    if champ:
        out["champion"] = conn.execute("SELECT name FROM clubs WHERE id=?", (champ,)).fetchone()[0]
        if champ == cid:
            conn.execute("UPDATE career SET money=money+?, reputation=MIN(100,reputation+6), titles=titles+1 WHERE id=?",
                         (COPA.COMPS[comp]["prize"], career["id"]))
            out["won"] = True
    else:
        if any(w == cid for _, w in winners):
            conn.execute("UPDATE career SET money=money+220****0000 WHERE id=?", (career["id"],))
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
        prize = 44_000_000  # €8M × 5.5
        conn.execute("UPDATE career SET money=money+?, reputation=MIN(100,reputation+4), titles=titles+1 WHERE id=?",
                     (prize, career["id"]))
    elif res.player_stage in ("Final", "Semifinais"):
        prize = 13_750_000  # €2.5M × 5.5
        conn.execute("UPDATE career SET money=money+? WHERE id=?", (prize, career["id"]))
    conn.execute("UPDATE career SET estadual_year=? WHERE id=?", (career["season_year"], career["id"]))
    _save_estadual_data(conn, career, _STATE_NAMES.get(state, f"Estadual {state}"), res)
    conn.commit()
    return {"ok": True, "kind": "estadual", "name": _STATE_NAMES.get(state, f"Estadual {state}"),
            "groups": res.group_tables, "log": res.log[-2:],
            "champion": res.champion.name if res.champion else "?",
            "player_stage": res.player_stage, "prize": prize}


def api_table_by_comp(conn, comp="league"):
    car = get_active_career(conn)
    cid = car["manager_club_id"] if car else 0
    if comp == "league":
        return {"rows": _full_table(conn, car, cid), "comp": comp,
                "season": car["season_year"] if car else 0,
                "name": "Brasileirão Série A"}
    if comp == "estadual":
        return api_estadual_table(conn)
    if comp.startswith("copa_"):
        return api_copa_bracket(conn, comp.split("_", 1)[1])
    if comp == "champions":
        return api_champions_table(conn)
    return {"rows": [], "comp": comp, "season": car["season_year"] if car else 0, "name": comp}


# ─── Web shim helpers ───────────────────────────────────────────────────────


def _web_champions(conn, career, stage_idx: int):
    """Play Champions League stage (group or KO)."""
    from engine import champions_league as CL
    cid = career["manager_club_id"]

    CL.play_stage(conn, career, stage_idx)

    # Check if manager's club won/advanced
    prize = 0
    player_advanced = False
    if stage_idx == 0:
        # Group stage: check if player in top 2
        groups = conn.execute("""
            SELECT DISTINCT group_id FROM championships
            WHERE career_id=? AND season_year=? AND comp='cl' AND stage_idx=0
        """, (career["id"], career["season_year"])).fetchall()
        for g in groups:
            standings = CL.group_standings(conn, career, g[0])
            if any(s.club_id == cid for s in standings[:2]):
                player_advanced = True
                prize = CL.PRIZE_BY_STAGE["group"]
                break
    else:
        # KO stage: check if player won this round
        won = conn.execute("""
            SELECT COUNT(*) FROM championships
            WHERE career_id=? AND season_year=? AND comp='cl' AND stage_idx=? AND winner_id=?
        """, (career["id"], career["season_year"], stage_idx, cid)).fetchone()[0]
        if won:
            player_advanced = True
            if stage_idx == 3:  # Final winner
                prize = CL.PRIZE_BY_STAGE["final"]
                conn.execute("UPDATE career SET money=money+?, reputation=MIN(100,reputation+6), titles=titles+1 WHERE id=?",
                            (prize, career["id"]))
            else:
                prize = CL.PRIZE_BY_STAGE[["group", "quarters", "semis", "final"][min(stage_idx, 2)]]
                conn.execute("UPDATE career SET money=money+? WHERE id=?", (prize, career["id"]))

    conn.commit()
    return {"ok": True, "kind": "champions", "stage": stage_idx, "stage_name": CL.STAGES[stage_idx][0],
            "player_advanced": player_advanced, "prize": prize}


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

    from engine.career import apply_promotion_relegation
    promo = apply_promotion_relegation(conn, career["season_year"], cid, league_id, table)

    roll_red_cards(conn, cid, seed=career["season_year"] * 7 + cid)
    fin = apply_season_finances(conn, career, manager_pos, n, won_title)
    career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
    rep = season_reputation(conn, career, manager_pos, n, won_title, fin)
    from engine.inbox import add_message
    _board_msg = (f"Posição final: {manager_pos}º de {n} (meta era {rep['expectation']}º).\n"
                  + "\n".join(rep["reasons"])
                  + f"\n\nReputação: {rep['old_rep']} → {rep['new_rep']} ({rep['delta']:+d})")
    if rep["sacked"]:
        _board_title = "🔴 Você foi demitido"
    elif rep["warned"]:
        _board_title = "🟡 Conselho emite advertência"
    else:
        _board_title = f"🏛 Avaliação de fim de temporada — {career['season_year']}"
    add_message(conn, career["id"], career["current_round"] or 0, "board", _board_title, _board_msg,
                ref_type="season", ref_id=career["season_year"])
    # season_reputation pode setar status='sacked' — get_active_career() filtra
    # status='active' e voltaria None aqui, derrubando o resto do fluxo.
    # Refaz pelo id, que não muda independente do status.
    career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()

    sacked = rep["sacked"]
    rehired = None
    if sacked:
        from engine.coach import offers_for_player, fill_vacancies
        import random
        # career["status"] já virou 'sacked' aqui (season_reputation aplicou) —
        # get_active_career() filtra status='active' e retornaria None, derrubando
        # o resto do fluxo. Refaz a busca direto pelo id, que não muda.
        career_id = career["id"]
        conn.execute("UPDATE career SET seasons_played=seasons_played+1 WHERE id=?", (career_id,))
        conn.commit()
        career = conn.execute("SELECT * FROM career WHERE id=?", (career_id,)).fetchone()
        offers = offers_for_player(conn, rep["new_rep"], cid)
        if offers:
            ch = offers[0]
            # Recontratado em outro clube — carreira volta a ficar ativa
            conn.execute("""UPDATE career SET manager_club_id=?, reputation=?, warnings=0,
                            status='active' WHERE id=?""",
                         (ch["club_id"], min(100, rep["new_rep"] + 8), career_id))
            conn.commit()
            career = conn.execute("SELECT * FROM career WHERE id=?", (career_id,)).fetchone()
            from engine.manager import occupy_club
            occupy_club(conn, ch["club_id"]); sync_player_coach(conn, career)
            fill_vacancies(conn, ch["club_id"], random.Random(career["season_year"]))
            set_expectation(conn, career)
            rehired = ch["name"]
        else:
            conn.execute("UPDATE career SET status='sacked' WHERE id=?", (career_id,))
            conn.commit()
            career = conn.execute("SELECT * FROM career WHERE id=?", (career_id,)).fetchone()
            sync_player_coach(conn, career)
        report = advance_season(conn, career["season_year"], manager_club_id=cid,
                                training_level=career["training_level"] or 2,
                                training_focus=career["training_focus"] or "geral")
        conn.execute("UPDATE career SET season_year=?, current_round=0 WHERE id=?", (report.year, career["id"]))
        conn.execute("DELETE FROM fixtures WHERE career_id=?", (career["id"],))
        conn.execute("DELETE FROM copa WHERE career_id=?", (career["id"],))
        conn.commit()
        return {"ok": True, "kind": "season_end", "champion": champion.club_name,
                "pos": manager_pos, "won_title": won_title, "fin": fin, "rep": rep,
                "sacked": True, "rehired": rehired, "promo": promo,
                "ai_transfers": report.ai_transfers}

    # Contratos do clube do jogador vencidos e NÃO renovados (painel "Contratos"
    # — engine.contracts) saem como agentes livres, igual ao fluxo do CLI.
    conn.execute("""UPDATE players SET club_id=NULL
        WHERE club_id=? AND retired=0 AND loan_from_club IS NULL
          AND contract_until IS NOT NULL AND contract_until<=?""",
        (cid, career["season_year"]))
    conn.commit()
    report = advance_season(conn, career["season_year"], manager_club_id=cid,
                            training_level=career["training_level"] or 2,
                                training_focus=career["training_focus"] or "geral")
    _summary = (f"🏆 Campeão: {champion.club_name}" + (" (você!)" if won_title else "") + "\n"
                f"📈 {report.newgens_created} novos jovens chegaram à base.\n"
                f"🔄 {report.ai_transfers} transferências movimentaram o mercado na janela.")
    if promo and promo.get("promoted"):
        _summary += f"\n🔀 Mudança de divisão: agora na {promo['league_name']}."
    add_message(conn, career["id"], 0, "record", f"📜 Temporada {career['season_year']} encerrada", _summary,
                ref_type="season", ref_id=career["season_year"])
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
            "sacked": False, "newgens": report.newgens_created, "promo": promo,
            "ai_transfers": report.ai_transfers}


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
    from engine.lineup import FORMATIONS, validate_lineup, validate_bench, MAX_BENCH_SIZE
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    squad = _load_squad_players(c, car["manager_club_id"])
    formation, xi = get_saved_xi(c, car, squad)
    xi_ids = {p.id for p in xi}
    ok, msg = validate_lineup(xi, formation)
    bench_ok, bench_msg = validate_bench(squad, xi)

    from engine.knowledge import cm_role
    def pj(p, on):
        attrs = {a: getattr(p, a, 50) for a in
                 ("pace", "technique", "strength", "finishing", "passing", "defending", "stamina")}
        role, role_label = cm_role(p.position, attrs)
        return {"id": p.id, "name": p.name, "pos": p.position, "ovr": p.overall,
                "role": role, "role_label": role_label,
                "age": getattr(p, "age", 0) or 0, "on": on,
                "fitness": getattr(p, "fitness", 100), "form": round(getattr(p, "form", 1.0), 2)}
    xi_out = [pj(p, True) for p in xi]
    bench = [pj(p, False) for p in squad if p.id not in xi_ids]
    bench = bench[:MAX_BENCH_SIZE]
    avg = round(sum(p.overall for p in xi) / 11, 1) if len(xi) == 11 else 0
    positions = json.loads(car["lineup_positions"] or "{}")
    return {"ok": True, "formation": formation, "formations": list(FORMATIONS.keys()),
            "style": car["tactic_style"] or "equilibrado",
            "xi": xi_out, "bench": bench, "avg": avg, "valid": ok, "msg": msg,
            "squad_size": len(squad), "max_squad": 30, "max_bench": MAX_BENCH_SIZE,
            "bench_valid": bench_ok, "bench_msg": bench_msg,
            "positions": positions}


def save_lineup(c, formation, style, xi_ids, positions=None):
    from engine.lineup import FORMATIONS, validate_bench, MAX_SQUAD_SIZE, MAX_BENCH_SIZE
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "Sem carreira ativa."}
    # Normaliza para 11 ids únicos
    ids = [int(i) for i in xi_ids if i is not None][:11]
    ids = list(dict.fromkeys(ids))
    if len(ids) != 11:
        return {"ok": False, "msg": f"Escalação precisa de 11 titulares (enviados {len(ids)})."}

    # Verifica se todos os ids pertencem ao elenco do técnico
    cid = car["manager_club_id"]
    rows = c.execute("SELECT id FROM players WHERE club_id=? AND retired=0", (cid,)).fetchall()
    squad_ids = {r["id"] for r in rows}
    invalid = [i for i in ids if i not in squad_ids]
    if invalid:
        return {"ok": False, "msg": f"Jogador(es) {invalid} não estão no elenco."}

    # Verifica limites de elenco
    if len(squad_ids) > MAX_SQUAD_SIZE:
        return {"ok": False, "msg": f"Elenco com {len(squad_ids)} jogadores (máx {MAX_SQUAD_SIZE})."}
    bench_count = len(squad_ids) - len(ids)
    if bench_count > MAX_BENCH_SIZE:
        return {"ok": False, "msg": f"Banco teria {bench_count} reservas (máx {MAX_BENCH_SIZE}). Venda ou empreste jogadores."}

    pos_json = json.dumps(positions or {})
    c.execute("UPDATE career SET formation=?, tactic_style=?, lineup=?, lineup_positions=? WHERE id=?",
              (formation, style, ",".join(str(i) for i in ids), pos_json, car["id"]))
    c.commit()
    return {"ok": True, "msg": "Escalação salva."}


def auto_lineup_ids(c, formation, skip_fatigue_above=None, skip_form_below=None):
    """11 ids auto pra uma formação (usado ao trocar formação na GUI)."""
    from ui.career import _load_squad_players
    from engine.lineup import auto_lineup
    car = get_active_career(c)
    squad = _load_squad_players(c, car["manager_club_id"])
    return [p.id for p in auto_lineup(squad, formation,
                                      skip_fatigue_above=skip_fatigue_above,
                                      skip_form_below=skip_form_below)]


# ─── Estádio & CT ──────────────────────────────────────────────────────────────

def api_stadium(c):
    from engine.finance import base_ticket_price, attendance_fill, stadium_revenue
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    club = c.execute("SELECT name, prestige, capacity, ticket_price, fan_mood FROM clubs WHERE id=?",
                     (car["manager_club_id"],)).fetchone()
    last = c.execute("SELECT manager_pos FROM season_history WHERE career_id=? ORDER BY season_year DESC LIMIT 1",
                     (car["id"],)).fetchone()
    pos = last["manager_pos"] if last and last["manager_pos"] else 10
    n = 20
    fan_mood = club["fan_mood"] if club["fan_mood"] is not None else 50
    base = base_ticket_price(club["prestige"])
    price = club["ticket_price"] or base
    fill = attendance_fill(club["prestige"], pos, n, price, fan_mood)
    rev = stadium_revenue(club["capacity"], club["prestige"], pos, n, price, fan_mood)
    tl = car["training_level"] or 2
    return {"ok": True, "capacity": club["capacity"] or 0, "base": base, "price": price,
            "fill": round(fill * 100), "public": int((club["capacity"] or 0) * fill),
            "fan_mood": fan_mood,
            "revenue": rev, "revenue_fmt": fmt_money(rev),
            "training": tl, "training_cost": tl * 13_750_000,  # €2.5M × 5.5
            "training_cost_fmt": fmt_money(tl * 13_750_000),  # €2.5M × 5.5
            "training_focus": car["training_focus"] or "geral",
            "training_focuses": ["geral", "fisico", "tecnico", "finalizacao"]}


def save_stadium(c, price, training, focus=None):
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    price = max(28, min(1650, int(price)))  # R$5-300 × 5.5 (escala BRL do TICKET_BASE)
    training = max(1, min(5, int(training)))
    c.execute("UPDATE clubs SET ticket_price=? WHERE id=?", (price, car["manager_club_id"]))
    if focus:
        c.execute("UPDATE career SET training_level=?, training_focus=? WHERE id=?",
                  (training, focus, car["id"]))
    else:
        c.execute("UPDATE career SET training_level=? WHERE id=?", (training, car["id"]))
    c.commit()
    return {"ok": True}




# ─── Finanças ─────────────────────────────────────────────────────────────────

def api_finance(c):
    from engine.finance import wage_bill, base_ticket_price, stadium_revenue, attendance_fill
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    cid = car["manager_club_id"]
    club = c.execute("""SELECT capacity, prestige, ticket_price, fan_mood FROM clubs WHERE id=?""", (cid,)).fetchone()
    rows = c.execute("""SELECT season_year, manager_pos
                        FROM season_history
                        WHERE career_id=?
                        ORDER BY season_year DESC""", (car["id"],)).fetchall()
    hist = []
    for r in rows:
        hist.append({
            "season": r["season_year"], "pos": r["manager_pos"] or "—",
        })
    wage = wage_bill(c, cid)
    base = base_ticket_price(club["prestige"])
    price = club["ticket_price"] or base
    fm = club["fan_mood"] if club["fan_mood"] is not None else 50
    fill = attendance_fill(club["prestige"], 10, 20, price, fm)
    rev = stadium_revenue(club["capacity"] or 0, club["prestige"], 10, 20, price, fm)
    return {
        "ok": True,
        "money": car["money"], "money_fmt": fmt_money(car["money"]),
        "wage_bill": wage, "wage_bill_fmt": fmt_money(wage),
        "budget": car["money"], "budget_fmt": fmt_money(car["money"]),
        "ticket": {"price": price, "base": base, "fill": round(fill * 100),
                   "public": int((club["capacity"] or 0) * fill), "revenue": rev,
                   "revenue_fmt": fmt_money(rev)},
        "history": hist,
    }


# ─── Histórico de partidas ────────────────────────────────────────────────────

def api_match_history(c, limit=30):
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    cid = car["manager_club_id"]
    rows = c.execute("""SELECT f.id, f.season_year, f.round_idx, f.home_id, f.away_id,
                               f.home_goals, f.away_goals, f.home_yellows, f.home_reds,
                               f.away_yellows, f.away_reds, f.played,
                               hc.name home, ac.name away
                        FROM fixtures f
                        JOIN clubs hc ON hc.id=f.home_id
                        JOIN clubs ac ON ac.id=f.away_id
                        WHERE f.career_id=? AND f.played=1
                          AND (f.home_id=? OR f.away_id=?)
                        ORDER BY f.season_year DESC, f.round_idx DESC
                        LIMIT ?""", (car["id"], cid, cid, limit)).fetchall()
    out = []
    for r in rows:
        is_home = r["home_id"] == cid
        gf = r["home_goals"] if is_home else r["away_goals"]
        ga = r["away_goals"] if is_home else r["home_goals"]
        res = "V" if gf > ga else ("E" if gf == ga else "D")
        out.append({
            "id": r["id"], "season": r["season_year"], "round": r["round_idx"],
            "home": r["home"], "away": r["away"],
            "hg": r["home_goals"], "ag": r["away_goals"],
            "gf": gf, "ga": ga, "result": res,
            "cards": f"{r['home_yellows']+r['away_yellows']}🟨 {r['home_reds']+r['away_reds']}🟥"
        })
    return {"ok": True, "matches": out}


# ─── Buscar time ──────────────────────────────────────────────────────────────

def api_search_clubs(c, term=""):
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    q = "SELECT id, name, league_id, prestige FROM clubs WHERE name LIKE ? ORDER BY prestige DESC, name LIMIT 40"
    rows = c.execute(q, (f"%{term}%",)).fetchall()
    return {"ok": True, "clubs": [{"id": r["id"], "name": r["name"], "prestige": r["prestige"]} for r in rows]}


def api_club_squad(c, club_id):
    from engine.knowledge import cm_role
    rows = c.execute("""SELECT id, name, position, age, overall, potential, value, wage
                        FROM players
                        WHERE club_id=? AND retired=0
                        ORDER BY overall DESC""", (club_id,)).fetchall()
    out = []
    for r in rows:
        role, role_label = cm_role(r["position"], dict(r))
        out.append({
            "id": r["id"], "name": r["name"], "pos": r["position"] or "?",
            "role": role, "role_label": role_label,
            "age": r["age"] or 0, "ovr": r["overall"], "pot": r["potential"],
            "value": r["value"], "value_fmt": fmt_money(r["value"]),
            "wage": r["wage"], "wage_fmt": fmt_money(r["wage"] or 0),
        })
    club = c.execute("SELECT name, prestige FROM clubs WHERE id=?", (club_id,)).fetchone()
    return {"ok": True, "club": {"name": club["name"], "prestige": club["prestige"]}, "players": out, "count": len(out)}


# ─── Scout ─────────────────────────────────────────────────────────────────────

def api_scout_players(c, min_ovr=60, max_ovr=99, position=None, max_price=None,
                      max_age=40, nationality=None, sort_by="pot", limit=100):
    from engine.knowledge import cm_role
    from engine.transfer import resistance_mult, buy_price
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    cid = car["manager_club_id"]
    prestige = c.execute("SELECT prestige FROM clubs WHERE id=?", (cid,)).fetchone()["prestige"]
    params = [cid, min_ovr, max_ovr, max_age]
    where = "p.retired=0 AND p.club_id<>? AND p.overall>=? AND p.overall<=? AND COALESCE(p.age,18)<=?"
    if position:
        where += " AND p.position=?"
        params.append(position)
    if nationality:
        where += " AND p.nationality=?"
        params.append(nationality)

    order = {"ovr": "p.overall DESC", "pot": "p.potential DESC, p.overall DESC",
             "age": "p.age ASC", "value": "p.value DESC", "asking": "p.value DESC"}.get(sort_by, "p.potential DESC, p.overall DESC")
    rows = c.execute(f"""SELECT p.id, p.name, p.position, p.age, p.overall, p.potential,
                               p.value, p.nationality, c.name club, c.prestige seller_prestige
                        FROM players p JOIN clubs c ON c.id=p.club_id
                        WHERE {where}
                        ORDER BY {order}
                        LIMIT ?""", params + [limit]).fetchall()
    out = []
    for r in rows:
        role, role_label = cm_role(r["position"], dict(r))
        mult = resistance_mult(r["seller_prestige"], prestige, r["overall"], False)
        asking = int(buy_price(r["value"], r["id"], car["id"], car["season_year"]) * mult)
        if max_price is not None and asking > max_price:
            continue
        out.append({
            "id": r["id"], "name": r["name"], "pos": r["position"] or "?",
            "role": role, "role_label": role_label,
            "age": r["age"] or 0, "ovr": r["overall"], "pot": r["potential"],
            "nat": r["nationality"] or "?", "club": r["club"],
            "value": r["value"], "value_fmt": fmt_money(r["value"]),
            "asking": asking, "asking_fmt": fmt_money(asking),
        })
    return {"ok": True, "players": out, "count": len(out)}

# ─── Mercado de transferências ──────────────────────────────────────────────────

def _ensure_market_lists(c):
    """Popula listas de transferência/empréstimo dos clubes IA uma vez por mundo
    (determinístico). Jogadores excedentes ficam à venda; jovens, p/ empréstimo.
    Ignora jogadores do clube humano — senão listar um próprio jogador bloqueia
    a população do mercado de IA."""
    car = get_active_career(c)
    mine = car["manager_club_id"] if car else -1
    has = c.execute("""SELECT 1 FROM players
        WHERE transfer_listed=1 AND club_id<>? LIMIT 1""", (mine,)).fetchone()
    if has:
        return
    c.execute("""UPDATE players SET transfer_listed=1
        WHERE retired=0 AND club_id<>? AND (id % 5)=0""", (mine,))
    c.execute("""UPDATE players SET loan_listed=1
        WHERE retired=0 AND club_id<>? AND (age IS NULL OR age<=23) AND (id % 7)=0""", (mine,))
    c.commit()


def api_nationalities(c):
    rows = c.execute("""SELECT nationality, COUNT(*) n FROM players
        WHERE retired=0 AND nationality IS NOT NULL AND nationality<>'default'
          AND nationality<>'' GROUP BY nationality ORDER BY n DESC""").fetchall()
    return [r["nationality"] for r in rows]


def api_market(c, position=None, max_price=None, min_ovr=0, max_ovr=99,
               min_age=0, max_age=99, nationality=None,
               only_transfer=False, only_loan=False, limit=400):
    from engine.transfer import buy_price, resistance_mult
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    _ensure_market_lists(c)
    buyer_prestige = c.execute("SELECT prestige FROM clubs WHERE id=?",
                               (car["manager_club_id"],)).fetchone()[0]
    q = """SELECT p.id, p.name, p.position, p.age, p.overall, p.potential, p.value,
                  p.release_clause, p.nationality, p.transfer_listed, p.loan_listed,
                  p.pace, p.technique, p.strength, p.finishing, p.passing, p.defending, p.stamina,
                  c.name club, c.prestige seller_prestige
           FROM players p JOIN clubs c ON c.id=p.club_id
           WHERE p.retired=0 AND p.club_id<>? AND p.loan_from_club IS NULL
             AND p.overall BETWEEN ? AND ?"""
    params = [car["manager_club_id"], min_ovr, max_ovr]
    if position:
        q += " AND p.position=?"; params.append(position)
    if max_price:
        q += " AND p.value<=?"; params.append(max_price)
    if min_age:
        q += " AND p.age>=?"; params.append(min_age)
    if max_age < 99:
        q += " AND p.age<=?"; params.append(max_age)
    if nationality:
        q += " AND p.nationality=?"; params.append(nationality)
    if only_transfer:
        q += " AND p.transfer_listed=1"
    if only_loan:
        q += " AND p.loan_listed=1"
    q += " ORDER BY p.overall DESC, p.potential DESC LIMIT ?"
    params.append(limit)
    rows = c.execute(q, params).fetchall()
    from engine.knowledge import cm_role
    out = []
    for r in rows:
        role, role_label = cm_role(r["position"], dict(r))
        # asking_and_clause(conn, id, career) reconsultava value/release_clause
        # já presentes em `r` — N+1 query que deixava o Mercado lento (até 400
        # SELECTs extras por render). Calcula direto a partir da própria linha.
        mult = resistance_mult(r["seller_prestige"], buyer_prestige, r["overall"], r["transfer_listed"])
        asking = int(buy_price(r["value"], r["id"], car["id"], car["season_year"]) * mult)
        clause = int((r["release_clause"] or int((r["value"] or 5_500_000) * 2.2)) * mult)
        flags = []
        if r["transfer_listed"]: flags.append("V")   # à venda
        if r["loan_listed"]: flags.append("E")       # empréstimo
        out.append({"id": r["id"], "name": r["name"], "pos": r["position"] or "?",
                    "role": role, "role_label": role_label,
                    "age": r["age"] or 0, "ovr": r["overall"], "pot": r["potential"],
                    "nat": r["nationality"] or "?", "club": r["club"],
                    "value": r["value"], "value_fmt": fmt_money(r["value"]),
                    "asking": asking, "asking_fmt": fmt_money(asking),
                    "clause": clause, "clause_fmt": fmt_money(clause),
                    "transfer_listed": bool(r["transfer_listed"]),
                    "loan_listed": bool(r["loan_listed"]),
                    "flags": "".join(flags)})
    return {"ok": True, "players": out, "count": len(out),
            "money": car["money"], "money_fmt": fmt_money(car["money"])}


def _notify_media(conn, career, your):
    """Posta na inbox a manchete da rodada — kind='media' (preenche infra
    que já existia ociosa: `inbox.KIND_LABELS["media"]` sem gerador).
    `round_media` é determinístico e auto-limita (0-1 peça/rodada, só
    quando há fato notável — resultado elástico ou sequência)."""
    from engine.media import round_media
    from engine.inbox import add_message
    for piece in round_media(conn, career, your):
        add_message(conn, career["id"], career["current_round"] or 0, "media",
                    piece["title"], piece["body"])


def _notify_incoming_offers(conn, career):
    """Posta na inbox as propostas NOVAS de assédio pelo seu elenco —
    kind='market'. `incoming_offers` é determinístico por (carreira,
    temporada, rodada) mas troca o clube pretendente a cada rodada pro
    mesmo jogador (RNG escolhe novo comprador entre candidatos toda vez)
    — dedup por (jogador, clube) não resolveria, ia "novo" toda rodada.
    Notifica 1x por JOGADOR por temporada ("há interesse em X" — o clube
    específico flutua, o que importa é saber que o mercado quer seu
    atleta). `notified_offers` (mesmo padrão json de `declined_offers`)
    guarda quem já avisou; vira de novo na troca de temporada. Ação
    (aceitar/recusar) continua em Elenco → Propostas recebidas."""
    import json
    from engine.transfer import incoming_offers
    from engine.inbox import add_message
    notified = json.loads(career["notified_offers"] or "[]")
    seen = {pid for pid, _cid, yr in notified if yr == career["season_year"]}
    new_entries = []
    for o in incoming_offers(conn, career):
        if o["player_id"] in seen:
            continue
        add_message(conn, career["id"], career["current_round"] or 0, "market",
                    f"💰 Interesse no mercado — {o['player_name']}",
                    f"{o['club_name']} sinalizou interesse em {o['player_name']} "
                    f"(OVR {o['overall']}), oferta inicial {fmt_money(o['amount'])}.\n"
                    f"Outros clubes podem aparecer enquanto durar o assédio.\n"
                    f"Responda em Elenco → Propostas recebidas.",
                    ref_type="player", ref_id=o["player_id"])
        seen.add(o["player_id"])
        new_entries.append([o["player_id"], o["club_id"], career["season_year"]])
    if new_entries:
        kept = [e for e in notified if e[2] == career["season_year"]] + new_entries
        conn.execute("UPDATE career SET notified_offers=? WHERE id=?",
                     (json.dumps(kept), career["id"]))
        conn.commit()


def api_incoming_offers(c):
    """Propostas de clubes IA pelos seus jogadores (assédio)."""
    from engine.transfer import incoming_offers
    car = get_active_career(c)
    if not car:
        return []
    out = []
    for o in incoming_offers(c, car):
        out.append({**o, "amount_fmt": fmt_money(o["amount"])})
    return out


def api_loan_terms(c, player_id):
    """Dados pra montar a proposta de empréstimo: salário do alvo + cobertura
    mínima exigida pelo clube dono (cresce com o overall)."""
    from engine.transfer import loan_min_coverage
    p = c.execute("SELECT id, name, overall, wage, club_id, loan_from_club FROM players WHERE id=?",
                  (player_id,)).fetchone()
    if not p:
        return {"ok": False, "msg": "Jogador não encontrado."}
    if p["loan_from_club"] is not None:
        return {"ok": False, "msg": "Esse jogador já está emprestado."}
    return {"ok": True, "name": p["name"], "overall": p["overall"],
            "wage": p["wage"] or 0, "wage_fmt": fmt_money(p["wage"] or 0),
            "min_coverage": loan_min_coverage(p["overall"] or 60)}


def api_loan_in(c, player_id, wage_pct, monthly_fee):
    """Propõe empréstimo — você banca wage_pct% do salário do clube dono +
    taxa mensal. Diferente de transferência definitiva: sem taxa de compra,
    sem agente, prazo de 1 temporada (ver engine.transfer.loan_in)."""
    from engine.transfer import loan_in
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "Sem carreira ativa."}
    ok, msg = loan_in(c, car, int(player_id), car["season_year"],
                      wage_pct=int(wage_pct), monthly_fee=int(monthly_fee))
    return {"ok": ok, "msg": msg}


def api_respond_offer(c, player_id, club_id, accept):
    from engine.transfer import respond_incoming_offer
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "sem carreira"}
    ok, msg = respond_incoming_offer(c, car, int(player_id), int(club_id), bool(accept))
    return {"ok": ok, "msg": msg}


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


def api_player_terms(c, player_id, agreed_fee):
    """Etapa 2 da negociação — depois que o clube aceita a taxa, o
    JOGADOR e o AGENTE entram na conversa (CM-style 3 partes)."""
    from engine.transfer import player_wage_demand, agent_fee
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    p = c.execute("SELECT wage, overall, age, club_id FROM players WHERE id=?", (player_id,)).fetchone()
    if not p:
        return {"ok": False}
    seller = c.execute("SELECT prestige FROM clubs WHERE id=?", (p["club_id"],)).fetchone()
    buyer = c.execute("SELECT prestige FROM clubs WHERE id=?", (car["manager_club_id"],)).fetchone()
    agreed_fee = int(agreed_fee)
    wage = player_wage_demand(p["wage"], p["overall"], p["age"],
                              buyer["prestige"] if buyer else 50,
                              seller["prestige"] if seller else 50)
    comm = agent_fee(agreed_fee, p["overall"])
    total = agreed_fee + comm
    return {"ok": True, "wage_demand": wage, "wage_demand_fmt": fmt_money(wage),
            "agent_fee": comm, "agent_fee_fmt": fmt_money(comm),
            "fee_fmt": fmt_money(agreed_fee),
            "total_cost": total, "total_cost_fmt": fmt_money(total),
            "money_fmt": fmt_money(car["money"])}


def api_finalize_transfer(c, player_id, fee, wage):
    """Fecha o negócio nos termos das 3 partes: paga o clube vendedor (taxa),
    acerta salário/contrato com o jogador, paga comissão ao agente."""
    from engine.transfer import agent_fee, buy_player_at
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "sem carreira"}
    p = c.execute("SELECT overall FROM players WHERE id=?", (player_id,)).fetchone()
    if not p:
        return {"ok": False, "msg": "Jogador não encontrado."}
    fee, wage = int(fee), int(wage)
    comm = agent_fee(fee, p["overall"])
    total = fee + comm
    if total > (car["money"] or 0):
        return {"ok": False, "msg": f"Caixa insuficiente — taxa + comissão do agente "
                                    f"soma {fmt_money(total)}, você tem {fmt_money(car['money'])}."}
    ok, msg = buy_player_at(c, car, player_id, fee)
    if not ok:
        return {"ok": False, "msg": msg}
    new_until = car["season_year"] + 4
    c.execute("UPDATE players SET wage=?, contract_until=? WHERE id=?", (wage, new_until, player_id))
    c.execute("UPDATE career SET money = money - ? WHERE id=?", (comm, car["id"]))
    c.commit()
    return {"ok": True, "msg": f"{msg}\n💼 Agente embolsou {fmt_money(comm)} de comissão.\n"
                               f"📝 Salário acertado em {fmt_money(wage)}/ano, contrato até {new_until}."}


def api_sell(c, player_id):
    from engine.transfer import sell_player
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "sem carreira"}
    ok, msg = sell_player(c, car, player_id)
    return {"ok": ok, "msg": msg}


# ─── Contratos & renegociação salarial ──────────────────────────────────────────

def api_contracts(c):
    """Jogadores do elenco com contrato terminando em breve, prontos pra negociar."""
    from engine import contracts as CT
    from engine.finance import wage_bill
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    cid = car["manager_club_id"]
    from engine.knowledge import cm_role
    rows = CT.expiring_players(c, cid, car["season_year"])
    out = []
    for r in rows:
        demand_wage, demand_years = CT._player_demand(c, r["id"], car)
        role, role_label = cm_role(r["position"], dict(r))
        out.append({
            "id": r["id"], "name": r["name"], "pos": r["position"] or "?",
            "role": role, "role_label": role_label,
            "age": r["age"] or 0, "ovr": r["overall"], "pot": r["potential"],
            "wage": r["wage"] or 0, "wage_fmt": fmt_money(r["wage"] or 0),
            "contract_until": r["contract_until"],
            "value_fmt": fmt_money(r["value"]),
            "form": round(r["form"] if r["form"] is not None else 1.0, 2),
            "demand_wage": demand_wage, "demand_wage_fmt": fmt_money(demand_wage),
            "demand_years": demand_years,
        })
    return {"ok": True, "players": out, "count": len(out),
            "money": car["money"], "money_fmt": fmt_money(car["money"]),
            "wage_bill_fmt": fmt_money(wage_bill(c, cid))}


def api_renewal_offer(c, player_id, wage, years):
    """Avalia proposta de renovação (accept/counter/reject)."""
    from engine import contracts as CT
    from engine.finance import wage_bill
    car = get_active_career(c)
    if not car:
        return {"ok": False}
    cid = car["manager_club_id"]
    p = c.execute("SELECT form FROM players WHERE id=?", (player_id,)).fetchone()
    form = p["form"] if p and p["form"] is not None else 1.0
    demand_wage, demand_years = CT._player_demand(c, player_id, car)
    result, val = CT.evaluate_renewal_offer(int(wage), int(years), demand_wage, demand_years,
                                             form, car["money"], wage_bill(c, cid))
    return {"ok": True, "result": result, "wage": val["wage"], "wage_fmt": fmt_money(val["wage"]),
            "years": val["years"], "demand_wage": demand_wage, "demand_wage_fmt": fmt_money(demand_wage),
            "demand_years": demand_years}


def api_renew(c, player_id, wage, years):
    from engine import contracts as CT
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "sem carreira"}
    ok, msg = CT.renew_contract(c, car, player_id, int(wage), int(years))
    return {"ok": ok, "msg": msg}


def api_let_expire(c, player_id):
    from engine import contracts as CT
    car = get_active_career(c)
    if not car:
        return {"ok": False, "msg": "sem carreira"}
    ok, msg = CT.let_expire(c, car, player_id)
    return {"ok": ok, "msg": msg}
