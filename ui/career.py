"""
FUTMANAGER — Career Mode UI
Hub de gestão: novo jogo, continuar, jogar temporada, scout, histórico.
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from paths import db_path


def _conn():
    c = sqlite3.connect(db_path())   # resolve save ativo a cada conexão
    c.row_factory = sqlite3.Row
    return c


def _fmt_money(v: int) -> str:
    """Formata euros: 45000000 → €45.0M"""
    if v >= 1_000_000:
        return f"€{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"€{v/1_000:.0f}K"
    return f"€{v}"


def _header(title: str):
    print(f"\n{'━'*58}")
    print(f"  ⚽  CARREIRA — {title}")
    print(f"{'━'*58}")


# ─── Estado da carreira ──────────────────────────────────────────────────────

def get_active_career(conn):
    return conn.execute(
        "SELECT * FROM career WHERE status='active' ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()


def _money_for_prestige(prestige: int) -> int:
    """Orçamento inicial proporcional ao prestígio do clube."""
    return int((prestige / 100) ** 3 * 150_000_000)


# ─── Novo jogo ───────────────────────────────────────────────────────────────

def new_career(conn):
    _header("NOVO JOGO")

    # Escolhe liga
    leagues = conn.execute("""
        SELECT l.id, l.name, co.code as country, COUNT(c.id) as n
        FROM leagues l
        LEFT JOIN countries co ON co.id=l.country_id
        LEFT JOIN clubs c ON c.league_id=l.id
        WHERE l.level >= 1
        GROUP BY l.id ORDER BY co.code
    """).fetchall()

    print("\n  Ligas:")
    for i, l in enumerate(leagues, 1):
        print(f"  {i:>2}. {l['name']:<28} ({l['country']}) — {l['n']} clubes")

    try:
        li = int(input("\n  Escolha a liga: ").strip()) - 1
        league = leagues[li]
    except (ValueError, IndexError):
        print("  Inválido.")
        return None

    # Escolhe clube
    clubs = conn.execute(
        "SELECT id, name, prestige FROM clubs WHERE league_id=? ORDER BY prestige DESC",
        (league["id"],)
    ).fetchall()
    print(f"\n  Clubes de {league['name']}:")
    for i, c in enumerate(clubs, 1):
        print(f"  {i:>2}. {c['name']:<30} (prestígio {c['prestige']})")

    try:
        ci = int(input("\n  Escolha o clube para gerir: ").strip()) - 1
        club = clubs[ci]
    except (ValueError, IndexError):
        print("  Inválido.")
        return None

    # Temporada base = maior season_year das ligas, ou 2026
    season = conn.execute("SELECT MAX(season) FROM leagues").fetchone()[0]
    try:
        season_year = int(str(season)[:4])
    except (ValueError, TypeError):
        season_year = 2026

    money = _money_for_prestige(club["prestige"])

    # Nome do técnico (você É o técnico do clube)
    coach_name = input("\n  Seu nome de técnico: ").strip() or "Técnico"

    # ── Cria um SAVE novo (cópia do mundo template) e passa a gravar nele ──
    import saves as SV
    club_id, club_name, club_prestige = club["id"], club["name"], club["prestige"]
    SV.new_save(f"{coach_name} - {club_name}")
    conn.close()
    conn = _conn()   # agora aponta para o save recém-criado

    conn.execute("UPDATE career SET status='archived' WHERE status='active'")
    conn.execute("""
        INSERT INTO career(manager_club_id, season_year, money, reputation)
        VALUES (?, ?, ?, ?)
    """, (club_id, season_year, money, club_prestige))
    conn.commit()

    career = get_active_career(conn)

    from engine.manager import set_expectation, create_player_coach
    create_player_coach(conn, career, coach_name)   # ocupa o clube como técnico
    exp = set_expectation(conn, career)

    print(f"\n  ✅ Carreira iniciada! (save criado)")
    print(f"     Técnico: {coach_name}")
    print(f"     Clube: {club_name}")
    print(f"     Temporada: {season_year}")
    print(f"     Orçamento: {_fmt_money(money)}")
    print(f"     Reputação: {club_prestige}/100")
    print(f"     🎯 Meta do conselho: terminar em {exp}º ou melhor")
    out = get_active_career(conn)
    conn.close()
    return out


# ─── Ver elenco ──────────────────────────────────────────────────────────────

def view_squad(conn, career):
    club = conn.execute("SELECT * FROM clubs WHERE id=?", (career["manager_club_id"],)).fetchone()
    _header(f"ELENCO — {club['name']}")

    players = conn.execute("""
        SELECT name, position, age, overall, potential, value, wage,
               contract_until, loan_from_club
        FROM players
        WHERE club_id=? AND retired=0
        ORDER BY CASE position WHEN 'GK' THEN 1 WHEN 'DF' THEN 2
                               WHEN 'MF' THEN 3 WHEN 'FW' THEN 4 END,
                 overall DESC
    """, (career["manager_club_id"],)).fetchall()

    print(f"\n  {'Nome':<22}{'Pos':<4}{'Id':>3}{'OVR':>4}{'POT':>4}{'Salário':>9}{'Contr':>6}")
    print(f"  {'─'*56}")
    for p in players:
        pot_str = f"{p['potential']}" if p['potential'] and p['potential'] > p['overall'] else "—"
        star = " ⭐" if p['potential'] and p['potential'] - p['overall'] >= 8 and (p['age'] or 99) <= 21 else ""
        loan = " 🔁" if p['loan_from_club'] is not None else ""
        ctr = str(p['contract_until']) if p['contract_until'] else "—"
        print(f"  {p['name'][:21]:<22}{p['position'] or '?':<4}{p['age'] or 0:>3}"
              f"{p['overall']:>4}{pot_str:>4}{_fmt_money(p['wage'] or 0):>9}{ctr:>6}{star}{loan}")

    from engine.finance import wage_bill
    avg = sum(p['overall'] for p in players) / max(len(players), 1)
    wb = wage_bill(conn, career["manager_club_id"])
    print(f"  {'─'*56}")
    print(f"  {len(players)} jogadores · OVR médio {avg:.1f} · folha {_fmt_money(wb)}/ano")
    print(f"  ⭐ promessa   🔁 emprestado")


# ─── Renovação de contratos ──────────────────────────────────────────────────

def _handle_contract_renewals(conn, career):
    """Mostra contratos do seu clube vencendo nesta temporada; oferece renovar."""
    year = career["season_year"]
    expiring = conn.execute("""
        SELECT id, name, position, age, overall, wage, contract_until
        FROM players
        WHERE club_id=? AND retired=0 AND loan_from_club IS NULL
          AND contract_until IS NOT NULL AND contract_until <= ?
        ORDER BY overall DESC
    """, (career["manager_club_id"], year)).fetchall()

    if not expiring:
        return

    print(f"\n  {'─'*54}")
    print(f"  📝 CONTRATOS VENCENDO ({len(expiring)})")
    for p in expiring:
        renew_wage = int((p["wage"] or 100_000) * 1.10)  # +10% para renovar
        print(f"\n     {p['name']} ({p['position']}, {p['age']}a, OVR {p['overall']})")
        print(f"     Salário atual {_fmt_money(p['wage'])} → renovar a {_fmt_money(renew_wage)}/ano (3 anos)")
        ans = input("     Renovar? [s/N]: ").strip().lower()
        if ans == "s":
            conn.execute(
                "UPDATE players SET contract_until=?, wage=? WHERE id=?",
                (year + 3, renew_wage, p["id"])
            )
            print(f"     ✅ Renovado até {year+3}")
        else:
            # Sai livre (vira agente livre)
            conn.execute(
                "UPDATE players SET club_id=NULL WHERE id=?", (p["id"],)
            )
            print(f"     👋 {p['name']} deixou o clube (livre)")
    conn.commit()


# ─── Mercado de técnicos ─────────────────────────────────────────────────────

def _run_coach_market(conn, career, player_league_id, player_table):
    """Avalia técnicos IA do mundo, demite fracos, preenche vagas. Mostra carrossel."""
    import random
    from engine.coach import (quick_league_table, evaluate_ai_coaches,
                              fill_vacancies)
    rng = random.Random(career["season_year"] * 13 + 1)

    club_id = career["manager_club_id"]

    # Colocações de todas as ligas
    finishes = {}
    # Liga do jogador: usa a tabela real
    n = len(player_table)
    for i, s in enumerate(player_table, 1):
        finishes[s.club_id] = (i, n)
    # Demais ligas: tabela rápida por força
    other_leagues = conn.execute(
        "SELECT id FROM leagues WHERE id != ?", (player_league_id,)
    ).fetchall()
    for (lid,) in other_leagues:
        order = quick_league_table(conn, lid, rng)
        nn = len(order)
        for pos, cid in enumerate(order, 1):
            finishes[cid] = (pos, nn)

    sacked = evaluate_ai_coaches(conn, club_id, finishes)
    hires = fill_vacancies(conn, club_id, rng)

    if sacked or hires:
        print(f"\n  {'─'*54}")
        print(f"  🔄 CARROSSEL DE TÉCNICOS")
        for s in sacked[:5]:
            cn = conn.execute("SELECT name FROM clubs WHERE id=?", (s["club_id"],)).fetchone()
            print(f"     🚪 {s['name']} demitido ({cn[0] if cn else '?'})")
        for h in hires[:5]:
            print(f"     ✍️  {h['coach']} assume o {h['club']} (rep {h['rep']})")
        extra = max(0, len(hires) - 5)
        if extra:
            print(f"     … +{extra} mudanças no mundo")


def _handle_player_sacked(conn, career, new_rep):
    """Técnico demitido: ofertas de outros clubes ou fim de carreira."""
    from engine.coach import offers_for_player, fill_vacancies
    from engine.manager import sync_player_coach, set_expectation, occupy_club
    import random
    old_club = career["manager_club_id"]
    rng = random.Random(career["season_year"])

    print(f"\n  {'═'*54}")
    print(f"  🚪 VOCÊ FOI DEMITIDO! (reputação {new_rep}/100)")
    print(f"  {'═'*54}")

    offers = offers_for_player(conn, new_rep, old_club)
    if not offers:
        print(f"\n  Nenhum clube interessado. Fim da linha — carreira encerrada.")
        conn.execute("UPDATE career SET status='sacked' WHERE id=?", (career["id"],))
        conn.commit()
        career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
        sync_player_coach(conn, career)   # técnico humano fica livre/aposenta
        fill_vacancies(conn, -1, rng)     # clube antigo arruma técnico IA
        return

    print(f"\n  📨 Propostas de outros clubes (você seria um upgrade):")
    for i, o in enumerate(offers, 1):
        print(f"  {i:>2}. {o['name']:<28} (prestígio {o['prestige']}, técnico atual rep {o['coach_rep']})")
    print(f"   0. Recusar tudo (encerrar carreira)")

    sel = input("\n  Aceitar qual? ").strip()
    try:
        idx = int(sel)
    except ValueError:
        idx = 0
    if idx <= 0 or idx > len(offers):
        print(f"\n  Você se aposenta da profissão. Carreira encerrada.")
        conn.execute("UPDATE career SET status='sacked' WHERE id=?", (career["id"],))
        conn.commit()
        career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
        sync_player_coach(conn, career)
        fill_vacancies(conn, -1, rng)
        return

    chosen = offers[idx - 1]
    recover = min(100, new_rep + 8)
    conn.execute("""
        UPDATE career SET manager_club_id=?, reputation=?, warnings=0 WHERE id=?
    """, (chosen["club_id"], recover, career["id"]))
    conn.commit()
    career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
    occupy_club(conn, chosen["club_id"])    # demite técnico IA do novo clube
    sync_player_coach(conn, career)         # humano assume o novo clube
    fill_vacancies(conn, chosen["club_id"], rng)  # reacomoda mercado (clube antigo etc.)
    exp = set_expectation(conn, career)
    print(f"\n  🤝 Você é o novo técnico do {chosen['name']}!")
    print(f"     Reputação {recover}/100  ·  Meta do conselho: {exp}º")


# ─── Assistir temporada rodada a rodada ──────────────────────────────────────

def _watch_season(league, club_id):
    """Joga rodada a rodada; transmite a RODADA inteira ao vivo (vários jogos)."""
    from engine.live import matchday_timeline, narrate_matchday

    sched = league.player_round_index(club_id)
    n_rounds = len(league.rounds)
    skip_all = False

    for ri in range(n_rounds):
        info = sched.get(ri)
        opp_txt = ""
        if info:
            loc, opp = info
            opp_txt = f"  ·  você: vs {opp.name} ({loc})"

        if not skip_all:
            print(f"\n  ══ Rodada {ri+1}/{n_rounds}{opp_txt} ══")
            ans = input("     [Enter] assistir rodada   ·   [p] só placares   ·   [s] simular resto: ").strip().lower()
            if ans == "s":
                skip_all = True

        if skip_all:
            league.simulate_round(ri)
            continue

        # Prebuild timelines de todos os jogos da rodada
        pairs = league.rounds[ri]
        items = matchday_timeline(pairs)
        spm = 0.0 if ans == "p" else 1.0
        results = narrate_matchday(items, club_id, spm=spm)
        league.simulate_round(ri, on_round=True, on_round_results=results)
        if ans != "p":
            input("\n     [Enter] próxima rodada...")


# ─── Copas (mata-mata) ───────────────────────────────────────────────────────

def _build_club(conn, r):
    from db.models import Club
    c = Club(id=r["id"], name=r["name"], short_name=r["name"][:12],
             league_id=r["league_id"], prestige=r["prestige"])
    c.players = _load_squad_players(conn, r["id"])
    return c


def _load_top_world_clubs(conn, n=16):
    rows = conn.execute(
        "SELECT * FROM clubs ORDER BY prestige DESC, id LIMIT ?", (n,)
    ).fetchall()
    return [_build_club(conn, r) for r in rows]


def _run_cups(conn, career, league_clubs, table, club_id, watch) -> int:
    """Roda Copa Nacional + Continental. Aplica prêmio/título/reputação. Retorna nº de títulos."""
    from engine.cup import run_cup
    titles = 0

    # Copa Nacional: clubes da liga, ordem = classificação final
    order_ids = [s.club_id for s in table]
    by_id = {c.id: c for c in league_clubs}
    nat_clubs = [by_id[i] for i in order_ids if i in by_id]
    if len(nat_clubs) >= 8:
        nat = run_cup("Copa Nacional", nat_clubs, watch_club_id=club_id)
        print(f"\n  {'─'*54}")
        for line in nat.log[-2:]:   # mostra semifinal + final
            print(line)
        print(f"  🏆 {nat.name}: {nat.champion.name}   ·   você: {nat.player_stage}")
        money, rep, t = _cup_reward(conn, career, nat, base=20_000_000)
        titles += t

    # Copa Continental: 16 melhores do mundo
    world = _load_top_world_clubs(conn, 16)
    if any(c.id == club_id for c in world):
        # garante que o clube do jogador (objeto com escalação/moral) seja usado
        world = [by_id.get(c.id, c) for c in world]
    cont = run_cup("Copa Continental", world, watch_club_id=club_id)
    print(f"\n  {'─'*54}")
    for line in cont.log[-2:]:
        print(line)
    print(f"  🌎 {cont.name}: {cont.champion.name}   ·   você: {cont.player_stage}")
    money, rep, t = _cup_reward(conn, career, cont, base=40_000_000)
    titles += t

    return titles


def _cup_reward(conn, career, cup, base):
    """Prêmio em € + reputação por campanha na copa."""
    money = 0
    rep = 0
    if cup.player_champion:
        money = base
        rep = 6
    elif cup.player_stage in ("Final", "Semifinal"):
        money = base // 3
        rep = 2
    if money or rep:
        conn.execute("UPDATE career SET money=money+?, reputation=MIN(100,reputation+?) WHERE id=?",
                     (money, rep, career["id"]))
        conn.commit()
        if money:
            print(f"     💰 Premiação: +{_fmt_money(money)}" + (f"  ·  reputação +{rep}" if rep else ""))
    return money, rep, (1 if cup.player_champion else 0)


# ─── Jogar temporada ─────────────────────────────────────────────────────────

def play_season(conn, career):
    from db.models import Club, Player
    from engine.season import League
    from engine.career import advance_season

    club_id = career["manager_club_id"]
    league_id = conn.execute("SELECT league_id FROM clubs WHERE id=?", (club_id,)).fetchone()[0]
    league_row = conn.execute("SELECT * FROM leagues WHERE id=?", (league_id,)).fetchone()

    _header(f"TEMPORADA {career['season_year']} — {league_row['name']}")
    watch = input("\n  Assistir suas partidas ao vivo? [s/N]: ").strip().lower() == "s"
    print("\n  Preparando temporada...")

    # Carrega clubes da liga com elencos
    clubs_rows = conn.execute("SELECT * FROM clubs WHERE league_id=?", (league_id,)).fetchall()
    clubs = []
    for r in clubs_rows:
        prows = conn.execute(
            "SELECT * FROM players WHERE club_id=? AND retired=0 ORDER BY overall DESC LIMIT 23",
            (r["id"],)
        ).fetchall()
        players = [Player(
            id=p["id"], name=p["name"], position=p["position"] or "MF",
            nationality=p["nationality"] or "", birth_date=p["birth_date"],
            club_id=p["club_id"], pace=p["pace"], technique=p["technique"],
            strength=p["strength"], finishing=p["finishing"], passing=p["passing"],
            defending=p["defending"], goalkeeping=p["goalkeeping"],
            stamina=p["stamina"], mental=p["mental"], overall=p["overall"],
            source=p["source"] or "",
        ) for p in prows]
        c = Club(id=r["id"], name=r["name"], short_name=r["name"][:12],
                 league_id=r["league_id"], prestige=r["prestige"])
        c.players = players
        clubs.append(c)

    if len(clubs) < 2:
        print("  Liga com poucos clubes.")
        return

    # Aplica escalação + estilo tático ao clube do jogador
    my_club = next((c for c in clubs if c.id == club_id), None)
    if my_club:
        _, xi = get_saved_xi(conn, career, my_club.players)
        my_club.starting_xi = xi
        from engine.lineup import style_mults
        my_club.style_atk, my_club.style_def = style_mults(career["tactic_style"] or "equilibrado")

    league = League(league_row["name"], clubs, str(career["season_year"]))

    if watch:
        _watch_season(league, club_id)
    else:
        league.simulate_all()
    table = league.get_table()
    _finish_season(conn, career, table, clubs)


def _finish_season(conn, career, table, clubs):
    """Processa o fim da temporada: tabela, copas, finanças, reputação, entressafra."""
    club_id = career["manager_club_id"]
    league_id = conn.execute("SELECT league_id FROM clubs WHERE id=?", (club_id,)).fetchone()[0]
    watch = False
    from engine.career import advance_season

    # Mostra tabela destacando o clube do manager
    print(f"\n  {'#':>2}  {'Clube':<26}{'J':>3}{'V':>3}{'E':>3}{'D':>3}{'SG':>5}{'Pts':>5}")
    print(f"  {'─'*54}")
    manager_pos = None
    for i, s in enumerate(table, 1):
        mark = " ◀ VOCÊ" if s.club_id == club_id else ""
        if s.club_id == club_id:
            manager_pos = i
        print(f"  {i:>2}. {s.club_name[:25]:<26}{s.played:>3}{s.wins:>3}"
              f"{s.draws:>3}{s.losses:>3}{s.gd:>+5}{s.points:>5}{mark}")

    champion = table[0]
    print(f"\n  🏆 Campeão: {champion.club_name}")
    won_title = (champion.club_id == club_id)
    if won_title:
        print(f"  🎉 PARABÉNS! Você foi CAMPEÃO!")
    else:
        print(f"  Sua posição: {manager_pos}º lugar")

    # (Copa do Brasil agora é intercalada no calendário, não no fim da temporada)
    cup_titles = 0

    # Registra histórico
    manager_pts = next((s.points for s in table if s.club_id == club_id), 0)
    conn.execute("""
        INSERT INTO season_history(career_id, season_year, league_id, champion_id, manager_pos, manager_pts)
        VALUES (?,?,?,?,?,?)
    """, (career["id"], career["season_year"], league_id, champion.club_id,
          manager_pos, manager_pts))

    # Persiste classificação completa (tela de tabela)
    conn.execute("DELETE FROM league_table WHERE career_id=? AND league_id=?",
                 (career["id"], league_id))
    for pos, s in enumerate(table, 1):
        conn.execute("""
            INSERT INTO league_table(career_id, season_year, league_id, club_id, pos,
                played, wins, draws, losses, gf, ga, points)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (career["id"], career["season_year"], league_id, s.club_id, pos,
              s.played, s.wins, s.draws, s.losses, s.gf, s.ga, s.points))
    conn.commit()

    # ── Disciplina: gera expulsões da temporada ──
    from engine.finance import apply_season_finances, roll_red_cards
    roll_red_cards(conn, club_id, seed=career["season_year"] * 7 + club_id)

    # ── Balanço financeiro da temporada ──
    fin = apply_season_finances(conn, career, manager_pos, len(table), won_title)
    career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
    print(f"\n  {'─'*54}")
    print(f"  💰 BALANÇO FINANCEIRO {career['season_year']}")
    print(f"     Patrocínio/TV:  + {_fmt_money(fin['sponsor'])}")
    print(f"     Bilheteria:     + {_fmt_money(fin['gate'])}")
    print(f"     Premiação:      + {_fmt_money(fin['prize'])}")
    if fin['title']:
        print(f"     Bônus título:   + {_fmt_money(fin['title'])}")
    print(f"     Folha salarial: − {_fmt_money(fin['wages'])}")
    print(f"     Treino (CT):    − {_fmt_money(fin['training_cost'])}")
    if fin['loan_fees']:
        print(f"     Taxas emprést.: − {_fmt_money(fin['loan_fees'])}")
    if fin['fines']:
        print(f"     Multas expulsão:− {_fmt_money(fin['fines'])}")
    print(f"     {'─'*30}")
    sinal = "+" if fin['net'] >= 0 else "−"
    print(f"     Saldo:          {sinal} {_fmt_money(abs(fin['net']))}")
    print(f"     Caixa: {_fmt_money(fin['money_before'])} → {_fmt_money(fin['money_after'])}")
    if fin['offenders']:
        tops = ", ".join(f"{o['name']} ({o['reds']}🟥)" for o in fin['offenders'][:4])
        print(f"     Expulsos: {tops}")
    if fin['bankrupt']:
        print(f"\n  ⚠️  CAIXA NEGATIVO! Venda jogadores para equilibrar a folha.")

    # ── Reputação do gestor / job security ──
    from engine.manager import season_reputation, set_expectation
    rep = season_reputation(conn, career, manager_pos, len(table), won_title, fin)
    career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
    print(f"\n  {'─'*54}")
    print(f"  👔 AVALIAÇÃO DO CONSELHO (meta: {rep['expectation']}º lugar)")
    for r in rep["reasons"]:
        print(f"     {r}")
    arrow = "↑" if rep["delta"] > 0 else ("↓" if rep["delta"] < 0 else "→")
    print(f"     Reputação: {rep['old_rep']} {arrow} {rep['new_rep']}")

    if not rep["sacked"] and rep["warned"]:
        print(f"\n  ⚠️  ADVERTÊNCIA DO CONSELHO! Melhore ou será demitido "
              f"(advertências: {rep['warnings']}/2).")

    # ── Mercado de técnicos (mundo inteiro) ──
    _run_coach_market(conn, career, league_id, table)

    # ── Gestor demitido: recebe ofertas, pode continuar em outro clube ──
    if rep["sacked"]:
        conn.execute("UPDATE career SET seasons_played = seasons_played + 1 WHERE id=?",
                     (career["id"],))
        conn.commit()
        career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
        _handle_player_sacked(conn, career, rep["new_rep"])
        return  # nova temporada começa no novo clube OU carreira encerrada

    # ── Renovação de contratos vencendo (seu clube) ──
    _handle_contract_renewals(conn, career)

    # ── Avança o mundo (age, retire, newgens) ──
    print(f"\n  {'─'*54}")
    print("  Processando entressafra (aposentadorias, base, evolução)...")
    report = advance_season(conn, career["season_year"], manager_club_id=club_id,
                            training_level=career["training_level"] or 2)

    # Atualiza carreira
    conn.execute("""
        UPDATE career SET
            season_year = ?,
            seasons_played = seasons_played + 1,
            titles = titles + ?,
            updated_at = datetime('now')
        WHERE id = ?
    """, (report.year, (1 if won_title else 0) + cup_titles, career["id"]))
    conn.commit()
    # Nova meta do conselho para a próxima temporada
    career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
    set_expectation(conn, career)

    # Relatório de entressafra
    print(f"\n  📋 ENTRESSAFRA → temporada {report.year}")
    print(f"     {report.newgens_created} jovens promovidos da base (mundo)")

    # Aposentados do próprio clube
    my_retired = [r for r in report.retired_notable if r.get("club_id") == club_id]
    if my_retired:
        print(f"\n  👋 Aposentadorias no seu clube:")
        for r in my_retired:
            print(f"     {r['name']} ({r['age']}a, OVR {r['overall']})")

    # Newgens do próprio clube
    my_newgens = conn.execute("""
        SELECT name, position, age, overall, potential
        FROM players
        WHERE club_id=? AND is_newgen=1 AND age <= 18
        ORDER BY potential DESC LIMIT 5
    """, (club_id,)).fetchall()
    if my_newgens:
        print(f"\n  🌱 Novos da sua base:")
        for n in my_newgens:
            star = " ⭐" if n['potential'] >= 78 else ""
            print(f"     {n['name'][:24]:<24} {n['position']} {n['age']}a  OVR {n['overall']} POT {n['potential']}{star}")


