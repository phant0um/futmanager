"""
FUTMANAGER — Feedback de treino no perfil (CM03/04)
GDD: "treino precisa explicar progresso" — em vez de criar um sistema novo
de sessões semanais (reescrita grande de `engine.career.develop_player` por
pouco ganho perceptível em jogo de texto), esta camada PURA explica em
linguagem humana o que o sistema de treino existente (`training_level`/
`training_focus`, fim de temporada) já está fazendo com cada jogador —
mesmo princípio de `engine.knowledge`/`cm_role`: deriva exibição a partir
de dados reais já computados, sem novo estado persistido.
"""
from __future__ import annotations
from engine.career import _growth_factor, TRAINING_FOCUS_ATTRS, ATTR_COLS
from engine.knowledge import ATTR_LABELS

FOCUS_LABELS = {"geral": "Geral", "fisico": "Físico",
                "tecnico": "Técnico", "finalizacao": "Finalização"}


def _phase(age: int) -> tuple[str, str]:
    """(fase, descrição) — espelha as faixas de `_growth_factor`."""
    if age <= 21:  return "joia", "em formação — absorve treino rápido"
    if age <= 27:  return "ascensao", "em ascensão — treino ainda rende bastante"
    if age <= 31:  return "pico", "no auge — atributos estáveis, treino mantém o nível"
    if age <= 34:  return "declinio", "em declínio leve — treino segura a queda"
    return "veterano", "veterano — treino tem efeito reduzido sobre os atributos"


def training_summary(conn, career, player_id: int) -> dict | None:
    """Resumo explicativo do treino pra 1 jogador do elenco — foco do CT,
    atributos beneficiados, fase de carreira e expectativa de evolução."""
    p = conn.execute("SELECT id, name, age, position, overall, potential "
                     "FROM players WHERE id=?", (player_id,)).fetchone()
    if not p:
        return None
    age = p["age"] or 25
    factor = _growth_factor(age)
    phase, phase_desc = _phase(age)
    focus = career["training_focus"] or "geral"
    level = career["training_level"] or 2
    biased = TRAINING_FOCUS_ATTRS.get(focus, tuple(ATTR_COLS))
    boosted = [ATTR_LABELS[a] for a in biased if a in ATTR_LABELS][:4]

    gap = max(0, (p["potential"] or p["overall"] or 60) - (p["overall"] or 60))
    if factor > 0 and gap > 0:
        trend = "subindo"
        text = (f"Foco em {FOCUS_LABELS.get(focus, focus)} — {p['name']} ({age}, {phase_desc}) "
                f"deve evoluir {', '.join(boosted[:2]) if focus != 'geral' else 'atributos gerais'} "
                f"esta temporada (margem até o potencial: {gap} pts).")
    elif factor > 0 and gap <= 0:
        trend = "estavel"
        text = (f"{p['name']} ({age}) já está perto do teto de potencial — "
                f"ganhos adicionais de treino devem ser pequenos.")
    elif factor == 0:
        trend = "estavel"
        text = (f"{p['name']} ({age}) está no auge — treino mantém forma e atributos, "
                f"sem grandes saltos de evolução.")
    else:
        trend = "caindo"
        text = (f"{p['name']} ({age}, {phase_desc}) — espere queda natural de atributos "
                f"físicos com a idade; treino de nível {level} ajuda a reduzir o ritmo.")

    return {
        "phase": phase, "phase_label": phase_desc, "trend": trend,
        "focus": focus, "focus_label": FOCUS_LABELS.get(focus, focus),
        "level": level, "boosted_attrs": boosted, "potential_gap": gap,
        "text": text,
    }
