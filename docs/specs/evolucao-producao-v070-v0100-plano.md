<!-- Papel: plano técnico da evolução para produção (v0.7.0 a v0.10.0), derivado de evolucao-producao-v070-v0100.md. -->

# Plano: evolução para produção (v0.7.0 a v0.10.0)

## Especificação relacionada

[evolucao-producao-v070-v0100.md](evolucao-producao-v070-v0100.md) (versão 0.2) e [ADR 0016](../architecture/decisions/0016-reabertura-roadmap-producao.md). Estado: entregue da v0.7.0 à v0.10.0 (2026-11-04 a 2026-11-06); a v1.0.0 seguiu para o [roadmap](roadmap-v0110-v100-plano.md). Trabalho em duas frentes paralelas, decididas pelo responsável em 2026-11-03 (seção "Sequência e dois times").

Cada versão tem especificação complementar, tarefas, revisão independente, candidato identificado por hash, validação com modelos reais sob teto fixo e o registro `docs/evidence/vXYZ-resultado.md`. Tag, publicação e calibração humana ficam com o responsável.

## Preparação do fluxo (etapa 0, antes da v0.7.0)

Aplicada uma vez, numa tarefa de documentação e ferramentas, sem produto (tarefa 62):

1. **Autorização por versão**, incorporada ao AGENTS.md por PR: cada versão segue da implementação à validação real dentro do teto, sem espera entre etapas.
2. **`.github/workflows/validate.yml`**: Ruff e `python tools/scripts/lint_and_tests.py --strict` em PR e push na `main`; sem segredos; o `.env` de teste é o do `conftest`.
3. **Scripts de ambiente** em `tools/scripts/`: `checar-memoria.ps1` e `limpar-ambiente.ps1` (alvos `.pytest_cache/*-runtime`, `_tmp/`, volumes anônimos do Docker).

## Decisões técnicas

### v0.7.0 — Identidade

1. **Principal por lojista e por operador, reaproveitando o mecanismo de sessão do `/v1`.** `api_principals` ganha os papéis `merchant` e `operator`. Chaves sintéticas vêm de `MERCHANT_ACCESS_KEYS` (`cliente1988:chave,cliente_demo_002:chave`) e `API_OPERATOR_ACCESS_KEY`, preenchidas no `.env.example` com valores fictícios nomeados como tal. `POST /v1/sessions` resolve a chave para o principal, o `customer_id` ligado e os **escopos** do papel. O ponto de troca por OIDC/JWT é um único adaptador em `api/identity.py` (`resolve_credential(credential) -> Principal`).
2. **`POST /messages` exige `Authorization: Bearer`, sem exceção.** O lojista vem do principal; `user_id` fica opcional e, se divergir, `403 identity_mismatch`. O smoke cria a sessão sozinho; `/docs` traz o exemplo de sessão; o README mostra duas chamadas. A CLI `ask` continua em processo, sem HTTP.
3. **Escopo por tool call.** Cada entrada de `TOOLS` declara `scope`; `CustomerContext` carrega `principal_id`, `role` e `scopes`; `registry.execute` verifica escopo e lojista antes do allowlist por agente e grava `audit_events` em todo call (aceito ou recusado) com principal, ferramenta, escopo e resultado. Limite de requisições por principal (janela deslizante em SQLite, `429 rate_limited`). O MCP passa a receber `--access-key` e deriva o lojista da chave.

### v0.7.0 — HITL

