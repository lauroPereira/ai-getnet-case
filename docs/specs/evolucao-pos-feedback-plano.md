<!-- Papel: plano técnico da evolução pós-feedback (v0.7.0 a v1.0.0), derivado de evolucao-pos-feedback.md. -->

# Plano: evolução pós-feedback (v0.7.0 a v1.0.0)

## Especificação relacionada

[evolucao-pos-feedback.md](evolucao-pos-feedback.md) (versão 0.2) e [ADR 0016](../architecture/decisions/0016-reabertura-pos-feedback.md). **Estado: aprovado em parte em 2026-11-03** (Q14 a Q17); Q19 aprovada e etapa 0 concluída (`f314205`); Q20 decidida por padrão (`opus`/`high`). Dois times decididos pelo responsável em 2026-11-03 (seção "Sequência, dois times e estimativa"). Base: `main` com a v0.6.0 (`2867ea7`; `87e1683` se o link do vídeo for integrado antes).

Cada versão segue o ciclo já usado: spec complementar curta → tarefas → Developer → Reviewer independente → candidato fixado → QA real com campanha de teto fixo → `docs/evidence/vXYZ-resultado.md` → merge local com a identidade do projeto → tag. Com a autorização por versão (seção "Preparação do fluxo"), tudo isso corre sem espera; o responsável entra na tag, no push e na calibração.

## Preparação do fluxo (etapa 0, antes da v0.7.0)

Adoções do `ampeli-sdd`, aplicadas uma vez, em uma tarefa de documentação e ferramentas (sem produto):

1. **Emenda ao AGENTS.md** (proposta por PR, conforme a regra do próprio arquivo). Texto proposto para a seção "Sobre este projeto":

   > **Autorização por versão (responsável, data da aprovação).** Dentro de uma versão aprovada em `docs/specs/`, o ciclo avança sem esperar o responsável: implementar as tarefas, commitar na branch da versão, despachar Reviewer e QA como subagentes com os modelos e esforços registrados em `.claude/agents/`, corrigir achados, rodar a campanha real dentro do teto fixado no plano, registrar evidência e fazer o merge local na `main` com a identidade do projeto. Continuam exigindo decisão do responsável: push da `main` e tags, alteração de AGENTS.md, CLAUDE.md, `.claude/`, credenciais e `.github/workflows/`, teto de campanha acima do plano, calibração humana, contato com o avaliador e ressubmissão. Concluída a versão, o Supervisor grava o relatório em `docs/relatorios/` e espera.

   Substitui, para o escopo desta evolução, a regra "Delegação (RNF-12)" de autorização caso a caso: a autorização passa a ser dada por versão, com modelo e esforço fixados em `.claude/agents/`.

2. **`.claude/agents/{developer,reviewer,qa}.md`** adaptados do Ampeli: frontmatter com `model`, `effort` e `tools` (Reviewer sem Edit/Write; QA com o navegador embutido), corpo curto apontando para `docs/wiki/agents/<papel>.md`, limites deste projeto (nenhuma chamada paga fora da campanha; sem acesso a `data/runtime/`, `.env`, `discovery/`; sem Git destrutivo; corpo de PR por arquivo; encerrar processos antes de relatar). Modelo e esforço conforme Q20.
3. **`.github/workflows/validate.yml`**: Ruff e `python tools/scripts/lint_and_tests.py --strict` em PR e push na `main`; sem segredos; o `.env` de teste é o do `conftest`.
4. **Scripts portados** para `tools/scripts/`: `medir-agentes.py` (parâmetro `--projeto`), `checar-memoria.ps1` (alvos `python.exe`, `qdrant`, `vmmemWSL`, `uvicorn`), `limpar-ambiente.ps1` (alvos `.pytest_cache/*-runtime`, `_tmp/`, volumes anônimos do Docker).
5. **`docs/templates/relatorio-do-supervisor.md`** e `docs/relatorios/`; despertador de 20 minutos na sessão do Supervisor; `docs/wiki/agents/README.md` ganha a matriz "modelo e esforço por papel".

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

