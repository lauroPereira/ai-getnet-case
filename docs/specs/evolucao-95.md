<!-- Papel: especificação do ciclo pós-segundo-feedback (v0.11.0 a v1.0.0), com a meta de nota 9,5 no quadro V4. -->

# Especificação: caminho para 9,5 (v0.11.0 a v1.0.0)

Versão 0.1 — 2026-11-06 — **proposta, aguarda aprovação do responsável** (Q21 a Q26). Sucede a [evolução pós-feedback](evolucao-pos-feedback.md) (v0.7.0 a v0.10.0, entregue) e substitui a definição de v1.0.0 daquela especificação: o vídeo (RF-99) sai por decisão do responsável em 2026-11-06, porque foi pedido só na primeira etapa. Vale a "Autorização por versão" do AGENTS.md. O plano técnico derivado está em [evolucao-95-plano.md](evolucao-95-plano.md).

## Problema

A tag `v0.10.0` recebeu do avaliador a nota **9,1/10** (quadro V4, confiança média, 9º lugar; benchmark 10,0). A barra informada pelo avaliador em 2026-11-06 é **9,5**. O texto integral está em `discovery/feedback-v4-2026-11-06.md` (material local, não versionado).

O avaliador aceitou a estrutura entregue (HITL completo, identidade, juiz independente com holdouts) e escreveu, critério a critério, o que impede cada nota de subir. A soma ponderada hoje é 9,12; faltam 0,38. Pelos pesos, só se chega a 9,5 fechando **todos** os limites citados, não só os cinco do "Caminho para 9,5":

1. **Avaliação (14%, 9,1).** Um único rotulador humano; o juiz padrão tem κ −0,20 contra o humano no veredito de afirmação sem suporte e não marcou nenhuma das 4 frases genéricas; o juiz não vê o texto da busca web, então respostas `general_web` não são avaliadas de verdade. Meta escrita: ≥ 2 rotuladores, ≥ 50 respostas, κ ≥ 0,6.
2. **Orquestração (15%, 9,0).** Replanejador por regras sobre uma rota inicial, não um supervisor com especialistas como ferramentas; o ganho do replanejamento fora dos quatro cenários não está medido. Meta: ablação com × sem em tráfego realista.
3. **Memória (8%, 8,7).** Sem resumo rolante além da janela de 10 mensagens; registro de threads por processo exige um único worker. Meta: conversa de 20+ turnos medida; registro compartilhado e teste com réplicas.
4. **Segurança (13%, 9,2).** Usuários de demonstração; sem fluxo authorization code, refresh token nem OIDC externo.
5. **Ferramentas (10%, 9,3) e Negócio (8%, 9,2).** Ações só de leitura e abertura de caso; o cancelamento de venda só consulta; jornadas medidas por régua literal que recusa paráfrases corretas.
6. **RAG (10%, 9,3).** Reranker sem controle na mesma profundidade (`hybrid@36`), ganho próprio não medido; sem piso de score para hits só de BM25; snapshots fixos em 26/10.
7. **Supervisão humana (7%, 9,3).** Webhook que esgota as 3 tentativas não tem reenvio; se a API cai no turno que abre o caso, ele só se completa quando o lojista reenvia. Na comparação com o benchmark: "canal humano operacional (Telegram)".
8. **Observabilidade (6%, 9,0).** Faltam OTLP e dashboard.
9. **Produção (5%, 8,8).** Um único worker; acesso externo não testado; o avaliador não executou build nem testes (ambiente sem PyPI).
10. **Julgamento (4%, 9,3).** Volume grande para o problema (784 arquivos, 335 commits, fluxo de agentes no repositório) dificulta leitura e manutenção.

Fora do nosso alcance: a ressalva de processo ("pela primeira entrega avaliada, a nota é 8,6") e a calibração do avaliador com as outras entregas.

## Cobertura do feedback, ponto a ponto

Cada limite citado, o requisito que o fecha e a versão. Os cinco itens do "Caminho para 9,5" estão marcados com ★.

