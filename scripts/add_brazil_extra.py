"""
FUTMANAGER — Brasil: Séries C/D + Estaduais
Adiciona ligas Série C e D (clubes reais, elencos gerados) e atribui o ESTADO
de cada clube brasileiro. Define os rosters dos estaduais (formato Paulistão:
16 clubes, 4 grupos, mata-mata).
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ─── Série C (20 clubes reais) ───────────────────────────────────────────────
SERIE_C = [
    ("ABC FC", "RN"), ("Athletic Club", "MG"), ("Botafogo-SP", "SP"),
    ("Brusque FC", "SC"), ("SER Caxias", "RS"), ("AD Confiança", "SE"),
    ("CSA", "AL"), ("AA Ferroviária", "SP"), ("Floresta EC", "CE"),
    ("Guarani FC", "SP"), ("Ituano FC", "SP"), ("Londrina EC", "PR"),
    ("Náutico", "PE"), ("São Bernardo FC", "SP"), ("Tombense FC", "MG"),
    ("Ypiranga FC", "RS"), ("São José-RS", "RS"), ("Figueirense FC", "SC"),
    ("Botafogo-PB", "PB"), ("Ferroviário CE", "CE"),
]

# ─── Série D (20 clubes reais) ───────────────────────────────────────────────
SERIE_D = [
    ("Anápolis FC", "GO"), ("Aparecidense", "GO"), ("Maringá FC", "PR"),
    ("Caxias do Sul... União Mogi", "SP"), ("Pouso Alegre FC", "MG"),
    ("Inter de Limeira", "SP"), ("Portuguesa Santista", "SP"),
    ("Rio Branco-AC", "AC"), ("Nova Iguaçu FC", "RJ"), ("Audax Rio", "RJ"),
    ("Sousa EC", "PB"), ("Treze FC", "PB"), ("Lagarto FC", "SE"),
    ("Real Noroeste", "ES"), ("Porto Velho EC", "RO"), ("Humaitá-AC", "AC"),
    ("Galvez EC", "AC"), ("São Raimundo-RR", "RR"), ("Trem-AP", "AP"),
    ("Manauara EC", "AM"),
]

# ─── Estado de clubes já existentes (Série A/B) ──────────────────────────────
STATE_MAP = {
    "CR Flamengo": "RJ", "Fluminense FC": "RJ", "CR Vasco da Gama": "RJ", "Botafogo FR": "RJ",
    "SE Palmeiras": "SP", "SC Corinthians Paulista": "SP", "São Paulo FC": "SP", "Santos FC": "SP",
    "RB Bragantino": "SP", "Mirassol FC": "SP",
    "CA Mineiro": "MG", "Cruzeiro EC": "MG",
    "Grêmio FBPA": "RS", "SC Internacional": "RS", "EC Juventude": "RS",
    "CA Paranaense": "PR", "Coritiba FBC": "PR",
    "EC Bahia": "BA", "EC Vitória": "BA",
    "SC Recife": "PE", "Sport Club do Recife": "PE",
    "Ceará SC": "CE", "Fortaleza EC": "CE",
    "Chapecoense AF": "SC",
    "Clube do Remo": "PA", "Paysandu SC": "PA",
    "Goiás EC": "GO", "Atlético Goianiense": "GO",
}

# ─── Estaduais: rosters por estado (formato Paulistão) ───────────────────────
# Mistura clubes do jogo + clubes "só estadual" (inseridos com generated)
ESTADUAIS = {
    "SP": ["SE Palmeiras", "SC Corinthians Paulista", "São Paulo FC", "Santos FC",
           "RB Bragantino", "Mirassol FC", "Guarani FC", "Ituano FC", "AA Ferroviária",
           "Botafogo-SP", "São Bernardo FC", "Portuguesa", "AA Ponte Preta",
           "Novorizontino", "EC Água Santa", "Inter de Limeira"],
    "RJ": ["CR Flamengo", "Fluminense FC", "CR Vasco da Gama", "Botafogo FR",
           "Nova Iguaçu FC", "Audax Rio", "Bangu AC", "Madureira EC",
           "Boavista SC", "Volta Redonda RJ", "Portuguesa-RJ", "Sampaio Corrêa-RJ"],
    "MG": ["CA Mineiro", "Cruzeiro EC", "América-MG", "Tombense FC", "Athletic Club",
           "Villa Nova AC", "Democrata GV", "Pouso Alegre FC", "Uberlândia EC", "Tupynambás"],
    "RS": ["Grêmio FBPA", "SC Internacional", "EC Juventude", "SER Caxias",
           "Ypiranga FC", "São José-RS", "GE Brasil de Pelotas", "Guarany de Bagé",
           "EC Pelotas", "Avenida FC"],
    "PR": ["CA Paranaense", "Coritiba FBC", "Londrina EC", "Maringá FC",
           "Operário-PR", "FC Cascavel", "Cianorte FC", "Azuriz FC"],
    "BA": ["EC Bahia", "EC Vitória", "Jacuipense", "Juazeirense",
           "Bahia de Feira", "Barcelona de Ilhéus"],
    "PE": ["SC Recife", "Náutico", "Santa Cruz FC", "Retrô FC", "Petrolina", "Central PE"],
    "CE": ["Ceará SC", "Fortaleza EC", "Floresta EC", "Ferroviário CE",
           "Maracanã CE", "Iguatu FC"],
    "GO": ["Goiás EC", "Atlético Goianiense", "Anápolis FC", "Aparecidense",
           "Vila Nova FC", "Goiânia EC"],
    "SC": ["Chapecoense AF", "Figueirense FC", "Brusque FC", "Avaí FC",
           "Criciúma EC", "Concórdia AC"],
    "PA": ["Clube do Remo", "Paysandu SC", "Águia de Marabá", "Tuna Luso",
           "Bragantino-PA", "Cametá SC"],
}


def _ensure_club(conn, name, state, league_id=None):
    row = conn.execute("SELECT id FROM clubs WHERE name=?", (name,)).fetchone()
    if row:
        conn.execute("UPDATE clubs SET state=? WHERE id=?", (state, row[0]))
        return row[0]
    cur = conn.execute(
        "INSERT INTO clubs(name, league_id, prestige, state) VALUES (?,?,?,?)",
        (name, league_id, 48, state))
    return cur.lastrowid


def _ensure_league(conn, name, level):
    row = conn.execute("SELECT id FROM leagues WHERE name=?", (name,)).fetchone()
    if row:
        return row[0]
    br = conn.execute("SELECT id FROM countries WHERE code='BR'").fetchone()
    br_id = br[0] if br else None
    cur = conn.execute(
        "INSERT INTO leagues(name, country_id, level, season) VALUES (?,?,?,?)",
        (name, br_id, level, "2026"))
    return cur.lastrowid


def run():
    from paths import db_path
    conn = sqlite3.connect(db_path())

    # Estado dos clubes existentes
    for name, st in STATE_MAP.items():
        conn.execute("UPDATE clubs SET state=? WHERE name=?", (st, name))

    # Série C
    lc = _ensure_league(conn, "Brasileirão Série C", 3)
    for name, st in SERIE_C:
        cid = _ensure_club(conn, name, st)
        conn.execute("UPDATE clubs SET league_id=?, prestige=COALESCE(NULLIF(prestige,0),45) WHERE id=?", (lc, cid))
    # Série D
    ld = _ensure_league(conn, "Brasileirão Série D", 4)
    for name, st in SERIE_D:
        cid = _ensure_club(conn, name, st)
        conn.execute("UPDATE clubs SET league_id=?, prestige=COALESCE(NULLIF(prestige,0),40) WHERE id=?", (ld, cid))

    # Clubes só-estadual (não estão em nenhuma divisão nacional)
    estadual_only = 0
    for st, clubs in ESTADUAIS.items():
        for name in clubs:
            row = conn.execute("SELECT id FROM clubs WHERE name=?", (name,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO clubs(name, league_id, prestige, state) VALUES (?,NULL,42,?)",
                    (name, st))
                estadual_only += 1
            else:
                conn.execute("UPDATE clubs SET state=? WHERE id=? AND state IS NULL", (st, row[0]))

    conn.commit()
    nc = conn.execute("SELECT COUNT(*) FROM clubs WHERE league_id=?", (lc,)).fetchone()[0]
    nd = conn.execute("SELECT COUNT(*) FROM clubs WHERE league_id=?", (ld,)).fetchone()[0]
    print(f"  ✓ Série C: {nc} clubes · Série D: {nd} clubes · estadual-only: +{estadual_only}")
    conn.close()


if __name__ == "__main__":
    run()