4. **Interrupção nativa do LangGraph.** Novo nó `human_review` depois de `escalation`: chama `interrupt(payload)` com o resumo, a pergunta pendente e o rascunho de resposta do agente. O grafo é compilado com `SqliteSaver` (pacote `langgraph-checkpoint-sqlite`, a acrescentar ao `pyproject`) em `runtime/checkpoints.sqlite3`; `thread_id = conversation_id`. A requisição HTTP do lojista termina com `status=handoff` e protocolo, como hoje; o estado do grafo fica salvo no ponto da interrupção e sobrevive a reinício da API.
5. **Retomada pelo operador.** `POST /v1/handoffs/{id}/actions` executa `graph.invoke(Command(resume={action, text, operator_id}), config=thread)` com um `RunContext` novo (`request_id` próprio, trace que referencia o original, orçamento normal). Depois de `human_review`, aresta condicional: `approve` e `reply` → `personality` (texto do operador como contribuição `from_operator=True`, evidência válida para a guarda); `reject` → `support` com `operator_instruction`, um ciclo, depois `replan`-free (na v0.7.0 o caminho após `reject` é `support → personality`). O turno gravado tem `via=operator` e o protocolo.
6. **Entrega ao lojista e webhooks.** Três caminhos: a próxima `POST /messages` da conversa devolve primeiro a resposta humana pendente (rota `human_reply`, sem chamada a modelo); `GET /v1/conversations/{id}` a mostra; e `webhooks.py` envia `conversation.replied` para a URL da sessão ou `CONVERSATION_WEBHOOK_URL`. Na criação do caso, `handoff.created` vai para `HANDOFF_WEBHOOK_URL`. Entrega em thread curta fora da requisição, assinatura `X-Signature: sha256=HMAC(secret, body)`, três tentativas com espera crescente, tabela `webhook_deliveries` consultável em `GET /v1/handoffs/{id}` e na conversa. O serviço `mocks` ganha `POST /ticketing/cases` que valida a assinatura, guarda o caso e o expõe em `GET /ticketing/cases`; o compose aponta `HANDOFF_WEBHOOK_URL` para ele.
7. **Fila e idempotência.** `handoff_cases` ganha `queue_state`, `claimed_by`, `claimed_at`, `answered_at`, `resume_count`, `channel`; nova tabela `handoff_events` (caso, ação, operador, chave de idempotência única, payload, carimbo). Reivindicação e ação usam `BEGIN IMMEDIATE`; segunda retomada → `409 already_resumed`; mesma chave → registro existente. Protocolo passa de `SIM-…` a `HO-…`; `simulated` sai do payload.
8. **Superfícies.** API (`GET /v1/handoffs`, `GET /v1/handoffs/{id}`, `POST …/claim`, `POST …/actions`), CLI `merchant-assistant operator list|show|act` e aba "Operador" no projeto web (sessão de operador, lista, detalhe com resumo e rascunho, três botões, entregas de webhook).

### v0.8.0 — Orquestração adaptativa

9. **Nó `replan` depois de `knowledge` e de `support`.** Entrada: resumo observável do resultado (`evidence_sufficient`, `missing`, `needs_selection`, `escalate`, ferramentas com falha, `operator_instruction`, saltos já feitos, rota original). Saída estruturada: `next ∈ {finish, knowledge, web, support, escalate, clarify}` + `reason` + `review` (o resultado responde à pergunta?). Regras determinísticas resolvem os casos claros sem modelo; o modelo (esforço `none`, ≤ 80 tokens) decide só na ambiguidade. Nunca repete o mesmo especialista sem informação nova.
10. **Orçamento de saltos no `RunContext`** (`MAX_PLAN_HOPS`, padrão 3) ao lado dos limites existentes; cada decisão vira passo de trace `replan` com `next`, `reason`, `review`, `hops` e origem. O grafo pré-definido do Router continua sendo o plano inicial.
11. **Cenários de replanejamento** no catálogo e nos JSONL (quatro, RF-88); política programada atualizada.

### v0.8.0 — Avaliação semântica