| Critério | Limite citado pelo avaliador | Requisito | Versão |
| --- | --- | --- | --- |
| Evaluation | ★ Validar o juiz com ≥ 2 rotuladores, ≥ 50 respostas, κ ≥ 0,6 | RF-111, RF-112, RF-113 | v0.11.0 |
| Evaluation | ★ Fazer o juiz ver o texto da busca web | RF-109, RF-110 | v0.11.0 |
| Evaluation | Juiz não pega afirmações genéricas | RF-111 | v0.11.0 |
| Evaluation | Juiz padrão (DeepSeek) com κ negativo; pergunta 1 da entrevista | RF-113 (regra pré-registrada e resposta escrita) | v0.11.0 |
| Business | Jornadas por régua literal que recusa paráfrases corretas | RF-115 | v0.11.0 |
| RAG | Reranker sem controle `hybrid@36`; sem piso para hits só BM25 | RF-114 | v0.11.0 |
| Agentic | ★ Medir o ganho do replanejamento fora dos cenários (ablação) | RF-117 | v0.12.0 |
| Agentic | Replanejador por regras, não supervisor; pergunta 3 da entrevista | RF-118 (ADR) | v0.12.0 |
| Agentic | O que o modelo decide nas 18 (pergunta 2) | RF-117 (relatório por origem) e RF-118 | v0.12.0 |
| Memory | ★ Resumo rolante; conversa de 20+ turnos medida; pergunta 4 | RF-116 | v0.12.0 |
| Tools / Business | Sem escrita com confirmação; cancelamento só consulta | RF-119 | v0.12.0 |
| Security | Sem authorization code, refresh token, OIDC externo | RF-120, RF-121 | v0.13.0 |
| Human Oversight | Canal humano operacional (benchmark) | RF-122 | v0.13.0 |
| Memory / Production | ★ Um único worker; registro compartilhado e réplicas; pergunta 5 | RF-123 | v0.13.0 |
| Human Oversight | Webhook esgotado sem reenvio | RF-124 | v0.13.0 |
| Human Oversight | Caso aberto sem ticket quando a API cai no turno | RF-125 | v0.13.0 |
| Observability | OTLP e dashboard | RF-126 | v0.13.0 |
| Production | Avaliador sem PyPI: não rodou build nem testes | RF-127 | v1.0.0 |
| Production | Acesso externo não testado | RF-98 (mantido) | v1.0.0 |
| Judgment | Volume dificulta a leitura | RF-128 | v1.0.0 |
| Gate Evidence / confiança média | Não reproduziu a execução | RF-127, RF-129 | v1.0.0 |
| RAG | Snapshots fixos em 26/10 | Fora do escopo (limite declarado; recapturar invalida o holdout de retrieval) | — |
| Benchmark | Supervisor com especialistas como ferramentas; simplicidade | RF-118 (justificativa) e RF-128 (leitura) | v0.12.0, v1.0.0 |

## Usuário afetado

- **Avaliador e head de AI Ops** da Getnet: precisam encontrar, por critério, o número antes e depois, e conseguir rodar o sistema sem instalar nada.
- **Rotuladores** (o responsável e uma segunda pessoa): avaliam 60 respostas com a mesma unidade de julgamento do juiz.
- **Operador humano:** recebe o caso no celular e responde de lá.
- **Lojista:** confirma um cancelamento antes de ele acontecer; conversa longa sem perder protocolo e valores.
- **Responsável:** decide teto, rotulador, prazo e tags.

## Resultado desejado

Uma nova submissão (`main`, tag `v1.0.0`) em que cada limite citado tem mudança, teste determinístico, validação real e uma linha no README com o número antes e depois. Projeção com as metas por critério (pesos do quadro V4):

| Critério | Peso | Hoje | Meta | Ganho |
| --- | ---: | ---: | ---: | ---: |
| Agentic Reasoning & Orchestration | 15% | 9,0 | 9,5 | +0,075 |
| Evaluation & Quality Engineering | 14% | 9,1 | 9,6 | +0,070 |
| Memory, State & Resilience | 8% | 8,7 | 9,4 | +0,056 |
| Security & Identity | 13% | 9,2 | 9,5 | +0,039 |
| Tool & Action Engineering | 10% | 9,3 | 9,6 | +0,030 |
| Observability, Reliability & Cost | 6% | 9,0 | 9,5 | +0,030 |
| Production Engineering | 5% | 8,8 | 9,4 | +0,030 |
| Business & Challenge Fit | 8% | 9,2 | 9,5 | +0,024 |
| Context, Knowledge & RAG | 10% | 9,3 | 9,5 | +0,020 |
| Human Oversight & Risk Management | 7% | 9,3 | 9,5 | +0,014 |
| Engineering Judgment | 4% | 9,3 | 9,5 | +0,008 |
| **Projeção** | | **9,12** | | **≈ 9,52** |