24. README "Resposta ao feedback" (tabela: dimensão → o que mudou → evidência → código), limitações reescritas, CHANGELOG, túnel testado, vídeo de 10–15 min.

## Componentes afetados

| Área | v0.7.0 | v0.8.0 | v0.9.0 | v0.10.0 |
| --- | --- | --- | --- | --- |
| `api/` | `identity.py`, `webhooks.py` novos; `app.py` (sessão em `/messages`); `v1.py` (sessões por papel, handoffs, rate limit); `schemas.py` | — | — | `metrics.py` |
| `orchestration/` | `graph.py` (checkpointer, `human_review`, retomada); `state.py`; `run.py` (principal) | `graph.py` (`replan`); `run.py` (`MAX_PLAN_HOPS`); `state.py` | — | — |
| `agents/` | `escalation.py`; `personality.py` | `replanner.py` novo; `support.py` | — | — |
| `tools/` | `base.py` (principal, escopos); `registry.py` (escopo, auditoria) | — | — | — |
| `conversations.py`, `cases.py` | turno `via=operator`; transições de `handoff` | — | — | resumo rolante |
| `mocks/` | `ticketing` | — | — | — |
| `data/migrations.py` | 0009 | 0010 | — | 0011 |
| `rag/` | — | — | `bm25.py`, `rerank.py`, `index.py` | — |
| `evaluation/` | — | `runner.py`, `calibration.py` | `retrieval.py` | — |
| `comparisons.py` | — | — | — | retomada |
| `prompts/` | `escalation.v2`, `personality.v4` | `judge.v3`, `replan.v1`, `router.v6`, `support.v8` | `rerank.v1` | `summary.v1` |
| `cli.py`, `mcp_server.py` | `operator …`; `--access-key` | `eval --repeat`, `eval-calibrate` | `eval-retrieval --mode --split` | — |
| `tests/` | identidade, escopos, fila, interrupção/retomada, idempotência, webhooks, reinício | replan, rubrica, agregação, calibração, holdout | híbrido, reranker, nDCG | métricas, alertas, retomada, resumo |
| `docker-compose.yml`, `.env.example` | chaves sintéticas, URLs de webhook | `EVALUATOR_MODEL` | `RETRIEVAL_MODE`, `RERANK` | OTLP |
| Projeto web | aba Operador; login por papel | formulário de calibração | — | — |
| `docs/` | spec complementar, tarefas, ADRs 0017 (identidade) e 0018 (interrupção e webhooks) | ADR 0019 (replanejamento) | ADR 0020 (híbrido) | — |

Não alterar: regras financeiras das ferramentas, snapshots públicos, ledger de orçamento. AGENTS.md, CLAUDE.md e `.claude/` só pela etapa 0 aprovada.

## Modelo de dados

**Migração 0009 (v0.7.0), reversível.** `api_principals.role` aceita `merchant` e `operator`; `api_principals.scopes` (JSON); `handoff_cases` + `queue_state`, `claimed_by`, `claimed_at`, `answered_at`, `resume_count`, `channel`; `handoff_events(event_id, case_id, action, operator_id, idempotency_key UNIQUE, payload, created_at)`; `webhook_deliveries(delivery_id, event, target, case_id, conversation_id, attempt, status, response_code, created_at)`; `messages.via`; `audit_events.principal_id`, `scope`, `outcome`; `rate_limit_hits(principal_id, window_start, count)`. Checkpoints do LangGraph em `runtime/checkpoints.sqlite3`, fora das migrações do domínio.

**Migração 0010 (v0.8.0).** `run_evaluations.rubric_version`, `scores`, `repetition`, `unsupported_claim`; `calibrations`.

