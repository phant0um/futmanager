"""
FUTMANAGER — Anonimizador de nomes de jogadores.
Substitui TODO nome de jogador por um nome fictício (mantém atributos, idade,
clube, nacionalidade). Usa os pools de nomes por país de generate_squads.
Determinístico: mesmo id → mesmo nome fictício (reprodutível).

Uso:  python3 scripts/anonymize_players.py [caminho_db]
      (padrão: data/futmanager.db)
"""
from __future__ import annotations
import hashlib
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from scripts.generate_squads import NAMES_BY_COUNTRY, LAST_NAMES


def _fake_name(nat: str, pid: int) -> str:
    nat = nat if nat in NAMES_BY_COUNTRY else "default"
    rng = random.Random(int(hashlib.md5(f"anon:{pid}".encode()).hexdigest(), 16) % (2**32))
    first = rng.choice(NAMES_BY_COUNTRY[nat])
    last = rng.choice(LAST_NAMES.get(nat, LAST_NAMES["default"]))
    return f"{first} {last}"


def anonymize(db_path: Path) -> int:
    c = sqlite3.connect(db_path)
    rows = c.execute("SELECT id, nationality FROM players").fetchall()
    for pid, nat in rows:
        c.execute("UPDATE players SET name=? WHERE id=?",
                  (_fake_name(nat or "default", pid), pid))
    # zera fonte 'real' (sofifa/fc26) -> tudo vira gerado
    c.execute("UPDATE players SET source='generated' WHERE source IS NOT NULL")
    c.commit()
    n = len(rows)
    c.close()
    return n


if __name__ == "__main__":
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "futmanager.db"
    print(f"Anonimizando {db} ...")
    n = anonymize(db)
    print(f"✅ {n} jogadores renomeados com nomes fictícios.")