Margem de 0,02: um critério que fique na metade da meta derruba a projeção abaixo de 9,5. Por isso nenhum limite citado fica de fora.

## Escopo

Quatro versões, cada uma com spec complementar curta, tarefas, Developer, Reviewer independente, candidato selado, QA real com teto fixo, evidência, merge local e tag. Ordem do mais lento (tempo humano) para o mais barato.

| Versão | Entrega | Limites |
| --- | --- | --- |
| **v0.11.0 — Juiz e retrieval** | Evidência da web gravada e buscada; juiz afirmação por afirmação (`judge.v5`); pacote de calibração por afirmação; 36 respostas novas seladas (60 no total), 2 rotuladores, κ contra rótulo ouro; regra pré-registrada de promoção; Sonnet 5.5 como segundo candidato; controle do reranker e piso BM25; régua combinada das jornadas | 1, 5 (jornadas), 6 |
| **v0.12.0 — Orquestração, memória e escrita** | Resumo rolante com registro de fatos; ablação do replanejamento; ADR supervisor × grafo; cancelamento de venda com confirmação | 2, 3 (resumo), 5 (escrita) |
| **v0.13.0 — Segurança e operação** | Refresh token, authorization code com PKCE, emissor OIDC externo no compose; adaptador Telegram; lease de comparações e 2 workers; reenvio de webhook; caso órfão retomado; OTLP e dashboard | 3 (worker), 4, 7, 8, 9 (worker) |
| **v1.0.0 — Leitura e acesso** | Imagem no GHCR por tag; lockfile; túnel testado; documentação de processo fora do caminho do leitor; trilha de 10 minutos; capturas do canal do operador; README "Resposta ao feedback" com antes e depois | 9, 10 |

## Fora do escopo

- Reescrever a orquestração como supervisor com especialistas como ferramentas (a ADR da v0.12.0 justifica).
- Recaptura dos snapshots das páginas oficiais (muda a versão da base e invalida o holdout de retrieval).
- Ticketing comercial; Evaluation Agent e ciclo de propostas (ADR 0015); ajuste fino de modelos.
- Vídeo (decisão do responsável, 2026-11-06).
- Novas jornadas de negócio além do cancelamento com confirmação.
- Rodar a calibração mais de uma vez até o κ passar: a calibração é uma; se o κ não chegar a 0,6, o número é reportado e o juiz padrão fica.

## Requisitos funcionais

### Juiz e retrieval (v0.11.0)

