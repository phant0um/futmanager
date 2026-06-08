# Documento de Design de Jogo — Manager de Futebol inspirado em CM 01/02

## Objetivo do documento

Este documento define a arquitetura conceitual, o fluxo de telas e o vocabulário sistêmico de um novo jogo de management football inspirado principalmente em **Championship Manager: Season 01/02**, incorporando melhorias modernas sem perder o núcleo de decisão rápida, densidade de dados e sensação de simulação sistêmica que tornaram CM01/02 um marco do gênero.[cite:1][cite:2]

O foco principal está em traduzir as inovações mais importantes de CM01/02 — especialmente atributos mascarados, scouting, notas de jogador, comparações, interação com mídia e board, cirurgia/reabilitação e amplitude de base de dados — em uma fundação reutilizável para um produto contemporâneo.[cite:2]

## Princípios de produto

O jogo deve preservar quatro pilares clássicos. Primeiro, **profundidade por sistemas**: o jogador vence entendendo relações entre scouting, moral, contratos, forma e contexto competitivo, e não por minigames isolados.[cite:2] Segundo, **interface densa, porém rápida**: muitas informações por tela, com navegação curta e orientada a listas. Terceiro, **conhecimento imperfeito**: o treinador nunca enxerga o mundo inteiro com precisão absoluta, em linha com o attribute masking de CM01/02.[cite:2] Quarto, **consequência persistente**: cada decisão deixa rastro em orçamento, reputação, confiança do board e ambiente interno.[cite:2][cite:1]

Para um híbrido moderno, três camadas adicionais devem ser incorporadas. A primeira é **legibilidade contemporânea**, com filtros avançados, comparação contextual e visualização de tendências. A segunda é **simulação explicável**, ou seja, o jogo informa por que uma recomendação, queda de forma ou conflito aconteceu. A terceira é **modularidade técnica**, permitindo expansão por patches, editor pré-jogo e regras de ligas configuráveis, algo alinhado ao avanço posterior de CM03/04 com editor e base mais ampla.[cite:1]

## Visão de sistema

### Arquitetura básica

A arquitetura do jogo pode ser organizada em sete módulos centrais, todos alimentados por um barramento de eventos de temporada.

1. **Core Sim Engine** — calendário, resultados, geração de partidas, progressão diária, reputação, moral, fadiga, lesões, evolução de atributos.
2. **World Database** — jogadores, clubes, staff, competições, regras nacionais, histórico, contratos, relações e observabilidade.
3. **Knowledge Layer** — masking, scouting, cobertura por região, confiabilidade de relatórios, rumores, conhecimento do board e da mídia.
4. **Management Layer** — táticas, treino, escalação, staff, transferências, contratos, finanças, pedidos ao board.
5. **Narrative Layer** — inbox, mídia, reações do board, eventos de vestiário, marcos estatísticos e contextualização do mundo.
6. **Interface Layer** — telas, listas, filtros, comparação lado a lado, dashboard diário, tooltips e atalhos.
7. **Persistence & Modding Layer** — saves, snapshots de temporada, editor pré-jogo, import/export de bases e regras.

### Fluxo macro do sistema

O loop sistêmico é simples na superfície e profundo nas consequências:

**Dia de jogo/simulação** → processa calendário e eventos → atualiza inbox → recalcula moral, forma, reputação e orçamento → libera novas ações do treinador → registra novos estados de conhecimento para scouting e mercado.

A camada mais importante para diferenciar o jogo é a separação entre **estado real** e **estado conhecido**. O jogador existe com atributos reais, condição médica real, personalidade real e potencial real no banco de dados; porém o usuário acessa apenas o subconjunto que seu clube descobriu por observação, convivência, relatórios ou notoriedade pública, refletindo diretamente a lógica do attribute masking de CM01/02.[cite:2]

### Entidades principais do domínio