12. **`judge` v3** com `groundedness`, `factual_correctness`, `relevance`, `usefulness` (1–5 + justificativa) e `unsupported_claim: bool`; recebe o conteúdo das evidências mascaradas, limitado a 6 000 caracteres com truncamento registrado.
13. **Juiz independente e repetições.** `EVALUATOR_MODEL` padrão diferente do `AGENT_MODEL`, decidido pelo custo medido em 5 casos (outro modelo OpenAI ou DeepSeek); `eval --repeat 3`; média, desvio, concordância exata e ±1; relatório por critério, rota e split.
14. **Calibração humana.** `eval-calibrate --sample 24` gera CSV sem os scores do juiz; `--import` calcula concordância (exata, ±1, kappa ponderado) e grava em `docs/evidence/`; formulário opcional na área Resultados.
15. **Holdout de respostas** `tests/scenarios/holdout_v080.jsonl` (≥ 20, metade pt), congelado por hash antes da campanha.
16. **Regressões de negócio.** Rótulos ampliados só onde a resposta real está correta (justificativa por caso); `router.v6` com a forma interrogativa inglesa e regressão programada.

### v0.9.0 — Retrieval

17. **Híbrido BM25 + denso com RRF em processo** (`rank-bm25`, tokenização sem acentos e stopwords pt/en, persistido em `runtime/bm25.pkl` com hash do corpus); `KnowledgeIndex.search(mode)`; `RETRIEVAL_MODE` com padrão decidido pela medição.
18. **Reranker** (`rerank.v1`, esforço `none`): recebe os 12 primeiros e devolve ordem; `RERANK=on|off`; medido em dev e holdout.
19. **Holdout de retrieval** `tests/scenarios/retrieval_holdout.jsonl` (≥ 20); `eval-retrieval --mode dense|hybrid|hybrid+rerank --split dev|holdout` com Recall@6, MRR e nDCG@6 lado a lado.

### v0.10.0 — Operação e resiliência

20. **`GET /metrics`** (texto Prometheus a partir de contadores em memória alimentados pelo `_record`), **OTLP opcional** (`OTEL_EXPORTER_OTLP_ENDPOINT`), `observability/prometheus/alerts.yml` (validado por `promtool` em teste) e `observability/grafana/assistant.json`.
21. **CI** `validate.yml` (já na etapa 0; aqui ganha o badge e a evidência).
22. **Comparação retomável.** `comparisons` guarda o estado por célula; na subida, células `pending` de comparações `running` são retomadas por uma thread de trabalho; `interrupted` deixa de existir como estado final.
23. **Resumo rolante.** Quando a conversa ultrapassa o limite de histórico, `conversations.summary` guarda um resumo das mensagens anteriores (uma chamada curta, esforço `none`, cacheado por `last_summarized_message_id`), entregue como dado aos agentes.

### v1.0.0 — Fechamento

24. Redefinido no [roadmap v0.11.0 a v1.0.0](roadmap-v0110-v100-plano.md).

## Componentes afetados

| Área | v0.7.0 | v0.8.0 | v0.9.0 | v0.10.0 |
| --- | --- | --- | --- | --- |
| `api/` | `identity.py`, `webhooks.py` novos; `app.py` (sessão em `/messages`); `v1.py` (sessões por papel, handoffs, rate limit); `schemas.py` | — | — | `metrics.py` |
| `orchestration/` | `graph.py` (checkpointer, `human_review`, retomada); `state.py`; `run.py` (principal) | `graph.py` (`replan`); `run.py` (`MAX_PLAN_HOPS`); `state.py` | — | — |
| `agents/` | `escalation.py`; `personality.py` | `replanner.py` novo; `support.py` | — | — |
| `tools/` | `base.py` (principal, escopos); `registry.py` (escopo, auditoria) | — | — | — |
| `conversations.py`, `cases.py` | turno `via=operator`; transições de `handoff` | — | — | resumo rolante |
| `mocks/` | `ticketing` | — | — | — |
| `data/migrations.py` | 0009, 0010 | 0011 | — | 0012 |
| `rag/` | — | — | `bm25.py`, `rerank.py`, `index.py` | — |
| `evaluation/` | — | `runner.py`, `calibration.py` | `retrieval.py` | — |
| `comparisons.py` | — | — | — | retomada |
| `prompts/` | `escalation.v2`, `personality.v4` | `judge.v3`, `replan.v1`, `router.v6`, `support.v8` | `rerank.v1` | `summary.v1` |
| `cli.py`, `mcp_server.py` | `operator …`; `--access-key` | `eval --repeat`, `eval-calibrate` | `eval-retrieval --mode --split` | — |
| `tests/` | identidade, escopos, fila, interrupção/retomada, idempotência, webhooks, reinício | replan, rubrica, agregação, calibração, holdout | híbrido, reranker, nDCG | métricas, alertas, retomada, resumo |
| `docker-compose.yml`, `.env.example` | chaves sintéticas, URLs de webhook | `EVALUATOR_*`, `JUDGE_*` | `RETRIEVAL_MODE`, `RERANK` | OTLP |
| Projeto web | aba Operador; login por papel | formulário de calibração | — | — |
| `docs/` | spec complementar, tarefas, ADRs 0017 (identidade) e 0018 (interrupção e webhooks) | ADR 0019 (replanejamento) | ADR 0020 (híbrido) | — |