# ─── Estadual (formato Paulistão, início de temporada) ───────────────────────

def _load_state_clubs(conn, state):
    from db.models import Club, Player
    rows = conn.execute("SELECT * FROM clubs WHERE state=? ORDER BY prestige DESC LIMIT 16", (state,)).fetchall()
    clubs = []
    for r in rows:
        prows = conn.execute(
            "SELECT * FROM players WHERE club_id=? AND retired=0 ORDER BY overall DESC LIMIT 18",
            (r["id"],)).fetchall()
        players = [Player(id=p["id"], name=p["name"], position=p["position"] or "MF",
            nationality=p["nationality"] or "", birth_date=p["birth_date"], club_id=p["club_id"],
            pace=p["pace"], technique=p["technique"], strength=p["strength"], finishing=p["finishing"],
            passing=p["passing"], defending=p["defending"], goalkeeping=p["goalkeeping"],
            stamina=p["stamina"], mental=p["mental"], overall=p["overall"], source=p["source"] or "")
            for p in prows]
        c = Club(id=r["id"], name=r["name"], short_name=r["name"][:12],
                 league_id=r["league_id"] or 0, prestige=r["prestige"])
        c.players = players
        clubs.append(c)
    return clubs


_STATE_NAMES = {"SP": "Paulistão", "RJ": "Campeonato Carioca", "MG": "Campeonato Mineiro",
                "RS": "Campeonato Gaúcho", "PR": "Campeonato Paranaense", "BA": "Campeonato Baiano",
                "PE": "Campeonato Pernambucano", "CE": "Campeonato Cearense", "GO": "Campeonato Goiano",
                "SC": "Campeonato Catarinense", "PA": "Campeonato Paraense"}