**Migração 0011 (v0.10.0).** `comparisons.cells` com estado por célula; `conversations.summary`, `last_summarized_message_id`.

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
| Unidade | credencial → principal → escopos; verificação de escopo e lojista; auditoria em todo call; rate limit; transições da fila; idempotência e `409` sob `BEGIN IMMEDIATE` concorrente; assinatura HMAC e tentativas; migração 0009 | regras do `replan`; saltos; agregação (média, desvio, concordância, kappa); CSV de calibração; migração 0010 | RRF; BM25 por hash; nDCG; reranker com modelo programado | formato `/metrics`; `promtool check rules`; retomada de células; resumo cacheado; migração 0011 |
| Contrato | esquemas de handoff, sessão, webhook; `401`/`403`/`429` | `judge` v3 e `replan` | — | — |
| Integração (programada) | interrupção e retomada nas três ações; retomada após reinício da API (novo processo sobre o mesmo checkpoint); turno `via=operator`; lojista B não lê fila nem conversa de A; webhook entregue ao receptor de ticketing do mocks em processo; MCP com chave; smoke com sessão | quatro cenários de replanejamento; `hops ≤ 3`; trace; campanha programada com `--repeat` | híbrido e reranker no grafo com embeddings falsos | comparação retomada; conversa de 30 turnos |
| Web (`AppTest`) | aba Operador, três ações, entregas | formulário de calibração | — | — |
| Validação real | 40 casos + 4 conversas + UC-20/21/22 (teto US$0,20) | casos + 4 cenários + holdout, 3 execuções com juiz independente (teto US$0,50) | retrieval dev + holdout nos três modos (teto US$0,10) | 10 exemplos + conversa longa (teto US$0,10) |
| Docker | smoke com sessão; receptor de ticketing; checkpoints no volume | — | — | `/metrics` no compose |

## Riscos técnicos

| Risco | Mitigação / retorno |
| --- | --- |
| `SqliteSaver` serializa o `GraphState`; `RunContext` vai por `config` | Teste de serialização; retorno: retomada em nível de aplicação (descartada por Q15, fica como plano B) |
| Retomada precisa de `RunContext` novo | `request_id` próprio ligado ao caso; trace referencia o original |
| Sessão obrigatória quebra o `curl` do avaliador | README com duas chamadas; `/docs` com sessão; smoke autônomo; chaves no `.env.example` |
| Webhook para fora do compose | URLs vazias por padrão; payload mascarado; HMAC; receptor interno |
| `replan` cria laços | Orçamento de saltos; sem repetição sem informação nova; limites existentes; teste de laço forçado |
| Juiz independente caro ou indisponível | Medir em 5 casos; DeepSeek como alternativa integrada |
| Holdout escrito pelo autor dos prompts | Paráfrases das páginas oficiais e do FAQ, não dos prompts; hash antes de rodar |
| BM25 em português sem stemming | Tokenização simples; medir; stemming só se o holdout pedir |
| Reranker piorar ou custar | Configurável; padrão decidido pela medição; registrado |
| Fluxo noturno sem o responsável | Decisões por padrão listadas como reversíveis no relatório; limites da autorização por versão |

Retorno por versão: tag anterior + migração descendente + remoção de `checkpoints.sqlite3`/`bm25.pkl`.

## Orçamento

Acumulado do projeto: US$0,69 de US$5,00. Campanhas: v0.7.0 ≤ US$0,20; v0.8.0 ≤ US$0,50; v0.9.0 ≤ US$0,10; v0.10.0 ≤ US$0,10; v1.0.0 smoke ≤ US$0,05. Total adicional ≤ US$0,95. Testes automatizados sem chamadas pagas.

## Plano de implementação

Cada item vira um arquivo em `docs/tasks/` quando a versão for aberta.

**Etapa 0 — preparação do fluxo** (após Q19 e Q20)

62. Emenda ao AGENTS.md por PR; `.claude/agents/`; `validate.yml`; scripts portados; modelo de relatório; matriz de modelos; despertador. Sem produto.

