# Plano — Scouting/Atributos + Negociação 3 partes (estilo CM 03/04)

## A) Olheiros (scouting) — atributos JÁ EXISTEM, só faltam visíveis

**Achado:** `players` já tem pace/technique/strength/finishing/passing/
defending/goalkeeping/stamina/mental no banco e em `models.Player`
(usados em `attack_score`/`defense_score`/`calc_overall`) — só não
aparecem em NENHUM painel da GUI. Escopo de A encolhe bastante: não
precisa migração nem geração, só "esconder por padrão, revelar via olheiro".

- [x] **Fundação feita** (Fase 1.1+1.2 do plano GDD —
      `~/.claude/plans/refactored-discovering-liskov.md`):
      `engine/knowledge.py` (`known_attrs` — masking puro, sem tabela nova:
      elenco próprio/listados → exato; resto → faixa/oculto, determinístico
      por hash, largura encolhe com prestígio do clube). `gameapi.api_player_detail`
      + `api_set_transfer_listed`. Painel `_panel_player` em `gui/app.py`
      (perfil completo: cabeçalho, contrato, grid de atributos mascarados,
      botão listar p/ transferência) — aberto por duplo-clique/"Ver perfil"
      em Elenco e Mercado. Testado headless (determinismo OK), rebuild feito.
- [x] **Pipeline básico feito** (Fase 1.3, simplificada — sem fila de
      missões/scouts contratáveis, ação direta "escalar olheiro" no perfil):
      `engine/scouting.py` (`run_scout` — custa caixa ∝ overall do alvo,
      confirma N atributos ∝ prestígio do clube, prioriza atributos-chave
      da posição, persiste em `scout_reports` com merge incremental,
      determinístico via hash). `gameapi.api_scout_player` debita e
      retorna relatório. `_panel_player`: botão "🔎 Escalar olheiro (custo)",
      atributo confirmado pinta dourado. Testado headless (custo debitado,
      merge sem duplicar, determinismo, bloqueia escotar o próprio elenco).
- [ ] (extra, não essencial) `scout_region`/shortlist de jovens promissores —
      fila de missões com scouts contratáveis — avaliar depois se fizer falta
- [x] **Comparação (Fase 1.4) feita**: botão "⚖ Comparar com…" no perfil
      abre `_panel_compare` — lado a lado com elenco próprio (combobox pra
      trocar o rival, sugere mesma posição), atributo maior marcado ▲ verde,
      cinza quando não dá pra comparar (faixa/oculto em algum dos dois).
      Sem módulo novo — direto em `gui/app.py` reusando `api_player_detail`
      (simplicidade > criar `engine/compare.py` pra um diff trivial).
- [ ] (fase 2, opcional) `engine/simulation.py` pondera atributos específicos
      em situações (pace em contra-ataque, finishing em chutes)

**Risco:** alto — toca schema de 14k+ jogadores e duas telas novas.

## B) Negociação de transferência em 3 partes (clube + jogador + agente) — [x] FEITO

Hoje só negocia com clube vendedor (`asking_and_clause`/`evaluate_offer`).
Jogador e agente não têm voz — fecha compra fácil demais.

**Implementado:** `engine/transfer.py` ganhou `player_wage_demand` (base =
salário atual; prêmio 10-50% se sai de clube de + prestígio pra - prestígio,
desconto 15% pra jovem ≤21 topar por oportunidade) e `agent_fee` (5-9.5%
∝ overall). `gameapi.api_player_terms` (calcula exigências após clube topar)
+ `api_finalize_transfer` (cobra taxa+comissão, valida caixa total ANTES de
mexer, seta salário/contrato novo). `gui/app.py _negotiate` agora abre
`_negotiate_terms` como 2ª etapa — mostra taxa acordada, exigência salarial
do jogador e comissão do agente num só diálogo (wizard de 2 passos, não 3
telas — simplicidade > over-engineering um state machine pra isso) antes de
fechar. Testado headless: fluxo completo (clube→jogador→agente→finalize),
determinístico, bloqueia se caixa não cobre taxa+comissão, salário/contrato
gravados corretos, dinheiro bate exatamente com `total_cost`.

## C) Comentário de partida mais rico (texto, estilo CM 03/04)

Hoje `engine/live.py build_timeline` só gera gol/amarelo/vermelho/contusão —
minutos vazios sem nada no feed. CM 03/04 enchia o jogo de "lances" mesmo
sem gol: chutes pra fora, defesas, escanteios, ataques perigosos.

- [ ] `engine/live.py`: nova função `_fillers(home, away, h_start, a_start)`
      gera eventos de "lance" (sem afetar placar): chute defendido, chute
      pra fora, escanteio, ataque perigoso, jogada individual — quantidade
      e time favorecido pesam por `attack_rating`/`defense_rating`/moral
      (igual já pesa gols). Novo `LiveEvent.kind="chance"`.
- [ ] Escolhe protagonista do lance ponderado por atributo (`finishing` pra
      ataque, `passing`/`technique` pra construção) — já dá pra usar mesmo
      sem esperar atributos novos (cai no fallback de `overall`).