def _run_estadual_ui(conn, career, state):
    from engine.estadual import run_estadual
    club_id = career["manager_club_id"]
    name = _STATE_NAMES.get(state, f"Estadual {state}")
    clubs = _load_state_clubs(conn, state)
    # aplica escalação/estilo ao clube do jogador
    my = next((c for c in clubs if c.id == club_id), None)
    if my:
        _, xi = get_saved_xi(conn, career, my.players); my.starting_xi = xi
        from engine.lineup import style_mults
        my.style_atk, my.style_def = style_mults(career["tactic_style"] or "equilibrado")

    _header(f"{name.upper()} {career['season_year']}")
    if len(clubs) < 8:
        print(f"\n  {state}: poucos clubes para o estadual."); input("\n  Enter..."); return
    print(f"\n  Formato Paulistão: {min(len(clubs),16)} clubes · 4 grupos · mata-mata")

    res = run_estadual(state, clubs, watch_club_id=club_id)

    # Grupos
    def _short(nm):
        toks = [t for t in nm.split() if t.upper() not in ("FC","EC","SC","AC","AA","CR","SE","AD","SER","GE")]
        return (" ".join(toks) or nm)[:11]
    for g, rows in res.group_tables.items():
        line = "  ".join(f"{_short(r['name'])}{'◀' if r['is_player'] else ''}({r['pts']})" for r in rows)
        print(f"   Grupo {g}: {line}")
    # Mata-mata (últimas fases)
    print()
    for blk in res.log[-2:]:
        print(blk)
    champ = res.champion.name if res.champion else "?"
    print(f"\n  🏆 Campeão {state}: {champ}   ·   você: {res.player_stage}")

    # Premiação ao jogador
    if res.player_champion:
        conn.execute("UPDATE career SET money=money+?, reputation=MIN(100,reputation+4), titles=titles+1 WHERE id=?",
                     (8_000_000, career["id"]))
        print(f"     💰 +€8.0M · reputação +4 · 🏆 título estadual!")
    elif res.player_stage in ("Final", "Semifinais"):
        conn.execute("UPDATE career SET money=money+? WHERE id=?", (2_500_000, career["id"]))
        print(f"     💰 +€2.5M (boa campanha)")
    conn.commit()
    input("\n  Enter... (jogue de novo para iniciar o Brasileirão)")


