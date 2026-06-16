---
title: FUT BRASIL — Manual de Implantação e Funcionalidades
projeto: brasfoot (FUT BRASIL)
stack: Python 3.12+ · SQLite · PyInstaller
atualizado: 2026-06-03
---

# FUT BRASIL — Manual de Implantação e Funcionalidades

> Clone do Brasfoot/Elifoot: gerenciador de futebol por temporadas.
> Modo carreira: você é o **técnico**, gere o clube, escala, negocia,
> assiste aos jogos ao vivo, sobrevive à pressão do conselho.
> Zero dependências em runtime (só stdlib). **Frontend web principal**; GUI compacta Tkinter como fallback offline; empacota como `.app` macOS windowed.

---

## 1. Visão geral

| Item | Valor |
|------|-------|
| Linguagem | Python 3.12+ (testado 3.13) |
| Banco | SQLite (`data/brasfoot.db`, ~1MB) |
| Deps runtime | **nenhuma** (stdlib pura) |
| Deps build | `pyinstaller` |
| Tamanho `.app` | ~8MB |
| Dados | 9 ligas · 202 clubes · ~5.000 jogadores reais (FC26) |
| Interface | **Web local (padrão)** · GUI compacta (`--gui`) · CLI (`--cli`) · web sem auto-open (`--web`) |

---

## 2. Pré-requisitos

```bash
python3 --version        # 3.12 ou superior
git --version            # para baixar dados OpenFootball
```

- **Rodar**: só Python 3 (stdlib). Sem pip install.
- **Empacotar `.app`**: `python3 -m pip install pyinstaller`
- **Reconstruir database**: git (clona repos OpenFootball)
- **Atualizar jogadores**: CSV do sofifa.com (FC26) — opcional

---

## 3. Implantação (deployment)

### 3.1 Rodar direto (desenvolvimento)

```bash
cd /Users/michelcsasznik/Dev/projetos/brasfoot
python3 main.py            # web principal (sobe servidor + abre navegador)
./jogar.sh                 # atalho para web principal
python3 main.py --gui      # GUI compacta (Tkinter) — fallback offline
./jogar_gui.sh             # atalho para GUI compacta
python3 main.py --cli      # modo terminal
python3 main.py --web      # servidor web local (http://localhost:8765) sem auto-abrir
```

A database já vem pronta em `data/futmanager.db`. A interface web abre no navegador
padrão: tela de saves → novo/carregar → hub (Jogar · Elenco · Classificação · Escalação ·
Mercado · Estádio & CT). A GUI compacta oferece um subconjunto das ações para uso
offline/leve.

### 3.2 Empacotar como `.app` macOS (distribuição)

```bash
python3 -m pip install pyinstaller         # uma vez
bash scripts/build_app.sh                  # gera dist/FutManager.app (windowed)
open dist/FutManager.app                   # testa (abre janela GUI, sem terminal)
```

- O `.app` é **double-clicável**: abre a janela GUI nativa direto (PyInstaller `BUNDLE`).
- A DB inicial vai embutida; saves vão para `~/Library/Application Support/FutManager/`
  (DB do bundle nunca é alterada — cada jogador tem seu save isolado).
- **Não assinado**: em outro Mac, Gatekeeper bloqueia → botão direito → Abrir (1ª vez).

### 3.3 Reconstruir a database do zero (pipeline reprodutível)

```bash
bash scripts/rebuild_db.sh
```

Executa o pipeline completo (idempotente):
1. `import_openfootball.py --all` — clona 9 ligas (estrutura + partidas)
2. `set_prestige.py` — prestígio dos clubes conhecidos
3. `seed_top_players.py` — ~200 craques reais com atributos
4. `data/update.py` — merge do CSV FC26 (sofifa) se presente
5. `generate_squads.py --min 18` — completa elencos finos
6. `migrate_career.py` — schema de carreira + ages/valores/salários/estádios

Resultado: `data/brasfoot.db` pristina (sem carreira, sem newgens).

---