Não alterar: regras financeiras das ferramentas, snapshots públicos, ledger de orçamento. AGENTS.md, CLAUDE.md e `.claude/` só pela etapa 0 aprovada.

## Modelo de dados

**Migração 0009 (v0.7.0), reversível.** `api_principals.role` aceita `merchant` e `operator`; `api_principals.scopes` (JSON); `handoff_cases` + `queue_state`, `claimed_by`, `claimed_at`, `answered_at`, `resume_count`, `channel`; `handoff_events(event_id, case_id, action, operator_id, idempotency_key UNIQUE, payload, created_at)`; `webhook_deliveries(delivery_id, event, target, case_id, conversation_id, attempt, status, response_code, created_at)`; `messages.via`; `audit_events.principal_id`, `scope`, `outcome`; `rate_limit_hits(principal_id, window_start, count)`. Checkpoints do LangGraph em `runtime/checkpoints.sqlite3`, fora das migrações do domínio.

**Migração 0010 (v0.7.0).** `webhook_outbox`: intenção durável de entrega por evento e destinatário, com corpo mascarado, estado e tentativas (outbox autorizada pelo responsável em 2026-11-03).

**Migração 0011 (v0.8.0).** Acrescenta `scores`, `repetition` e `unsupported_claim` a `run_evaluations` e cria `calibrations`; `rubric_version` já existe desde a migração 0008.

**Migração 0012 (v0.10.0).** `comparisons.cells` com estado por célula; `conversations.summary`, `last_summarized_message_id`.

## APIs ou interfaces

| Rota | Papel | Mudança |
| --- | --- | --- |
| `POST /messages` | merchant | **Incompatível:** sessão obrigatória; `user_id` opcional, `403 identity_mismatch` se divergir; resposta ganha `via` e, com resposta humana pendente, rota `human_reply` |
| `POST /v1/sessions` | — | Aceita chave de lojista e de operador; resposta inclui `role`, `customer_id`, `scopes`; aceita `webhook_url` opcional |
| `GET /v1/handoffs?state=` | operator | Fila |
| `GET /v1/handoffs/{id}` | operator | Resumo, pergunta pendente, rascunho, conversa mascarada, eventos, entregas de webhook |
| `POST /v1/handoffs/{id}/claim` | operator | `409` se já reivindicado por outro |
| `POST /v1/handoffs/{id}/actions` | operator | `{"action": "approve"\|"reply"\|"reject", "text", "idempotency_key"}`; retoma o grafo; `409 already_resumed` |
| `GET /v1/conversations/{id}` | merchant (dono), operator | Turnos `via=operator`, entregas |
| `GET /ready` | — | + `pending_handoffs`, `retrieval_mode`, `checkpoints` |
| `GET /metrics` | — (rede interna) | Prometheus |
| Mocks | — | `POST/GET /ticketing/cases` |
| CLI | — | `operator list|show|act`, `eval --repeat`, `eval-calibrate`, `eval-retrieval --mode --split` |
| MCP | — | `--access-key` |