**v0.7.0 — Identidade e HITL real**

Revisto pelo responsável em 2026-11-03, na abertura da versão: credencial por **JWT com emissor próprio** (RS256, JWKS) em vez de chave com sessão opaca, e **serviço de ticketing próprio** com tela no projeto web, integrado por webhooks assinados nos dois sentidos, em vez do receptor passivo. Detalhe, contrato entre os times e nova tarefa **66b** (serviço de ticketing, Time B) em [identidade-hitl-v070.md](identidade-hitl-v070.md), versão 2; prevalece sobre as decisões técnicas 1, 2, 3 e 6 deste plano onde divergirem.

Pré-condição de toda versão a partir daqui: o Supervisor roda numa sessão do Claude Code aberta em `C:\workspace\ai-getnet-case` (não numa pasta acima) e iniciada depois da etapa 0. Antes do primeiro despacho, confirma que `developer`, `reviewer` e `qa` aparecem na lista de tipos de agente; se não aparecerem, não despacha (o despacho cairia num agente genérico sem os limites do frontmatter) e avisa o responsável.

63. Identidade: papéis e escopos, `identity.py`, chaves sintéticas no `.env.example`, sessão obrigatória em `POST /messages`, `identity_mismatch`, auditoria em todo tool call, rate limit, MCP com chave, smoke e `/docs`.
64. Fila de operador: migração 0009, `handoff_events`, rotas `GET/claim/actions` com idempotência e `409`, CLI `operator`.
65. Interrupção e retomada: `langgraph-checkpoint-sqlite`, nó `human_review`, `Command(resume)`, arestas `approve/reply/reject`, turno `via=operator`, entrega na próxima mensagem e no GET, estado do caso, retomada após reinício.
66. Webhooks: `webhooks.py`, assinatura, tentativas, `webhook_deliveries`, receptor de ticketing no `mocks`, compose.
67. Interface web: login por papel e aba Operador (Time B, depois da 64; projeto irmão).
68. Regressão, candidato, revisão, QA real (UC-20 a UC-22), evidência, ADRs 0017 e 0018, README/CHANGELOG, tag.

**v0.8.0 — Orquestração adaptativa e avaliação semântica**

69. `replan`: nó, regras, `replan.v1`, orçamento de saltos, trace; quatro cenários.
70. Rubrica `judge` v3 com evidências; juiz independente; `eval --repeat`; agregação; migração 0010 (Time B, paralelo a 69).
71. Calibração humana: `eval-calibrate`, CSV, concordância; formulário na interface.
72a. Holdout de respostas (≥ 20 casos, metade pt), escrito e lacrado por hash antes de qualquer ajuste de prompt da v0.8.0 (Time B, durante a v0.7.0).
72b. Correções das jornadas de negócio; `router.v6` (Time A).
73. Regressão, candidato, revisão, QA real com 3 execuções e holdout, calibração pelo responsável, evidência, ADR 0019, README/CHANGELOG, tag.

**v0.9.0 — Retrieval híbrido** (Time A, em paralelo com a v0.10.0)

74. BM25 + RRF, `RETRIEVAL_MODE`, persistência por hash, `search(mode)`.
75. Reranker configurável; holdout de retrieval; `eval-retrieval --mode --split`; nDCG; decisão registrada.
76. Regressão, candidato, revisão, QA real, evidência, ADR 0020, tag.

**v0.10.0 — Operação e resiliência** (Time B, em paralelo com a v0.9.0)

77. `/metrics`, OTLP opcional, regras de alerta e painel, `/ready` ampliado.
78. Comparação retomável (migração 0011) e resumo rolante de conversas.
79. Regressão, candidato, revisão, QA real, evidência, tag.

**v1.0.0 — Fechamento e ressubmissão**

