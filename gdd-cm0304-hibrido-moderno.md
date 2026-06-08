# Documento de Design de Jogo — Manager de Futebol inspirado em CM 03/04

## Objetivo do documento

Este documento define a arquitetura conceitual, o fluxo de telas e o vocabulário sistêmico de um novo jogo de management football inspirado principalmente em **Championship Manager 03/04**, usando essa edição como referência para um produto moderno centrado em **match engine 2D legível**, **módulo de mídia mais forte**, **relacionamentos entre jogadores**, **treino visualmente explicável** e **grande escala de base de dados**.[cite:1][cite:2]

CM03/04 é um ponto especialmente útil porque preserva a profundidade clássica da série, mas já introduz uma camada mais moderna de apresentação sistêmica: relações entre atletas, treino com efeitos visíveis no perfil, match engine melhorado com clima e indicadores visuais, replays de partidas salvas e editor pré-jogo.[cite:2][cite:1]

## Princípios de produto

O novo jogo deve herdar cinco pilares de CM03/04. O primeiro é **simulação densa com feedback visível**: o usuário continua administrando sistemas complexos, mas recebe sinais mais claros sobre causa e efeito, como treinamento refletido no perfil do atleta e status visuais durante a partida.[cite:2] O segundo é **mundo grande e pesquisado**, inspirado na base com mais de 200 mil jogadores, 43 países jogáveis e 92 divisões, porque escala e abrangência sustentam descoberta, longevidade e mercado emergente.[cite:1] O terceiro é **partida como centro dramático**, graças ao motor 2D, comentário expandido, clima e melhor IA.[cite:2]

O quarto pilar é **vida social do elenco**: CM03/04 adicionou relações jogador-jogador, o que abre espaço para moral coletiva, química de unidade, conflitos e afinidades relevantes para desempenho.[cite:2] O quinto é **editabilidade do mundo**, com editor pré-jogo e estrutura preparada para ajuste de base e regras antes da carreira começar.[cite:1] Para um híbrido moderno, esses pilares devem ser combinados com UX contemporânea, explicabilidade estatística e forte navegabilidade por listas.

## Visão de sistema

### Arquitetura básica

A arquitetura proposta pode ser organizada em oito módulos centrais, conectados por um pipeline de eventos diários e semanais.

1. **Core Simulation Engine** — tempo, agenda, partidas, forma, moral, fadiga, lesões, reputação e progressão da temporada.
2. **Match & Commentary Engine** — cálculo da partida, estados contextuais, feed de eventos, visual 2D, clima e replay.
3. **Squad Dynamics Engine** — relacionamentos entre jogadores, coesão, hierarquia, conflitos, grupos e influência.
4. **Training & Development Engine** — treinos coletivos, foco individual, crescimento, declínio, carga física e feedback visual.
5. **World Database & Rules Engine** — clubes, ligas, países, competições, jogadores, regras nacionais, staff e histórico.
6. **Media & Narrative Engine** — notícias, rumorologia, board reactions, premiações e interpretação pública dos eventos.
7. **Management Layer** — elenco, scouting, contratos, táticas, finanças, staff e decisões institucionais.
8. **Persistence & Editing Layer** — save system, replay storage, snapshots, editor pré-jogo e importação/exportação de dados.

### Loop sistêmico principal

O loop sistêmico do jogo funciona assim:

**Avançar tempo** → processar treino, recuperação, mídia, scouting e agenda → resolver partidas quando existirem → recalcular moral, forma, coesão, reputação e finanças → atualizar inbox, rankings e relatórios → liberar nova rodada de decisões do treinador.

A principal diferença em relação a um design mais "CM01/02 puro" é que CM03/04 favorece **visibilidade de estado**. O usuário continua administrando um sistema profundo, mas percebe com mais clareza o efeito do treino, o estado contextual do jogador em campo e a vida social do elenco.[cite:2]

### Entidades principais do domínio