Contrato `/v1` aditivo em tudo, exceto os papéis novos em `/sessions`.

## Estratégia de testes

| Nível | v0.7.0 | v0.8.0 | v0.9.0 | v0.10.0 |
| --- | --- | --- | --- | --- |
| Unidade | credencial → principal → escopos; verificação de escopo e lojista; auditoria em todo call; rate limit; transições da fila; idempotência e `409` sob `BEGIN IMMEDIATE` concorrente; assinatura HMAC e tentativas; migrações 0009 e 0010 | regras do `replan`; saltos; agregação (média, desvio, concordância, kappa); CSV de calibração; migração 0011 | RRF; BM25 por hash; nDCG; reranker com modelo programado | formato `/metrics`; `promtool check rules`; retomada de células; resumo cacheado; migração 0012 |
| Contrato | esquemas de handoff, sessão, webhook; `401`/`403`/`429` | `judge` v3 e `replan` | — | — |
| Integração (programada) | interrupção e retomada nas três ações; retomada após reinício da API (novo processo sobre o mesmo checkpoint); turno `via=operator`; lojista B não lê fila nem conversa de A; webhook entregue ao receptor de ticketing do mocks em processo; MCP com chave; smoke com sessão | quatro cenários de replanejamento; `hops ≤ 3`; trace; campanha programada com `--repeat` | híbrido e reranker no grafo com embeddings falsos | comparação retomada; conversa de 30 turnos |
| Web (`AppTest`) | aba Operador, três ações, entregas | formulário de calibração | — | — |
| Validação real | 40 casos + 4 conversas + UC-20/21/22 (teto US$0,20) | casos + 4 cenários + holdout, 3 execuções com juiz independente (teto US$0,50) | retrieval dev + holdout nos três modos (teto US$0,10) | 10 exemplos + conversa longa (teto US$0,10) |
| Docker | smoke com sessão; receptor de ticketing; checkpoints no volume | — | — | `/metrics` no compose |

## Riscos técnicos

| Risco | Mitigação / retorno |
| --- | --- |
| `SqliteSaver` serializa o `GraphState`; `RunContext` vai por `config` | Teste de serialização (retomada em nível de aplicação não adotada, Q15) |
| Retomada precisa de `RunContext` novo | `request_id` próprio ligado ao caso; trace referencia o original |
| Sessão obrigatória quebra o `curl` do README | README com duas chamadas; `/docs` com sessão; smoke autônomo; chaves no `.env.example` |
| Webhook para fora do compose | URLs vazias por padrão; payload mascarado; HMAC; receptor interno |
| `replan` cria laços | Orçamento de saltos; sem repetição sem informação nova; limites existentes; teste de laço forçado |
| Juiz independente caro ou indisponível | Medir em 5 casos; DeepSeek como alternativa integrada |
| Holdout escrito pelo autor dos prompts | Paráfrases das páginas oficiais e do FAQ, não dos prompts; hash antes de rodar |
| BM25 em português sem stemming | Tokenização simples; medir; stemming só se o holdout pedir |
| Reranker piorar ou custar | Configurável; padrão decidido pela medição; registrado |

Retorno por versão: tag anterior + migração descendente + remoção de `checkpoints.sqlite3`/`bm25.pkl`.

## Orçamento

### Decisão aprovada em 2026-11-04

Reserva de planejamento de **US$2,50** para as validações reais até a v1.0.0, aprovada pelo responsável, dentro do teto acumulado de **US$5,00** vigente na época (desde 2026-11-07, o limite é definido por provedor). Cada campanha tem teto próprio, registrado antes da execução:

| Etapa | Teto da campanha |
| --- | --- |
| Complemento da amostra de desenvolvimento da v0.8.0 | US$0,10 |
| Campanha `v080-qa` | US$0,50 por padrão; até US$1,10 em montagem única (2026-11-04, ledger primário a US$1,70), mais US$0,30 de contingência (2026-11-05) |
| Validações da v0.9.0 e da v0.10.0 | US$0,10 cada |

Provedores: OpenAI para o assistente, embeddings e busca web; DeepSeek como juiz independente; TypeSafe para o Router Jev. Testes automatizados e ensaios programados têm custo zero de API. O gasto de cada versão está no [índice de evidências](../evidence/README.md); as regras da campanha da v0.8.0 estão no [roteiro da v0.8.0](orquestracao-avaliacao-v080.md#requisitos-não-funcionais).

## Plano de implementação

Cada item vira um arquivo em `docs/tasks/` quando a versão for aberta.

**Etapa 0 — preparação do fluxo** (após Q19)

62. Autorização por versão no AGENTS.md (por PR); `validate.yml`; scripts de ambiente. Sem produto.

**v0.7.0 — Identidade e HITL real**

Revisto pelo responsável em 2026-11-03, na abertura da versão: credencial por **JWT com emissor próprio** (RS256, JWKS) em vez de chave com sessão opaca, e **serviço de ticketing próprio** com tela no projeto web, integrado por webhooks assinados nos dois sentidos, em vez do receptor passivo. Detalhe e tarefa **66b** (serviço de ticketing) em [identidade-hitl-v070.md](identidade-hitl-v070.md), versão 2; prevalece sobre as decisões técnicas 1, 2, 3 e 6 deste plano onde divergirem.

63. Identidade: papéis e escopos, `identity.py`, chaves sintéticas no `.env.example`, sessão obrigatória em `POST /messages`, `identity_mismatch`, auditoria em todo tool call, rate limit, MCP com chave, smoke e `/docs`.
64. Fila de operador: migração 0009, `handoff_events`, rotas `GET/claim/actions` com idempotência e `409`, CLI `operator`.
65. Interrupção e retomada: `langgraph-checkpoint-sqlite`, nó `human_review`, `Command(resume)`, arestas `approve/reply/reject`, turno `via=operator`, entrega na próxima mensagem e no GET, estado do caso, retomada após reinício.
66. Webhooks: `webhooks.py`, assinatura, tentativas, `webhook_deliveries`, receptor de ticketing no `mocks`, compose.
67. Interface web: login por papel e aba Operador (projeto web, depois da 64).
68. Regressão, candidato, validação real (UC-20 a UC-22), evidência, ADRs 0017 e 0018, README/CHANGELOG, tag.

**v0.8.0 — Orquestração adaptativa e avaliação semântica**

69. `replan`: nó, regras, `replan.v1`, orçamento de saltos, trace; quatro cenários.
70. Rubrica `judge` v3 com evidências; juiz independente; `eval --repeat`; agregação; migração 0011 (em paralelo à 69).
71. Calibração humana: `eval-calibrate`, CSV, concordância; formulário na interface.
72a. Holdout de respostas (≥ 20 casos, metade pt), escrito e lacrado por hash antes de qualquer ajuste de prompt da v0.8.0 (durante a v0.7.0).
72b. Correções das jornadas de negócio; `router.v6`.
73. Regressão, candidato, validação real com 3 execuções e holdout, calibração pelo responsável, evidência, ADR 0019, README/CHANGELOG, tag.

**v0.9.0 — Retrieval híbrido** (em paralelo com a v0.10.0)

> **Reescopo de 2026-11-05 (responsável):** a v0.9.0 passa a ser "Juiz Claude e retrieval híbrido", tarefas 79 a 82, spec em [juiz-retrieval-v090.md](juiz-retrieval-v090.md). O experimento do juiz (`claude-opus-5-5` sobre a amostra de calibração da v0.8.0) entra antes do retrieval; o provedor Anthropic nos agentes fica fora da entrega de 2026-11-06. Os itens 74 a 76 abaixo correspondem às tarefas 80 e 81; a v0.10.0, às tarefas 83 a 86.

74. BM25 + RRF, `RETRIEVAL_MODE`, persistência por hash, `search(mode)`.
75. Reranker configurável; holdout de retrieval; `eval-retrieval --mode --split`; nDCG; decisão registrada.
76. Regressão, candidato, validação real, evidência, ADR 0020, tag.

**v0.10.0 — Operação e resiliência** (em paralelo com a v0.9.0)

77. `/metrics`, OTLP opcional, regras de alerta e painel, `/ready` ampliado.
78. Comparação retomável (migração 0012) e resumo rolante de conversas.
79. Regressão, candidato, validação real, evidência, tag.

**v1.0.0 — Fechamento**

Redefinido no [roadmap v0.11.0 a v1.0.0](roadmap-v0110-v100-plano.md) (tarefas 105 a 108).

## Sequência e dois times

Decidido pelo responsável em 2026-11-03: duas frentes de trabalho. O **Time A** fica no caminho crítico; o **Time B** adianta trabalho que não compartilha arquivos com o A. Validação real, integração e tag seguem uma versão por vez, em ordem.

### Distribuição

| Período | Time A (caminho crítico) | Time B (trabalho independente) |
| --- | --- | --- |
| Etapa 0 | concluída | — |
| v0.7.0 | 63 → 64 → 65 → 66 no backend; 68 fecha | 67 (aba Operador, repositório web, depois da 64 fixar o contrato de `/v1/handoffs`); em seguida 72a: escrever e lacrar o holdout de respostas (só dados) |
| v0.8.0 | 69 (`replan` no grafo); depois 72b (correções das jornadas e `router.v6`); 73 fecha | 70 (rubrica `judge` v3, juiz independente, repetições, migração 0011) e 71 (calibração) |
| v0.9.0 e v0.10.0, em paralelo | v0.9.0 inteira: 74 → 75 → 76 | v0.10.0 inteira: 77 e 78 → 79 |
| v1.0.0 | no roadmap | — |

A tarefa 72 do plano se divide em **72a** (holdout, Time B, durante a v0.7.0) e **72b** (jornadas e Router, Time A, na v0.8.0). Escrever o holdout antes de qualquer ajuste de prompt da v0.8.0, por quem não ajusta prompts, e lacrá-lo por hash atende o RF-92 com mais rigor que escrevê-lo depois.

### Donos de arquivo por período

Um arquivo compartilhado tem um dono por período; o outro time não o edita, e arquivos novos pertencem a quem os cria. `cli.py`, `config.py`, `pyproject.toml`, `docker-compose.yml` e `.env.example` recebem só acréscimos no fim do bloco correspondente. README, CHANGELOG e `docs/evidence/vXYZ-resultado.md` são atualizados no fechamento de cada versão.

### Migrações reservadas

0009 e 0010 → v0.7.0 (A); 0011 → v0.8.0 (B); 0012 → v0.10.0 (B). A v0.9.0 não cria migração. Em 2026-11-03 a v0.7.0 precisou da 0010 (outbox durável dos webhooks, autorizada pelo responsável); as reservas seguintes avançaram um número. Um número reservado não é reutilizado nem antecipado; uma migração a mais recebe o número seguinte livre, registrado nesta lista.

### Regras de execução

Cada time trabalha num checkout próprio, com ambiente Python próprio, para que os testes de um não importem o código do outro. A revisão de cada time é independente da implementação. Docker, Qdrant em serviço e validação real rodam um por vez, e a integração segue a ordem v0.7.0 → v0.8.0 → v0.9.0 → v0.10.0: no período paralelo, a v0.10.0 entra em validação depois da integração da v0.9.0.