80. README "Resposta ao feedback", limitações, CHANGELOG, `docs/evidence/v100-resultado.md`.
81. Túnel externo testado; Docker smoke final em ambiente limpo.
82. Vídeo curto dos deltas; tag `v1.0.0`; mensagem de ressubmissão proposta ao responsável.

## Sequência, dois times e estimativa

Decidido pelo responsável em 2026-11-03: dois times, cada um com um Developer e um Reviewer, coordenados pelo mesmo Supervisor. O **Time A** fica no caminho crítico; o **Time B** adianta trabalho que não compartilha arquivos com o A. QA, merge e tag continuam um por vez e em ordem de versão.

### Distribuição

| Período | Time A (caminho crítico) | Time B (trabalho independente) |
| --- | --- | --- |
| Etapa 0 | concluída | — |
| v0.7.0 | 63 → 64 → 65 → 66 no backend; 68 fecha | 67 (aba Operador, repositório web, depois da 64 fixar o contrato de `/v1/handoffs`); em seguida 72a: escrever e lacrar o holdout de respostas (só dados) |
| v0.8.0 | 69 (`replan` no grafo); depois 72b (correções das jornadas e `router.v6`); 73 fecha | 70 (rubrica `judge` v3, juiz independente, repetições, migração 0010) e 71 (calibração) |
| v0.9.0 e v0.10.0, em paralelo | v0.9.0 inteira: 74 → 75 → 76 | v0.10.0 inteira: 77 e 78 → 79 |
| v1.0.0 | 80 → 81 → 82, um time só | — |

A tarefa 72 do plano se divide em **72a** (holdout, Time B, durante a v0.7.0) e **72b** (jornadas e Router, Time A, na v0.8.0). Escrever o holdout antes de qualquer ajuste de prompt da v0.8.0, por quem não ajusta prompts, e lacrá-lo por hash atende o RF-92 com mais rigor que escrevê-lo depois.

### Donos de arquivo por período

Um arquivo compartilhado tem um dono por período; o outro time não o edita. Arquivos novos pertencem a quem os cria.

| Arquivo ou área | v0.7.0 | v0.8.0 | v0.9.0 e v0.10.0 |
| --- | --- | --- | --- |
| `orchestration/graph.py`, `state.py`, `run.py` | A | A | ninguém (B pede ao Supervisor se precisar) |
| `api/v1.py`, `api/app.py`, `api/schemas.py` | A | A | B (v0.10.0: `/metrics`, `/ready`) |
| `data/migrations.py` | A (0009) | B (0010) | B (0011) |
| `agents/` | A | A (`replanner.py`, `support.py`) | A (`knowledge.py`, se o híbrido exigir) |
| `rag/` | — | — | A |
| `evaluation/` | — | B (`runner.py`, `calibration.py`) | A (`retrieval.py`) |
| `conversations.py`, `comparisons.py` | A | — | B |
| `prompts/` | A | A (`replan`, `router`, `support`); B (`judge.v3`) | A (`rerank`); B (`summary`) |
| `cli.py`, `config.py`, `pyproject.toml`, `docker-compose.yml`, `.env.example` | A | compartilhados só por acréscimo | compartilhados só por acréscimo |
| `tests/scenarios/` | B (holdout, 72a) | A (rótulos das jornadas) | A (holdout de retrieval) |
| Projeto web | B | B (formulário de calibração) | — |
| README, CHANGELOG, `docs/evidence/vXYZ-resultado.md` | Supervisor, no fechamento | Supervisor | Supervisor |

"Só por acréscimo": cada time acrescenta linhas no fim do bloco correspondente e não altera linhas existentes; o conflito, se houver, é resolvido na atualização com a `main`.

### Migrações reservadas

0009 → v0.7.0 (A); 0010 → v0.8.0 (B); 0011 → v0.10.0 (B). A v0.9.0 não cria migração. Um número reservado não é reutilizado nem antecipado; se uma versão precisar de outra migração, o Supervisor reserva o número seguinte livre e atualiza esta lista.