| Entidade | Função sistêmica | Campos essenciais |
|---|---|---|
| Jogador | Unidade esportiva e social | atributos, condição, moral, forma, relações, papel, contrato, histórico |
| Clube | Estrutura institucional | orçamento, board, instalações, reputação, staff, cultura |
| Staff | Suporte técnico e informacional | qualidade de treino, scouting, medicina, negociação, motivação |
| Partida | Produção de resultado e drama | tática, clima, eventos, estatísticas, status visuais, replay |
| Relação | Vínculo entre atores | afinidade, rivalidade, respeito, influência, histórico de eventos |
| Sessão de treino | Unidade de desenvolvimento | carga, foco, ganho esperado, risco físico, feedback |
| Evento narrativo | Interpretação do sistema | notícia, cobrança, rumor, prêmio, reação pública |
| Regra de competição | Restrição do mundo | calendário, inscrições, disciplina, premiação, elegibilidade |

## Núcleo sistêmico herdado de CM 03/04

### 1. Motor de partida 2D com leitura expandida

CM03/04 preserva o visual 2D top-down introduzido em CM4, mas melhora o **match engine**, adicionando mais comentários, IA melhor, efeitos climáticos e indicadores visuais de estado.[cite:1][cite:2] Para o novo jogo, isso significa que a tela de partida não deve ser apenas um resolvedor invisível nem um simulador hipergráfico; ela deve ser um **painel tático legível em movimento**.

#### Objetivos do match engine

- transmitir causa e efeito tático;
- informar estado físico e emocional em tempo real;
- permitir intervenção leve, porém relevante;
- sustentar replay útil para análise.

#### Elementos visuais mínimos

- campo 2D com posições e deslocamentos;
- feed de comentários contextual;
- status visual sobre jogadores, como cansaço, lesão, nervosismo ou boa fase;
- indicador climático, como chuva, vento ou neve;
- mini heat/territory summary por fases do jogo.

### 2. Relações entre jogadores

Uma das adições mais relevantes de CM03/04 foi o sistema de **player-to-player relationships**.[cite:2] Para um jogo moderno, isso deve sair do nível decorativo e virar um subsistema com impacto real em performance, moral e retenção do elenco.

#### Tipos de relação

- amizade;
- rivalidade;
- respeito profissional;
- parceria de campo;
- influência hierárquica;
- afinidade cultural/linguística.

#### Efeitos sistêmicos

- duplas com alta parceria melhoram sincronia;
- conflitos deterioram moral coletiva;
- líderes positivos elevam coesão de setores;
- panelinhas podem isolar recém-chegados;
- transferências e promessas quebradas afetam a rede de relações.

#### Modelo recomendado

Cada par de jogadores deve ter um valor de afinidade, mas o sistema também precisa calcular níveis agregados:

- coesão por setor (defesa, meio, ataque);
- coesão do XI titular;
- clima do vestiário;
- índice de influência de líderes;
- risco de conflito latente.

### 3. Treino intuitivo com feedback visual

CM03/04 introduz um **novo sistema de treino intuitivo**, com os efeitos do treino visualmente indicados no perfil do jogador.[cite:2] Essa ideia é extremamente valiosa para um híbrido moderno, porque une profundidade clássica com feedback claro.

#### Estrutura recomendada

O treino deve operar em três níveis:

- **plano coletivo**: distribuição da semana;
- **foco individual**: atributo, papel ou recuperação;
- **adaptação automática**: correção por fadiga, risco médico e minutagem.

#### Feedback no perfil

Cada jogador deve exibir:

- carga atual;
- tendência de evolução por grupo de atributo;
- ganho recente;
- risco de sobrecarga;
- adequação ao papel treinado;
- explicação textual do progresso.

Exemplo de feedback: “melhora leve em passe e visão após 3 semanas de foco como armador recuado” ou “queda de sharpness por baixa minutagem apesar de treino satisfatório”. Esse tipo de visualização é diretamente alinhado à lógica indicada para CM03/04.[cite:2]

### 4. Módulo de mídia mais forte