## 4. Estrutura do projeto

```
brasfoot/
├── main.py                  # entry point
├── paths.py                 # resolve caminhos dev vs bundle (DB gravável)
├── brasfoot.spec            # config PyInstaller
│
├── db/
│   ├── schema.sql           # schema base (clubes, jogadores, ligas, partidas)
│   ├── models.py            # dataclasses Club/Player/Standing/Match
│   └── migrate_career.py    # migração: carreira, técnicos, escalação, estádio
│
├── engine/                  # motor do jogo (lógica pura)
│   ├── simulation.py        # simulação de partida (Poisson, sem numpy; moral + estilo)
│   ├── season.py            # liga round-robin + moral dinâmica
│   ├── cup.py               # copas (mata-mata, pênaltis)
│   ├── live.py              # transmissão ao vivo (jogo + rodada)
│   ├── lineup.py            # formações + escalação + estilo tático
│   ├── career.py            # virada de temporada: idade, evolução, aposentadoria, newgens, treino
│   ├── transfer.py          # mercado: compra/venda/empréstimo, negociação, cláusula
│   ├── finance.py           # receita, folha, CT, multas, bilheteria
│   ├── manager.py           # reputação do técnico, job security
│   └── coach.py             # mercado de técnicos (IA + humano)
│
├── ui/
│   ├── cli.py               # menu principal, partida avulsa, ligas
│   └── career.py            # modo carreira completo (hub + telas)
│
├── scripts/
│   ├── rebuild_db.sh        # pipeline completo de reconstrução
│   ├── import_openfootball.py
│   ├── set_prestige.py
│   ├── seed_top_players.py
│   ├── generate_squads.py
│   └── build_app.sh         # empacota .app
│
└── data/
    ├── brasfoot.db          # database SQLite (embutida no .app)
    ├── update.py            # merge FC26 sofifa CSV + atributos gerados
    └── sources/             # repos OpenFootball + fc26_players.csv (não versionado)
```

---

## 5. Pipeline de dados

```
OpenFootball (git, CC0)  ──┐
  ligas, clubes, partidas  │
                           ├──► SQLite ──► jogo
FC26 sofifa (CSV scraper)  │
  24k jogadores + atributos│
                           │
Gerador algorítmico ───────┘
  preenche elencos finos
```

| Fonte | Fornece | Como |
|-------|---------|------|
| OpenFootball | Estrutura de ligas, clubes, partidas reais | `import_openfootball.py` (git clone) |
| FC26 sofifa | Nomes + atributos reais (~24k jogadores) | scraper JS no browser → `fc26_players.csv` |
| seed_top_players | ~200 craques com stats afinados à mão | `seed_top_players.py` |
| gerador | Profundidade de elenco (reservas) | `generate_squads.py` |

### Atualizar jogadores (nova temporada FC)

1. No sofifa.com (logado), rodar o scraper JS → baixar `fc26_players.csv`
2. Salvar em `data/sources/fc26_players.csv`
3. `python3 data/update.py --skip-openfootball --skip-top-seed`
4. `python3 db/migrate_career.py` (recalcula valores/salários)

---

## 6. Funções embutidas

### 6.1 Menu principal (`ui/cli.py`)

| # | Função |
|---|--------|
| 1 | **Modo Carreira** (núcleo do jogo) |
| 2 | Ver ligas disponíveis |
| 3 | Simular temporada avulsa |
| 4 | Simular partida rápida (com opção **assistir ao vivo**) |
| 5 | Ver classificação |
| 6 | Ver jogadores de um clube |
| 7 | Atualizar database (dev) |

### 6.2 Modo Carreira — hub (`ui/career.py`)

```
1 Ver elenco          5 🎟️  Estádio & CT
2 📋 Escalação         6 📊 Classificação
3 ▶️  Jogar temporada   7 🔍 Buscar time (elencos)
4 💰 Mercado           8 Scout · 9 Histórico
```