# ─── Copa do Brasil (fase intercalada) ───────────────────────────────────────

def _run_copa_stage_ui(conn, career, comp, stage_idx):
    from engine import copa as COPA
    from engine.live import build_timeline, broadcast
    from engine.lineup import style_mults
    club_id = career["manager_club_id"]
    stage_name = COPA.STAGES[stage_idx][0]
    comp_name = COPA.COMPS[comp]["name"]
    prize_full = COPA.COMPS[comp]["prize"]

    # Clubes envolvidos na fase (com elencos)
    ids = set()
    for r in conn.execute("""SELECT home_id, away_id FROM copa
            WHERE career_id=? AND season_year=? AND comp=? AND stage_idx=? AND played=0""",
            (career["id"], career["season_year"], comp, stage_idx)).fetchall():
        ids.add(r["home_id"]); ids.add(r["away_id"])
    by_id = {}
    for cid in ids:
        by_id[cid] = _club_with_squad(conn, cid)
    my = by_id.get(club_id)
    watch = False
    _header(f"{comp_name.upper()} — {stage_name}")
    pt = COPA.player_tie(conn, career, comp, stage_idx)
    if my and pt:
        my.starting_xi = get_saved_xi(conn, career, my.players)[1]
        my.style_atk, my.style_def = style_mults(career["tactic_style"] or "equilibrado")
        print(f"\n  Seu confronto: vs {pt['opp_name']}")
        watch = input("  Assistir ao vivo? [s/N]: ").strip().lower() == "s"

    def on_match(h, a):
        if watch:
            res = build_timeline(h, a); broadcast(res, h, a, spm=1.3); return res
        from engine.simulation import simulate_match
        return simulate_match(h, a)

    lines, winners = COPA.play_stage(conn, career, comp, stage_idx, by_id, on_match=on_match)
    print(f"\n  ── {comp_name} · {stage_name} ──")
    for ln in lines:
        print(ln)

    # Final? coroa o campeão
    champ = COPA.champion_id(conn, career, comp)
    if champ:
        cname = conn.execute("SELECT name FROM clubs WHERE id=?", (champ,)).fetchone()[0]
        print(f"\n  🏆 CAMPEÃO — {comp_name}: {cname}")
        if champ == club_id:
            conn.execute("UPDATE career SET money=money+?, reputation=MIN(100,reputation+6), titles=titles+1 WHERE id=?",
                         (prize_full, career["id"]))
            print(f"     💰 +{_fmt_money(prize_full)} · reputação +6 · 🏆 título!")
            conn.commit()
    else:
        # premiação por avançar
        still_in = any(wid == club_id for _, wid in winners)
        if still_in:
            conn.execute("UPDATE career SET money=money+? WHERE id=?", (4_000_000, career["id"]))
            print(f"\n  ✅ Você avançou! 💰 +€4M de premiação")
            conn.commit()
        elif my and pt:
            print(f"\n  ❌ Eliminado na {stage_name}.")
    input("\n  Enter... (volte a jogar para continuar o Brasileirão)")


def _club_with_squad(conn, club_id):
    from db.models import Club, Player
    r = conn.execute("SELECT * FROM clubs WHERE id=?", (club_id,)).fetchone()
    prows = conn.execute(
        "SELECT * FROM players WHERE club_id=? AND retired=0 ORDER BY overall DESC LIMIT 18",
        (club_id,)).fetchall()
    players = [Player(id=p["id"], name=p["name"], position=p["position"] or "MF",
        nationality=p["nationality"] or "", birth_date=p["birth_date"], club_id=p["club_id"],
        pace=p["pace"], technique=p["technique"], strength=p["strength"], finishing=p["finishing"],
        passing=p["passing"], defending=p["defending"], goalkeeping=p["goalkeeping"],
        stamina=p["stamina"], mental=p["mental"], overall=p["overall"], source=p["source"] or "")
        for p in prows]
    c = Club(id=r["id"], name=r["name"], short_name=r["name"][:12],
             league_id=r["league_id"] or 0, prestige=r["prestige"])
    c.players = players
    return c


# ─── Jogar UMA rodada (volta à gestão entre jogos) ───────────────────────────