| Entidade | Função sistêmica | Campos essenciais |
|---|---|---|
| Jogador | Unidade principal de desempenho | atributos reais, atributos conhecidos, potencial, personalidade, posição, pé preferido, condição, moral, reputação, contrato |
| Clube | Nó institucional | orçamento, reputação, board, folha salarial, staff, instalações, torcida |
| Staff | Geração de conhecimento e suporte | scouting, treino, médico, negociação, disciplina |
| Competição | Regras e contexto | calendário, formato, registro disciplinar, premiação, elegibilidade |
| Relatório | Saída de conhecimento | fonte, confiança, data, conclusão, atributos observados |
| Evento | Mudança discreta do mundo | lesão, rumor, reclamação, notícia, reunião de board, suspensão |
| Partida | Produção de resultado | tática, seleção, clima, forma, eventos, estatísticas |
| Contrato | Vínculo regulatório | salário, duração, cláusulas, bônus, proteção regulatória |

### Camadas de verdade e percepção

Para um jogo moderno inspirado em CM01/02, cada informação deve ser classificada em uma destas categorias:

- **Verdade oculta**: valor real no banco, invisível ao usuário.
- **Conhecimento parcial**: faixa estimada ou julgamento textual por scouting.
- **Conhecimento confirmado**: atributo revelado por convivência, observação suficiente ou fonte confiável.
- **Conhecimento rumoroso**: informação não verificada, útil para narrativa e mercado.

Essa separação permite preservar o espírito clássico de descoberta, ao mesmo tempo em que moderniza a UX com indicadores de confiança, recência e origem do dado.[cite:2]

## Núcleo sistêmico herdado de CM 01/02

### 1. Atributos mascarados como sistema-base

CM01/02 introduziu formalmente o modo de **attribute masking**, no qual o treinador só enxerga jogadores que “realisticamente conheceria”, e esse conceito deve ser elevado de opção de partida para fundação do design moderno.[cite:2]

#### Regras do masking

- Jogadores do próprio elenco começam amplamente revelados.
- Jogadores de clubes rivais frequentes têm observação parcial por exposição competitiva.
- Jogadores de ligas remotas aparecem com poucas informações públicas.
- Reputação global, partidas televisionadas e convocações internacionais aumentam conhecimento passivo.
- Relatórios de scout convertem faixas em dados confirmados.

#### Representação em UI

Na lista de busca, cada atributo pode aparecer em um de quatro estados:

- valor numérico exato;
- faixa estimada, como 10–14;
- julgamento verbal, como “bom”, “fraco”, “elite”; 
- desconhecido total, como “—”.

#### Benefício para o novo jogo

Isso cria exploração real, valoriza staff e impede que a busca por talento seja apenas um problema de filtro. O sistema também sustenta progressão institucional: clubes grandes têm melhor cobertura, clubes pequenos vivem de informação incompleta e apostas calculadas.[cite:2]

### 2. Scouting como produção de conhecimento

O scouting em CM01/02 ganha relevância justamente porque o mundo não é transparente.[cite:2] No novo jogo, o scouting deve ser modelado como um pipeline:

**Pedido de observação** → alocação de scout → custo de tempo e orçamento → relatório parcial → possível observação adicional → confirmação ou revisão da hipótese.

#### Tipos de scouting

| Tipo | Escopo | Saída esperada |
|---|---|---|
| Scouting de jogador | 1 atleta | atributos observados, estilo, encaixe tático, risco |
| Scouting de elenco | 1 clube | mapa de talentos, titulares, vulnerabilidades |
| Scouting de competição | 1 liga/copa | shortlist inicial, melhores médias, oportunidades |
| Scouting regional | país/região | descoberta passiva, nomes emergentes |
| Scouting por papel | perfil tático | lista ranqueada por função desejada |

#### Variáveis do relatório

- capacidade do scout;
- conhecimento linguístico/regional;
- reputação do alvo;
- número de jogos observados;
- recência dos dados;
- viés do observador;
- compatibilidade com o estilo do técnico.