#### Escalação + tática (`engine/lineup.py`)
- 7 formações: 4-4-2, 4-3-3, 4-2-3-1, 3-5-2, 5-3-2, 3-4-3, 4-5-1
- Auto-monta melhor 11 por posição; troca titular ↔ reserva
- O 11 escalado define os ratings de ataque/defesa na simulação
- **Estilo tático** `[e]`:
  - Ofensivo (+12% ataque / −10% defesa) — mais gols pró e contra
  - Equilibrado — neutro
  - Defensivo (−14% ataque / +12% defesa) — trava o jogo contra times fortes

#### Jogar temporada (`engine/season.py` + `engine/live.py`)
- Round-robin ida e volta (38 rodadas / 20 clubes)
- **Assistir ao vivo**: transmissão da rodada inteira (~2min)
  - Feed de gols/cartões/contusões de todos os jogos, por minuto
  - Seu jogo com detalhe extra; placar consolidado + nome do estádio
  - `[Enter]` assistir · `[p]` só placares · `[s]` simular resto
- Resultado ao vivo alimenta a classificação
- **Copas** (após a liga) — `engine/cup.py`:
  - Copa Nacional (16 clubes da sua liga) + Copa Continental (16 melhores do mundo)
  - Mata-mata com pênaltis no empate; prêmio €, reputação, títulos
  - Sua campanha: Oitavas → Quartas → Semi → Final → CAMPEÃO 🏆

#### Estádio & CT (`engine/finance.py` + `engine/career.py`)
- **Ingresso**: editar preço → muda ocupação (curva de demanda) → muda bilheteria
- **Centro de Treinamento** (CT): nível 1-5, custo €2.5M×nível/ano
  - Nível >2 acelera a evolução do seu elenco; <2 economiza

#### Mercado de transferências (`engine/transfer.py`)
- **Comprar**: filtro por posição/preço; **negociação** (oferta → contraproposta → aceite)
- **Cláusula de rescisão**: pagar = compra forçada instantânea
- **Vender**: oferta de clube IA; vender **ídolo** (OVR≥82) custa reputação
- **Empréstimo IN**: sem taxa, propõe % do salário + taxa mensal; IA aceita se compensa
- **Empréstimo OUT**: libera salário; jogador volta após 1 temporada
- Limites de elenco: 16–32 jogadores

#### Estádio e ingressos (`engine/finance.py`)
- Editar preço do ingresso → muda ocupação (curva de demanda) → muda bilheteria
- Projeção ao vivo: ocupação % + público + receita anual
- Existe preço ótimo (caro = vazio, barato = cheio mas pouca grana)

#### Classificação / Buscar time (página de gestão)
- Classificação completa persistida (P/J/V/E/D/GP/GC/SG), zonas 🟢/🔴, ◀ você
- Buscar qualquer clube → técnico, estádio, elenco completo, valores

### 6.3 Economia (`engine/finance.py`)

Ao fim de cada temporada:

```
RECEITA = patrocínio/TV (prestígio) + bilheteria (preço×público)
          + premiação (posição) + bônus título + premiação de copas
DESPESA = folha salarial + CT + taxas de empréstimo + multas de expulsão
SALDO   = RECEITA − DESPESA  →  caixa
```

- Caixa negativo = aviso (precisa vender)
- Salários + CT limitam compras (folha alta = insustentável)
- Multa por cartão vermelho (4% do salário anual por expulsão)

### 6.4 Moral (`engine/season.py`)

- Cada clube tem **moral 0.85–1.15** que afeta o ataque
- Vitória sobe a moral, derrota desce; regride à média com o tempo
- Propaga entre rodadas — boa fase rende mais gols (e o inverso)

### 6.5 Virada de temporada (`engine/career.py`)

A entressafra processa o mundo inteiro:
1. **Envelhecimento**: todos +1 ano
2. **Evolução/regressão**: cresce até 27 (pico) → platô 28-31 → declina de 32
   (curva por idade × potencial; CT do clube dá bônus de evolução ao seu elenco)