def play_round(conn, career):
    """Joga a próxima rodada da liga e volta à tela de gestão (loop Brasfoot)."""
    from engine import calendar as CAL
    from engine.simulation import simulate_match
    from engine.season import _update_morale
    from engine.live import build_timeline, broadcast
    from engine.lineup import style_mults

    club_id = career["manager_club_id"]
    state = conn.execute("SELECT state FROM clubs WHERE id=?", (club_id,)).fetchone()[0]
    country = conn.execute("""
        SELECT co.code FROM clubs c JOIN leagues l ON l.id=c.league_id
        JOIN countries co ON co.id=l.country_id WHERE c.id=?
    """, (club_id,)).fetchone()
    country = country[0] if country else None

    # ── Estadual no início da temporada (clubes brasileiros) ──
    if state and (career["estadual_year"] or 0) != career["season_year"]:
        _run_estadual_ui(conn, career, state)
        conn.execute("UPDATE career SET estadual_year=? WHERE id=?",
                     (career["season_year"], career["id"]))
        conn.commit()
        career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
        return  # volta à gestão; jogue de novo para iniciar a liga

    CAL.ensure_fixtures(conn, career)
    nrounds = CAL.num_rounds(conn, career)
    cr = career["current_round"] or 0

    # ── Copas intercaladas (Copa do Brasil + Libertadores + Sul-Americana) ──
    if country in ("BR", "AR"):
        from engine import copa as COPA
        due = COPA.due_comp(conn, career, cr)
        if due:
            comp, st = due
            _run_copa_stage_ui(conn, career, comp, st)
            return  # volta à gestão

    if cr >= nrounds:
        _finish_round_season(conn, career)
        return

    # Clubes da liga (objetos com elenco) p/ esta rodada
    clubs = CAL._load_league_clubs(conn, CAL.league_id_of(conn, club_id))
    by_id = {c.id: c for c in clubs}
    my = by_id.get(club_id)
    if my:
        _, xi = get_saved_xi(conn, career, my.players)
        my.starting_xi = xi
        my.style_atk, my.style_def = style_mults(career["tactic_style"] or "equilibrado")
    for c in clubs:
        c.morale = CAL._club_morale(conn, career, c.id)

    fxs = conn.execute("""
        SELECT id, home_id, away_id FROM fixtures
        WHERE career_id=? AND season_year=? AND round_idx=? AND played=0
    """, (career["id"], career["season_year"], cr)).fetchall()

    _header(f"RODADA {cr+1}/{nrounds} — Temporada {career['season_year']}")
    watch = False
    # Seu jogo
    my_fx = next((f for f in fxs if club_id in (f["home_id"], f["away_id"])), None)
    if my_fx:
        opp = by_id.get(my_fx["away_id"] if my_fx["home_id"] == club_id else my_fx["home_id"])
        loc = "🏠 casa" if my_fx["home_id"] == club_id else "✈️  fora"
        print(f"\n  Seu jogo: vs {opp.name} ({loc})")
        watch = input("  Assistir ao vivo? [s/N]: ").strip().lower() == "s"

    # Joga todos os confrontos da rodada
    for f in fxs:
        h, a = by_id[f["home_id"]], by_id[f["away_id"]]
        is_player = club_id in (h.id, a.id)
        if is_player and watch:
            res = build_timeline(h, a); broadcast(res, h, a, spm=1.3)
        else:
            res = simulate_match(h, a)
        conn.execute("UPDATE fixtures SET played=1, home_goals=?, away_goals=? WHERE id=?",
                     (res.home_goals, res.away_goals, f["id"]))
        _update_morale(h, a, res.home_goals, res.away_goals)
        if is_player and not watch:
            print(f"\n  📋 {h.name} {res.home_goals} x {res.away_goals} {a.name}")
    conn.execute("UPDATE career SET current_round=?, updated_at=datetime('now') WHERE id=?",
                 (cr + 1, career["id"]))
    conn.commit()

    # Mini-tabela
    tab = CAL.standings(conn, career)
    pos = next((i for i, s in enumerate(tab, 1) if s.club_id == club_id), "?")
    print(f"\n  Sua posição: {pos}º  ·  rodada {cr+1}/{nrounds} concluída")
    print(f"  {'#':>2} {'Clube':<22}{'Pts':>4}{'J':>3}")
    for i, s in enumerate(tab[:5], 1):
        mk = " ◀" if s.club_id == club_id else ""
        print(f"  {i:>2} {s.club_name[:21]:<22}{s.points:>4}{s.played:>3}{mk}")

    if cr + 1 >= nrounds:
        print(f"\n  🏁 Última rodada! Processando fim de temporada...")
        input("\n  Enter...")
        _finish_round_season(conn, career)


def _finish_round_season(conn, career):
    """Fim de temporada no modo rodada-a-rodada: usa a tabela acumulada."""
    from engine import calendar as CAL
    clubs = CAL._load_league_clubs(conn, CAL.league_id_of(conn, career["manager_club_id"]))
    table = CAL.standings(conn, career)
    finished_season = career["season_year"]
    _finish_season(conn, career, table, clubs)
    # Reset calendário p/ a nova temporada
    conn.execute("DELETE FROM fixtures WHERE career_id=? AND season_year=?",
                 (career["id"], finished_season))
    conn.execute("DELETE FROM copa WHERE career_id=? AND season_year=?",
                 (career["id"], finished_season))
    conn.execute("UPDATE career SET current_round=0 WHERE id=?", (career["id"],))
    conn.commit()


# ─── Scout: melhores newgens do mundo ────────────────────────────────────────

def scout_newgens(conn, career):
    _header("SCOUT — JOVENS PROMESSAS DO MUNDO")
    rows = conn.execute("""
        SELECT p.name, p.position, p.age, p.overall, p.potential,
               p.value, c.name as club, p.nationality
        FROM players p LEFT JOIN clubs c ON c.id=p.club_id
        WHERE p.is_newgen=1 AND p.age <= 20 AND p.retired=0
        ORDER BY p.potential DESC, p.overall DESC LIMIT 25
    """).fetchall()

    if not rows:
        print("\n  Nenhum newgen ainda. Jogue uma temporada primeiro.")
        return

    print(f"\n  {'Nome':<24}{'Pos':<5}{'Id':>3}{'OVR':>5}{'POT':>5}{'Valor':>9}  Clube")
    print(f"  {'─'*70}")
    for r in rows:
        print(f"  {r['name'][:23]:<24}{r['position']:<5}{r['age']:>3}"
              f"{r['overall']:>5}{r['potential']:>5}{_fmt_money(r['value'] or 0):>9}  {(r['club'] or '?')[:22]}")


# ─── Histórico ───────────────────────────────────────────────────────────────

def view_history(conn, career):
    _header("HISTÓRICO DA CARREIRA")
    club = conn.execute("SELECT name FROM clubs WHERE id=?", (career["manager_club_id"],)).fetchone()
    print(f"\n  Clube: {club['name']}")
    print(f"  Temporadas: {career['seasons_played']}  ·  Títulos: {career['titles']}")

    rows = conn.execute("""
        SELECT sh.season_year, sh.manager_pos, sh.manager_pts, c.name as champ
        FROM season_history sh
        LEFT JOIN clubs c ON c.id = sh.champion_id
        WHERE sh.career_id=? ORDER BY sh.season_year
    """, (career["id"],)).fetchall()

    if rows:
        print(f"\n  {'Temp':<7}{'Pos':>4}{'Pts':>5}   Campeão")
        print(f"  {'─'*45}")
        for r in rows:
            trophy = " 🏆" if r['manager_pos'] == 1 else ""
            print(f"  {r['season_year']:<7}{r['manager_pos']:>3}º{r['manager_pts']:>5}   {(r['champ'] or '?')[:22]}{trophy}")


# ─── Mercado de transferências ───────────────────────────────────────────────

def transfer_market(conn, career):
    while True:
        career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
        from engine.transfer import squad_size
        n = squad_size(conn, career["manager_club_id"])
        _header("MERCADO DE TRANSFERÊNCIAS")
        from engine.finance import wage_bill
        wb = wage_bill(conn, career["manager_club_id"])
        print(f"\n  💰 Caixa: {_fmt_money(career['money'])}   ·   📋 Folha: {_fmt_money(wb)}/ano   ·   👥 {n}")
        print("""
  1. Comprar jogador
  2. Vender jogador
  3. Pegar emprestado (loan in)
  4. Emprestar jogador (loan out)
  0. Voltar
""")
        ch = input("  Opção: ").strip()
        if ch == "1":
            market_buy(conn, career)
        elif ch == "2":
            market_sell(conn, career)
        elif ch == "3":
            market_loan_in(conn, career)
        elif ch == "4":
            market_loan_out(conn, career)
        elif ch == "0":
            break


def market_buy(conn, career):
    from engine.transfer import (list_market, asking_and_clause,
                                 evaluate_offer, buy_player_at)
    _header("COMPRAR")

    pos = input("  Posição (GK/DF/MF/FW ou Enter p/ todas): ").strip().upper() or None
    if pos and pos not in ("GK", "DF", "MF", "FW"):
        pos = None
    raw = input("  Preço máximo em €M (Enter p/ orçamento): ").strip()
    try:
        max_price = int(float(raw) * 1_000_000) if raw else career["money"]
    except ValueError:
        max_price = career["money"]

    players = list_market(conn, career["manager_club_id"], position=pos,
                          max_price=max_price, limit=30)
    if not players:
        print("\n  Nenhum jogador no filtro.")
        return

    print(f"\n  {'#':>2} {'Nome':<19}{'Pos':<4}{'OVR':>4}{'Pede':>8}{'Cláusula':>10}{'Salário':>8}")
    print(f"  {'─'*70}")
    for i, p in enumerate(players, 1):
        asking, clause = asking_and_clause(conn, p["id"], career)
        wg = conn.execute("SELECT wage FROM players WHERE id=?", (p["id"],)).fetchone()[0] or 0
        print(f"  {i:>2} {p['name'][:18]:<19}{p['position']:<4}{p['overall']:>4}"
              f"{_fmt_money(asking):>8}{_fmt_money(clause):>10}{_fmt_money(wg):>8}")

    sel = input("\n  Nº para negociar (Enter cancela): ").strip()
    if not sel:
        return
    try:
        chosen = players[int(sel) - 1]
    except (ValueError, IndexError):
        print("  Inválido.")
        return

    _negotiate_buy(conn, career, chosen)
    input("\n  Enter...")


