"""
FUTMANAGER — Prestige Setter
Define prestígio (1-100) dos clubes conhecidos. Idempotente.
Clubes não listados mantêm o default (60).
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from paths import db_path

PRESTIGE = {
    # Brasileirão
    "CR Flamengo": 88, "SE Palmeiras": 87, "CA Mineiro": 83, "Botafogo FR": 81,
    "SC Internacional": 80, "Grêmio FBPA": 79, "SC Corinthians Paulista": 78,
    "São Paulo FC": 77, "Cruzeiro EC": 76, "CR Vasco da Gama": 74,
    "Fluminense FC": 74, "EC Bahia": 72, "Fortaleza EC": 72, "RB Bragantino": 70,
    "Santos FC": 70, "EC Vitória": 65, "SC Recife": 64, "Ceará SC": 63,
    "EC Juventude": 62, "Mirassol FC": 60, "Chapecoense AF": 58,
    "CA Paranaense": 68, "Coritiba FBC": 65, "Clube do Remo": 55,
    # Premier League
    "Manchester City FC": 96, "Arsenal FC": 93, "Liverpool FC": 94,
    "Chelsea FC": 90, "Manchester United FC": 88, "Tottenham Hotspur FC": 87,
    "Newcastle United FC": 84, "Aston Villa FC": 83, "Brighton & Hove Albion FC": 80,
    "West Ham United FC": 78, "Fulham FC": 75, "Brentford FC": 74,
    "Wolverhampton Wanderers FC": 73, "Everton FC": 72, "Crystal Palace FC": 71,
    "Nottingham Forest FC": 70, "AFC Bournemouth": 69, "Leicester City FC": 68,
    "Ipswich Town FC": 62, "Southampton FC": 60, "Leeds United FC": 68,
    "Sunderland AFC": 63, "Burnley FC": 62,
    # La Liga
    "FC Barcelona": 96, "Real Madrid CF": 97, "Atlético de Madrid": 90,
    "Sevilla FC": 83, "Real Sociedad": 82, "Villarreal CF": 81, "Athletic Club": 80,
    "Valencia CF": 79, "Real Betis Balompié": 78, "Getafe CF": 68,
    "Celta de Vigo": 70, "Girona FC": 72, "Rayo Vallecano": 67,
    # Serie A
    "FC Internazionale Milano": 92, "SSC Napoli": 89, "Juventus FC": 90,
    "AC Milan": 91, "AS Roma": 85, "SS Lazio": 83, "ACF Fiorentina": 80,
    "Atalanta BC": 84, "Bologna FC 1909": 78, "Torino FC": 74,
    # Ligue 1
    "Paris Saint-Germain FC": 95, "AS Monaco FC": 87, "Olympique Lyonnais": 84,
    "Olympique de Marseille": 85, "LOSC Lille": 83, "RC Lens": 79,
    "Stade Rennais FC": 78, "OGC Nice": 77,
    # Eredivisie
    "AFC Ajax": 88, "PSV Eindhoven": 89, "Feyenoord Rotterdam": 87,
    "AZ Alkmaar": 80, "FC Utrecht": 75, "FC Twente": 76,
    # Primeira Liga
    "SL Benfica": 88, "FC Porto": 89, "Sporting CP": 87, "SC Braga": 80,
    # Argentina
    "Club Atlético River Plate": 87, "Club Atlético Boca Juniors": 86,
    "Racing Club": 80, "Club Atlético Independiente": 78,
}


def run():
    conn = sqlite3.connect(db_path())
    updated = 0
    for name, p in PRESTIGE.items():
        r = conn.execute("UPDATE clubs SET prestige=? WHERE name=?", (p, name))
        updated += r.rowcount
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM clubs").fetchone()[0]
    print(f"  ✓ prestígio: {updated}/{total} clubes")
    conn.close()


if __name__ == "__main__":
    run()
