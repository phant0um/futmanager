"""
FUTMANAGER — Top Players Seeder
Inserts ~400 real top players with approximate FC25/26 attributes.
Ratings based on public EA FC 25 data.
Format: (name, position, nationality, club_name, age, pace, technique,
          strength, finishing, passing, defending, goalkeeping, stamina, mental, overall)
"""
from __future__ import annotations
import sqlite3
import hashlib
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "futmanager.db"

# ─── TOP PLAYERS ─────────────────────────────────────────────────────────────
# (name, pos, nat, club, age, pac, tec, str, fin, pas, def, gk, sta, men, ovr)

TOP_PLAYERS = [
    # ── PREMIER LEAGUE ───────────────────────────────────────────────────────
    # Arsenal
    ("Bukayo Saka",          "FW","EN","Arsenal FC",           23, 88,89,72,83,85,52,10,85,86, 90),
    ("Martin Ødegaard",      "MF","NO","Arsenal FC",           26, 74,93,67,79,93,65,10,82,93, 90),
    ("Declan Rice",          "MF","EN","Arsenal FC",           26, 75,79,85,65,84,88,10,90,87, 88),
    ("David Raya",           "GK","ES","Arsenal FC",           29, 62,68,76,15,70,20,88,78,85, 87),
    ("Gabriel Magalhães",    "DF","BR","Arsenal FC",           27, 72,68,88,30,72,87,10,82,82, 85),
    ("William Saliba",       "DF","FR","Arsenal FC",           23, 80,72,86,28,74,88,10,85,83, 87),
    ("Kai Havertz",          "FW","DE","Arsenal FC",           25, 78,85,80,83,82,58,10,82,83, 85),
    ("Leandro Trossard",     "FW","BE","Arsenal FC",           30, 82,86,68,82,82,48,10,80,83, 84),
    ("Ben White",            "DF","EN","Arsenal FC",           27, 79,74,78,40,78,83,10,84,82, 84),
    ("Thomas Partey",        "MF","GH","Arsenal FC",           31, 72,77,87,60,80,80,10,84,83, 83),

    # Manchester City
    ("Erling Haaland",       "FW","NO","Manchester City FC",   24, 89,82,88,92,72,44,10,87,83, 91),
    ("Kevin De Bruyne",      "MF","BE","Manchester City FC",   33, 76,90,78,84,94,65,10,80,95, 91),
    ("Phil Foden",           "MF","EN","Manchester City FC",   24, 83,90,68,83,88,60,10,82,88, 89),
    ("Rúben Dias",           "DF","PT","Manchester City FC",   27, 73,73,88,25,76,91,10,84,89, 88),
    ("Rodri",                "MF","ES","Manchester City FC",   28, 72,83,87,72,88,90,10,87,93, 91),
    ("Bernardo Silva",       "MF","PT","Manchester City FC",   30, 80,90,68,78,90,65,10,84,90, 88),
    ("Manuel Akanji",        "DF","CH","Manchester City FC",   29, 78,72,87,28,74,88,10,84,82, 85),
    ("Ederson",              "GK","BR","Manchester City FC",   31, 70,72,80,15,80,20,90,80,87, 88),
    ("Josko Gvardiol",       "DF","HR","Manchester City FC",   23, 83,73,87,48,74,85,10,86,80, 85),

    # Liverpool
    ("Mohamed Salah",        "FW","EG","Liverpool FC",         32, 90,88,72,87,84,46,10,83,88, 90),
    ("Virgil van Dijk",      "DF","NL","Liverpool FC",         33, 78,76,93,35,82,91,10,83,90, 90),
    ("Alisson Becker",       "GK","BR","Liverpool FC",         32, 68,72,80,15,73,20,91,80,88, 90),
    ("Trent Alexander-Arnold","DF","EN","Liverpool FC",        26, 79,84,72,65,92,68,10,82,88, 88),
    ("Alexis Mac Allister",  "MF","AR","Liverpool FC",         26, 74,83,78,76,87,74,10,84,86, 86),
    ("Dominik Szoboszlai",   "MF","HU","Liverpool FC",         24, 80,85,77,78,85,65,10,83,84, 85),
    ("Cody Gakpo",           "FW","NL","Liverpool FC",         25, 84,84,78,81,78,54,10,82,80, 84),
    ("Darwin Núñez",         "FW","UY","Liverpool FC",         25, 93,78,83,80,72,48,10,86,74, 84),
    ("Andrew Robertson",     "DF","SC","Liverpool FC",         31, 84,77,75,52,82,74,10,87,83, 84),
    ("Ryan Gravenberch",     "MF","NL","Liverpool FC",         22, 77,79,82,68,82,72,10,83,80, 84),

    # Chelsea
    ("Cole Palmer",          "MF","EN","Chelsea FC",           22, 76,91,70,87,89,55,10,80,88, 89),
    ("Enzo Fernández",       "MF","AR","Chelsea FC",           24, 74,82,78,70,87,72,10,84,84, 85),
    ("Moisés Caicedo",       "MF","EC","Chelsea FC",           23, 78,77,84,60,82,83,10,86,80, 85),
    ("Reece James",          "DF","EN","Chelsea FC",           25, 83,80,80,62,82,80,10,83,82, 85),
    ("Nicolas Jackson",      "FW","SN","Chelsea FC",           23, 90,82,78,78,72,46,10,82,74, 82),
    ("Levi Colwill",         "DF","EN","Chelsea FC",           21, 77,73,84,28,76,85,10,82,80, 82),
    ("Robert Sánchez",       "GK","ES","Chelsea FC",           27, 65,67,78,15,68,20,85,76,80, 82),

    # Tottenham
    ("Son Heung-min",        "FW","KR","Tottenham Hotspur FC", 32, 88,88,72,84,82,52,10,83,86, 87),
    ("James Maddison",       "MF","EN","Tottenham Hotspur FC", 28, 72,90,67,78,90,58,10,78,88, 85),
    ("Pape Matar Sarr",      "MF","SN","Tottenham Hotspur FC", 22, 82,79,76,64,80,68,10,85,78, 82),
    ("Dejan Kulusevski",     "MF","SE","Tottenham Hotspur FC", 25, 84,84,75,75,82,60,10,83,80, 83),
    ("Cristian Romero",      "DF","AR","Tottenham Hotspur FC", 26, 78,72,88,32,72,88,10,84,82, 85),
    ("Guglielmo Vicario",    "GK","IT","Tottenham Hotspur FC", 28, 66,68,76,15,70,20,86,78,82, 84),

    # Manchester United
    ("Bruno Fernandes",      "MF","PT","Manchester United FC", 30, 74,88,72,78,92,60,10,80,90, 88),
    ("Marcus Rashford",      "FW","EN","Manchester United FC", 27, 92,83,76,80,76,48,10,83,76, 84),
    ("Rasmus Højlund",       "FW","DK","Manchester United FC", 22, 87,78,82,80,68,48,10,83,74, 82),
    ("André Onana",          "GK","CM","Manchester United FC", 28, 68,70,78,15,72,20,87,78,83, 85),
    ("Kobbie Mainoo",        "MF","EN","Manchester United FC", 19, 74,79,74,65,80,68,10,80,78, 80),
    ("Lisandro Martínez",    "DF","AR","Manchester United FC", 27, 72,72,87,30,74,89,10,83,85, 85),

    # Newcastle
    ("Alexander Isak",       "FW","SE","Newcastle United FC",  25, 88,85,78,85,78,52,10,84,80, 86),
    ("Bruno Guimarães",      "MF","BR","Newcastle United FC",  27, 76,83,83,72,87,78,10,87,85, 87),
    ("Nick Pope",            "GK","EN","Newcastle United FC",  32, 64,67,78,15,68,20,87,78,83, 85),
    ("Anthony Gordon",       "FW","EN","Newcastle United FC",  23, 88,84,72,78,78,50,10,83,78, 83),

    # Aston Villa
    ("Ollie Watkins",        "FW","EN","Aston Villa FC",       29, 88,83,78,84,74,50,10,86,80, 86),
    ("Youri Tielemans",      "MF","BE","Aston Villa FC",       27, 72,83,72,72,87,68,10,80,84, 83),
    ("Emi Martínez",         "GK","AR","Aston Villa FC",       32, 66,70,80,15,70,20,89,80,87, 88),
    ("Pau Torres",           "DF","ES","Aston Villa FC",       27, 73,75,84,28,80,86,10,82,84, 84),
    ("Douglas Luiz",         "MF","BR","Aston Villa FC",       27, 74,82,80,68,83,74,10,83,82, 83),

    # ── LA LIGA ──────────────────────────────────────────────────────────────
    # Real Madrid
    ("Kylian Mbappé",        "FW","FR","Real Madrid CF",       26, 97,90,76,92,83,38,10,88,88, 93),
    ("Vinícius Júnior",      "FW","BR","Real Madrid CF",       24, 95,89,74,84,80,36,10,86,83, 92),
    ("Jude Bellingham",      "MF","EN","Real Madrid CF",       21, 80,88,82,83,86,72,10,85,90, 90),
    ("Luka Modrić",          "MF","HR","Real Madrid CF",       39, 74,90,62,74,92,72,10,76,95, 87),
    ("Federico Valverde",    "MF","UY","Real Madrid CF",       26, 84,83,82,76,83,74,10,90,83, 87),
    ("Rodrygo Goes",         "FW","BR","Real Madrid CF",       24, 88,87,70,82,82,48,10,83,82, 86),
    ("Thibaut Courtois",     "GK","BE","Real Madrid CF",       32, 68,72,84,15,72,20,92,80,90, 92),
    ("Antonio Rüdiger",      "DF","DE","Real Madrid CF",       32, 80,70,92,32,72,90,10,83,84, 86),
    ("Éder Militão",         "DF","BR","Real Madrid CF",       27, 82,73,87,28,72,89,10,84,82, 86),
    ("David Alaba",          "DF","AT","Real Madrid CF",       32, 74,78,82,48,80,86,10,80,85, 83),
    ("Aurélien Tchouaméni",  "MF","FR","Real Madrid CF",       25, 78,78,87,62,80,84,10,86,80, 84),

    # Barcelona
    ("Robert Lewandowski",   "FW","PL","FC Barcelona",         37, 72,83,83,93,78,44,10,80,88, 88),
    ("Lamine Yamal",         "FW","ES","FC Barcelona",         17, 92,88,66,80,84,40,10,80,83, 86),
    ("Pedri",                "MF","ES","FC Barcelona",         23, 76,91,68,74,91,65,10,82,90, 88),
    ("Gavi",                 "MF","ES","FC Barcelona",         20, 74,86,70,68,88,68,10,84,88, 85),
    ("Frenkie de Jong",      "MF","NL","FC Barcelona",         27, 78,85,76,68,88,70,10,84,86, 86),
    ("Marc-André ter Stegen","GK","DE","FC Barcelona",         33, 66,72,78,15,74,20,90,78,88, 89),
    ("Raphinha",             "FW","BR","FC Barcelona",         28, 89,87,72,80,82,50,10,84,80, 86),
    ("Ronald Araújo",        "DF","UY","FC Barcelona",         25, 80,72,90,30,72,90,10,84,83, 86),
    ("Jules Koundé",         "DF","FR","FC Barcelona",         26, 82,76,83,38,78,86,10,82,82, 85),

    # Atlético de Madrid
    ("Antoine Griezmann",    "FW","FR","Atlético de Madrid",   34, 80,88,72,84,84,62,10,80,88, 86),
    ("Julián Álvarez",       "FW","AR","Atlético de Madrid",   25, 82,84,78,84,80,58,10,83,82, 86),
    ("Jan Oblak",            "GK","SI","Atlético de Madrid",   32, 58,68,82,15,70,20,91,78,88, 89),
    ("José María Giménez",   "DF","UY","Atlético de Madrid",   30, 76,70,87,30,72,88,10,82,82, 84),
    ("Marcos Llorente",      "MF","ES","Atlético de Madrid",   30, 82,79,78,68,82,72,10,85,80, 82),

    # Villarreal
    ("Yerlan Álex Baena",    "MF","ES","Villarreal CF",        23, 82,84,68,72,84,58,10,80,80, 81),

    # Athletic Club
    ("Nico Williams",        "FW","ES","Athletic Club",        22, 93,86,70,78,80,44,10,82,80, 84),
    ("Oihan Sancet",         "MF","ES","Athletic Club",        24, 76,83,74,78,82,62,10,80,80, 81),

    # ── SERIE A ──────────────────────────────────────────────────────────────
    # Inter Milan
    ("Lautaro Martínez",     "FW","AR","FC Internazionale Milano", 27, 82,86,82,88,78,52,10,84,84, 89),
    ("Nicolò Barella",       "MF","IT","FC Internazionale Milano", 28, 78,84,80,70,87,74,10,87,86, 87),
    ("Hakan Çalhanoğlu",     "MF","TR","FC Internazionale Milano", 30, 72,87,74,80,88,68,10,80,87, 86),
    ("Alessandro Bastoni",   "DF","IT","FC Internazionale Milano", 26, 74,76,84,30,82,86,10,82,84, 86),
    ("Yann Sommer",          "GK","CH","FC Internazionale Milano", 36, 60,68,75,15,70,20,88,74,87, 86),
    ("Marcus Thuram",        "FW","FR","FC Internazionale Milano", 27, 90,80,84,82,72,50,10,85,76, 84),
    ("Federico Dimarco",     "DF","IT","FC Internazionale Milano", 27, 80,76,74,60,80,78,10,82,78, 82),
    ("Benjamin Pavard",      "DF","FR","FC Internazionale Milano", 28, 78,74,82,38,76,84,10,82,80, 83),

    # Milan
    ("Rafael Leão",          "FW","PT","AC Milan",             25, 92,86,78,82,76,46,10,83,78, 87),
    ("Christian Pulisic",    "FW","US","AC Milan",             26, 86,86,72,80,82,54,10,81,80, 84),
    ("Mike Maignan",         "GK","FR","AC Milan",             29, 68,70,80,15,70,20,90,80,86, 88),
    ("Theo Hernández",       "DF","FR","AC Milan",             27, 88,78,78,60,78,72,10,85,76, 84),
    ("Tijjani Reijnders",    "MF","NL","AC Milan",             26, 78,82,76,70,84,70,10,83,80, 83),
    ("Alvaro Morata",        "FW","ES","AC Milan",             32, 80,78,80,80,74,52,10,80,78, 81),

    # Napoli
    ("Khvicha Kvaratskhelia", "FW","GE","SSC Napoli",          23, 88,90,72,82,82,46,10,83,82, 88),
    ("Victor Osimhen",       "FW","NG","SSC Napoli",           26, 91,78,86,88,68,48,10,87,74, 88),
    ("Giovanni Di Lorenzo",  "DF","IT","SSC Napoli",           31, 80,76,78,50,78,80,10,84,80, 82),
    ("Alex Meret",           "GK","IT","SSC Napoli",           27, 64,68,74,15,68,20,86,76,82, 83),
    ("Stanislav Lobotka",    "MF","SK","SSC Napoli",           30, 70,84,72,64,88,70,10,80,86, 84),

    # Juventus
    ("Dušan Vlahović",       "FW","RS","Juventus FC",          24, 79,80,84,90,72,48,10,82,76, 84),
    ("Kenan Yıldız",         "MF","TR","Juventus FC",          19, 82,86,68,76,82,52,10,78,78, 80),
    ("Federico Chiesa",      "FW","IT","Juventus FC",          27, 88,87,72,80,78,52,10,82,78, 83),
    ("Weston McKennie",      "MF","US","Juventus FC",          26, 80,76,82,66,76,70,10,86,74, 79),
    ("Gleison Bremer",       "DF","BR","Juventus FC",          27, 78,70,90,28,72,90,10,84,80, 84),

    # Roma
    ("Paulo Dybala",         "FW","AR","AS Roma",              31, 78,91,68,82,86,52,10,77,86, 85),
    ("Romelu Lukaku",        "FW","BE","AS Roma",              31, 80,72,92,84,68,46,10,82,74, 82),
    ("Lorenzo Pellegrini",   "MF","IT","AS Roma",              28, 74,84,74,74,87,66,10,80,83, 82),

    # Lazio
    ("Ciro Immobile",        "FW","IT","SS Lazio",             35, 78,80,74,84,72,44,10,78,80, 80),
    ("Mattia Zaccagni",      "FW","IT","SS Lazio",             29, 84,82,70,78,76,50,10,80,76, 80),
    ("Guido Rodríguez",      "MF","AR","SS Lazio",             30, 72,76,82,58,80,80,10,82,78, 79),

    # Atalanta
    ("Gianluca Scamacca",    "FW","IT","Atalanta BC",          25, 78,78,84,82,68,48,10,80,74, 81),
    ("Ademola Lookman",      "FW","NG","Atalanta BC",          27, 88,86,72,82,78,46,10,82,76, 83),
    ("Teun Koopmeiners",     "MF","NL","Atalanta BC",          26, 74,86,78,80,86,66,10,82,84, 85),
    ("Marten de Roon",       "MF","NL","Atalanta BC",          33, 70,75,82,58,80,80,10,82,78, 78),

    # Fiorentina
    ("Nicolás González",     "FW","AR","ACF Fiorentina",       26, 87,84,74,78,78,52,10,83,76, 81),
    ("Luca Ranieri",         "DF","IT","ACF Fiorentina",       24, 76,70,80,28,72,82,10,80,74, 76),

    # Bologna
    ("Jesper Lindström",     "FW","DK","Bologna FC 1909",      24, 86,82,70,74,76,48,10,80,74, 78),
    ("Remo Freuler",         "MF","CH","Bologna FC 1909",      32, 74,78,78,62,82,72,10,82,78, 78),

    # ── LIGUE 1 ──────────────────────────────────────────────────────────────
    # PSG
    ("Ousmane Dembélé",      "FW","FR","Paris Saint-Germain FC", 27, 95,90,70,82,80,44,10,82,78, 87),
    ("Achraf Hakimi",        "DF","MA","Paris Saint-Germain FC", 26, 91,82,76,62,83,74,10,87,80, 87),
    ("Marquinhos",           "DF","BR","Paris Saint-Germain FC", 30, 76,74,84,32,80,88,10,83,86, 87),
    ("Gianluigi Donnarumma", "GK","IT","Paris Saint-Germain FC", 26, 68,70,84,15,72,20,91,80,87, 90),
    ("Fabian Ruiz",          "MF","ES","Paris Saint-Germain FC", 28, 72,84,72,70,88,68,10,78,84, 83),
    ("Bradley Barcola",      "FW","FR","Paris Saint-Germain FC", 22, 90,84,70,78,76,44,10,80,74, 82),
    ("Vitinha",              "MF","PT","Paris Saint-Germain FC", 25, 74,88,68,70,88,62,10,80,86, 84),

    # Monaco
    ("Wissam Ben Yedder",    "FW","FR","AS Monaco FC",         34, 76,84,68,84,76,42,10,76,80, 80),
    ("Takumi Minamino",      "MF","JP","AS Monaco FC",         29, 83,82,70,74,80,56,10,83,76, 78),
    ("Aleksandr Golovin",    "MF","RU","AS Monaco FC",         28, 80,84,70,68,84,58,10,80,80, 80),

    # Lyon
    ("Alexandre Lacazette",  "FW","FR","Olympique Lyonnais",   33, 74,82,74,82,74,46,10,76,80, 80),
    ("Corentin Tolisso",     "MF","FR","Olympique Lyonnais",   30, 74,79,82,68,80,72,10,82,78, 78),

    # Marseille
    ("Pierre-Emerick Aubameyang","FW","GA","Olympique de Marseille", 35, 84,76,74,80,68,42,10,76,74, 78),
    ("Valentin Rongier",     "MF","FR","Olympique de Marseille", 30, 74,76,74,58,80,70,10,83,76, 76),

    # Lille
    ("Jonathan David",       "FW","CA","LOSC Lille",           24, 84,84,74,86,74,46,10,82,76, 84),
    ("Rémy Cabella",         "MF","FR","LOSC Lille",           34, 78,82,66,72,80,54,10,74,78, 76),

    # ── EREDIVISIE ───────────────────────────────────────────────────────────
    # Ajax
    ("Jordan Henderson",     "MF","EN","AFC Ajax",             34, 68,78,76,56,83,72,10,78,82, 77),
    ("Brian Brobbey",        "FW","NL","AFC Ajax",             23, 86,78,86,78,66,50,10,83,68, 78),
    ("Kenneth Taylor",       "MF","NL","AFC Ajax",             22, 76,80,72,64,80,64,10,80,74, 76),
    ("Devyne Rensch",        "DF","NL","AFC Ajax",             22, 83,76,72,50,76,76,10,83,74, 76),

    # PSV
    ("Luuk de Jong",         "FW","NL","PSV Eindhoven",        34, 72,72,82,80,66,50,10,78,74, 78),
    ("Johan Bakayoko",       "FW","BE","PSV Eindhoven",        22, 90,83,70,72,74,46,10,80,70, 78),
    ("Jerdy Schouten",       "MF","NL","PSV Eindhoven",        28, 72,78,80,62,83,72,10,83,78, 79),
    ("Walter Benítez",       "GK","AR","PSV Eindhoven",        32, 62,68,76,15,68,20,86,76,80, 83),
    ("Malik Tillman",        "MF","US","PSV Eindhoven",        23, 80,82,72,72,80,60,10,80,76, 79),

    # Feyenoord
    ("Santiago Giménez",     "FW","MX","Feyenoord Rotterdam",  23, 82,80,78,84,68,46,10,82,72, 81),
    ("Quinten Timber",       "MF","NL","Feyenoord Rotterdam",  23, 78,79,74,66,80,68,10,82,74, 77),
    ("Gernot Trauner",       "DF","AT","Feyenoord Rotterdam",  32, 72,70,82,28,74,82,10,80,76, 77),

    # ── PRIMEIRA LIGA ────────────────────────────────────────────────────────
    # Benfica
    ("Ángel Di María",       "FW","AR","SL Benfica",           36, 80,86,66,78,86,46,10,74,84, 81),
    ("Fredrik Aursnes",      "MF","NO","SL Benfica",           28, 80,77,76,62,78,74,10,85,74, 77),
    ("Jan Vertonghen",       "DF","BE","SL Benfica",           37, 66,74,82,28,76,84,10,74,82, 76),
    ("Orkun Kökçü",          "MF","NL","SL Benfica",           24, 75,83,72,68,85,62,10,78,80, 79),
    ("Vangelis Pavlidis",    "FW","GR","SL Benfica",           25, 80,78,80,82,68,48,10,80,72, 79),

    # Porto
    ("Evanilson",            "FW","BR","FC Porto",             25, 83,80,78,82,68,48,10,82,72, 80),
    ("Galeno",               "FW","BR","FC Porto",             26, 88,83,72,74,72,46,10,80,70, 78),
    ("Pepê Aquino",          "FW","BR","FC Porto",             27, 87,80,72,72,72,52,10,80,70, 77),
    ("Diogo Costa",          "GK","PT","FC Porto",             25, 66,70,76,15,70,20,88,76,82, 85),
    ("Alan Varela",          "MF","AR","FC Porto",             23, 74,76,80,60,80,74,10,82,74, 77),

    # Sporting CP
    ("Viktor Gyökeres",      "FW","SE","Sporting CP",          26, 84,80,86,90,70,50,10,86,76, 86),
    ("Pedro Gonçalves",      "MF","PT","Sporting CP",          26, 80,87,68,80,84,56,10,78,82, 83),
    ("Gonçalo Inácio",       "DF","PT","Sporting CP",          23, 74,74,82,28,78,84,10,80,78, 81),
    ("Morten Hjulmand",      "MF","DK","Sporting CP",          25, 74,78,82,58,82,76,10,84,76, 79),
    ("Ousmane Diomande",     "DF","CI","Sporting CP",          22, 80,72,86,28,72,86,10,82,74, 80),

    # ── BRASILEIRÃO ──────────────────────────────────────────────────────────
    # Flamengo
    ("Arrascaeta",           "MF","UY","CR Flamengo",          30, 78,90,68,80,88,58,10,78,86, 84),
    ("Pedro",                "FW","BR","CR Flamengo",          27, 78,82,80,88,72,46,10,78,76, 84),
    ("De La Cruz",           "MF","UY","CR Flamengo",          27, 78,87,68,72,88,60,10,78,82, 82),
    ("Gerson",               "MF","BR","CR Flamengo",          27, 78,82,82,68,83,72,10,83,78, 81),
    ("Everton Cebolinha",    "FW","BR","CR Flamengo",          28, 82,83,70,74,74,50,10,78,72, 78),
    ("Alex Sandro",          "DF","BR","CR Flamengo",          34, 78,72,76,48,76,72,10,78,72, 74),
    ("Léo Ortiz",            "DF","BR","CR Flamengo",          28, 76,70,86,28,72,86,10,82,76, 78),
    ("Rossi",                "GK","AR","CR Flamengo",          30, 62,66,76,15,68,20,85,74,78, 80),

    # Palmeiras
    ("Estêvão",              "FW","BR","SE Palmeiras",         17, 86,88,66,76,82,42,10,76,78, 80),
    ("Raphael Veiga",        "MF","BR","SE Palmeiras",         29, 72,86,68,80,86,56,10,76,82, 81),
    ("Gustavo Gómez",        "DF","PY","SE Palmeiras",         31, 72,70,88,30,72,88,10,82,82, 80),
    ("Weverton",             "GK","BR","SE Palmeiras",         37, 62,64,76,15,66,20,84,70,80, 78),
    ("Zé Rafael",            "MF","BR","SE Palmeiras",         32, 76,78,78,60,80,72,10,82,74, 76),
    ("Richard Ríos",         "MF","CO","SE Palmeiras",         24, 80,79,76,64,78,70,10,84,72, 77),
    ("Vanderlan",            "DF","BR","SE Palmeiras",         20, 82,72,74,40,72,76,10,82,66, 72),
    ("Flaco López",          "FW","AR","SE Palmeiras",         24, 80,76,78,80,68,48,10,78,68, 76),

    # Atlético-MG
    ("Hulk",                 "FW","BR","CA Mineiro",           38, 72,72,88,76,64,48,10,68,72, 74),
    ("Paulinho",             "FW","BR","CA Mineiro",           24, 84,78,82,78,66,50,10,82,68, 77),
    ("Rubens",               "FW","BR","CA Mineiro",           23, 88,78,74,70,68,46,10,80,64, 73),
    ("Guilherme Arana",      "DF","BR","CA Mineiro",           27, 82,74,72,48,74,72,10,82,70, 74),
    ("Igor Rabello",         "DF","BR","CA Mineiro",           28, 74,68,84,28,70,84,10,80,74, 74),
    ("Everson",              "GK","BR","CA Mineiro",           34, 60,64,76,15,64,20,82,72,76, 76),
    ("Battaglia",            "MF","AR","CA Mineiro",           29, 74,78,80,60,80,72,10,82,74, 76),
    ("Otávio",               "MF","BR","CA Mineiro",           29, 76,80,72,68,80,64,10,80,72, 75),

    # Botafogo
    ("Luiz Henrique",        "FW","BR","Botafogo FR",          23, 88,82,72,72,74,46,10,80,66, 76),
    ("Artur Jorge",          "MF","BR","Botafogo FR",          27, 76,78,74,62,78,64,10,78,72, 73),
    ("Thiago Almada",        "MF","AR","Botafogo FR",          23, 80,84,68,72,82,56,10,78,74, 77),
    ("Savarino",             "FW","VE","Botafogo FR",          24, 83,82,70,72,76,48,10,80,68, 75),
    ("Marlon Freitas",       "MF","BR","Botafogo FR",          28, 76,76,78,56,78,70,10,83,70, 73),
    ("John",                 "GK","BR","Botafogo FR",          24, 62,64,74,15,64,20,82,72,74, 76),
    ("Barboza",              "DF","UY","Botafogo FR",          24, 74,68,82,28,70,82,10,80,70, 73),

    # Internacional
    ("Alan Patrick",         "MF","BR","SC Internacional",     32, 72,84,68,76,82,58,10,72,80, 78),
    ("Valencia",             "FW","EC","SC Internacional",     26, 86,76,82,76,64,50,10,82,66, 75),
    ("Borré",                "FW","CO","SC Internacional",     29, 82,76,74,76,66,50,10,80,68, 74),
    ("Rochet",               "GK","UY","SC Internacional",     29, 64,66,76,15,66,20,84,74,76, 78),
    ("Thiago Maia",          "MF","BR","SC Internacional",     27, 74,76,78,56,78,72,10,82,68, 73),

    # Grêmio
    ("Soteldo",              "FW","VE","Grêmio FBPA",          27, 84,86,64,74,78,44,10,76,72, 76),
    ("Cristaldo",            "MF","AR","Grêmio FBPA",          27, 74,82,70,72,82,60,10,76,76, 75),
    ("Pepê",                 "FW","BR","Grêmio FBPA",          27, 86,80,70,72,72,50,10,80,66, 74),
    ("Du Queiroz",           "MF","BR","Grêmio FBPA",          24, 76,76,74,58,76,68,10,80,66, 71),
    ("Kannemann",            "DF","AR","Grêmio FBPA",          34, 70,68,84,28,70,82,10,74,76, 73),

    # São Paulo
    ("Calleri",              "FW","AR","São Paulo FC",         31, 74,74,80,80,66,48,10,74,70, 75),
    ("Lucas Moura",          "FW","BR","São Paulo FC",         32, 80,82,68,72,76,48,10,72,72, 73),
    ("Luciano",              "FW","BR","São Paulo FC",         29, 80,78,72,72,68,50,10,76,66, 71),
    ("Pablo Maia",           "MF","BR","São Paulo FC",         22, 76,76,74,56,78,68,10,80,68, 71),
    ("Arboleda",             "DF","EC","São Paulo FC",         32, 72,68,86,28,70,84,10,76,76, 73),

    # Fluminense
    ("Germán Cano",          "FW","AR","Fluminense FC",        36, 68,72,76,80,62,44,10,68,70, 73),
    ("Martinelli",           "MF","BR","Fluminense FC",        22, 80,80,72,64,78,64,10,80,68, 72),
    ("Ganso",                "MF","BR","Fluminense FC",        34, 62,84,60,64,86,52,10,60,82, 72),
    ("Fábio",                "GK","BR","Fluminense FC",        44, 58,62,72,15,62,20,80,60,80, 72),

    # Cruzeiro
    ("Gabigol",              "FW","BR","Cruzeiro EC",          28, 78,82,72,82,68,48,10,74,72, 78),
    ("Lucas Silva",          "MF","BR","Cruzeiro EC",          32, 72,74,78,54,76,70,10,78,70, 70),
    ("Anderson Varejão... Kaique Rocha","DF","BR","Cruzeiro EC", 22, 74,68,82,28,68,80,10,80,68, 71),

    # Corinthians
    ("Memphis Depay",        "FW","NL","SC Corinthians Paulista", 31, 82,84,74,80,78,50,10,76,78, 81),
    ("Yuri Alberto",         "FW","BR","SC Corinthians Paulista", 24, 84,78,78,80,68,46,10,82,72, 78),
    ("Rodrigo Garro",        "MF","AR","SC Corinthians Paulista", 27, 74,84,68,74,84,58,10,78,78, 79),
    ("André Carrillo",       "MF","PE","SC Corinthians Paulista", 33, 76,82,68,70,80,56,10,74,76, 77),
    ("Ángel Romero",         "FW","PY","SC Corinthians Paulista", 32, 78,78,72,76,74,50,10,76,72, 76),
    ("Hugo Souza",           "GK","BR","SC Corinthians Paulista", 26, 66,66,76,15,68,20,84,74,76, 79),
    ("Matheus Bidu",         "DF","BR","SC Corinthians Paulista", 25, 82,74,72,46,74,76,10,82,70, 75),
    ("Félix Torres",         "DF","EC","SC Corinthians Paulista", 27, 74,70,84,30,72,82,10,78,74, 76),
    ("Cacá",                 "DF","BR","SC Corinthians Paulista", 25, 72,68,82,28,70,80,10,78,72, 74),
    ("José Martínez",        "MF","VE","SC Corinthians Paulista", 30, 74,74,80,56,76,78,10,82,74, 76),
    ("Maycon",               "MF","BR","SC Corinthians Paulista", 28, 74,76,76,62,78,70,10,82,72, 75),
    ("Breno Bidon",          "MF","BR","SC Corinthians Paulista", 19, 74,76,72,58,76,66,10,80,68, 72),
    ("André Ramalho",        "DF","BR","SC Corinthians Paulista", 33, 72,68,84,28,70,82,10,76,74, 74),

    # RB Bragantino
    ("Cleiton",              "GK","BR","RB Bragantino", 28, 64,66,76,15,68,20,82,74,76, 78),
    ("Eduardo Sasha",        "FW","BR","RB Bragantino", 33, 74,74,80,78,68,48,10,76,70, 75),
    ("Vitinho",              "FW","BR","RB Bragantino", 26, 84,78,70,72,72,46,10,80,68, 74),
    ("Lucas Evangelista",    "MF","BR","RB Bragantino", 30, 72,80,70,68,82,62,10,80,74, 76),
    ("Jadsom Silva",         "MF","BR","RB Bragantino", 27, 74,74,78,58,76,72,10,82,70, 73),
    ("Pedro Henrique",       "DF","BR","RB Bragantino", 30, 70,68,82,28,70,80,10,78,72, 73),
    ("Juninho Capixaba",     "DF","BR","RB Bragantino", 28, 80,74,72,46,74,72,10,82,68, 72),
    ("Thiago Borbas",        "FW","UY","RB Bragantino", 23, 80,76,80,78,68,48,10,80,66, 74),
    ("Nathan Mendes",        "DF","BR","RB Bragantino", 22, 78,70,80,30,70,78,10,80,68, 71),
    ("Praxedes",             "MF","BR","RB Bragantino", 25, 74,78,72,64,78,64,10,80,70, 72),

    # CA Paranaense (Athletico-PR)
    ("Mycael",               "GK","BR","CA Paranaense", 21, 66,64,74,15,66,20,80,72,72, 74),
    ("Fernandinho",          "MF","BR","CA Paranaense", 40, 64,76,74,58,80,72,10,68,80, 74),
    ("Thiago Heleno",        "DF","BR","CA Paranaense", 36, 66,66,84,30,68,82,10,72,76, 74),
    ("Luiz Fernando",        "FW","BR","CA Paranaense", 28, 84,78,72,74,72,48,10,80,68, 73),
    ("Cuello",               "FW","AR","CA Paranaense", 24, 82,80,68,72,76,50,10,78,70, 74),
    ("Esquivel",             "DF","BR","CA Paranaense", 26, 80,72,72,44,74,74,10,80,68, 72),
    ("Felipinho",            "MF","BR","CA Paranaense", 24, 76,76,72,60,76,66,10,80,68, 71),
    ("Pablo",                "FW","BR","CA Paranaense", 33, 72,72,80,78,66,48,10,74,70, 73),
    ("Léo Godoy",            "DF","AR","CA Paranaense", 29, 80,72,74,42,74,74,10,82,68, 72),
    ("Erick",                "MF","BR","CA Paranaense", 27, 78,76,74,64,76,66,10,80,70, 72),

    # ── ARGENTINA ────────────────────────────────────────────────────────────
    # River
    ("Miguel Borja",         "FW","CO","Club Atlético River Plate", 32, 82,74,80,80,62,48,10,76,66, 76),
    ("Nacho Fernández",      "MF","AR","Club Atlético River Plate", 34, 70,82,66,68,84,56,10,68,80, 74),
    ("Enzo Díaz",            "DF","AR","Club Atlético River Plate", 28, 80,72,72,42,74,74,10,82,66, 72),
    ("Franco Armani",        "GK","AR","Club Atlético River Plate", 38, 58,62,74,15,64,20,82,66,80, 76),
    ("Pablo Solari",         "FW","AR","Club Atlético River Plate", 23, 86,78,70,68,70,46,10,80,62, 71),

    # Boca
    ("Edinson Cavani",       "FW","UY","Club Atlético Boca Juniors", 38, 72,74,76,80,66,44,10,66,72, 74),
    ("Sergio Romero",        "GK","AR","Club Atlético Boca Juniors", 37, 60,62,74,15,64,20,80,62,78, 73),
    ("Pol Fernández",        "MF","AR","Club Atlético Boca Juniors", 33, 74,78,72,60,78,66,10,76,72, 72),
    ("Cristian Medina",      "MF","AR","Club Atlético Boca Juniors", 22, 78,78,72,62,76,64,10,80,66, 72),

    # UCL wildcards (in case some aren't in league DBs)
    ("Harry Kane",           "FW","EN","Tottenham Hotspur FC", 31, 70,84,84,90,82,52,10,80,88, 90),
    ("Sadio Mané",           "FW","SN","FC Bayern München",    32, 88,83,76,78,76,52,10,82,74, 82),
    ("Robert Lewandowski",   "FW","PL","FC Barcelona",         36, 72,83,83,93,78,44,10,80,88, 88),
]