def _negotiate_buy(conn, career, player):
    """Loop de negociação: ofertas, contrapropostas, cláusula."""
    from engine.transfer import asking_and_clause, evaluate_offer, buy_player_at
    asking, clause = asking_and_clause(conn, player["id"], career)
    name = player["name"]

    print(f"\n  ── Negociando {name} ──")
    print(f"  Clube pede: {_fmt_money(asking)}   ·   Cláusula: {_fmt_money(clause)}")
    print(f"  Seu caixa: {_fmt_money(career['money'])}")
    print(f"  (pagar a cláusula = compra imediata, sem negociar)")

    rounds = 0
    while rounds < 4:
        rounds += 1
        raw = input(f"\n  Oferta em €M (Enter desiste): ").strip()
        if not raw:
            print("  Negociação encerrada.")
            return
        try:
            offer = int(float(raw) * 1_000_000)
        except ValueError:
            print("  Valor inválido.")
            continue

        if offer > career["money"]:
            print(f"  ⚠️ Você só tem {_fmt_money(career['money'])} em caixa.")
            continue

        result, amount = evaluate_offer(offer, asking, clause)
        if result == "clause":
            ok, msg = buy_player_at(conn, career, player["id"], offer)
            print(f"\n  💥 CLÁUSULA PAGA! {msg}")
            return
        elif result == "accept":
            ok, msg = buy_player_at(conn, career, player["id"], offer)
            print(f"\n  🤝 Proposta aceita! {msg}")
            return
        elif result == "counter":
            print(f"  ↪️  Recusado. Contraproposta do clube: {_fmt_money(amount)}")
            ans = input(f"     Aceitar {_fmt_money(amount)}? [s/N]: ").strip().lower()
            if ans == "s":
                if amount > career["money"]:
                    print(f"  ⚠️ Sem caixa para {_fmt_money(amount)}.")
                    return
                ok, msg = buy_player_at(conn, career, player["id"], amount)
                print(f"\n  🤝 {msg}")
                return
            asking = amount  # clube agora aceita esse patamar
        else:
            print(f"  ❌ Oferta muito baixa. Clube nem considera.")


def market_sell(conn, career):
    from engine.transfer import sell_price, sell_player
    _header("VENDER")

    squad = conn.execute("""
        SELECT id, name, position, age, overall, potential, value
        FROM players WHERE club_id=? AND retired=0
        ORDER BY overall DESC
    """, (career["manager_club_id"],)).fetchall()

    if not squad:
        print("\n  Elenco vazio.")
        return

    from engine.manager import IDOL_OVERALL
    print(f"\n  {'#':>2} {'Nome':<22}{'Pos':<4}{'Id':>3}{'OVR':>4}{'Oferta':>10}")
    print(f"  {'─'*50}")
    for i, p in enumerate(squad, 1):
        offer = sell_price(p["value"], p["id"], career["id"], career["season_year"])
        idol = " ⭐ÍDOLO" if p["overall"] >= IDOL_OVERALL else ""
        print(f"  {i:>2} {p['name'][:21]:<22}{p['position']:<4}{p['age']:>3}"
              f"{p['overall']:>4}{_fmt_money(offer):>10}{idol}")

    sel = input("\n  Nº para vender (Enter cancela): ").strip()
    if not sel:
        return
    try:
        chosen = squad[int(sel) - 1]
    except (ValueError, IndexError):
        print("  Inválido.")
        return

    # Aviso: vender ídolo machuca reputação
    if chosen["overall"] >= IDOL_OVERALL:
        print(f"\n  ⚠️  {chosen['name']} é ÍDOLO (OVR {chosen['overall']}). "
              f"Vendê-lo irrita a torcida e o conselho.")
        if input("  Confirmar venda? [s/N]: ").strip().lower() != "s":
            print("  Venda cancelada.")
            return

    ok, msg = sell_player(conn, career, chosen["id"])
    print(f"\n  {msg}")
    if ok and chosen["overall"] >= IDOL_OVERALL:
        from engine.manager import idol_sale_penalty
        hit = idol_sale_penalty(conn, career, chosen["overall"])
        if hit:
            print(f"  📉 Revolta da torcida: reputação -{hit}")
    input("\n  Enter...")


def market_loan_in(conn, career):
    from engine.transfer import list_market, loan_in, loan_min_coverage
    _header("PEGAR EMPRESTADO (loan in)")
    print("  Proponha % do salário que vai bancar + taxa mensal ao dono.")
    print("  Quanto melhor o jogador, maior a cobertura exigida.")

    pos = input("\n  Posição (GK/DF/MF/FW ou Enter): ").strip().upper() or None
    if pos and pos not in ("GK", "DF", "MF", "FW"):
        pos = None

    players = list_market(conn, career["manager_club_id"], position=pos,
                          min_ovr=60, max_ovr=84, limit=25)
    players = [p for p in players if conn.execute(
        "SELECT loan_from_club FROM players WHERE id=?", (p["id"],)).fetchone()[0] is None]
    if not players:
        print("\n  Nenhum jogador emprestável no filtro.")
        input("\n  Enter...")
        return

    print(f"\n  {'#':>2} {'Nome':<22}{'Pos':<4}{'OVR':>4}{'Salário':>9}{'Exige':>7}  Clube")
    print(f"  {'─'*64}")
    for i, p in enumerate(players, 1):
        wg = conn.execute("SELECT wage FROM players WHERE id=?", (p["id"],)).fetchone()[0] or 0
        req = loan_min_coverage(p["overall"])
        print(f"  {i:>2} {p['name'][:21]:<22}{p['position']:<4}{p['overall']:>4}"
              f"{_fmt_money(wg):>9}{req:>6}%  {(p['club'] or '?')[:14]}")

    sel = input("\n  Nº para propor (Enter cancela): ").strip()
    if not sel:
        return
    try:
        chosen = players[int(sel) - 1]
    except (ValueError, IndexError):
        print("  Inválido.")
        return

    # Proposta
    try:
        wage_pct = int(input("  % do salário que vai bancar (0-100): ").strip() or "50")
        wage_pct = max(0, min(100, wage_pct))
    except ValueError:
        wage_pct = 50
    try:
        fee_raw = input("  Taxa mensal em €K (Enter = 0): ").strip()
        monthly_fee = int(float(fee_raw) * 1000) if fee_raw else 0
    except ValueError:
        monthly_fee = 0

    ok, msg = loan_in(conn, career, chosen["id"], career["season_year"],
                      wage_pct=wage_pct, monthly_fee=monthly_fee)
    print(f"\n  {msg}")
    input("\n  Enter...")


def market_loan_out(conn, career):
    from engine.transfer import loan_out
    _header("EMPRESTAR JOGADOR (loan out)")
    print("  Libera o salário do jogador por 1 temporada; ele volta depois.")

    squad = conn.execute("""
        SELECT id, name, position, age, overall, wage
        FROM players WHERE club_id=? AND retired=0 AND loan_from_club IS NULL
        ORDER BY overall ASC
    """, (career["manager_club_id"],)).fetchall()
    if not squad:
        print("\n  Nenhum jogador emprestável.")
        input("\n  Enter...")
        return

    print(f"\n  {'#':>2} {'Nome':<22}{'Pos':<4}{'Id':>3}{'OVR':>4}{'Salário':>10}")
    print(f"  {'─'*50}")
    for i, p in enumerate(squad, 1):
        print(f"  {i:>2} {p['name'][:21]:<22}{p['position']:<4}{p['age']:>3}"
              f"{p['overall']:>4}{_fmt_money(p['wage'] or 0):>10}")

    sel = input("\n  Nº para emprestar (Enter cancela): ").strip()
    if not sel:
        return
    try:
        chosen = squad[int(sel) - 1]
    except (ValueError, IndexError):
        print("  Inválido.")
        return
    ok, msg = loan_out(conn, career, chosen["id"], career["season_year"])
    print(f"\n  {msg}")
    input("\n  Enter...")


# ─── Escalação (formação + 11) ───────────────────────────────────────────────

def _load_squad_players(conn, club_id):
    from db.models import Player
    rows = conn.execute(
        "SELECT * FROM players WHERE club_id=? AND retired=0 ORDER BY overall DESC", (club_id,)
    ).fetchall()
    return [Player(
        id=p["id"], name=p["name"], position=p["position"] or "MF",
        nationality=p["nationality"] or "", birth_date=p["birth_date"],
        club_id=p["club_id"], pace=p["pace"], technique=p["technique"],
        strength=p["strength"], finishing=p["finishing"], passing=p["passing"],
        defending=p["defending"], goalkeeping=p["goalkeeping"],
        stamina=p["stamina"], mental=p["mental"], overall=p["overall"],
        source=p["source"] or "", age=p["age"] or 0,
        wage=p["wage"] or 0, contract_until=p["contract_until"],
        form=p["form"] if p["form"] is not None else 1.0,
        fitness=p["fitness"] if p["fitness"] is not None else 100,
    ) for p in rows]


def get_saved_xi(conn, career, squad):
    """Retorna (formation, xi_players) da escalação salva, ou auto."""
    from engine.lineup import auto_lineup, DEFAULT_FORMATION
    formation = career["formation"] or DEFAULT_FORMATION
    saved = career["lineup"]
    if saved:
        ids = [int(x) for x in saved.split(",") if x.strip().isdigit()]
        by_id = {p.id: p for p in squad}
        xi = [by_id[i] for i in ids if i in by_id]
        if len(xi) == 11:
            return formation, xi
    return formation, auto_lineup(squad, formation)