MobyGames lista explicitamente o **Improved Media Module** como uma das novidades centrais de CM03/04.[cite:2] Isso sugere um jogo menos silencioso, no qual o mundo reage aos eventos da temporada com mais frequência e variedade.

#### Funções do módulo de mídia

- contextualizar resultados e crises;
- amplificar rumores de mercado;
- afetar moral, reputação e paciência do board;
- transformar feitos isolados em narrativa recorrente.

#### Tipos de peça narrativa

- manchete de rodada;
- rumor de contratação;
- coletiva pré-jogo;
- coletiva pós-jogo;
- crise de vestiário;
- matéria sobre sequência invicta;
- repercussão de prêmio individual.

### 5. Replay de partidas salvas

CM03/04 trouxe a capacidade de **ver partidas anteriormente salvas**.[cite:1] Em um design atual, isso deve ser expandido para um módulo de análise leve.

#### Requisitos

- lista de partidas arquivadas;
- timeline de eventos;
- replay por lances-chave;
- marcadores de gols, cartões, substituições e lesões;
- visão simplificada de estatísticas do replay.

Isso transforma a partida em dado revisável, útil tanto para aprendizado do jogador quanto para ferramentas de conteúdo e compartilhamento.

### 6. Editor pré-jogo

A presença de um **pre-game database editor** em CM03/04 é uma pista importante de arquitetura.[cite:1] O novo jogo deve nascer com uma camada formal de edição de dados, não tratá-la como ferramenta improvisada de modding posterior.

#### Escopo do editor

- jogadores;
- clubes;
- ligas e divisões;
- calendários e regras;
- atributos, reputação e contratos;
- kits mínimos de metadata para staff e competições.

#### Benefícios

- facilita patches oficiais e de comunidade;
- reduz custo de manutenção;
- amplia vida útil do produto;
- suporta cenários históricos, alternativos e licenciamentos parciais.

## Arquitetura funcional detalhada

### Módulo 1 — Simulação de temporada

Processa o calendário diário, atualiza estados físicos e morais, dispara eventos de mídia e resolve consequências institucionais. O foco não é apenas calcular partidas, mas manter o mundo em movimento.

**Submódulos**:
- agenda e calendário;
- forma e momentum;
- lesões e recuperação;
- moral individual e coletiva;
- progressão temporal;
- consequências reputacionais.

### Módulo 2 — Motor de partida e comentário

Esse módulo calcula o jogo, gera eventos e os traduz em visual 2D e linguagem textual.

**Submódulos**:
- resolução tática;
- probabilidades por zona do campo;
- clima e contexto;
- comentário dinâmico;
- indicadores visuais;
- replay persistente.

### Módulo 3 — Dinâmica de elenco

É o coração diferencial do design inspirado em CM03/04. Ele armazena e recalcula relações, grupos sociais, influência de líderes e tensões acumuladas.

**Submódulos**:
- matriz de afinidade;
- grupos e panelinhas;
- hierarquia do elenco;
- promessas e ressentimentos;
- adaptação cultural e linguística;
- coesão por unidade tática.

### Módulo 4 — Treino e desenvolvimento

Gerencia sessões, evolução, declínio, carga física e encaixe por papel.

**Submódulos**:
- calendário de treino;
- foco individual;
- efeito por atributo;
- integração com condição física;
- feedback visual de progresso;
- aprendizagem tática.

### Módulo 5 — Mundo e regras

CM03/04 chegou a 43 países jogáveis em 92 divisões e base superior a 200.000 jogadores, com dados pesquisados por mais de 2.500 pesquisadores.[cite:1] O novo jogo deve tratar escala de dados como feature central, não só volume bruto.

**Requisitos**:
- estrutura por país, divisão e competição;
- histórico por temporada;
- IDs estáveis;
- versionamento de base;
- editor nativo;
- regras por federação e competição.

### Módulo 6 — Mídia e narrativa

Transforma saídas do sistema em histórias compreensíveis.

**Entradas**:
- resultados;
- sequência de forma;
- conflitos de elenco;
- negociações;
- marcos estatísticos;
- prêmios.