#### Estrutura do relatório

Todo relatório deveria conter:

- resumo executivo em 2–4 linhas;
- nível de confiança;
- atributos observados e não observados;
- papel sugerido;
- comparação com jogadores do elenco;
- risco médico, disciplinar e de adaptação;
- faixa de custo salarial e de transferência.

### 3. Notas de jogador e memória gerencial

CM01/02 adicionou **player notes**, o que parece pequeno, mas é uma mecânica poderosa de apropriação de conhecimento pelo usuário.[cite:2] Em um híbrido moderno, isso deve virar um sistema de memória híbrida entre texto livre e tags estruturadas.

#### Estrutura recomendada

- **Notas livres**: texto do usuário.
- **Tags rápidas**: “alvo”, “revender”, “risco físico”, “plano B”, “monitorar”.
- **Notas automáticas**: geradas por eventos (“reclamou de reserva”, “3 lesões musculares em 8 meses”).
- **Vínculo temporal**: cada nota tem data e origem.

Isso reduz carga cognitiva em saves longos e transforma o acúmulo de informação em parte do skill ceiling do jogo.

### 4. Comparação de jogadores

CM01/02 trouxe **player comparisons**, reforçando a leitura relativa em vez da absoluta.[cite:2] O novo jogo deve ter comparação em três níveis:

- **Lado a lado clássico**: atributos, idade, custo, forma, lesões.
- **Contextual ao elenco**: “melhor que seu titular em antecipação, pior em velocidade”.
- **Contextual ao papel**: aderência a funções como zagueiro de cobertura, meia armador, ponta de profundidade.

Essa última camada é fundamental para modernizar o design sem descaracterizar o DNA de CM.

### 5. Board, mídia e cirurgia/reabilitação

CM01/02 também ampliou a interação com **board e mídia** e adicionou a possibilidade de enviar jogadores para **cirurgia**, reforçando o papel do treinador como gestor institucional, não apenas escalador.[cite:2]

#### Board

- objetivos esportivos e financeiros;
- nível de confiança;
- pedidos de orçamento e instalações;
- risco de demissão;
- pressão por elenco, juventude, vendas ou estilo de jogo.

#### Mídia

- notícias diárias;
- rumores de mercado;
- perguntas pré e pós-jogo;
- impacto sobre moral, reputação e ambiente.

#### Reabilitação/cirurgia

- indicação médica baseada em lesão recorrente;
- decisão do usuário com custo e prazo;
- efeito em risco futuro e disponibilidade.

Esses sistemas devem permanecer, mas com telemetria mais clara e feedback explicável para um público moderno.[cite:2]

## Arquitetura funcional detalhada

### Módulo 1 — Simulação de mundo

Responsável por processar o calendário, gerar partidas, aplicar fadiga, treinos, lesões, moral, suspensões e repercussão. Esse módulo nunca conversa diretamente com a interface; ele apenas publica estados e eventos.

**Submódulos**:
- agenda e calendários;
- resolução de partidas;
- condição física e médica;
- moral e dinâmica social;
- reputação e forma;
- progressão temporal.

### Módulo 2 — Banco de dados mundial

CM01/02 já operava com cerca de 100 ligas em 27 países, e esse senso de mundo vivo é parte do valor percebido do jogo.[cite:2] A nova versão deve usar uma base relacional ou orientada a documentos com indexação por pessoa, clube, competição, país e temporada.

**Requisitos**:
- IDs estáveis para jogador, clube, competição e staff;
- histórico de temporadas;
- regras por federação;
- armazenamento de atributos reais e conhecidos em camadas separadas;
- suporte nativo a editor pré-jogo, inspirado na direção em que CM03/04 avançou com database editor e expansão de ligas/dados.[cite:1]

### Módulo 3 — Conhecimento e scouting

