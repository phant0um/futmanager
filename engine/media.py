"""
FUTMANAGER — Módulo de mídia (CM03/04)
GDD: "Improved Media Module" — mundo reage aos eventos da temporada com
mais frequência. `inbox.KIND_LABELS["media"]` já existia mas ninguém
gerava mensagem desse `kind` — esta camada PURA preenche essa infra
ociosa, transformando dados que JÁ EXISTEM (placar da rodada, sequência
de resultados em `fixtures`, moral) em texto de manchete/notícia.
Não inventa estado novo, não toca simulação/dinheiro — cosmético/narrativo.
Determinístico via hash(career, round, kind) — mesma seed-pattern de
`incoming_offers`/`ai_transfer_window`.
"""
from __future__ import annotations
import hashlib
import random

MAX_PER_ROUND = 1   # evita spam — 1 manchete por rodada, só quando há "fato"


def _seed(career_id: int, round_no: int, tag: str) -> random.Random:
    return random.Random(int(hashlib.md5(
        f"media:{career_id}:{round_no}:{tag}".encode()).hexdigest(), 16) % (2**31))


def _recent_results(conn, career, club_id: int, n: int = 40) -> list[str]:
    """Últimos resultados (mais recente primeiro): 'V'/'E'/'D'."""
    rows = conn.execute("""
        SELECT home_id, away_id, home_goals, away_goals, round_idx FROM fixtures
        WHERE career_id=? AND season_year=? AND played=1
          AND (home_id=? OR away_id=?)
        ORDER BY round_idx DESC LIMIT ?
    """, (career["id"], career["season_year"], club_id, club_id, n)).fetchall()
    out = []
    for r in rows:
        is_home = r["home_id"] == club_id
        gf = r["home_goals"] if is_home else r["away_goals"]
        ga = r["away_goals"] if is_home else r["home_goals"]
        out.append("V" if gf > ga else ("D" if gf < ga else "E"))
    return out


_MILESTONES = (3, 5, 8, 12, 16, 20, 25, 30)


def _streak_story(results: list[str], club_name: str) -> tuple[str, str] | None:
    """Sequência de resultados iguais (ou invencibilidade) vira matéria —
    só em marcos (3, 5, 8, 12...), senão repetiria a mesma notícia toda
    rodada enquanto a sequência dura (vira spam, igual erro já visto com
    `incoming_offers` — dedup por "fato novo", não por "fato em curso")."""
    if len(results) < 3:
        return None
    n_win = next((i for i, r in enumerate(results) if r != "V"), len(results))
    n_loss = next((i for i, r in enumerate(results) if r != "D"), len(results))
    n_unbeaten = next((i for i, r in enumerate(results) if r == "D"), len(results))

    if n_win in _MILESTONES:
        return (f"📈 {club_name} embala sequência de {n_win} vitórias",
                f"O {club_name} chega embalado, com {n_win} triunfos seguidos. "
                f"A torcida já sonha com voos mais altos na competição.")
    if n_loss in _MILESTONES:
        return (f"📉 Crise no {club_name} — {n_loss}ª derrota seguida",
                f"O {club_name} acumula {n_loss} derrotas consecutivas e a pressão sobre "
                f"o departamento de futebol cresce a cada rodada.")
    if n_unbeaten >= 4 and n_unbeaten in _MILESTONES:
        return (f"🛡️ {club_name} segue invicto há {n_unbeaten} jogos",
                f"Sem perder há {n_unbeaten} partidas, o {club_name} mostra solidez na "
                f"temporada e se firma como pedra no sapato dos rivais.")
    return None


def _match_headline(your: dict, club_name: str) -> tuple[str, str] | None:
    """Manchete sobre o resultado do próprio jogo nesta rodada — só quando
    é resultado marcante (goleada, virada de placar elástico, clássico)."""
    if not your:
        return None
    is_home = your["home"] == club_name
    gf = your["hg"] if is_home else your["ag"]
    ga = your["ag"] if is_home else your["hg"]
    rival = your["away"] if is_home else your["home"]
    if gf - ga >= 3:
        return (f"🔥 Goleada! {club_name} aplica {gf}x{ga} no {rival}",
                f"Atuação de gala: o {club_name} passou por cima do {rival} e "
                f"deixou a torcida em êxtase com a atuação avassaladora.")
    if ga - gf >= 3:
        return (f"😬 Vexame — {club_name} leva {ga}x{gf} do {rival}",
                f"Noite para esquecer: a derrota elástica para o {rival} acende o "
                f"alerta e deve pautar a semana de treinos.")
    return None


def round_media(conn, career, your: dict | None) -> list[dict]:
    """Gera 0-1 peça de mídia pra rodada — prioriza fato mais notável
    (resultado marcante > sequência). Retorna lista de {title, body}."""
    cid = career["manager_club_id"]
    club = conn.execute("SELECT name FROM clubs WHERE id=?", (cid,)).fetchone()
    if not club:
        return []
    name = club["name"]
    cr = career["current_round"] or 0
    rng = _seed(career["id"], cr, "media")

    candidates = []
    hl = _match_headline(your, name)
    if hl:
        candidates.append(hl)
    results = _recent_results(conn, career, cid)
    st = _streak_story(results, name)
    if st:
        candidates.append(st)

    if not candidates:
        return []
    # determinístico: se há mais de um fato, escolhe 1 (prioriza o mais "quente"
    # — resultado da própria rodada antes de sequência histórica)
    title, body = candidates[0]
    return [{"title": title, "body": body}]
