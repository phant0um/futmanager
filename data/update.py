"""
FUTMANAGER — Data Update Script
Orquestra atualização da database:
  1. Pull OpenFootball (estrutura + partidas)
  2. Merge FC25 Kaggle CSV (atributos dos jogadores)
  3. Gera atributos para jogadores sem match no FC25

Usage:
    python data/update.py
    python data/update.py --skip-kaggle   # só OpenFootball
    python data/update.py --kaggle-csv path/to/fc25.csv
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import math
import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "futmanager.db"

# Prestígio por clube (fallback se não tiver no DB)
# Liga top = 75, divisão inferior = 40-55
PRESTIGE_DEFAULT = 60


# ─── Merge FC25 Kaggle CSV ────────────────────────────────────────────────────

# Mapeamento: coluna Kaggle → atributo interno
FC25_COL_MAP = {
    "pace":           "pace",
    "skill_moves":    None,   # ignora
    "shooting":       "finishing",
    "passing":        "passing",
    "dribbling":      "technique",
    "defending":      "defending",
    "physic":         "strength",
    "gk_diving":      "goalkeeping",
    "gk_handling":    "goalkeeping",  # média com diving
    "gk_reflexes":    "goalkeeping",  # média com diving
    "mentality_vision": "mental",
    "power_stamina":  "stamina",
}

POS_MAP_FC25 = {
    "GK": "GK",
    "CB": "DF", "LB": "DF", "RB": "DF", "LWB": "DF", "RWB": "DF",
    "CDM": "MF", "CM": "MF", "CAM": "MF", "LM": "MF", "RM": "MF",
    "LW": "FW", "RW": "FW", "ST": "FW", "CF": "FW",
}


def merge_fc25(conn: sqlite3.Connection, csv_path: Path):
    """
    Merge FC25 (Kaggle) ou FC26 (sofifa scraper) CSV.
    Auto-detecta formato pelo header.
    """
    import unicodedata, re

    def normalize(s: str) -> str:
        s = unicodedata.normalize("NFD", s.lower())
        return "".join(c for c in s if unicodedata.category(c) != "Mn")

    # Posição sofifa → jogo
    POS_SOFIFA = {
        "GK":"GK",
        "CB":"DF","LB":"DF","RB":"DF","LWB":"DF","RWB":"DF",
        "CDM":"MF","CM":"MF","CAM":"MF","LM":"MF","RM":"MF",
        "LW":"FW","RW":"FW","ST":"FW","CF":"FW",
    }

    # Remove TODOS os códigos de posição do nome (podem estar no meio ou fim)
    _POS_CODES = re.compile(r'\s+(?:GK|CB|LB|RB|LWB|RWB|CDM|CM|CAM|LM|RM|LW|RW|ST|CF)(?=\s|$)')

    rows = conn.execute("SELECT id, name FROM players").fetchall()
    name_to_id = {normalize(r[1]): r[0] for r in rows}

    # Índice por sobrenome (última palavra) para fallback
    from collections import defaultdict
    lastname_to_ids: dict = defaultdict(list)
    for r in rows:
        parts = normalize(r[1]).split()
        if parts:
            lastname_to_ids[parts[-1]].append((r[0], normalize(r[1])))

    # ── Club fuzzy lookup ────────────────────────────────────────────────────
    CLUB_ALIASES = {
        "inter": "FC Internazionale Milano",
        "internazionale": "FC Internazionale Milano",
        "inter milan": "FC Internazionale Milano",
        "atletico mineiro": "CA Mineiro",
        "atletico-mg": "CA Mineiro",
        "benfica": "SL Benfica",
        "sporting": "Sporting CP",
        "porto": "FC Porto",
        "ajax": "AFC Ajax",
        "psv": "PSV Eindhoven",
        "feyenoord": "Feyenoord Rotterdam",
        "river plate": "Club Atlético River Plate",
        "boca juniors": "Club Atlético Boca Juniors",
        "flamengo": "CR Flamengo",
        "palmeiras": "SE Palmeiras",
        "gremio": "Grêmio FBPA",
        "vasco": "CR Vasco da Gama",
        "corinthians": "SC Corinthians Paulista",
        "sao paulo": "São Paulo FC",
    }
    all_clubs_db = conn.execute("SELECT id, name FROM clubs").fetchall()
    club_exact_n  = {normalize(r[1]): r[0] for r in all_clubs_db}
    # Token index for fuzzy fallback
    club_token_idx: dict = defaultdict(list)
    for r in all_clubs_db:
        for tok in normalize(r[1]).split():
            if len(tok) > 3:
                club_token_idx[tok].append(r[0])

    def find_club_id(raw: str) -> int | None:
        if not raw:
            return None
        n = normalize(raw)
        # 1. Alias manual
        if n in CLUB_ALIASES:
            n = normalize(CLUB_ALIASES[n])
        # 2. Exact
        if n in club_exact_n:
            return club_exact_n[n]
        # 3. Strip common suffixes/prefixes
        stripped = re.sub(r"\b(fc|cf|sc|ac|afc|fk|sk|de|del|the|1909|bv|sv)\b", "", n).strip()
        if stripped in club_exact_n:
            return club_exact_n[stripped]
        # 4. Token overlap
        tokens = set(stripped.split()) - {"", "fc", "cf", "sc"}
        best_id, best_score = None, 0.0
        seen: set = set()
        for tok in tokens:
            for cid in club_token_idx.get(tok, []):
                if cid in seen:
                    continue
                seen.add(cid)
                c_n = normalize(conn.execute("SELECT name FROM clubs WHERE id=?", (cid,)).fetchone()[0])
                c_tokens = set(c_n.split()) - {"", "fc", "cf", "sc"}
                score = len(tokens & c_tokens) / max(len(tokens | c_tokens), 1)
                if score > best_score:
                    best_score, best_id = score, cid
        return best_id if best_score >= 0.4 else None
    # ────────────────────────────────────────────────────────────────────────

    def get_int(row: dict, col: str, default: int = 50) -> int:
        try:
            return max(1, min(99, int(float(row.get(col) or default))))
        except (ValueError, TypeError):
            return default

    updated = 0
    inserted = 0

    seen_ids: set = set()  # dedup por sofifa_id (scraper paralelo gerou repetidos)

    with open(csv_path, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        is_fc26 = "sprint_speed" in headers  # FC26 scraper format

        for row in reader:
            # ── Dedup por sofifa_id ──
            if is_fc26:
                sid = (row.get("sofifa_id") or "").strip()
                if sid:
                    if sid in seen_ids:
                        continue
                    seen_ids.add(sid)

            # ── Descarta linhas malformadas (sem overall válido) ──
            if is_fc26:
                ovr_raw = (row.get("overall") or "").strip()
                if not ovr_raw.isdigit() or int(ovr_raw) < 40:
                    continue  # linha de scrape suja → pula

            # ── Nome ──────────────────────────────────────────
            if is_fc26:
                raw_name = row.get("short_name", "").strip()
                # Remove prefixo de número de camisa (ex: "25\xa0F. Stevanović")
                raw_name = re.sub(r"^\d+[\s\xa0]+", "", raw_name).strip()
                # Extrai primeiro código de posição encontrado (antes de remover)
                first_pos_m = _POS_CODES.search(raw_name)
                first_pos = first_pos_m.group(0).strip() if first_pos_m else ""
                # Remove TODOS os códigos de posição do nome
                name = _POS_CODES.sub("", raw_name).strip()
                # Junta posição extraída com a coluna player_positions
                all_pos = ((first_pos + " ") + row.get("player_positions","")).split()
            else:
                name = row.get("long_name") or row.get("short_name") or ""
                all_pos = row.get("player_positions","MF").replace(",", " ").split()

            # Normaliza posição → GK/DF/MF/FW
            pos = "MF"
            for p in all_pos:
                mapped = POS_SOFIFA.get(p.strip().upper())
                if mapped:
                    pos = mapped
                    break

            nationality = row.get("nationality_name", "") or row.get("nationality", "")

            # ── Atributos ─────────────────────────────────────
            if is_fc26:
                pace      = get_int(row, "sprint_speed")
                technique = get_int(row, "dribbling")
                strength  = get_int(row, "strength")
                # Finishing proxy: média de att_position + long_shots
                finishing = round((get_int(row,"att_position") + get_int(row,"long_shots")) / 2)
                passing   = get_int(row, "short_passing")
                defending = get_int(row, "standing_tackle")
                gk        = max(get_int(row,"gk_diving"), get_int(row,"gk_handling"), get_int(row,"gk_reflexes"))
                stamina   = get_int(row, "stamina")
                mental    = round((get_int(row,"reactions") + get_int(row,"vision") + get_int(row,"composure")) / 3)
                source    = "fc26_sofifa"
            else:
                pace      = get_int(row, "pace")
                finishing = get_int(row, "shooting")
                passing   = get_int(row, "passing")
                technique = get_int(row, "dribbling")
                defending = get_int(row, "defending")
                strength  = get_int(row, "physic")
                mental    = get_int(row, "mentality_vision", 50)
                stamina   = get_int(row, "power_stamina", 50)
                gk        = max(get_int(row,"gk_diving"), get_int(row,"gk_handling"), get_int(row,"gk_reflexes"))
                source    = "fc25_kaggle"

            overall = get_int(row, "overall")

            norm_name = normalize(name)
            if not norm_name:
                continue

            # Tenta match exato; depois por sobrenome se nome abreviado (ex: "K. Mbappe")
            pid_match = name_to_id.get(norm_name)
            if pid_match is None and is_fc26:
                parts = norm_name.split()
                # Nome abreviado: primeira parte é inicial (ex: "k." ou "w.")
                is_abbrev = len(parts) >= 2 and len(parts[0].replace(".","")) <= 2
                if is_abbrev:
                    last = parts[-1]
                    candidates = lastname_to_ids.get(last, [])
                    if len(candidates) == 1:
                        pid_match = candidates[0][0]
                    elif len(candidates) > 1:
                        # Disambigua pela inicial
                        initial = parts[0].rstrip(".").lower()
                        for cid, cname in candidates:
                            cparts = cname.split()
                            if cparts and cparts[0].startswith(initial):
                                pid_match = cid
                                break

            if pid_match is not None:
                pid = pid_match
                conn.execute("""
                    UPDATE players SET
                        pace=?, technique=?, strength=?, finishing=?,
                        passing=?, defending=?, goalkeeping=?, stamina=?,
                        mental=?, overall=?, source=?
                    WHERE id=? AND source != 'top_seed'
                """, (pace, technique, strength, finishing, passing,
                      defending, gk, stamina, mental, overall, source, pid))
                updated += 1
            else:
                club_id = find_club_id(row.get("club_name", ""))
                if club_id is None:
                    continue   # sem clube válido — descarta

                conn.execute("""
                    INSERT OR IGNORE INTO players(
                        name, position, nationality,
                        pace, technique, strength, finishing,
                        passing, defending, goalkeeping, stamina,
                        mental, overall, club_id, source
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (name, pos, nationality, pace, technique, strength,
                      finishing, passing, defending, gk, stamina, mental,
                      overall, club_id, source))
                inserted += 1

    conn.commit()
    label = "FC26" if is_fc26 else "FC25"
    print(f"  ✓ {label}: {updated} atualizados, {inserted} inseridos")