Esse módulo é o diferencial estratégico. Ele controla o que pode ser visto, quando pode ser visto e com que confiabilidade.

**Entradas**:
- reputação do clube;
- rede de scouts;
- cobertura geográfica;
- jogos assistidos;
- exposição por competições.

**Saídas**:
- nível de conhecimento por jogador;
- relatórios;
- shortlist qualificada;
- atualização de faixas para números exatos.

### Módulo 4 — Gestão esportiva

Abrange seleção, tática, funções, treino, staff, hierarquia do elenco e preparação para partidas. Mesmo quando o motor de partida for mais moderno, o loop decisório deve continuar leve e frequente, como nos jogos clássicos da série.[cite:2][cite:1]

### Módulo 5 — Mercado e contratos

CM01/02 incorporou o novo sistema regulatório europeu de transferências, o que mostra que regras legais e econômicas podem ser parte do gameplay e não só pano de fundo.[cite:2] No novo jogo, esse módulo deve tratar:

- oferta por jogador;
- negociação salarial;
- bônus e cláusulas;
- agentes;
- proteção contratual;
- elegibilidade e registro.

### Módulo 6 — Narrativa sistêmica

A inbox é o coração da experiência. O usuário não deve “consultar sistemas”; ele deve receber o mundo pelos eventos da caixa de entrada e navegar para agir.

**Tipos de mensagem**:
- relatório de scout;
- reação de mídia;
- cobrança do board;
- atualização médica;
- reclamação de jogador;
- notícia de mercado;
- prêmio, recorde ou marco.

### Módulo 7 — UI shell e navegação

A interface deve priorizar listas, abas, filtros e drill-down. O padrão é: **visão geral → lista → detalhe → ação → retorno à inbox ou dashboard**.

## Diagrama de telas

### Mapa principal de navegação

```text
[TELA INICIAL]
 ├─ Novo Jogo
 │   ├─ Seleção de Base / Regras
 │   ├─ Seleção de Ligas Ativas
 │   ├─ Escolha de Clube/Perfil
 │   └─ Configuração de Dificuldade / Masking
 ├─ Carregar Jogo
 ├─ Editor Pré-jogo
 └─ Opções

[DASHBOARD / INBOX]
 ├─ Caixa de Entrada
 ├─ Próxima Partida
 ├─ Elenco
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
 ├─ Banco de Dados / Pesquisa
 └─ Histórico
```

### Fluxo de elenco e jogador

```text
[Elenco]
 ├─ Lista Geral
 │   ├─ Filtros
 │   ├─ Registro / Inscrição
 │   ├─ Hierarquia
 │   └─ Comparar Jogadores
 └─ [Perfil do Jogador]
     ├─ Visão Geral
     ├─ Atributos
     ├─ Condição
     ├─ Tática / Papel
     ├─ Histórico
     ├─ Contrato
     ├─ Relatórios
     ├─ Notas
     ├─ Relações
     └─ Ações
         ├─ Conversar
         ├─ Colocar à venda
         ├─ Renovar contrato
         ├─ Enviar para cirurgia
         └─ Adicionar à shortlist
```

### Fluxo de scouting e mercado

```text
[Scouting]
 ├─ Dashboard de Cobertura
 ├─ Scouts
 ├─ Missões Ativas
 ├─ Relatórios Recebidos
 ├─ Shortlist
 ├─ Pesquisa de Jogadores
 │   ├─ Filtro por posição
 │   ├─ Filtro por papel
 │   ├─ Filtro por atributos conhecidos
 │   ├─ Filtro por custo
 │   └─ Filtro por região/competição
 └─ [Perfil do Alvo]
     ├─ Atributos Mascarados
     ├─ Relatório do Scout
     ├─ Comparação com Elenco
     ├─ Interesse / Disponibilidade
     └─ Fazer Oferta
```

### Fluxo de partida