**Saídas**:
- notícias;
- perguntas;
- manchetes;
- impacto reputacional;
- pressão pública;
- marcos históricos.

### Módulo 7 — Gestão esportiva e institucional

Abrange táticas, mercado, contratos, scouting, finanças e board. Embora CM03/04 destaque mais relações e treino, ele continua sendo um manager completo de alta profundidade.[cite:2][cite:1]

### Módulo 8 — Persistência, replay e edição

Salva a carreira, indexa replays, preserva estados da temporada e suporta modificações do banco antes do início do jogo. Esse módulo é indispensável para longevidade e comunidade.

## Diagrama de telas

### Mapa principal de navegação

```text
[TELA INICIAL]
 ├─ Novo Jogo
 │   ├─ Escolher Base de Dados
 │   ├─ Selecionar Países/Ligas
 │   ├─ Configurar Regras
 │   ├─ Escolher Clube
 │   └─ Definir Perfil do Técnico
 ├─ Carregar Jogo
 ├─ Editor Pré-jogo
 ├─ Replays Salvos
 └─ Opções

[DASHBOARD / INBOX]
 ├─ Caixa de Entrada
 ├─ Próxima Partida
 ├─ Elenco
 ├─ Relações
 ├─ Táticas
 ├─ Treino
 ├─ Scouting
 ├─ Transferências
 ├─ Staff
 ├─ Clube
 ├─ Finanças
 ├─ Board
 ├─ Mídia
 ├─ Competições
 ├─ Base de Dados
 └─ Histórico
```

### Fluxo de relações e elenco

```text
[Elenco]
 ├─ Lista Geral
 ├─ Hierarquia
 ├─ Moral
 ├─ Forma
 └─ [Perfil do Jogador]
     ├─ Visão Geral
     ├─ Atributos
     ├─ Condição
     ├─ Treino
     ├─ Partidas
     ├─ Contrato
     ├─ Relacionamentos
     ├─ Relatórios
     └─ Ações

[Relações]
 ├─ Matriz do Elenco
 ├─ Grupos Sociais
 ├─ Influência / Liderança
 ├─ Conflitos Abertos
 └─ Coesão por Setor
```

### Fluxo de treino

```text
[Treino]
 ├─ Calendário Semanal
 ├─ Planos Coletivos
 ├─ Focos Individuais
 ├─ Carga e Risco
 ├─ Relatório de Evolução
 └─ [Perfil do Jogador > Treino]
     ├─ Tendências
     ├─ Ganhos Recentes
     ├─ Papel em Desenvolvimento
     ├─ Adaptação Tática
     └─ Recomendação do Staff
```

### Fluxo de partida e replay

```text
[Próxima Partida]
 ├─ Escalação
 ├─ Oposição
 ├─ Briefing
 ├─ Instruções
 └─ Match View
     ├─ Campo 2D
     ├─ Comentário
     ├─ Eventos
     ├─ Estatísticas
     ├─ Status Visuais
     └─ Ajustes ao vivo

[Pós-jogo]
 ├─ Resultado
 ├─ Ratings
 ├─ Reações
 ├─ Mídia
 └─ Salvar Replay

[Replays Salvos]
 ├─ Lista de Partidas
 ├─ Timeline de Eventos
 ├─ Lances-chave
 └─ Estatísticas do Replay
```

### Fluxo institucional e narrativo

```text
[Mídia]
 ├─ Notícias
 ├─ Coletivas
 ├─ Rumores
 ├─ Prêmios
 └─ Reputação Pública

[Board]
 ├─ Confiança
 ├─ Objetivos
 ├─ Reuniões
 ├─ Pedidos
 └─ Risco de Demissão

[Editor Pré-jogo]
 ├─ Jogadores
 ├─ Clubes
 ├─ Staff
 ├─ Competições
 ├─ Regras
 └─ Exportar Base
```

## Especificação de páginas-chave

### 1. Dashboard / Inbox

Continua sendo a tela central do jogo, mas em um produto inspirado em CM03/04 ela precisa refletir mais claramente a vida sistêmica do clube.