### Regras de execução

1. **Worktree por time.** O Time A trabalha no checkout principal (`C:\workspace\ai-getnet-case`). O Time B trabalha num `git worktree` **fora** da pasta do repositório (`C:\workspace\ai-getnet-case-wt\time-b`), para o validador e o pytest de um não varrerem o outro.
2. **Ambiente Python próprio no worktree.** O `.venv` do checkout principal tem o pacote instalado em modo editável apontando para o `src/` principal; usado no worktree, os testes do Time B importariam o código do Time A. O worktree do B cria seu próprio ambiente (`uv venv .venv -p 3.13 && uv pip install -e ".[ingest,dev]"`) e o Supervisor confere, antes do primeiro despacho, que `python -c "import merchant_assistant; print(merchant_assistant.__file__)"` aponta para o `src/` do worktree.
3. **Branches.** Cada time tem a branch da sua versão (`codex/v0.8.0-avaliacao` para o B durante a v0.7.0, por exemplo). Quando a versão anterior entra na `main`, o time que adiantou trabalho atualiza a branch com a `main` antes de pedir revisão; o Reviewer revisa sobre a base atualizada.
4. **Contexto frio entre e dentro dos times.** Cada Reviewer é um despacho novo, sem a passagem do Developer e sem diagnóstico do Supervisor. O mesmo Reviewer revalida as rodadas de correção do seu time. O Supervisor não repassa a um time conclusões do outro, só contratos já integrados.
5. **Capacidade.** Até dois Developers e dois Reviewers ao mesmo tempo, desde que `checar-memoria.ps1` responda "cabe" antes de cada despacho. Docker, Qdrant em serviço e QA real: um por vez, sempre.
6. **Ordem de entrega.** QA, merge e tag na ordem v0.7.0 → v0.8.0 → v0.9.0 → v0.10.0 → v1.0.0. No período paralelo, a v0.10.0 só entra em QA depois do merge da v0.9.0 e da atualização da sua branch com a `main`.
7. **Despacho e medição.** A descrição de todo despacho cita o time e uma tarefa (`Time B, tarefa 70`), para `medir-agentes.py` ratear custo e o relatório separar os dois times.
8. **Limpeza sem atingir o outro time.** A limpeza é do Supervisor, depois de cada QA apto, sempre rodada no checkout principal: o script não toca o worktree do B (fica fora do scratchpad), os ledgers de campanha, `data/runtime/` nem os volumes com nome do Docker. O único ponto compartilhado são os scratchpads das sessões, onde os subagentes dos dois times escrevem. Com nenhum agente rodando nos dois times, a limpeza é completa (`limpar-ambiente.ps1`, simulação e depois `-Aplicar`). Com agente do outro time rodando, ela roda com `-Aplicar -SemScratchpad`, e a limpeza completa fica para quando os dois times pararem. O Supervisor nunca encerra processo nem remove worktree do outro time.

### Estimativa

| Versão | Um time | Dois times |
| --- | --- | --- |
| v0.7.0 | uma noite | uma noite (67 e 72a saem do caminho crítico) |
| v0.8.0 | uma noite + 1 h de calibração | meia noite + 1 h de calibração (70 e 71 adiantados) |
| v0.9.0 + v0.10.0 | uma noite (meia + meia, em série) | meia noite (em paralelo, QA em série) |
| v1.0.0 | meio dia + vídeo | meio dia + vídeo |
| **Total** | **cerca de quatro noites** | **cerca de três noites** |

Régua: `ampeli-sdd`, ciclo Opus xhigh, 40 pontos por noite com 20 min ativos por ponto; a v0.6.0 deste case saiu em um dia. O ganho dos dois times é cerca de um terço, não o dobro: QA, merge e os arquivos do grafo continuam seriais. Sem a autorização por versão, cada noite vira cerca de dois dias.