def manage_lineup(conn, career):
    from engine.lineup import (FORMATIONS, formation_slots, auto_lineup,
                               validate_lineup, DEFAULT_FORMATION)
    squad = _load_squad_players(conn, career["manager_club_id"])
    if len(squad) < 11:
        print("\n  Elenco insuficiente para escalar.")
        input("\n  Enter..."); return

    formation, xi = get_saved_xi(conn, career, squad)
    style = career["tactic_style"] or "equilibrado"

    while True:
        _header("ESCALAÇÃO")
        print(f"\n  Formação: {formation}    (DF-MF-FW = {'-'.join(map(str, FORMATIONS[formation]))})")
        # Mostra XI por linha
        lines = {"GK": [], "DF": [], "MF": [], "FW": []}
        for p in xi:
            lines.setdefault(p.position, lines["MF"]).append(p)
        for pos in ("GK", "DF", "MF", "FW"):
            ps = lines.get(pos, [])
            if ps:
                tag = "  ".join(f"{p.name.split()[-1][:10]}({p.overall})" for p in ps)
                print(f"   {pos}: {tag}")
        avg = sum(p.overall for p in xi) / 11
        ok, msg = validate_lineup(xi, formation)
        print(f"\n   Média do 11: {avg:.1f}   {'✅ válida' if ok else '⚠️ '+msg}")
        print(f"   Estilo: {style.upper()}")
        print("""
   [f] formação   [t] trocar jogador   [e] estilo tático
   [a] auto       [s] salvar e voltar  [0] voltar sem salvar
""")
        ch = input("   Opção: ").strip().lower()
        if ch == "f":
            print("\n   Formações:", ", ".join(FORMATIONS.keys()))
            nf = input("   Nova formação: ").strip()
            if nf in FORMATIONS:
                formation = nf
                xi = auto_lineup(squad, formation)
        elif ch == "e":
            print("\n   1. Ofensivo (+ataque −defesa)")
            print("   2. Equilibrado")
            print("   3. Defensivo (−ataque +defesa)")
            m = {"1": "ofensivo", "2": "equilibrado", "3": "defensivo"}.get(input("   Estilo: ").strip())
            if m:
                style = m
        elif ch == "a":
            xi = auto_lineup(squad, formation)
        elif ch == "t":
            _swap_lineup_player(xi, squad)
        elif ch == "s":
            ok, msg = validate_lineup(xi, formation)
            if not ok:
                print(f"   {msg}"); input("\n   Enter..."); continue
            ids = ",".join(str(p.id) for p in xi)
            conn.execute("UPDATE career SET formation=?, lineup=?, tactic_style=? WHERE id=?",
                         (formation, ids, style, career["id"]))
            conn.commit()
            print("   ✅ Escalação + estilo salvos."); input("\n   Enter..."); return
        elif ch == "0":
            return


def _swap_lineup_player(xi, squad):
    print("\n   Titulares:")
    for i, p in enumerate(xi, 1):
        print(f"   {i:>2}. {p.position} {p.name[:20]:<20} OVR {p.overall}")
    try:
        out_i = int(input("   Sair (nº): ").strip()) - 1
        out = xi[out_i]
    except (ValueError, IndexError):
        return
    bench = [p for p in squad if p.id not in {x.id for x in xi}]
    bench.sort(key=lambda p: (p.position != out.position, -p.overall))
    print(f"\n   Reservas (entrar no lugar de {out.name}):")
    for i, p in enumerate(bench[:15], 1):
        same = "▶" if p.position == out.position else " "
        print(f"  {same}{i:>2}. {p.position} {p.name[:20]:<20} OVR {p.overall}")
    try:
        in_i = int(input("   Entrar (nº): ").strip()) - 1
        inn = bench[in_i]
    except (ValueError, IndexError):
        return
    xi[out_i] = inn


# ─── Estádio e ingressos ─────────────────────────────────────────────────────

def manage_stadium(conn, career):
    from engine.finance import (base_ticket_price, attendance_fill,
                                stadium_revenue)
    club = conn.execute(
        "SELECT name, prestige, capacity, ticket_price FROM clubs WHERE id=?",
        (career["manager_club_id"],)
    ).fetchone()

    # Posição esperada = última no histórico, senão meio de tabela
    last = conn.execute("""
        SELECT manager_pos FROM season_history
        WHERE career_id=? ORDER BY season_year DESC LIMIT 1
    """, (career["id"],)).fetchone()
    pos = last["manager_pos"] if last and last["manager_pos"] else 10
    n_clubs = 20

    base = base_ticket_price(club["prestige"])
    cur_price = club["ticket_price"] or base

    while True:
        fill = attendance_fill(club["prestige"], pos, n_clubs, cur_price)
        rev = stadium_revenue(club["capacity"], club["prestige"], pos, n_clubs, cur_price)
        public = int(club["capacity"] * fill)

        tl = career["training_level"] or 2
        _header(f"ESTÁDIO & CT — {club['name']}")
        print(f"\n  🏟️  Capacidade: {club['capacity']:,} lugares  ·  ref €{base}  ·  atual €{cur_price}")
        print(f"  Projeção ({pos}º): ocupação {fill*100:.0f}% ({public:,}/jogo) · bilheteria {_fmt_money(rev)}/ano")
        print(f"\n  🏋️  Centro de Treinamento — nível {tl}/5  (custo {_fmt_money(tl*2_500_000)}/ano)")
        print(f"      Nível >2 acelera a evolução do seu elenco; <2 economiza.")
        print(f"\n  [p] mudar preço de ingresso   [t] mudar nível do CT   [0] voltar")
        ch = input("  Opção: ").strip().lower()
        if ch == "t":
            raw = input("  Novo nível do CT (1-5): ").strip()
            if raw.isdigit():
                nl = max(1, min(5, int(raw)))
                conn.execute("UPDATE career SET training_level=? WHERE id=?", (nl, career["id"]))
                conn.commit()
                career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()
                print(f"  ✅ CT nível {nl}")
            continue
        elif ch != "p":
            break
        raw = input("  Novo preço em € (Enter cancela): ").strip()
        if not raw:
            continue
        try:
            new_price = max(5, min(300, int(float(raw))))
        except ValueError:
            print("  Inválido.")
            continue
        cur_price = new_price
        conn.execute("UPDATE clubs SET ticket_price=? WHERE id=?",
                     (new_price, career["manager_club_id"]))
        conn.commit()
        print(f"  ✅ Ingresso ajustado para €{new_price}")


# ─── Busca de times + classificação (página de gestão) ───────────────────────

def browse_teams(conn, career):
    while True:
        _header("BUSCAR TIME")
        q = input("\n  Nome do clube (parcial, Enter volta): ").strip()
        if not q:
            return
        matches = conn.execute(
            "SELECT id, name, prestige, league_id FROM clubs WHERE name LIKE ? ORDER BY prestige DESC LIMIT 12",
            (f"%{q}%",)
        ).fetchall()
        if not matches:
            print("  Nenhum clube."); continue
        for i, m in enumerate(matches, 1):
            print(f"  {i:>2}. {m['name']:<32} (prestígio {m['prestige']})")
        sel = input("\n  Ver elenco (nº): ").strip()
        try:
            club = matches[int(sel) - 1]
        except (ValueError, IndexError):
            continue
        _show_club_page(conn, club["id"])


def _show_club_page(conn, club_id):
    club = conn.execute("SELECT * FROM clubs WHERE id=?", (club_id,)).fetchone()
    coach = conn.execute(
        "SELECT name, reputation FROM coaches WHERE club_id=? AND retired=0 LIMIT 1", (club_id,)
    ).fetchone()
    players = conn.execute("""
        SELECT name, position, age, overall, potential, value
        FROM players WHERE club_id=? AND retired=0
        ORDER BY CASE position WHEN 'GK' THEN 1 WHEN 'DF' THEN 2
                               WHEN 'MF' THEN 3 WHEN 'FW' THEN 4 END, overall DESC
    """, (club_id,)).fetchall()

    _header(club["name"])
    tech = f"{coach['name']} (rep {coach['reputation']})" if coach else "— (humano ou vago)"
    cap = club["capacity"] or 0
    print(f"\n  Prestígio: {club['prestige']}   ·   Técnico: {tech}")
    print(f"  Estádio: {cap:,} lugares   ·   Ingresso: €{club['ticket_price'] or 0}")
    print(f"\n  {'Nome':<22}{'Pos':<4}{'Id':>3}{'OVR':>4}{'POT':>4}{'Valor':>10}")
    print(f"  {'─'*52}")
    for p in players:
        pot = p['potential'] if p['potential'] and p['potential'] > p['overall'] else '—'
        print(f"  {p['name'][:21]:<22}{p['position'] or '?':<4}{p['age'] or 0:>3}"
              f"{p['overall']:>4}{str(pot):>4}{_fmt_money(p['value'] or 0):>10}")
    if players:
        avg = sum(p['overall'] for p in players) / len(players)
        print(f"  {'─'*52}")
        print(f"  {len(players)} jogadores · OVR médio {avg:.1f}")
    input("\n  Enter...")