#### Blocos recomendados

- inbox cronológica;
- próximo jogo;
- moral coletiva;
- status de coesão;
- alertas de treino e fadiga;
- manchetes recentes;
- atalhos para replay e relações;
- botão de avançar tempo.

### 2. Perfil do jogador

No design inspirado em CM03/04, essa tela precisa integrar três dimensões ao mesmo tempo: atleta, ativo contratual e nó social.

#### Blocos essenciais

- identidade e posição;
- atributos e papel;
- forma, moral e condição;
- feedback de treino;
- relações importantes;
- contrato e mercado;
- histórico e relatórios.

#### Melhorias modernas úteis

- gráfico simples de evolução por bloco de atributos;
- indicador de química com parceiros de setor;
- explicação de queda/subida recente;
- risco de conflito ou adaptação.

### 3. Tela de relações

Essa é uma das páginas mais importantes para diferenciar o produto.

#### Componentes

- matriz de afinidade entre atletas;
- grupos sociais detectados automaticamente;
- líderes positivos e negativos;
- atletas isolados;
- eventos recentes que alteraram relações;
- impacto estimado na coesão do XI titular.

Essa página traduz uma inovação de CM03/04 em ferramenta estratégica real.[cite:2]

### 4. Tela de treino

Deve transformar um sistema complexo em linguagem operacional rápida.

#### Componentes

- calendário semanal;
- presets táticos e físicos;
- intensidade por dia;
- foco por grupo ou atleta;
- previsão de risco físico;
- ganhos recentes do elenco;
- recomendações automáticas do staff.

### 5. Match view

A tela de partida precisa ser informativa sem virar ruído visual.

#### Componentes

- campo 2D principal;
- feed textual de comentários;
- placar, tempo, clima e momentum;
- ícones de status dos jogadores;
- comandos rápidos de ajuste;
- aba de estatísticas.

### 6. Replays salvos

Essa página deve permitir revisão prática da partida, apoiando análise e compartilhamento.

#### Componentes

- lista filtrável de jogos;
- marcadores por evento;
- corte por tempo ou lance-chave;
- comparativo estatístico resumido;
- opção de exportar snapshot narrativo.

## Dicionário de termos do jogo

### Atributos

CM03/04 pede um modelo de atributos que converse bem com treino visual, match engine legível e papéis funcionais. O conjunto abaixo mantém a clareza clássica, mas com separação útil para explicabilidade.

| Grupo | Atributo | Definição sistêmica |
|---|---|---|
| Técnico | Finalização | Conversão de chances em gol |
| Técnico | Passe | Precisão e progressão da posse |
| Técnico | Drible | Capacidade de eliminar adversários com bola |
| Técnico | Primeiro toque | Controle inicial e preparação da jogada |
| Técnico | Cruzamento | Qualidade de bolas laterais |
| Técnico | Marcação | Acompanhamento e contenção defensiva |
| Técnico | Desarme | Execução do tackle |
| Técnico | Cabeceio | Eficiência aérea ofensiva e defensiva |
| Técnico | Técnica | Qualidade geral de execução |
| Mental | Decisões | Escolha de ação adequada em contexto |
| Mental | Antecipação | Leitura prévia das jogadas |
| Mental | Posicionamento | Ocupação correta sem e com bola |
| Mental | Composure | Controle sob pressão |
| Mental | Visão | Leitura criativa do jogo |
| Mental | Trabalho em equipe | Cooperação com o plano coletivo |
| Mental | Determinação | Persistência e resposta à adversidade |
| Mental | Liderança | Influência sobre outros jogadores |
| Mental | Concentração | Capacidade de manter execução sem erros |
| Físico | Aceleração | Arranque curto |
| Físico | Velocidade | Deslocamento em alta intensidade |
| Físico | Resistência | Sustentação do esforço |
| Físico | Força | Contato físico e proteção |
| Físico | Agilidade | Mudança de direção e equilíbrio |
| Físico | Impulsão | Salto vertical |
| Goleiro | Reflexos | Reação a finalizações |
| Goleiro | Um contra um | Eficiência em confrontos diretos |
| Goleiro | Saída do gol | Ações fora da linha |
| Goleiro | Manuseio | Segurança com a bola |
| Goleiro | Reposição | Qualidade de distribuição |

