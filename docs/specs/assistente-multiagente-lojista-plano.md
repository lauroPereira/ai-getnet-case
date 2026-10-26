<!-- Papel: plano técnico derivado da especificação principal; define componentes, contratos, testes e a sequência de tarefas. -->

# Plano: Assistente multiagente de suporte ao lojista

Versão 0.1 — 2026-10-26 — **aprovado pelo responsável em 2026-10-26**, junto com as decisões 0001 a 0005.

## Especificação relacionada

[docs/specs/assistente-multiagente-lojista.md](assistente-multiagente-lojista.md)

## Decisões técnicas

| Tema | Escolha proposta | Registro |
| --- | --- | --- |
| Linguagem e API | Python 3.13, FastAPI, Pydantic v2, uvicorn | [0001](../architecture/decisions/0001-python-fastapi-pydantic.md) |
| Orquestração e comunicação | LangGraph com estado tipado; agentes como nós que se comunicam por chamadas diretas sobre o estado | [0002](../architecture/decisions/0002-orquestracao-langgraph-estado-tipado.md) |
| RAG | Qdrant, `text-embedding-3-small`, cópia versionada do conteúdo coletado | [0003](../architecture/decisions/0003-rag-qdrant-e-copia-versionada-do-conteudo.md) |
| Dados e ferramentas | SQLite com seed sintético; ferramentas como funções de domínio; MCP como adaptador na fatia 2 | [0004](../architecture/decisions/0004-dados-sinteticos-sqlite-e-ferramentas-de-dominio.md) |
| Modelos e orçamento | OpenAI como baseline (Responses API, saídas estruturadas, busca web); guarda de orçamento persistente; Jev opcional no Router | [0005](../architecture/decisions/0005-modelos-openai-e-guarda-de-orcamento.md) |
| Prompts | Um arquivo por agente em `prompts/`, com `id` e `version` no cabeçalho; versão registrada em cada trace | Este plano |
| Observabilidade | Logs JSON (stdlib `logging`) e traces por etapa em SQLite local; integração externa (ex.: Langfuse) fica como evolução | Este plano |
| Lint e testes | ruff e pytest; `tools/scripts/lint_and_tests.py --strict` como verificação única | Este plano |

## Componentes afetados

Projeto novo; todos os componentes são criados.

```text
src/merchant_assistant/
  api/            app FastAPI, schemas de entrada e saída, erros
  orchestration/  grafo, estado, limites, guarda de orçamento
  agents/         router, knowledge, support, escalation
  guardrails/     classificação de entrada, mascaramento, verificação de saída
  rag/            fontes, coleta, extração, fragmentação, índice, recuperação
  tools/          funções de domínio, registro, vínculo cliente-recurso
  data/           banco, seed, relógio, glossário de status
  llm/            interface de modelo, cliente OpenAI, modelo programado, embeddings, tabela de preços
  observability/  logs e traces
  cli.py          bootstrap, ingest, seed, eval
  config.py       configuração por variáveis de ambiente
prompts/          router, knowledge, support, escalation (versionados)
data/
  sources/        lista versionada de fontes públicas
  snapshots/      conteúdo coletado e versionado
  knowledge-demo/ base operacional fictícia (promovida de discovery/, sem contexto privado)
  runtime/        banco, índice local, traces e casos simulados (ignorado pelo Git)
tests/
  unit/  integration/  scenarios/
Dockerfile  docker-compose.yml  pyproject.toml  .env.example
```

## Modelo de dados

Banco SQLite sintético, recriado pelo seed. Valores em centavos com moeda explícita; datas com fuso.

| Tabela | Campos principais |
| --- | --- |
| customers | customer_id, display_name, segment |
| contracts | customer_id, products (Pix, Link de Pagamento, maquininhas), settlement_plan, effective_from |
| sales | sale_id, customer_id, captured_at, gross_minor, installments, channel, device_id |
| receivables | receivable_id, sale_id, customer_id, amount_minor, expected_payment_date, source_status |
| payouts | receivable_id, stage, credit_confirmed, confirmed_at |
| devices | device_id, customer_id, model, connectivity, last_seen_at |
| authorization_events | transaction_id, customer_id, device_id, occurred_at, amount_minor, status, response_code |
| support_cases | case_id, customer_id, topic, status, attempts, created_at |
| handoff_cases | case_id, protocol, idempotency_key, payload, created_at |

