"""
FUTMANAGER — Conhecimento de jogadores (masking de atributos)
Atributos granulares (pace/technique/strength/finishing/passing/defending/
goalkeeping/stamina/mental) já existem no banco mas eram invisíveis na UI.
Esta camada decide O QUE o clube do jogador "enxerga" deles — sem alterar
os valores reais usados pela simulação (masking é só de exibição).

Regra:
- Seu elenco e jogadores publicamente listados (transfer/loan) → exato
  (você o vê todo dia / mercado expõe "raio-x" público).
- Resto → faixa, cuja largura encolhe com o prestígio do seu clube
  (rede de observação melhor) — ou totalmente oculto ("?").
- Determinístico via hash (career, player, attr): mesmo jogador sempre
  mostra a mesma faixa, sem RANDOM() do SQLite.

Scouting (próxima fase) sobrescreve isso com valor confirmado — grava em
scout_reports e passa a contar como "conhecido", igual elenco próprio.
"""
from __future__ import annotations
import hashlib
import random

ATTRS = ("pace", "technique", "strength", "finishing", "passing",
         "defending", "goalkeeping", "stamina", "mental")

ATTR_LABELS = {
    "pace": "Ritmo", "technique": "Técnica", "strength": "Força",
    "finishing": "Finalização", "passing": "Passe", "defending": "Defesa",
    "goalkeeping": "Goleiro", "stamina": "Disposição", "mental": "Mental",
}


def _rng(career_id: int, player_id: int, attr: str) -> random.Random:
    digest = hashlib.md5(f"knowledge:{career_id}:{player_id}:{attr}".encode()).digest()
    return random.Random(digest)


def known_attrs(attrs: dict, career_id: int, player_id: int, *,
                is_own: bool, is_listed: bool, prestige: int | None,
                confirmed: set[str] | None = None) -> dict:
    """attr → valor exato (int), faixa ('45-58') ou '?'.

    confirmed: atributos já revelados por scouting (futuro) — sempre exatos.
    """
    confirmed = confirmed or set()
    if is_own or is_listed:
        return {a: attrs.get(a) for a in ATTRS}

    prestige = prestige or 50
    hide_chance = max(0.05, 0.45 - prestige / 250)   # prestígio 80 → 13%; 30 → 33%
    band = max(4, 22 - prestige // 5)                # prestígio 80 → 6; 30 → 16

    out = {}
    for a in ATTRS:
        real = attrs.get(a)
        if a in confirmed or real is None:
            out[a] = real if real is not None else "?"
            continue
        rng = _rng(career_id, player_id, a)
        if rng.random() < hide_chance:
            out[a] = "?"
            continue
        jitter = rng.randint(-band // 2, band // 2)
        center = max(1, min(99, real + jitter))
        lo = max(1, center - band // 2)
        hi = min(99, center + band // 2)
        out[a] = f"{lo}-{hi}" if lo != hi else lo
    return out