### Estados derivados

CM03/04 pede atenção especial a estados que precisam ser visíveis em jogo e no perfil.

- **Condition**: energia imediata do atleta.
- **Match fitness**: capacidade de suportar partida oficial.
- **Sharpness**: ritmo competitivo recente.
- **Form**: desempenho recente em sequência.
- **Morale**: estado emocional individual.
- **Cohesion**: nível de integração do grupo ou unidade.
- **Relationship score**: afinidade com outro ator.
- **Training load**: carga física da semana.
- **Development trend**: tendência recente de evolução.

### Posições nominais

| Código | Nome |
|---|---|
| GK | Goleiro |
| SW | Líbero |
| DC | Zagueiro central |
| DR / DL | Lateral direito / esquerdo |
| WBR / WBL | Ala direito / esquerdo |
| DMC | Volante |
| MC | Meio-campista central |
| MRC / MLC | Meio-campista meia-direita / meia-esquerda |
| AMC | Meia ofensivo central |
| AMR / AML | Meia ofensivo aberto direito / esquerdo |
| ST | Atacante |
| FC | Centroavante / atacante central |

### Skill set / papéis funcionais

Como CM03/04 enfatiza melhor o que acontece em campo, vale explicitar papéis funcionais como ponte entre atributo, treino e comportamento no match engine.

| Papel | Posições típicas | Descrição |
|---|---|---|
| Goleiro de área | GK | domina cruzamentos e protege a área |
| Goleiro construtor | GK | participa da saída curta |
| Zagueiro de cobertura | DC | protege profundidade e corrige rupturas |
| Zagueiro agressivo | DC | sobe no duelo e quebra linhas adversárias |
| Lateral de profundidade | DR/DL | ataca corredor externo e cruza |
| Lateral invertido | DR/DL | fecha por dentro para circular posse |
| Volante destruidor | DMC | protege zaga e vence duelos |
| Regista | DMC/MC | organiza de trás com passe e visão |
| Box-to-box | MC | percorre áreas e oferece volume |
| Meia de chegada | MC/AMC | pisa na área e finaliza |
| Armador avançado | AMC/MC | cria em zona de decisão |
| Winger clássico | AMR/AML | dá amplitude e cruza |
| Inside forward | AMR/AML | corta para dentro buscando finalização |
| Segundo atacante | AMC/ST | conecta linhas e ataca espaços intermediários |
| Homem-alvo | ST/FC | sustenta jogo direto e disputa aérea |
| Atacante de ruptura | ST | ameaça profundidade com aceleração |
| Finalizador de área | FC | vive da última linha e da conclusão |

### Atributos críticos por papel

| Papel | Atributos prioritários |
|---|---|
| Goleiro construtor | reposição, compostura, decisões, saída do gol |
| Zagueiro de cobertura | antecipação, posicionamento, aceleração, marcação |
| Lateral invertido | passe, decisões, trabalho em equipe, técnica |
| Volante destruidor | marcação, desarme, resistência, concentração |
| Regista | passe, visão, decisões, compostura |
| Box-to-box | resistência, trabalho em equipe, decisões, chegada |
| Armador avançado | visão, passe, primeiro toque, técnica |
| Winger clássico | aceleração, drible, cruzamento, agilidade |
| Inside forward | drible, aceleração, finalização, sem bola |
| Homem-alvo | força, cabeceio, primeiro toque, compostura |
| Atacante de ruptura | aceleração, sem bola, decisões, finalização |

## Modelo de dados conceitual

### Jogador