O seed usa deslocamentos sobre a data do relógio (D-1 para as vendas de "ontem", D+1 para a previsão), de modo que a demonstração sempre tem dados recentes. `cliente1988` é o cliente principal; `cliente_demo_002` serve ao isolamento. Os status de origem preservam o nome original e são normalizados por um glossário versionado (ex.: `LOT_DONE` = lote processado, sem crédito confirmado).

Tabelas das fatias 2 e 3 (conversas, mensagens, pricing, cobranças, habilitações, cancelamentos) entram nas tarefas dessas fatias.

## APIs ou interfaces

### Endpoint

`POST /messages`

```json
{ "message": "When will the money from yesterday's sales be deposited?", "user_id": "cliente1988", "conversation_id": null }
```

```json
{
  "answer": "...",
  "status": "answered",
  "route": "support",
  "agents": ["router", "customer_support"],
  "sources": [{ "type": "tool", "name": "get_receivables_schedule", "observed_at": "..." }],
  "request_id": "req_...",
  "conversation_id": "conv_...",
  "resolution": { "state": "in_progress", "evidence": null }
}
```

Também: `GET /health`, `GET /ready` e, somente em modo demonstração, `GET /traces/{request_id}`.

### Contratos dos agentes

| Agente | Saída validada |
| --- | --- |
| Router | `route`, `intents[]`, `language`, `missing_data[]`, `safety{category, action}` |
| Knowledge | `mode` (rag, web), `claims[]`, `citations[{title, url, source_kind, chunk_id}]`, `evidence_sufficient`, `procedure_id`, `missing[]` |
| Customer Support | `facts[{tool, field, value, source, observed_at}]`, `needs_selection`, `missing[]`, `escalate`, `reason`, `answer` |
| Escalation | `case_id`, `protocol`, `reason`, `summary`, `queries[]`, `attempts[]`, `pending_question` |

Composição: com um único especialista, a resposta dele é usada diretamente. Na rota combinada, o Knowledge roda primeiro e o Customer Support compõe a resposta com o procedimento recebido. Toda resposta passa pela verificação de saída (RF-08).

### Grafo

```text
input_guard → router ─┬─ knowledge ───────────────────────────────→ output_guard → respond
                      ├─ general_web → knowledge(web) ─────────────→ output_guard → respond
                      ├─ support → support_prefix → support ────────→ output_guard → respond
                      ├─ knowledge_and_support → support_prefix → knowledge → support → output_guard → respond
                      ├─ human_handoff → support_prefix (tolerante a falhas) → escalation → respond
                      ├─ clarify → respond
                      └─ out_of_scope → respond (recusa)
support --escalate--> escalation
```

### Ferramentas do núcleo

O `customer_id` é injetado pelo contexto em todas as ferramentas; o modelo nunca o informa.

| Ferramenta | Argumentos do modelo | Retorno principal |
| --- | --- | --- |
| get_receivables_schedule | date_from, date_to, status opcional | Recebíveis com valor, data prevista, status original e normalizado, origem e instante |
| get_payout_status | receivable_id | Etapa, crédito confirmado ou não, instante |
| get_device_status | device_id opcional | Dispositivo(s) com modelo, conectividade e último sinal |
| find_authorization_events | date_from, date_to, status (padrão: negada), limit | Eventos com código, categoria e mensagem para o lojista |
| get_contract_snapshot | nenhum | Produtos, plano e vigência |
| get_complaint_history | topic opcional | Casos, tentativas e pendências (prefixo) |
| run_customer_healthcheck | topic | Verificações `ok`, `pending`, `attention`, `unknown`, `unavailable`, `not_applicable` (prefixo) |

Erros estruturados: `NOT_FOUND`, `FORBIDDEN_RESOURCE`, `INVALID_ARGUMENT`, `UNAVAILABLE`, `TIMEOUT`.

## Estratégia de testes