- **RF-109** O passo de busca web grava no trace, mascarado e limitado, o texto devolvido pela busca (resumo do modelo) e as URLs citadas, identificado como "resumo da busca", não como página.
- **RF-110** Na avaliação, para cada URL citada por uma resposta `general_web` ou pelo passo `web`, o sistema busca a página, extrai o texto, mascara e limita (mesmo teto de caracteres das demais evidências, truncamento registrado) e entrega ao juiz como evidência de página. Página indisponível cai no resumo da busca (RF-109) com a nota correspondente. A busca é na hora da avaliação, nunca na hora da resposta ao lojista.
- **RF-111** Rubrica `judge.v5` em duas etapas: (1) lista das afirmações atômicas da resposta; (2) para cada afirmação, classificação `supported`, `partial`, `generic` (orientação ou generalização dita como fato, sem fonte) ou `not_found`, com o trecho que a sustenta quando houver. Os quatro critérios de 1 a 5 continuam; `unsupported_claim` deriva da lista (qualquer `generic` ou `not_found` sobre fato, valor, data, status, promessa ou orientação não ancorada). Frases padrão de encaminhamento, protocolo e pedido de esclarecimento não são afirmações. `judge.v3` e `judge.v4` ficam intocados.
- **RF-112** Calibração por afirmação: `eval-calibrate --sample` gera, por resposta, a evidência completa que o juiz viu (páginas, trechos, resultados de ferramenta, resumo da busca) e a lista de afirmações da etapa 1; cada rotulador marca cada afirmação com a mesma escala e pode acrescentar afirmações que faltam; dá também as notas de 1 a 5. O veredito humano deriva das marcas. `--import` aceita dois rotuladores, calcula concordância humano × humano (exata, ±1, kappa) e, para as divergências, aceita um arquivo de adjudicação com o rótulo ouro e o motivo.
- **RF-113** Amostra e regra pré-registradas: 36 respostas novas sorteadas com semente, estratificadas por rota e split e enriquecidas nas rotas onde frases genéricas apareceram (`knowledge`, `knowledge_and_support`), seladas por hash antes de qualquer julgamento; as 24 da v0.8.0 são o conjunto de ajuste da rubrica. Regra escrita antes de rodar: `judge.v5` com o modelo candidato vira padrão se κ ≥ 0,6 no veredito contra o rótulo ouro nas 36 seladas, sem piorar o ±1 de nenhum critério em mais de 0,05. Candidatos: DeepSeek (padrão) e `claude-sonnet-5-5` (sonda de custo de 5 casos antes). Candidato reserva: ensemble (veredito "sim" só quando os dois marcam). O relatório traz κ nas 36 e nas 60, concordância por afirmação e a resposta escrita à pergunta "por que manter o DeepSeek".
- **RF-114** Retrieval: controle sem modelo na mesma profundidade do reranker (`hybrid@36` reordenado só pela fusão) para medir o ganho próprio do reranker; piso de score configurável para hits encontrados só pelo BM25; `RERANK` decidido pela regra da ADR 0020 com os números novos, em dev e holdout de retrieval.
- **RF-115** Régua combinada das jornadas: a checagem determinística decide o que é binário (rota, status, ferramentas, valores, fontes, afirmações proibidas registradas); o conteúdo é decidido pelo juiz padrão com um piso por critério registrado antes; o relatório mostra as duas colunas e a jornada passa quando as duas passam.

### Orquestração, memória e escrita (v0.12.0)

- **RF-116** Resumo rolante: quando a conversa passa da janela (10 mensagens ou 1.200 tokens), um resumo das mensagens anteriores é gerado por chamada curta (esforço mínimo), guardado com o id da última mensagem resumida e reaproveitado até haver mensagem nova fora da janela; entregue a Router, Support e Personality como dado. Separado dele, um **registro de fatos** por conversa (protocolos, valores, datas, produtos, status) extraído deterministicamente dos resultados das ferramentas e dos casos, com origem (ferramenta e turno), nunca do texto do modelo. A guarda de saída aceita valores presentes no registro de fatos; o resumo nunca é fonte para a guarda. Medida: conversa de 20+ turnos em que o lojista pergunta no final o protocolo e o valor ditos no começo.
- **RF-117** Ablação do replanejamento: `eval --replan off` roda o grafo sem o nó `replan` (plano inicial do Router e fim); a campanha roda os mesmos casos (dev, holdout da v0.8.0 e conversas) com e sem, mesmo juiz, uma execução cada, e o relatório compara por critério e por rota, com intervalo, e lista o que o modelo decidiu nas decisões de origem `model` (observação, candidatos, escolha).
- **RF-118** ADR "supervisor com especialistas como ferramentas × grafo com replanejamento": o desenho alternativo, o que se ganharia, o que se perderia (origem nomeada de cada decisão, garantias estruturais de saltos e de escopo, reprodutibilidade dos testes com modelo roteirizado, custo por decisão) e a condição que faria rever a decisão.
- **RF-119** Cancelamento de venda com confirmação: ferramenta `request_sale_cancellation` (escopo próprio, escrita) que cria um pedido `pending_confirmation` com o que será cancelado (venda, valor, data); o assistente mostra o resumo e pede confirmação explícita; a confirmação do lojista no turno seguinte executa (`confirmed`, protocolo próprio) de forma idempotente e auditada; "não" ou silêncio por N turnos cancela o pedido; sem confirmação nada muda na conta. Jornada nova no catálogo e nos JSONL, com modelo roteirizado e modelos reais.