# ─── Import ───────────────────────────────────────────────────────────────────

def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    inserted = 0
    updated = 0
    skipped = 0

    for row in TOP_PLAYERS:
        if len(row) == 15:
            name, pos, nat, club_name, age, pac, tec, st, fin, pas, df, gk, sta, men, ovr = row
        else:
            print(f"  ⚠ linha inválida: {row}")
            continue

        birth_year = 2026 - age
        birth_date = f"{birth_year}-07-01"
        pid = int(hashlib.md5(f"top:{name}:{club_name}".encode()).hexdigest(), 16) % 9_999_999

        # Encontra clube
        club_row = conn.execute(
            "SELECT id FROM clubs WHERE name=?", (club_name,)
        ).fetchone()
        if not club_row:
            # Busca fuzzy
            club_row = conn.execute(
                "SELECT id FROM clubs WHERE name LIKE ?", (f"%{club_name[:10]}%",)
            ).fetchone()
        club_id = club_row["id"] if club_row else None

        if conn.execute("SELECT id FROM players WHERE id=?", (pid,)).fetchone():
            # Update se já existe
            conn.execute("""
                UPDATE players SET
                    name=?, position=?, nationality=?, birth_date=?, club_id=?,
                    pace=?, technique=?, strength=?, finishing=?,
                    passing=?, defending=?, goalkeeping=?, stamina=?,
                    mental=?, overall=?, source='top_seed'
                WHERE id=?
            """, (name, pos, nat, birth_date, club_id,
                  pac, tec, st, fin, pas, df, gk, sta, men, ovr, pid))
            updated += 1
        else:
            conn.execute("""
                INSERT INTO players(
                    id, name, position, nationality, birth_date, club_id,
                    pace, technique, strength, finishing, passing,
                    defending, goalkeeping, stamina, mental, overall, source
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'top_seed')
            """, (pid, name, pos, nat, birth_date, club_id,
                  pac, tec, st, fin, pas, df, gk, sta, men, ovr))
            inserted += 1

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM players WHERE source='top_seed'").fetchone()[0]
    print(f"  ✓ top players: {inserted} inseridos, {updated} atualizados")
    print(f"  ✓ total top_seed na DB: {total}")

    # Mostra distribuição por liga
    print()
    rows = conn.execute("""
        SELECT l.name, COUNT(p.id) as n, ROUND(AVG(p.overall),1) as avg
        FROM players p
        JOIN clubs c ON c.id=p.club_id
        JOIN leagues l ON l.id=c.league_id
        WHERE p.source='top_seed'
        GROUP BY l.id ORDER BY n DESC
    """).fetchall()
    for r in rows:
        print(f"  {r['name']:<30} {r['n']:>3} jogadores  avg={r['avg']}")

    conn.close()


if __name__ == "__main__":
    run()