```text
Player
- player_id
- full_name
- common_name
- date_of_birth
- nationality_primary
- nationality_secondary
- preferred_foot
- height
- weight
- positions_nominal[]
- roles_fit[]
- attributes{}
- condition_state
- fitness_state
- sharpness_state
- form_state
- morale_state
- leadership_score
- social_groups[]
- relationship_edges[]
- contract_id
- club_id
- reputation_local
- reputation_world
- training_focus
- development_log[]
```

### Relação entre jogadores

```text
RelationshipEdge
- edge_id
- source_player_id
- target_player_id
- relationship_type
- affinity_score
- trust_score
- conflict_score
- last_event_id
- last_updated_at
- same_language_bonus
- same_unit_bonus
- rivalry_flag
```

### Sessão de treino

```text
TrainingSession
- session_id
- club_id
- week_id
- session_type
- intensity
- target_units[]
- risk_modifier
- expected_effects{}
- staff_owner_id
- notes
```

### Replay de partida

```text
MatchReplay
- replay_id
- match_id
- saved_at
- event_markers[]
- key_highlights[]
- match_stats{}
- weather_context
- tactical_snapshots[]
```

## Regras de UX para um híbrido moderno

### 1. Partida legível acima de tudo

O visual 2D deve ser funcional, não ornamental. Como CM03/04 já valorizava comentário, IA melhorada, clima e status visuais, a versão moderna precisa ampliar a legibilidade e não abandonar essa linha.[cite:2][cite:1]

### 2. Relações precisam ser jogáveis

Relações não podem existir só em flavor text. O usuário deve conseguir diagnosticar, prever e influenciar efeitos sobre coesão, retenção e performance.

### 3. Treino deve explicar progresso

Toda mudança relevante precisa aparecer em linguagem humana: por que melhorou, por que estagnou, por que entrou em risco físico.

### 4. Escala de dados precisa servir à navegação

Base grande sem filtros bons vira atrito. Como CM03/04 trabalhava em escala muito ampla, o híbrido moderno precisa contrabalancear isso com presets, colunas customizáveis e filtros salvos.[cite:1]

## Roadmap de implementação sugerido

### Fase 1 — Vertical slice centrado em partida e elenco

- dashboard/inbox;
- perfil de jogador;
- match view 2D simplificado;
- relações básicas entre jogadores;
- treino com feedback visual mínimo;
- pós-jogo e replay simples.

### Fase 2 — Temporada jogável

- calendário;
- competições e tabela;
- mídia expandida;
- moral, coesão e liderança;
- mercado e contratos;
- board e finanças.

### Fase 3 — Escala e longevidade

- editor pré-jogo;
- expansão de países e divisões;
- replay avançado;
- analytics tático;
- eventos históricos e premiações;
- suporte forte a modding.

## Decisões de design mais importantes

1. **A tela de partida é um sistema de leitura, não só uma animação.** Isso decorre diretamente do foco de CM03/04 em match engine, comentários, clima e indicadores visuais.[cite:2]
2. **Relações entre jogadores devem impactar desempenho e retenção.** Essa é a inovação sistêmica mais distintiva do jogo.[cite:2]
3. **Treino precisa ser visível e explicável no perfil.** Esse é um dos legados mais úteis de CM03/04 para um jogo moderno.[cite:2]
4. **Replay deve virar ferramenta de análise.** A possibilidade de rever partidas salvas já existia e pode ser expandida com baixo risco conceitual.[cite:1]
5. **Editor pré-jogo não é acessório; é infraestrutura.** A própria edição de 03/04 sinaliza isso.[cite:1]
6. **Escala do mundo deve ser sentida pelo jogador.** Países, divisões e profundidade de base precisam gerar descoberta, contexto e mercado vivo.[cite:1]

## Encerramento técnico

Um sucessor espiritual de CM03/04 deve preservar o que essa edição faz melhor: transformar um manager clássico em uma experiência mais visível, social e interpretável, sem perder profundidade.[cite:2][cite:1] O caminho correto para modernizar esse DNA não é hiperrealismo visual, mas sim melhor leitura do match engine, sistema robusto de relações, treino explicável, replays úteis e um mundo editável e vasto.[cite:2][cite:1]