- [ ] `broadcast`/`narrate_matchday`/feed da GUI: trata `kind="chance"` —
      feed só mostra lances do time do jogador (`is_player`), evita spam
      em rodada com vários jogos simultâneos (mesmo filtro de yellow/injury)
- [ ] Calibra volume: ~6-10 lances de texto por jogo, distribuídos, sem
      lotar o feed nem deixar minuto vazio

**Risco:** baixo — só acrescenta eventos cosméticos, não toca placar/sim.
**Esforço:** baixo-médio.

## Status — TODOS os itens A/B/C feitos e testados (rebuild .app ok)
- C → B → fundação de A (perfil+masking+scouting+comparação) — ordem seguida
- Headless: determinismo, custo/caixa, persistência, merge incremental — OK

## Fase 2 do GDD — Inbox + Notas + Board — [x] FEITO
(plano completo em `~/.claude/plans/refactored-discovering-liskov.md`)

- `engine/inbox.py` (novo): `add_message`/`list_messages`/`unread_count`/
  `mark_read`. Tabela `inbox_messages` (career/round/kind/title/body/read).
  Mensagens geradas nos pontos que já existiam mas só "passavam pela tela":
  fim de temporada (resumo: campeão, newgens, transfers de IA, acesso/queda
  — kind="record"), avaliação do conselho (motivos/reputação/demissão —
  kind="board", reaproveita `season_reputation` sem alterar), relatório de
  scouting pronto (kind="scout_report", plugado em `engine/scouting.run_scout`).
- `player_notes` (tabela nova) + `api_player_notes`/`api_add_note`/
  `api_delete_note`. Campo de texto + combobox de tag (alvo/revender/risco/
  monitorar) direto no perfil de jogador (`_render_notes` em `_panel_player`).
- Painel "📨 Inbox" novo na sidebar — cards por mensagem (não lida = 🔵
  dourado), scroll, marca tudo como lido ao abrir.
- Board multi-eixo (2.3 do plano): **não estendido** — `season_reputation`
  já cobre campanha/título/rebaixamento/finanças com boa granularidade;
  reescrever pra "eixos com confiança própria" seria troca de sistema que
  funciona por algo mais complexo sem ganho claro agora. Decisão: manter,
  só canalizar a saída pra inbox (feito).
- Testado headless: notas (CRUD + persistência), scouting → mensagem na
  inbox, temporada completa simulada → 2 mensagens (resumo + board) com
  texto correto, mark_read zera unread.

## Fase 3.1 — Lesão/cirurgia real (escolhido pelo user entre 4 itens) — [x] FEITO
(plano: `~/.claude/plans/refactored-discovering-liskov.md`, item Fase 3)

- `engine/injury.py` (novo): `INJURY_TYPES` (6 tipos, leve/média/grave c/
  semanas e queda de fitness), `roll_injury`/`record_injury` (determinístico
  via hash career+player+round), `active_injury`, `process_recoveries`
  (decrementa 1 semana/rodada, marca recovered + restaura fitness mínimo),
  `surgery_offer`/`decide_surgery` (custo ∝ gravidade×semanas, corta ~45%
  do prazo, 12% risco determinístico de complicação que adiciona semanas).
- Tabela `injuries` (career/player/club/kind/weeks_total/weeks_left/
  surgery/status/season/round). `LiveResult.injuries` (novo campo em
  `engine/live.py`) carrega `{player_id, name, club_id}` de quem saiu
  contundido na timeline.
- **Escopo: só elenco do técnico humano** — persistência/gestão médica em
  `play_round_live` (gameapi.py) só roda quando `club_id == cid` (custo de
  I/O + balanceamento em 14k+ jogadores de IA não compensa). Gera mensagem
  inbox kind="medical" na lesão e na recuperação. `process_recoveries`
  roda toda rodada (1 rodada ≈ 1 semana).
- `gameapi.api_player_detail` agora retorna `injury` (status + oferta de
  cirurgia) quando é elenco próprio e há lesão ativa. `api_decide_surgery`
  novo — debita custo, recalcula prazo, aplica complicação se rolar.
- `_panel_player`: card vermelho com status da lesão + prazo, e se ainda
  não operado, oferta de cirurgia (custo/prazo/risco) com botão "Decidir
  pela cirurgia" → confirma → `_decide_surgery`.
- Testado headless: lesão ocorreu na rodada 7 (Carlos Silva, lesão no
  joelho, 8 semanas), mensagem inbox correta, fitness caiu, cirurgia
  debitou €2.0M e cortou pra 3 semanas, `process_recoveries` avançou e
  marcou 'recovered' + gerou mensagem de alta médica. Rebuild `.app` ok.

**Nota:** `play_round_live` (modo "ao vivo") é o único caminho que gera
`LiveResult`/eventos de lesão — `_web_league_round` (modo "simular rápido",
usado por `api_play`) chama `simulate_match` sem timeline, então só
acontece lesão real jogando ao vivo. Mesma assimetria pré-existente que
já valia pra cartões/lances de texto — não é regressão, é o desenho atual.