# ─── Gerador Algorítmico de Atributos ────────────────────────────────────────

def _age_curve(birth_date: str | None) -> float:
    """Multiplicador por idade. Pico ~26. Decaimento após 32."""
    if not birth_date:
        return 0.95
    try:
        year = int(birth_date[:4])
        age = 2026 - year
        if age < 17:   return 0.70
        if age < 21:   return 0.85
        if age < 24:   return 0.93
        if age < 28:   return 1.00
        if age < 32:   return 0.97
        if age < 36:   return 0.88
        return 0.75
    except (ValueError, IndexError):
        return 0.95


def generate_attributes(
    player_id: int,
    player_name: str,
    position: str,
    birth_date: str | None,
    club_prestige: int,
) -> dict:
    """
    Gera atributos deterministicamente via seed = hash do nome+id.
    Garante que mesmo jogador sempre terá os mesmos atributos.
    """
    seed = int(hashlib.md5(f"{player_id}:{player_name}".encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)

    base = club_prestige  # 1–100 → base de rating
    curve = _age_curve(birth_date)

    def attr(center: int, spread: int = 12) -> int:
        raw = center + rng.randint(-spread, spread)
        return max(1, min(99, round(raw * curve)))

    pos_profiles = {
        "GK": {
            "goalkeeping": attr(base + 5, 10),
            "defending":   attr(base - 10, 8),
            "strength":    attr(base - 5, 8),
            "mental":      attr(base, 10),
            "pace":        attr(base - 20, 8),
            "technique":   attr(base - 15, 8),
            "finishing":   attr(20, 8),
            "passing":     attr(base - 10, 8),
            "stamina":     attr(base - 5, 8),
        },
        "DF": {
            "defending":   attr(base + 8, 10),
            "strength":    attr(base + 5, 8),
            "mental":      attr(base, 10),
            "pace":        attr(base - 5, 12),
            "passing":     attr(base - 8, 10),
            "technique":   attr(base - 15, 8),
            "finishing":   attr(base - 20, 8),
            "stamina":     attr(base, 8),
            "goalkeeping": attr(20, 5),
        },
        "MF": {
            "passing":     attr(base + 8, 10),
            "technique":   attr(base + 5, 10),
            "mental":      attr(base + 5, 8),
            "stamina":     attr(base + 5, 8),
            "defending":   attr(base - 5, 10),
            "pace":        attr(base, 12),
            "finishing":   attr(base - 5, 10),
            "strength":    attr(base - 5, 8),
            "goalkeeping": attr(20, 5),
        },
        "FW": {
            "finishing":   attr(base + 10, 10),
            "pace":        attr(base + 8, 12),
            "technique":   attr(base + 5, 10),
            "strength":    attr(base, 8),
            "mental":      attr(base, 8),
            "passing":     attr(base - 5, 10),
            "defending":   attr(base - 15, 8),
            "stamina":     attr(base - 5, 8),
            "goalkeeping": attr(20, 5),
        },
    }

    attrs = pos_profiles.get(position, pos_profiles["MF"])

    import sys as _sys; _sys.path.insert(0, str(ROOT))
    from db.models import Player
    overall = Player.calc_overall(position, attrs)
    attrs["overall"] = overall
    return attrs


def fill_missing_attributes(conn: sqlite3.Connection):
    """Gera atributos para jogadores que ainda não têm (source='openfootball' ou 'generated')."""
    players = conn.execute("""
        SELECT p.id, p.name, p.position, p.birth_date, p.source,
               COALESCE(c.prestige, 60) as prestige
        FROM players p
        LEFT JOIN clubs c ON c.id = p.club_id
        WHERE p.source != 'fc25_kaggle' AND p.overall = 50
    """).fetchall()

    updated = 0
    for pid, name, pos, dob, source, prestige in players:
        attrs = generate_attributes(pid, name, pos or "MF", dob, prestige)
        conn.execute("""
            UPDATE players SET
                pace=?, technique=?, strength=?, finishing=?,
                passing=?, defending=?, goalkeeping=?, stamina=?,
                mental=?, overall=?, source='generated'
            WHERE id=?
        """, (
            attrs["pace"], attrs["technique"], attrs["strength"], attrs["finishing"],
            attrs["passing"], attrs["defending"], attrs["goalkeeping"], attrs["stamina"],
            attrs["mental"], attrs["overall"], pid,
        ))
        updated += 1

    conn.commit()
    print(f"  ✓ generated: {updated} jogadores com atributos gerados")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FUTMANAGER DB Updater")
    parser.add_argument("--skip-openfootball", action="store_true")
    parser.add_argument("--skip-kaggle", action="store_true")
    parser.add_argument("--skip-top-seed", action="store_true")
    parser.add_argument("--kaggle-csv", type=Path, default=ROOT / "data" / "sources" / "fc26_players.csv")
    parser.add_argument("--season", default="2026")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)

    if not args.skip_openfootball:
        print("\n[1/4] OpenFootball...")
        import subprocess, sys
        cmd = [sys.executable, str(ROOT / "scripts" / "import_openfootball.py"),
               "--all", "--season", args.season]
        subprocess.run(cmd, check=True)
        # Gera elencos para novos clubes
        print("\n[2/4] Gerando elencos...")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_squads.py")], check=True)

    if not args.skip_kaggle and args.kaggle_csv.exists():
        print("\n[3/4] FC25 Kaggle CSV...")
        merge_fc25(conn, args.kaggle_csv)
    else:
        if not args.skip_kaggle:
            print(f"\n[3/4] FC25 CSV não encontrado — pulando.")

    if not args.skip_top_seed:
        print("\n[4/4] Top players seed...")
        import subprocess, sys
        subprocess.run([sys.executable, str(ROOT / "scripts" / "seed_top_players.py")], check=True)

    print("\nGerando atributos faltantes...")
    fill_missing_attributes(conn)

    conn.close()
    print("\n✅ Database atualizada.")


if __name__ == "__main__":
    main()
