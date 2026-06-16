# ⚽ FutManager

Gerenciador de futebol por temporadas no estilo **Brasfoot / Elifoot**, em Python puro.
Você é o **técnico**: monta o elenco, escala, negocia no mercado, assiste aos jogos,
administra as finanças do estádio e sobrevive à pressão do conselho — temporada após temporada.

> **Nomes de jogadores são fictícios** (gerados aleatoriamente). Estrutura de ligas e clubes
> baseada em dados abertos do [OpenFootball](https://github.com/openfootball) (CC0).

## Destaques

- **Frontend web principal** — interface mais bonita e moderna, roda no navegador padrão.
- **GUI compacta offline** (Tkinter) — fallback leve para uso sem browser.
- **Modo terminal** (`--cli`) — controle total via texto.
- **Zero dependências em runtime** — só a stdlib do Python. Empacota como `.app` macOS (~11 MB).
- **Modo carreira completo:**
  - Evolução/regressão por idade (cresce até ~27, estabiliza, decai após 32), aposentadorias e *newgens*
  - Mercado de transferências com negociação, contraproposta, cláusula de rescisão, vendas e empréstimos
  - Finanças: patrocínio, bilheteria (preço do ingresso afeta o público), premiações, salários, multas
  - Reputação do técnico: campanha vs. expectativa do conselho → pode ser demitido (e recontratado por outro clube)
  - Escalação com formações e estilo tático (ofensivo / equilibrado / defensivo) + Centro de Treinamento
  - Calendário brasileiro: estaduais (formato Paulistão), Séries A/B/C/D, Copa do Brasil, Libertadores e Sul-Americana — tudo intercalado
  - Múltiplos *saves* (um mundo independente por jogo)

## Rodar

```bash
python3 main.py          # web principal (sobe servidor + abre navegador)
python3 main.py --gui    # GUI compacta (Tkinter) - fallback offline
python3 main.py --cli    # modo terminal
python3 main.py --web    # servidor web (sem auto-abrir browser)
```

Ou use os scripts prontos:

```bash
bash jogar.sh      # web principal
bash jogar_gui.sh  # GUI compacta
```

A database inicial já vem pronta em `data/futmanager.db`.

## Empacotar `.app` (macOS)

```bash
python3 -m pip install pyinstaller
bash scripts/build_app.sh        # gera dist/FutManager.app
open dist/FutManager.app
```

## Arquitetura

Toda a lógica de jogo vive em **`gameapi.py`** — funções I/O-free que recebem uma conexão
SQLite e devolvem dicts. A GUI (`gui/app.py`) e o web (`web/server.py`) são apenas camadas
de apresentação sobre essa mesma API. Fonte única de verdade.

```
gameapi.py        camada de jogo (estado, jogar, escalação, mercado, estádio)
engine/           simulação, temporada, carreira, finanças, copas, estaduais, mercado
db/               models + migração de schema
gui/app.py        GUI Tkinter original (mantida para compatibilidade)
gui/compact.py    GUI Tkinter compacta (fallback offline)
web/              frontend web principal (modo padrão)
launch_web.py     launcher: sobe servidor + abre navegador
scripts/          pipeline de database (rebuild, geração de elencos, anonimização)
```

## Reconstruir a database

```bash
bash scripts/rebuild_db.sh        # clona OpenFootball, gera elencos, monta o mundo
python3 scripts/anonymize_players.py   # garante nomes fictícios
```

Detalhes completos no [MANUAL.md](MANUAL.md).

---

Licença do código: MIT. Estrutura de ligas/clubes: OpenFootball (CC0).