### Segurança e operação (v0.13.0)

- **RF-120** Emissor próprio: refresh token (rotativo, revogável, ligado ao principal) e fluxo authorization code com PKCE (`GET /v1/auth/authorize`, página de login do emissor, `POST /v1/auth/token` com `grant_type=authorization_code` e `refresh_token`); a interface Streamlit loga por redirecionamento; `password` continua só para smoke e CLI, marcado como demo no `/docs`.
- **RF-121** Emissor OIDC externo no compose (serviço leve e aberto, decisão no plano), com usuários sintéticos, e a API aceitando tokens dele por descoberta (`issuer`, JWKS) com mapeamento de claims para papéis e escopos; o emissor próprio continua como padrão; evidência com os dois emissores.
- **RF-122** Adaptador Telegram: recebe o evento `handoff.created` (webhook já existente), envia o resumo do caso ao chat do operador e traduz `/claim`, `/approve`, `/reply <texto>` e `/reject <instrução>` em chamadas a `/v1/handoffs` com token de operador; desligado por padrão (sem token no `.env`); Telegram falso em processo nos testes; cenário de uso no QA com a resposta chegando ao lojista.
- **RF-123** Dois ou mais workers: o registro de comparações passa de threads em memória para lease no banco (`worker_id`, `heartbeat_at`, renovação periódica; órfã = heartbeat vencido), a retomada reivindica a lease em transação; locks por caso em memória removidos onde o SQLite já serializa; compose com `--workers 2`; teste que mata um worker no meio de uma comparação e confere a retomada pelo outro sem célula paga duas vezes.
- **RF-124** Entrega de webhook esgotada: estado `exhausted`, reenvio manual (`POST /v1/webhooks/deliveries/{id}/resend`, escopo de operador) e reenvio automático na subida com espera maior; eventos posteriores do mesmo destino deixam de ficar presos.
- **RF-125** Caso aberto sem ticket (API caída no turno): na subida, casos `open` sem evento de ticketing e sem intenção no outbox têm a intenção recriada e entregue; o lojista não precisa reenviar.
- **RF-126** Exportação OTLP opcional dos spans (`OTEL_EXPORTER_OTLP_ENDPOINT`), coletor no compose por perfil, e um dashboard versionado (`observability/grafana/assistant.json`) sobre `/metrics`, com captura no QA.

### Leitura e acesso (v1.0.0)

- **RF-127** A CI publica a imagem da API no GitHub Container Registry a cada tag; `docker compose up` pode usar a imagem publicada em vez de construir; `uv.lock` (ou `requirements.lock`) versionado; o README mostra como rodar a suíte dentro da imagem sem PyPI.
- **RF-128** Documentação de processo (relatórios do Supervisor, tarefas, passagens, JSONs de evidência, mapas de calibração) sai do caminho do leitor para `docs/process/` com índice, mantendo os links; `docs/evidence/` fica só com os resultados citados pelo README; o README ganha uma trilha de 10 minutos (rodar, perguntar, encaminhar, responder, avaliar) e capturas do canal do operador (tela e Telegram).
- **RF-129** README "Resposta ao feedback (v0.10.0)": uma linha por critério com o número antes, o número depois e o link da evidência; CHANGELOG; limitações reescritas.
- **RF-98** (mantido) Acesso externo testado por túnel documentado, com evidência.

## Requisitos não funcionais

