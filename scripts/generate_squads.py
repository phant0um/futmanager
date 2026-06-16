"""
FUTMANAGER — Squad Generator
Gera elencos com atributos para todos os clubes sem jogadores.
"""
from __future__ import annotations
import hashlib
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
DB_PATH = ROOT / "data" / "futmanager.db"

from db.models import Player
from data.update import generate_attributes

# Interleaved: qualquer prefixo tem spread posicional decente.
# 21 jogadores: 2 GK, 6 DF, 7 MF, 6 FW. GK primeiro garante goleiro em fills pequenos.
SQUAD_TEMPLATE = [
    "GK", "DF", "MF", "FW", "DF", "MF", "FW",
    "DF", "MF", "FW", "DF", "MF", "FW", "GK",
    "DF", "MF", "FW", "DF", "MF", "FW", "MF",
]

# Nomes genéricos por país (seed para variação cultural)
NAMES_BY_COUNTRY = {
    "BR": ["Carlos","Lucas","Gabriel","Felipe","João","Rodrigo","Diego","André","Rafael",
           "Thiago","Leandro","Fernando","Bruno","Gustavo","Mateus","Eduardo","Leonardo",
           "Pedro","Paulo","Victor","Alex","Daniel","Hugo","Igor","Kauan","Luan","Murilo",
           "Natan","Otávio","Pablo","Renato","Sávio","Tiago","Artur","Caio","Danilo","Enzo",
           "Fabrício","Guilherme","Henrique","Vitor","Willian","Yago","Zé Luis","Allan"],
    "EN": ["James","John","Michael","David","Chris","Daniel","Ryan","Tom","Jack","Harry",
           "Oliver","George","Lewis","Charlie","Jake","Luke","Josh","Adam","Sam","Ben",
           "William","Robert","Joseph","Aaron","Nathan","Jordan","Kyle","Scott","Dean","Owen"],
    "ES": ["Carlos","Alejandro","Sergio","Javier","Pablo","Miguel","Antonio","David","Luis",
           "Jorge","Marcos","Raúl","Iván","Fernando","Diego","Álvaro","Adrián","Rubén",
           "Víctor","Jesús","Alberto","Roberto","Gonzalo","Emilio","Borja","Dani","Koke"],
    "DE": ["Maximilian","Lukas","Jonas","Felix","Leon","Niklas","Tim","Jan","Fabian","Tobias",
           "Florian","Stefan","Thomas","Marco","Patrick","Bastian","Sven","Lars","Kevin","Marc"],
    "IT": ["Marco","Andrea","Luca","Matteo","Giovanni","Francesco","Lorenzo","Alessandro",
           "Simone","Davide","Filippo","Riccardo","Nicola","Federico","Stefano","Emiliano"],
    "FR": ["Antoine","Kylian","Paul","Benjamin","Lucas","Thomas","Hugo","Raphaël","Adrien",
           "Clément","Théo","Ousmane","Moussa","Karim","Kingsley","Marcus","Axel","Ferland"],
    "PT": ["João","Rúben","Bruno","Bernardo","Vitinha","Gonçalo","Diogo","Rafa","Pedro","Nuno"],
    "NL": ["Virgil","Frenkie","Memphis","Daley","Stefan","Donyell","Denzel","Cody","Xavi","Ryan"],
    "MX": ["Carlos","Eduardo","Guillermo","Andrés","Raúl","Javier","Diego","Hirving","Jesús","Edson"],
    "AR": ["Lionel","Angel","Rodrigo","Alejandro","Nicolás","Marcos","Paulo","Thiago","Lautaro","Julián"],
    "EU": ["Marco","James","Diego","Alexis","Neymar","Pedro","Karim","Antoine","Robert","Sadio"],
    "default": ["Alex","Bruno","Carlos","David","Emil","Franco","Gerard","Hugo","Ivan","Juan"],
}


def _get_names(country: str, n: int, seed: int) -> list[str]:
    pool = NAMES_BY_COUNTRY.get(country, NAMES_BY_COUNTRY["default"])
    rng = random.Random(seed)
    # Permite repetição se pool pequeno
    if n <= len(pool):
        return rng.sample(pool, n)
    return [rng.choice(pool) for _ in range(n)]


# Sobrenomes para dar unicidade aos gerados (evita "38 Neymar" no mundo)
LAST_NAMES = {
    "BR": ["Silva","Santos","Oliveira","Souza","Costa","Pereira","Lima","Almeida","Rocha","Ferreira","Gomes","Ribeiro","Carvalho","Araújo","Barbosa"],
    "EN": ["Smith","Jones","Taylor","Brown","Wilson","Walker","White","Hughes","Green","Hall","Clarke","Wright","Hill","Cooper","Ward"],
    "ES": ["García","Martínez","López","Sánchez","Pérez","Gómez","Ruiz","Torres","Romero","Navarro","Molina","Ortega","Castro","Vega"],
    "DE": ["Müller","Schmidt","Weber","Wagner","Becker","Hoffmann","Koch","Richter","Klein","Wolf","Schäfer","Braun","Krüger"],
    "IT": ["Rossi","Russo","Ferrari","Esposito","Bianchi","Romano","Greco","Conti","Marino","Gallo","Costa","Rizzo","Bruno"],
    "FR": ["Martin","Bernard","Dubois","Thomas","Robert","Petit","Durand","Leroy","Moreau","Simon","Laurent","Michel","Garcia"],
    "PT": ["Silva","Santos","Ferreira","Pereira","Costa","Carvalho","Sousa","Gomes","Lopes","Marques","Fernandes","Ribeiro"],
    "NL": ["Jansen","Visser","Bakker","Smit","Meijer","Mulder","Bos","Vos","Peters","Hendriks","Dijk","Berg"],
    "MX": ["Hernández","García","Martínez","López","González","Pérez","Rodríguez","Sánchez","Ramírez","Torres","Flores"],
    "AR": ["González","Rodríguez","Fernández","López","Martínez","Pérez","García","Díaz","Romero","Sosa","Álvarez","Acosta"],
    "EU": ["Silva","Smith","García","Rossi","Martin","Jansen","Costa","Müller","Santos","Torres"],
    "default": ["Silva","Smith","García","Rossi","Martin","Jansen","Costa","Müller","Santos","Torres"],
}