3. **Aposentadorias**: por idade+posição (GK até 43, linha até 40)
4. **Newgens**: ~800/temporada no mundo, potencial enviesado (2% wonderkids POT 82-92)
5. **Contratos**: vencidos auto-renovam (IA); os seus você decide (renovar/liberar)
6. **Empréstimos**: vencidos retornam ao clube dono
7. **Valores de mercado** recalculados

### 6.6 Carreira do técnico (`engine/manager.py` + `engine/coach.py`)

- **Você é o técnico** (papel único, não há "gestor" separado)
- **Reputação 0-100**, varia por:
  - Campanha vs meta do conselho (±20)
  - Título (+12), rebaixamento (−15)
  - Saúde financeira (±)
  - Vender ídolos (−)
- **Job security**: reputação <38 = advertência (2 = demissão); <25 = demissão imediata
- **Mercado de técnicos**: 202 técnicos IA + você, mesma regra
  - Demitido (IA ou humano) → agente livre → recontratado
  - **Você demitido recebe ofertas** (escalam com reputação): continua em outro clube ou encerra
  - Carrossel de técnicos a cada temporada

---

## 7. Fluxo recomendado de uso

```
1. python3 main.py
2. Modo Carreira → Nova carreira
3. Escolher liga + clube + nome do técnico
4. 📋 Escalação: formação, 11 titulares e estilo tático
5. 💰 Mercado: reforçar (negociar/cláusula/empréstimo)
6. 🎟️  Estádio & CT: preço do ingresso + nível de treino
7. ▶️  Jogar temporada (assistir ao vivo ou simular) + copas
8. Renovar contratos · ver balanço · reputação
9. Repetir: construir dinastia sem ser demitido
```

---

## 8. Esquema do banco (tabelas principais)

| Tabela | Conteúdo |
|--------|----------|
| `leagues` / `clubs` / `players` | estrutura + elencos |
| `countries` | países das ligas |
| `matches` / `rounds` / `seasons` | partidas e calendário |
| `career` | save do técnico (clube, ano, caixa, reputação, formação, escalação, tática, CT) |
| `coaches` | técnicos (IA + humano `is_player=1`) |
| `season_history` | campeões + colocação por temporada |
| `league_table` | classificação persistida (tela de tabela) |
| `transfers` | histórico de transferências |

Colunas-chave em `players`: `overall`, `potential`, `age`, `wage`, `contract_until`,
`value`, `release_clause`, `loan_from_club`, `red_cards`, `is_newgen`, `retired`.

Colunas-chave em `career`: `formation`, `lineup`, `tactic_style`, `training_level`,
`expectation`, `warnings`. Em `clubs`: `prestige`, `capacity`, `ticket_price`.

---

## 9. Troubleshooting

| Problema | Solução |
|----------|---------|
| "Database não encontrada" | `bash scripts/rebuild_db.sh` |
| `.app` não abre em outro Mac | botão direito → Abrir (Gatekeeper) |
| Atualizar DB no `.app` | indisponível no bundle; use versão dev |
| Carreira bugada | save em `~/Library/Application Support/BrasfootClone/`; apagar reinicia |
| Rebuild lento | `import_openfootball` clona repos (1ª vez ~1min) |
| Quer dados novos | baixar `fc26_players.csv` → `data/update.py` |

---

## 10. Resumo técnico

FUT BRASIL é um gerenciador completo: carreira por temporadas, escalação +
estilo tático, mercado com negociação/cláusula/empréstimo, economia
(folha/bilheteria/CT/multas/copas), moral dinâmica, treino, copas nacionais e
continentais, mundo vivo (evolução pico-27/declínio-32, newgens, aposentadoria),
mercado de técnicos com job security, e transmissão de partidas ao vivo.
Tudo em Python stdlib, database SQLite reprodutível via pipeline,
distribuível como `.app` de 8MB.

**Para implantar pronto para uso:** `python3 main.py` (dev) ou
`PyInstaller + build_app.sh` (`.app`). Database já incluída.