```text
[Próxima Partida]
 ├─ Preparação
 │   ├─ Escalação
 │   ├─ Instruções
 │   ├─ Oposição
 │   └─ Briefing do Staff
 ├─ Match View
 │   ├─ Campo 2D / Visual simplificado
 │   ├─ Comentário
 │   ├─ Estatísticas
 │   ├─ Eventos
 │   └─ Ajustes em tempo real
 └─ Pós-jogo
     ├─ Resultado
     ├─ Ratings
     ├─ Reações
     └─ Inbox
```

### Fluxo institucional

```text
[Clube]
 ├─ Visão Geral
 ├─ Staff
 ├─ Instalações
 ├─ Juventude
 ├─ Finanças
 └─ História

[Board]
 ├─ Confiança
 ├─ Objetivos
 ├─ Pedidos
 ├─ Reuniões
 └─ Risco de Demissão

[Mídia]
 ├─ Notícias
 ├─ Rumores
 ├─ Coletivas
 └─ Reputação Pública
```

## Especificação de páginas-chave

### 1. Dashboard / Inbox

É a tela principal do jogo. Toda mudança importante precisa aparecer aqui como mensagem clicável. A tela deve combinar:

- lista cronológica de mensagens;
- próximo compromisso;
- status rápido de moral, lesões e confiança do board;
- alertas de mercado e scouting;
- botão de avançar o tempo.

A regra de design é simples: o usuário nunca deve se perguntar “o que faço agora?”. A inbox deve responder isso.

### 2. Perfil do jogador

Essa é a tela mais importante do jogo. Ela precisa concentrar profundidade sem ficar opaca.

#### Blocos essenciais

- cabeçalho com nome, idade, clube, nacionalidade, posição e status;
- painel de atributos com masking;
- condição física, moral e forma;
- papel sugerido e adequação tática;
- histórico de partidas e desempenho;
- contrato e valor de mercado;
- notas, relatórios e comparação.

#### Regras modernas úteis

- mostrar **fonte do conhecimento** em cada atributo revelado;
- indicar **última atualização** do relatório;
- destacar **inconsistências** entre scouts diferentes;
- permitir comparação instantânea com titular da mesma posição.

### 3. Pesquisa de jogadores

A pesquisa é o motor do “vício bom” do jogo. Para um híbrido moderno, essa página deve preservar a magia de descobrir talentos, sem virar planilha fria.

#### Colunas recomendadas

- nome;
- idade;
- posição principal/secundária;
- clube;
- reputação;
- custo estimado;
- salário estimado;
- status de observação;
- atributos conhecidos-chave;
- encaixe no papel selecionado.

#### Filtros recomendados

- posição;
- faixa etária;
- nacionalidade / região;
- destro/canhoto;
- atributos mínimos conhecidos;
- faixa de preço;
- expiração contratual;
- disponibilidade para transferência/empréstimo.

### 4. Tela de scouting

Deve mostrar o estado da rede de observação do clube.

#### Componentes

- mapa/regiões cobertas;
- scouts e suas especialidades;
- fila de missões;
- relatórios recentes;
- taxa de acerto histórica;
- custo mensal do departamento.

Essa página transforma scouting de “botão utilitário” em subsistema estratégico.

## Dicionário de termos do jogo

### Atributos

Os atributos devem ser agrupados por famílias. O ideal é manter um conjunto clássico, inspirado na legibilidade dos managers antigos, mas com nomenclatura consistente e ligada a efeitos claros.