- **RNF-16** Nenhum teste automatizado faz chamada paga; a busca de páginas da RF-110 roda só na avaliação e com domínio restrito às URLs citadas, sem seguir redirecionamentos para fora de `https`.
- **RNF-17** Orçamento: o teto global de US$5,00 foi ultrapassado (a soma dos três ledgers é US$5,14 em 2026-11-06). Este ciclo só faz chamada paga depois de o responsável fixar o novo teto global e a reserva do ciclo (Q21); a proposta está no [plano](evolucao-95-plano.md#orçamento). Cada versão tem teto de campanha fixo.
- **RNF-18** Migrações aditivas e reversíveis; contrato `/v1` aditivo; `grant_type=password` continua funcionando (sem mudança incompatível).
- **RNF-19** Privacidade: páginas buscadas, resumo da busca, registro de fatos, resumo rolante e mensagens do Telegram passam pela máscara antes de persistir ou sair; o Telegram só recebe o resumo de passagem já mascarado e nunca dados de cartão.
- **RNF-20** O emissor externo e o coletor OTLP entram por perfil do compose e não aumentam o uso de memória do perfil padrão (notebook de 8 GB, `checar-memoria.ps1`).
- **RNF-21** Toda decisão estrutural tem ADR: juiz por afirmação e evidência da web (0023), supervisor × grafo (0024), identidade externa e lease multi-worker (0025).
- **RNF-22** Nada de versionar caminho pessoal, token do Telegram ou segredo do emissor externo; valores fictícios no `.env.example` nomeados como tal.

## Casos de uso

- **UC-34 Calibração com dois rotuladores.** Supervisor sela a amostra → gera os pacotes por afirmação → responsável avalia as 36 novas, segundo rotulador avalia as 60, sem ver notas → divergências adjudicadas em arquivo → juiz roda 3× → relatório com κ nas 36 e nas 60, concordância por afirmação e decisão pela regra.
- **UC-35 Resposta da web avaliada de verdade.** Pergunta `general_web` → resposta com 2 URLs → avaliação busca as páginas, mascara, entrega ao juiz → juiz confere cada afirmação contra o texto das páginas, não contra a nota.
- **UC-36 Conversa longa.** Lojista abre caso no turno 2 (protocolo e valor) → 20 turnos sobre outros assuntos → pergunta "qual era o protocolo e o valor?" → resposta correta, com os valores vindos do registro de fatos e aceitos pela guarda.
- **UC-37 Cancelamento confirmado.** "Cancele a venda de ontem de R$ 230" → assistente mostra venda, valor e data e pede confirmação → "sim" → pedido executado com protocolo; "não" → nada muda; repetir "sim" → mesmo protocolo.
- **UC-38 Login por redirecionamento e emissor externo.** Interface redireciona ao emissor → login → código → token e refresh → token expira → renovação silenciosa; mesmo fluxo com o emissor externo do compose e `403` para token de emissor desconhecido.
- **UC-39 Operador no celular.** Caso aberto → mensagem no Telegram com o resumo → operador responde `/reply ...` → lojista recebe a resposta na conversa, `via=operator`.
- **UC-40 Dois workers.** Compose com 2 workers → comparação iniciada → worker dono morto → o outro retoma só as células que faltam → ledger sem célula duplicada.
- **UC-41 Avaliador sem PyPI.** `docker pull` da imagem publicada → `docker compose up` → suíte estrita dentro da imagem → 10 exemplos do desafio.

## Critérios de aceitação

| ID | Critério | Como comprovar |
| --- | --- | --- |
| CA-60 | Respostas `general_web` avaliadas com o texto das páginas citadas; a nota "texto não gravado" some do relatório quando a página foi buscada | Relatório da campanha v0.11.0; teste com servidor de páginas em processo |
| CA-61 | Calibração com 60 respostas, 2 rotuladores, rótulo ouro adjudicado; κ do veredito reportado nas 36 seladas e nas 60, com intervalo; concordância por afirmação; decisão do padrão pela regra escrita antes, cumprida ou não | `docs/evidence/v0110-calibracao.md` e README |
| CA-62 | Meta do avaliador: κ ≥ 0,6 nas 36 seladas com algum candidato pré-registrado | Mesmo relatório; se não atingido, o número e a causa ficam escritos |
| CA-63 | Tabela híbrido × `hybrid@36` × reranker em dev e holdout de retrieval, decisão de `RERANK` pela regra; piso BM25 medido | `eval-retrieval` |
| CA-64 | Jornadas ≥ 12/13 pela régua combinada, com as duas colunas no relatório | Campanha real |
| CA-65 | Conversa real de 20+ turnos devolve protocolo e valor do início; teste determinístico equivalente; resumo gerado uma vez por avanço da janela | Campanha v0.12.0 e suíte |
| CA-66 | Relatório com × sem replan nos mesmos casos (dev + holdout + conversas), por critério e rota, com a lista das decisões de origem `model` | `docs/evidence/v0120-ablacao-replan.md` |
| CA-67 | Cancelamento só executa após confirmação explícita; repetição idempotente; recusa deixa a conta intacta; auditoria com escopo de escrita | Suíte e jornada real |
| CA-68 | Authorization code com PKCE e refresh rotativo funcionando na interface; token do emissor externo aceito; token de emissor desconhecido recusado | Suíte, QA na interface com os dois emissores |
| CA-69 | Caso chega ao Telegram e a resposta do operador chega ao lojista; adaptador desligado por padrão | QA real com bot do responsável |
| CA-70 | Compose com 2 workers; worker morto no meio de uma comparação; retomada pelo outro sem célula duplicada; `/metrics`, rate limit, handoffs e outbox corretos com 2 processos | QA de operação |
| CA-71 | Entrega esgotada reenviada; caso órfão completado na subida sem reenvio do lojista | Suíte e QA de operação |
| CA-72 | Spans no coletor OTLP; dashboard carregado sobre `/metrics` com captura | QA de operação |
| CA-73 | Imagem no GHCR por tag; suíte estrita roda dentro da imagem sem PyPI; lockfile versionado | CI e evidência |
| CA-74 | `docs/process/` com índice e links válidos; README com trilha de 10 min, capturas e tabela antes × depois por critério; túnel testado | Revisão do responsável; `checar-caminhos-pessoais.py` |

## Riscos

| Risco | Efeito | Mitigação |
| --- | --- | --- |
| κ ≥ 0,6 não atingido mesmo com as três alavancas | A meta de maior peso fica aberta | Candidato reserva (ensemble) pré-registrado; relatório com concordância por afirmação, que tem n maior; resposta escrita para a entrevista |
| Rotuladores discordam entre si | Rótulo ouro fraco | Mesma unidade de julgamento (afirmações); adjudicação registrada; κ humano × humano reportado |
| Páginas citadas pela busca mudam ou somem | Evidência da web incompleta | Fallback no resumo da busca com nota; extrato gravado na primeira busca e reaproveitado |
| Resumo rolante inventar ou perder números | Resposta errada em conversa longa | Registro de fatos determinístico; guarda de saída não aceita o resumo como fonte |
| Cancelamento executar sem confirmação | Efeito indevido na conta | Estado `pending_confirmation` persistido; execução só por turno de confirmação explícita; auditoria |
| Emissor externo pesar no notebook de 8 GB | QA bloqueado | Serviço leve por perfil do compose; `checar-memoria.ps1` antes |
| Dois workers expõem outra condição de corrida | Dado duplicado | Teste com processo morto; `BEGIN IMMEDIATE` já usado; revisão independente do lease |
| Telegram exige rede de saída e token | Vazamento ou bloqueio | Desligado por padrão; só resumo mascarado; token fora do repositório |
| Reorganização de `docs/` quebrar links | README com links mortos | Verificador de links no `lint_and_tests.py`; mover por `git mv` |
| Avaliador recalibrar notas por comparação com outras entregas | Ganho menor que o projetado | Tabela antes × depois por critério; imagem pronta para subir a confiança |

## Questões em aberto

| ID | Questão | Resposta |
| --- | --- | --- |
| Q21 | Novo teto global de API e reserva deste ciclo (proposta no plano: teto global US$6,25; reserva US$1,00 mais a sonda do Sonnet, decidida à parte) | Responsável |
| Q22 | Quem é o segundo rotulador e quando tem ~3 h | Responsável |
| Q23 | Prazo da reavaliação (perguntar no grupo) | Responsável |
| Q24 | Emissor OIDC externo: serviço leve (Dex) ou Keycloak | Proposta: Dex, pelo consumo de memória; Keycloak se o avaliador pedir |
| Q25 | `docs/process/` como pasta no repositório ou branch de arquivo | Proposta: pasta, para os links continuarem válidos |
| Q26 | Imagem pronta resolve o ambiente sem PyPI do avaliador (perguntar no grupo) | Responsável |