def _full_name(country: str, first: str, rng: random.Random) -> str:
    pool = LAST_NAMES.get(country, LAST_NAMES["default"])
    return f"{first} {rng.choice(pool)}"


def generate_squad(club_id: int, club_name: str, prestige: int, country: str) -> list[dict]:
    seed = int(hashlib.md5(f"squad:{club_id}:{club_name}".encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    names = _get_names(country, len(SQUAD_TEMPLATE), seed)

    players = []
    age_ranges = {"GK": (24, 36), "DF": (21, 34), "MF": (20, 32), "FW": (19, 30)}

    for i, (pos, first) in enumerate(zip(SQUAD_TEMPLATE, names)):
        pname = _full_name(country, first, rng)
        pid = int(hashlib.md5(f"{club_id}:{i}:{pname}".encode()).hexdigest(), 16) % 9_999_999
        age = rng.randint(*age_ranges[pos])
        birth_year = 2026 - age
        birth_date = f"{birth_year}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"

        attrs = generate_attributes(pid, pname, pos, birth_date, prestige)

        # Titulares (primeiros 11) com leve bônus
        bonus = 4 if i < 11 else 0
        overall = attrs["overall"] + bonus

        # Cap: gerados são PROFUNDIDADE de elenco, não estrelas.
        # Ficam abaixo dos jogadores reais (top_seed/fc26) do clube.
        cap = prestige - (4 if i < 11 else 10)
        attr_keys = ["pace","technique","strength","finishing","passing",
                     "defending","goalkeeping","stamina","mental"]
        if overall > cap:
            # Escala atributos pelo mesmo fator do overall reduzido
            scale = cap / max(overall, 1)
            for k in attr_keys:
                attrs[k] = max(20, round(attrs[k] * scale))
            overall = cap

        players.append({
            "id": pid,
            "name": pname,
            "position": pos,
            "nationality": country,
            "birth_date": birth_date,
            "club_id": club_id,
            "pace":        min(99, attrs["pace"]        + bonus),
            "technique":   min(99, attrs["technique"]   + bonus),
            "strength":    min(99, attrs["strength"]    + bonus),
            "finishing":   min(99, attrs["finishing"]   + bonus),
            "passing":     min(99, attrs["passing"]     + bonus),
            "defending":   min(99, attrs["defending"]   + bonus),
            "goalkeeping": min(99, attrs["goalkeeping"] + bonus),
            "stamina":     min(99, attrs["stamina"]     + bonus),
            "mental":      min(99, attrs["mental"]      + bonus),
            "overall":     min(99, overall),
            "potential":   min(99, overall + rng.randint(5, 20)),
            "source":      "generated",
            "star_player": 0,
            "minutes_played": 0,
            "fame": 0,
        })
    return players


def run(only_empty: bool = True, min_squad: int = 0):
    """
    Gera elencos para clubes.
    only_empty=True  → só clubes sem jogadores.
    min_squad>0      → completa qualquer clube até ter min_squad jogadores
                       (adiciona só o que falta, preservando os existentes).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Detecta se coluna 'retired' existe (pode rodar antes da migração de carreira)
    has_retired = any(r[1] == "retired" for r in conn.execute("PRAGMA table_info(players)").fetchall())
    count_filter = "AND COALESCE(p.retired,0)=0" if has_retired else ""

    clubs = conn.execute(f"""
        SELECT c.id, c.name, c.prestige, co.code as country,
               (SELECT COUNT(*) FROM players p WHERE p.club_id=c.id {count_filter}) as n
        FROM clubs c
        LEFT JOIN leagues l ON l.id = c.league_id
        LEFT JOIN countries co ON co.id = l.country_id
    """).fetchall()

    total = 0
    touched = 0
    for club in clubs:
        existing = club["n"]
        if min_squad > 0:
            need = max(0, min_squad - existing)
        elif only_empty:
            need = SQUAD_SIZE if existing == 0 else 0
        else:
            need = SQUAD_SIZE

        if need <= 0:
            continue
        touched += 1

        country = club["country"] or "default"
        squad = generate_squad(club["id"], club["name"], club["prestige"], country)
        # Adiciona só os 'need' jogadores faltantes (cobre todas as posições)
        for p in squad[:need]:
            conn.execute("""
                INSERT OR IGNORE INTO players(
                    id, name, position, nationality, birth_date, club_id,
                    pace, technique, strength, finishing, passing,
                    defending, goalkeeping, stamina, mental, overall, potential, source,
                    star_player, minutes_played, fame
                ) VALUES (:id,:name,:position,:nationality,:birth_date,:club_id,
                          :pace,:technique,:strength,:finishing,:passing,
                          :defending,:goalkeeping,:stamina,:mental,:overall,:potential,:source,
                          :star_player, :minutes_played, :fame)
            """, p)
            total += 1

    conn.commit()
    conn.close()
    print(f"  ✓ {total} jogadores gerados em {touched} clubes")


# Tamanho base de um elenco gerado
SQUAD_SIZE = len(SQUAD_TEMPLATE)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Regenera todos")
    parser.add_argument("--min", type=int, default=0, help="Completa clubes até N jogadores")
    args = parser.parse_args()
    run(only_empty=not args.all, min_squad=args.min)