| Grupo | Atributo | Definição sistêmica |
|---|---|---|
| Técnico | Finalização | Qualidade ao concluir chances |
| Técnico | Passe | Precisão e variedade de distribuição |
| Técnico | Drible | Capacidade de conduzir em pressão |
| Técnico | Primeiro toque | Qualidade da recepção e preparação |
| Técnico | Cruzamento | Eficiência em bolas para a área |
| Técnico | Marcação | Capacidade de acompanhar e bloquear adversários |
| Técnico | Desarme | Execução do tackle e roubo limpo |
| Técnico | Cabeceio | Força e precisão no jogo aéreo |
| Técnico | Técnica | Refinamento geral em execução com bola |
| Mental | Decisões | Escolha da melhor ação sob contexto |
| Mental | Antecipação | Leitura do que vai acontecer |
| Mental | Posicionamento | Ocupação inteligente de espaço |
| Mental | Composure | Controle emocional sob pressão |
| Mental | Trabalho em equipe | Disposição para cooperar taticamente |
| Mental | Determinação | Persistência diante de adversidade |
| Mental | Visão | Capacidade de enxergar linhas de passe e jogadas |
| Mental | Sem bola | Movimentação ofensiva inteligente |
| Mental | Agressividade | Intensidade competitiva e confronto |
| Físico | Velocidade | Pico de deslocamento |
| Físico | Aceleração | Arranque nos primeiros metros |
| Físico | Resistência | Capacidade de sustentar ritmo |
| Físico | Força | Poder de choque e proteção |
| Físico | Agilidade | Mudança de direção e equilíbrio corporal |
| Físico | Impulsão | Capacidade de salto |
| Goleiro | Reflexos | Reação a finalizações |
| Goleiro | Um contra um | Eficiência em situações diretas |
| Goleiro | Saída do gol | Decisão e alcance em cruzamentos/bolas longas |
| Goleiro | Manuseio | Segurança ao segurar ou espalmar |
| Goleiro | Reposição | Qualidade na distribuição com mãos e pés |

### Estados derivados

Além dos atributos-base, o jogo deve usar valores derivados para explicar desempenho.

- **Forma**: rendimento nas últimas partidas.
- **Moral**: estado emocional atual.
- **Sharpness**: prontidão competitiva recente.
- **Condition**: energia imediata para jogar.
- **Match fitness**: capacidade de sustentar uma partida oficial.
- **Risk index**: probabilidade de queda de rendimento, lesão ou adaptação ruim.

### Posições

O jogo deve separar **posição nominal** de **papel funcional**.

#### Posições nominais

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

Papéis funcionais modernizam a leitura sem destruir a lógica clássica. Eles permitem que um mesmo jogador tenha posição igual, mas uso totalmente diferente.

| Papel | Posições típicas | Descrição |
|---|---|---|
| Zagueiro de cobertura | DC | recua, protege profundidade, corrige linha |
| Zagueiro agressivo | DC | antecipa, sobe no duelo, quebra jogadas |
| Lateral construtor | DR/DL | apoia por dentro e participa da circulação |
| Lateral de profundidade | DR/DL | dá amplitude e cruza com frequência |
| Volante destruidor | DMC | protege defesa e vence duelos |
| Regista | DMC/MC | organiza de trás com visão e passe |
| Box-to-box | MC | percorre áreas e impacta ataque/defesa |
| Armador avançado | AMC/MC | cria passes decisivos entre linhas |
| Meia de chegada | MC/AMC | ataca área e finaliza |
| Winger clássico | AMR/AML | busca linha de fundo e cruzamento |
| Inside forward | AMR/AML | corta para dentro para finalizar |
| Segundo atacante | AMC/ST | conecta meio e ataque, flutua |
| Homem-alvo | ST/FC | segura jogo e disputa bolas longas |
| Atacante de ruptura | ST | explora profundidade e aceleração |
| Finalizador de área | FC | vive da última linha e do último toque |

### Atributos críticos por papel