| Nível | O que verifica | Dependências | Critérios |
| --- | --- | --- | --- |
| Unidade | Ferramentas (vínculo, filtros, datas), fragmentação, mascaramento, guarda de orçamento, validação de contratos | Nenhuma | CA-06, CA-07, CA-12 |
| Contrato | Schemas da API, das saídas dos agentes e das ferramentas | Nenhuma | RF-01, RF-05 |
| Integração determinística | Grafo completo com modelo programado, embeddings falsos, Qdrant em memória, seed e relógio fixo; 10 exemplos e UC-11 a UC-18; falhas injetadas | Nenhuma rede | CA-01 a CA-03, CA-05, CA-08 a CA-11, CA-14 |
| Avaliação real limitada | Roteamento por caso, Recall@k, aderência às fontes (verificação de números e rubrica em amostra), qualidade do encaminhamento, custo e latência | OpenAI, dentro da reserva | CA-01, CA-04, CA-17 |
| Smoke Docker | `docker compose up --build` em ambiente limpo e envio dos 10 exemplos | Docker, chave | CA-13 |

O conjunto rotulado (`tests/scenarios/`) separa casos de desenvolvimento de casos reservados para avaliação. Cada execução registra quais dependências foram simuladas.

## Riscos técnicos

| Risco | Mitigação ou reversão |
| --- | --- |
| Extração vazia em páginas dinâmicas | Conferir o texto extraído por página; navegador headless só para as páginas que precisarem |
| Recuperação inglês → português fraca | Medir na tarefa 10; reescrever a consulta para português antes da busca |
| Saída estruturada inválida | Validação com uma nova tentativa limitada; depois, caminho seguro |
| Custo da busca web e das avaliações | Guarda de orçamento persistente; limites por requisição; avaliação em lotes pequenos |
| Datas em fuso errado | Relógio único injetado; testes na virada do dia |
| Acoplamento ao LangGraph | Agentes como funções puras sobre o estado; o grafo só faz a ligação |

## Plano de implementação

Cada etapa é uma tarefa em `docs/tasks/`. As fatias 2 a 4 serão detalhadas em tarefas quando a fatia 1 terminar, com base no que for aprendido.

**Fatia 0 — Verificação**

1. [Verificar fontes oficiais e imagem do enunciado](../tasks/01-verificar-fontes-e-enunciado.md)
2. [Verificar acesso e preços dos modelos](../tasks/02-verificar-acesso-e-precos-dos-modelos.md)

**Fatia 1 — Núcleo**

3. [Estrutura base do projeto Python](../tasks/03-estrutura-base-python.md)
4. [Contrato da API de mensagens](../tasks/04-contrato-api-mensagens.md)
5. [Dados sintéticos e relógio](../tasks/05-dados-sinteticos-e-relogio.md)
6. [Ferramentas de suporte do núcleo](../tasks/06-ferramentas-suporte-nucleo.md)
7. [Pipeline de ingestão RAG](../tasks/07-pipeline-ingestao-rag.md)
8. [Orquestração, estado e limites](../tasks/08-orquestracao-estado-e-limites.md)
9. [Router e guardrails](../tasks/09-router-e-guardrails.md)
10. [Knowledge Agent](../tasks/10-knowledge-agent.md)
11. [Customer Support Agent](../tasks/11-customer-support-agent.md)
12. [Escalation Agent](../tasks/12-escalation-agent.md)
13. [Docker e README inicial](../tasks/13-docker-e-readme-inicial.md)
14. [Avaliação dos exemplos do desafio](../tasks/14-avaliacao-exemplos-desafio.md)

**Fatia 2 — Confiabilidade e acompanhamento (a detalhar):** histórico e estados de atendimento (RF-28, RF-29), acompanhamento técnico (RF-30), servidor MCP (RF-31).

**Fatia 3 — Profundidade (a detalhar, cortável):** pricing fictício e cobrança (RF-32), habilitação de bandeiras (RF-33), cancelamento de venda (RF-34).

**Fatia 4 — Demonstração (a detalhar):** seletor LLM/Jev (RF-35), interface (RF-36), README final, revisão de privacidade antes do primeiro push e vídeo (CA-16, CA-25).

Dependências: 03 antes de tudo na fatia 1; 05 antes de 06; 01 antes de 07; 04 e 08 antes de 09 a 12; 06 antes de 11; 07 antes de 10; 13 e 14 por último.
