#!/bin/bash
# FUTMANAGER — Full DB Rebuild Pipeline
# Reconstrói a database do zero, reprodutível. Pristina, pronta para carreira.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY=python3

echo "🔄 Rebuild completo da database..."
echo ""

# 0. Remove DB antiga
rm -f data/futmanager.db data/futmanager.db-wal data/futmanager.db-shm

# 1. Importa estrutura + partidas (OpenFootball, 9 ligas)
echo "[1/5] OpenFootball (ligas, clubes, partidas)..."
$PY scripts/import_openfootball.py --all --season 2026

# 2. Prestígio dos clubes
echo ""
echo "[2/5] Prestígio dos clubes..."
$PY scripts/set_prestige.py
# Clubes de divisões inferiores (level>=2) sem prestígio definido → mais baixo
$PY -c "
import sqlite3
c=sqlite3.connect('data/futmanager.db')
c.execute('''UPDATE clubs SET prestige=50 WHERE prestige=60 AND league_id IN
  (SELECT id FROM leagues WHERE level>=2)''')
c.commit(); print('  ✓ prestígio divisões inferiores')
"

# 3. Top players reais (seed)
echo ""
echo "[3/5] Top players (seed)..."
$PY scripts/seed_top_players.py | tail -2

# 4. Merge FC26 sofifa CSV (se existir)
echo ""
echo "[4/6] FC26 sofifa CSV..."
if [ -f data/sources/fc26_players.csv ]; then
    $PY data/update.py --skip-openfootball --skip-top-seed 2>&1 | grep -E "FC26|generated" || true
else
    echo "  ⚠ fc26_players.csv ausente — pulando"
fi

# 5. Completa elencos finos até 18 jogadores (gerados sintéticos)
echo ""
echo "[5/6] Completando elencos (mínimo 18)..."
$PY scripts/generate_squads.py --min 18

# 6. Migração de carreira (age, potential, career table) — SEM avançar temporada
echo ""
echo "[6/7] Schema de carreira..."
$PY db/migrate_career.py | tail -3

# 7. Brasil extra: Série C/D + estaduais (clubes reais) + estados
echo ""
echo "[7/7] Brasil: Séries C/D + estaduais..."
$PY scripts/add_brazil_extra.py
$PY scripts/generate_squads.py --min 18         # preenche os novos clubes
$PY db/migrate_career.py | tail -1               # age/valor/salário dos novos (idempotente)

echo ""
echo "✅ Rebuild completo."
$PY -c "
import sqlite3
c=sqlite3.connect('data/futmanager.db')
print('   Jogadores:', c.execute('SELECT COUNT(*) FROM players WHERE retired=0').fetchone()[0])
print('   Newgens:', c.execute('SELECT COUNT(*) FROM players WHERE is_newgen=1').fetchone()[0], '(deve ser 0)')
print('   Carreiras:', c.execute('SELECT COUNT(*) FROM career').fetchone()[0], '(deve ser 0)')
print('   Clubes:', c.execute('SELECT COUNT(*) FROM clubs').fetchone()[0])
"
