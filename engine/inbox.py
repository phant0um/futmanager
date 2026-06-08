"""
FUTMANAGER — Inbox narrativa
Cimento que reúne, num só lugar persistente e revisitável, avisos que hoje
só "passam pela tela" (proposta recebida, cobrança do board, fim de
temporada, relatório de scout pronto). GDD: "o usuário nunca deve se
perguntar o que fazer agora" — a inbox é o ponto de entrada de eventos.
Camada pura: grava/lê. Quem decide QUANDO gerar mensagem é o chamador
(api_play, season end, scouting, etc), não esta camada.
"""
from __future__ import annotations

KIND_LABELS = {
    "board": "🏛  Conselho", "scout_report": "🔎 Olheiro", "market": "💰 Mercado",
    "media": "📰 Mídia", "medical": "🚑 Médico", "record": "📜 Histórico",
}


def add_message(conn, career_id: int, round_no: int, kind: str, title: str, body: str,
                ref_type: str | None = None, ref_id: int | None = None):
    conn.execute(
        "INSERT INTO inbox_messages (career_id, round, kind, title, body, ref_type, ref_id) "
        "VALUES (?,?,?,?,?,?,?)",
        (career_id, round_no, kind, title, body, ref_type, ref_id)
    )
    conn.commit()


def list_messages(conn, career_id: int, limit: int = 100) -> list[dict]:
    rows = conn.execute(
        "SELECT id, round, kind, title, body, read, ref_type, ref_id, created_at "
        "FROM inbox_messages WHERE career_id=? ORDER BY id DESC LIMIT ?",
        (career_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def unread_count(conn, career_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM inbox_messages WHERE career_id=? AND read=0", (career_id,)
    ).fetchone()
    return row[0] if row else 0


def mark_read(conn, career_id: int, message_id: int | None = None):
    """message_id=None → marca tudo como lido (ex: ao abrir a inbox)."""
    if message_id is None:
        conn.execute("UPDATE inbox_messages SET read=1 WHERE career_id=? AND read=0", (career_id,))
    else:
        conn.execute("UPDATE inbox_messages SET read=1 WHERE id=? AND career_id=?",
                     (message_id, career_id))
    conn.commit()