| Papel | Atributos prioritários |
|---|---|
| Zagueiro de cobertura | antecipação, posicionamento, aceleração, marcação |
| Volante destruidor | marcação, desarme, trabalho em equipe, resistência |
| Regista | passe, visão, decisões, compostura |
| Armador avançado | visão, passe, técnica, primeiro toque |
| Winger clássico | aceleração, drible, cruzamento, agilidade |
| Inside forward | drible, aceleração, finalização, sem bola |
| Homem-alvo | força, cabeceio, primeiro toque, compostura |
| Atacante de ruptura | aceleração, sem bola, finalização, decisões |

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
- attributes_real{}
- attributes_known{}
- personality{}
- medical{}
- morale_state
- form_state
- contract_id
- club_id
- reputation_local
- reputation_world
- notes_user[]
- notes_system[]
- knowledge_sources[]
```

### Scout report

```text
ScoutReport
- report_id
- player_id
- scout_id
- mission_id
- created_at
- confidence_score
- observed_matches
- role_projection
- strengths[]
- weaknesses[]
- hidden_risks[]
- transfer_estimate
- wage_estimate
- adaptation_risk
- injury_risk
- summary_text
- attributes_revealed{}
```

### Knowledge state

```text
KnowledgeState
- subject_type (player/club/league)
- subject_id
- observer_club_id
- knowledge_level
- last_updated_at
- source_type (match/scout/media/internal)
- certainty
- visible_fields[]
```

## Regras de UX para um híbrido moderno

### 1. Densidade com clareza

CM01/02 era amado por permitir operar rápido dentro de muita informação.[cite:2] O novo jogo deve manter listas densas, mas com:

- ordenação inteligente;
- presets de colunas;
- hover para definição rápida;
- filtros salvos;
- comparação inline.

### 2. Explicabilidade

Quando um jogador rende mal, o jogo deve dizer por quê. Exemplos:

- “queda de sharpness por 3 partidas sem jogar”; 
- “moral baixa após promessa quebrada”; 
- “atributo estimado revisado após 4 observações”.

### 3. Descoberta como recompensa

A descoberta de talentos deve ser um prazer sistêmico. Relatórios, torneios de base, observação regional e comparação com seu elenco precisam produzir sensação de achado, não apenas checklist.

## Roadmap de implementação sugerido

### Fase 1 — Vertical slice

- dashboard/inbox;
- perfil de jogador;
- banco de dados básico;
- attribute masking;
- scouting de jogador;
- comparação lado a lado;
- mercado simples.

### Fase 2 — Núcleo de temporada

- calendário completo;
- geração de partidas;
- moral, forma e condição;
- board e mídia;
- notas de jogador;
- cirurgia/reabilitação.

### Fase 3 — Modernização

- papéis funcionais;
- relatórios explicáveis;
- replay de partidas;
- editor pré-jogo;
- analytics avançado;
- mod support.

## Decisões de design mais importantes

1. **Masking não é opcional de luxo; é o centro do loop de descoberta.** Isso vem diretamente da inovação mais marcante de CM01/02.[cite:2]
2. **Scouting deve gerar conhecimento, não apenas opinião.** O relatório precisa alterar o estado de visibilidade do mundo.
3. **Perfil de jogador é a tela sagrada do produto.** A maior parte da profundidade deve convergir para ela.
4. **Posição e papel são coisas diferentes.** Essa é a principal ponte entre o classicismo de CM e a legibilidade moderna.
5. **Inbox é a espinha dorsal da experiência.** O jogador precisa sentir que governa um clube vivendo num mundo ativo.
6. **Regras regulatórias e médicas devem ter gameplay real.** CM01/02 já mostrava isso com sistema de transferências da UE e cirurgia de jogadores.[cite:2]

## Encerramento técnico

Um sucessor espiritual de CM01/02 não precisa copiar sua interface pixel a pixel; ele precisa copiar sua filosofia: um mundo vasto, informação imperfeita, listas rápidas, consequências persistentes e prazer de descobrir vantagem antes dos outros.[cite:2] A modernização correta não substitui essa base por espetáculo visual, e sim adiciona explicabilidade, papéis funcionais, melhor comparação e navegação mais inteligente, preservando o coração da experiência clássica.[cite:2][cite:1]