def view_classificacao(conn, career):
    # Tabela AO VIVO da temporada corrente (a partir das partidas já jogadas)
    from engine import calendar as CAL
    played = conn.execute(
        "SELECT COUNT(*) FROM fixtures WHERE career_id=? AND season_year=? AND played=1",
        (career["id"], career["season_year"])).fetchone()[0]

    _header("CLASSIFICAÇÃO")
    if played > 0:
        tab = CAL.standings(conn, career)
        n = len(tab)
        print(f"\n  Temporada {career['season_year']} (em andamento)")
        print(f"  {'#':>2} {'Clube':<24}{'P':>3}{'J':>3}{'V':>3}{'E':>3}{'D':>3}{'GP':>4}{'GC':>4}{'SG':>4}")
        print(f"  {'─'*60}")
        for i, s in enumerate(tab, 1):
            mark = " ◀" if s.club_id == career["manager_club_id"] else ""
            zone = "🟢" if i <= 4 else ("🔴" if i > n - 3 else "  ")
            print(f"  {zone}{i:>2} {s.club_name[:23]:<24}{s.points:>3}{s.played:>3}"
                  f"{s.wins:>3}{s.draws:>3}{s.losses:>3}{s.gf:>4}{s.ga:>4}{s.gd:>+4}{mark}")
        input("\n  Enter..."); return

    # Senão, última temporada persistida
    league_id = conn.execute("SELECT league_id FROM clubs WHERE id=?",
                             (career["manager_club_id"],)).fetchone()[0]
    row = conn.execute("""
        SELECT MAX(season_year) FROM league_table WHERE career_id=? AND league_id=?
    """, (career["id"], league_id)).fetchone()
    last = row[0] if row else None
    if not last:
        print("\n  Sem classificação ainda. Jogue uma rodada.")
        input("\n  Enter..."); return
    rows = conn.execute("""
        SELECT lt.pos, cl.name, lt.played, lt.wins, lt.draws, lt.losses,
               lt.gf, lt.ga, lt.points, lt.club_id
        FROM league_table lt JOIN clubs cl ON cl.id=lt.club_id
        WHERE lt.career_id=? AND lt.league_id=? AND lt.season_year=?
        ORDER BY lt.pos
    """, (career["id"], league_id, last)).fetchall()
    n = len(rows)
    print(f"\n  Temporada {last} (final)")
    print(f"  {'#':>2} {'Clube':<24}{'P':>3}{'J':>3}{'V':>3}{'E':>3}{'D':>3}{'GP':>4}{'GC':>4}{'SG':>4}")
    print(f"  {'─'*60}")
    for r in rows:
        mark = " ◀" if r["club_id"] == career["manager_club_id"] else ""
        zone = "🟢" if r["pos"] <= 4 else ("🔴" if r["pos"] > n - 3 else "  ")
        print(f"  {zone}{r['pos']:>2} {r['name'][:23]:<24}{r['points']:>3}{r['played']:>3}"
              f"{r['wins']:>3}{r['draws']:>3}{r['losses']:>3}{r['gf']:>4}{r['ga']:>4}"
              f"{r['gf']-r['ga']:>+4}{mark}")
    input("\n  Enter...")


# ─── Hub principal ───────────────────────────────────────────────────────────

def career_hub(conn, career):
    """Loop da carreira ativa."""
    while True:
        career = conn.execute("SELECT * FROM career WHERE id=?", (career["id"],)).fetchone()

        # Demitido? encerra a carreira
        if career["status"] == "sacked":
            print("\n  Carreira encerrada (demitido). Volte ao menu para começar outra.")
            input("\n  Enter...")
            break

        club = conn.execute("SELECT name FROM clubs WHERE id=?", (career["manager_club_id"],)).fetchone()
        rep = career["reputation"] or 50
        rep_icon = "🟢" if rep >= 60 else ("🟡" if rep >= 40 else "🔴")
        warn = "  ⚠️ ADVERTIDO" if (career["warnings"] or 0) >= 1 else ""

        # Próximo evento (estadual / copa intercalada / rodada da liga)
        try:
            from engine import calendar as CAL
            state = conn.execute("SELECT state FROM clubs WHERE id=?", (career["manager_club_id"],)).fetchone()[0]
            crow = conn.execute("""SELECT co.code FROM clubs c JOIN leagues l ON l.id=c.league_id
                JOIN countries co ON co.id=l.country_id WHERE c.id=?""", (career["manager_club_id"],)).fetchone()
            country = crow[0] if crow else None
            cr = (career["current_round"] or 0)
            if state and (career["estadual_year"] or 0) != career["season_year"]:
                prox = "🏆 Estadual (início da temporada)"
            else:
                CAL.ensure_fixtures(conn, career)
                nr = CAL.num_rounds(conn, career)
                prox = None
                if country in ("BR", "AR"):
                    from engine import copa as COPA
                    due = COPA.due_comp(conn, career, cr)
                    if due:
                        comp, st = due
                        pt = COPA.player_tie(conn, career, comp, st)
                        adv = "vs " + pt["opp_name"] if pt else ""
                        prox = f"🏆 {COPA.COMPS[comp]['name']} — {COPA.STAGES[st][0]} {adv}"
                if prox is None:
                    nm = CAL.next_match(conn, career)
                    prox = (f"Rodada {cr+1}/{nr} · vs {nm['opp_name']} ({nm['loc']})"
                            if nm else "Temporada concluída — jogue p/ entressafra")
        except Exception:
            prox = "—"

        print(f"\n{'═'*58}")
        print(f"  🏟️   {club['name']}  ·  Temporada {career['season_year']}")
        print(f"  💰 {_fmt_money(career['money'])}   🏆 {career['titles']} títulos   "
              f"📅 {career['seasons_played']} temp.")
        print(f"  {rep_icon} Reputação {rep}/100   👔 Meta: {career['expectation'] or '?'}º{warn}")
        print(f"  ⚽ Próximo: {prox}")
        print(f"{'═'*58}")
        print("""
  1. Ver elenco          5. 🎟️  Estádio & CT
  2. 📋 Escalação         6. 📊 Classificação
  3. ▶️  Jogar próxima rodada   7. 🔍 Buscar time (elencos)
  4. 💰 Mercado           8. Scout · 9. Histórico
  0. Salvar e voltar ao menu
""")
        ch = input("  Opção: ").strip()
        if ch == "1":
            view_squad(conn, career)
            input("\n  Enter...")
        elif ch == "2":
            manage_lineup(conn, career)
        elif ch == "3":
            play_round(conn, career)
            input("\n  Enter...")
        elif ch == "4":
            transfer_market(conn, career)
        elif ch == "5":
            manage_stadium(conn, career)
        elif ch == "6":
            view_classificacao(conn, career)
        elif ch == "7":
            browse_teams(conn, career)
        elif ch == "8":
            scout_newgens(conn, career)
            input("\n  Enter...")
        elif ch == "9":
            view_history(conn, career)
            input("\n  Enter...")
        elif ch == "0":
            print("\n  💾 Carreira salva.")
            break
        else:
            print("  Opção inválida.")


def run_career():
    """Entry point do modo carreira — gerência de múltiplos saves."""
    import saves as SV

    while True:
        slist = SV.list_saves()
        _header("MODO CARREIRA — SAVES")
        if slist:
            print("\n  Jogos salvos:")
            for i, s in enumerate(slist, 1):
                st = " (demitido)" if s.get("status") == "sacked" else ""
                print(f"  {i:>2}. {s['coach']} — {s['club']}  ·  temp {s['season']}  ·  "
                      f"rep {s['reputation']}  🏆{s['titles']}{st}")
            print("\n  N. Novo jogo   ·   A<nº> apagar   ·   0. Voltar")
        else:
            print("\n  Nenhum save. Comece um novo jogo.")
            print("\n  N. Novo jogo   ·   0. Voltar")

        ch = input("\n  Opção: ").strip().upper()
        if ch == "0" or ch == "":
            return
        if ch == "N":
            _new_game_flow()
            continue
        if ch.startswith("A"):
            try:
                idx = int(ch[1:]) - 1
                SV.delete_save(slist[idx]["slug"])
                print("  🗑️  Save apagado.")
            except (ValueError, IndexError):
                print("  Inválido.")
            input("\n  Enter...")
            continue
        # Carregar save existente
        try:
            chosen = slist[int(ch) - 1]
        except (ValueError, IndexError):
            print("  Opção inválida."); continue
        SV.load_save(chosen["slug"])
        conn = _conn()
        career = get_active_career(conn)
        if not career:
            print("  Save sem carreira ativa (técnico demitido)."); conn.close(); input("\n  Enter..."); continue
        career_hub(conn, career)
        conn.close()


def _new_game_flow():
    """Coleta liga/clube/técnico, cria um save novo e entra na carreira."""
    import saves as SV
    conn = _conn()                  # template (ou save ativo) só p/ listar mundo
    career = new_career(conn)       # cria save dentro + insere carreira
    if career:
        conn = _conn()              # reconecta no save recém-criado/ativo
        career = get_active_career(conn)
        input("\n  Enter para entrar na carreira...")
        career_hub(conn, career)
    conn.close()
