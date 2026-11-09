# Contrato da API v1

A interface web usa somente esta API HTTP. O projeto irmão [ai-getnet-case-web](https://github.com/lauroPereira/ai-getnet-case-web) mantém o snapshot OpenAPI consumido pela interface em `openapi-v1.json`; o mapa Python é gerado por `tools/generate_client.py` nesse projeto. Esse arquivo não pertence ao repositório backend.

## Identidade e autorização

- `POST /v1/auth/token` (OAuth 2.0, corpo `application/x-www-form-urlencoded`): `grant_type=password` para os usuários de demonstração e `client_credentials` para o serviço de ticketing. Devolve um JWT RS256 do emissor próprio; as chaves públicas estão em `/.well-known/jwks.json` e a descoberta em `/.well-known/openid-configuration`.
- `POST /v1/auth/revoke` revoga o token. Token ausente, inválido, expirado ou revogado retorna `401`.
- Papéis `merchant`, `operator`, `service`, `demo` e `admin`, com escopos. O lojista vem do token; o backend verifica papel, escopo e dono em cada rota. Sessão demo não publica perfis. As chaves de provedor não fazem parte do contrato nem da interface.
- `POST /v1/sessions` e `DELETE /v1/sessions/current` (v0.4.0 a v0.6.0) deram lugar a essas rotas na v0.7.0 ([decisão 0017](../architecture/decisions/0017-identidade-principal-escopos.md)). O contrato completo de identidade, fila e webhooks está na [especificação v0.7.0](../specs/identidade-hitl-v070.md), seção "Contrato entre os times".

## Rotas

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `POST /v1/auth/token` | público | emite JWT pelas concessões `password` e `client_credentials` |
| `POST /v1/auth/revoke` | Bearer | revoga o token atual |
| `GET /v1/catalog/models` | Bearer | catálogo datado com preço, capacidades, parâmetros por agente e links para documentação oficial |
| `GET /v1/profiles` | Bearer | perfis publicados visíveis ao papel |
| `POST /v1/profiles` | admin | cria rascunho compatível |
| `PUT /v1/profiles/{profile_id}/draft` | admin | atualiza versão de rascunho por controle otimista de versão |
| `POST /v1/profiles/{profile_id}/publish` | admin | publica uma versão imutável |
| `POST /v1/router/compare` | Bearer | executa somente os Routers LLM e JEV para o mesmo snapshot |
| `POST /v1/messages` | Bearer | atende usando o método escolhido; pode consumir uma comparação vinculada |
| `GET /v1/runs/{request_id}` | Bearer/dono | consulta snapshot saneado de execução |
| `GET /v1/conversations/{conversation_id}` | Bearer/dono | consulta conversa do cliente vinculado; operadores leem conversas com caso |
| `GET /v1/handoffs`, `GET /v1/handoffs/{case_id}` | operador (`handoff:operate`) | fila de casos encaminhados e detalhe, com eventos e entregas de webhook (v0.7.0) |
| `POST /v1/handoffs/{case_id}/claim`, `POST /v1/handoffs/{case_id}/actions` | operador (`handoff:operate`) | reivindicação e ações `approve`, `reply`, `reject`, idempotentes por `idempotency_key`; `409 claimed_by_other`, `409 already_resumed` (v0.7.0) |
| `POST /v1/integrations/ticketing/events` | serviço (`handoff:integrate`) com assinatura HMAC | eventos `ticket.assigned`, `ticket.action` e `ticket.solved`, idempotentes por `id` (v0.7.0) |

As rotas da base de conhecimento (`/v1/kb/*`, v0.5.0) estão na [proposta aprovada](../specs/api-kb-v050-proposta.md).

## Comparação e uso

A comparação valida input guard, perfil publicado, papel/dono da conversa e limite de orçamento antes de chamar os dois Routers. O `comparison_id` fica associado ao principal, cliente, conversa, digest da mensagem, digest do estado, perfil/versão, método escolhido e expiração de cinco minutos. `POST /v1/messages` valida esses campos e consome a comparação em uma única transação `BEGIN IMMEDIATE`; decisão ausente, vencida, incompatível ou já consumida retorna `409`. A decisão selecionada vai direto ao Router do atendimento, evitando nova chamada ao Router. As ferramentas dos agentes restantes pertencem somente ao atendimento.

O snapshot da execução registra perfil e digest, versões de prompt/base, mecanismo e modelos efetivos, modo, chamadas, ferramentas, fontes e duração quando disponíveis. `effective_parameters_by_agent` inclui somente parâmetros de fato enviados pelo adaptador; valores internos usados apenas para estimar reserva não são descritos como parâmetro efetivo. Custos são apresentados como estimativas com faixa/tarifa registrada, nunca como fatura exata. Respostas não incluem chave de provedor ou chave de acesso.

## Parâmetros de modelos por agente

O catálogo permite configurar `max_output_tokens` somente para `openai:gpt-6-luna` e `deepseek:deepseek-flash`, com a faixa de 16 até o limite existente do agente: Router 300, Knowledge 500, Support 1200, Escalation 400 e Personality 600. A aplicação aceita apenas inteiros estritos, rejeita chaves desconhecidas e valores fora da faixa antes de persistir uma nova versão. A avaliação sob demanda (v0.6.0) usa o avaliador fixo do backend, sem parâmetro por perfil; JEV/TypeSafe não expõe esse parâmetro.

O adaptador aplica o menor valor entre o limite configurado e o limite da chamada. O mesmo valor efetivo é reservado no medidor antes de construir o payload ao provedor; o parâmetro não pode ampliar uma reserva nem contornar a guarda de orçamento. Versão publicada e digest incluem a configuração, e o snapshot expõe `effective_parameters_by_agent`. Fontes e limites por agente estão em [evidência de parâmetros](../evidence/v040-parametros-modelo-fontes.md).

## Erros e compatibilidade

`401` token inválido ou ausente; `403` papel sem permissão; `404` recurso ausente ou de outro dono; `409` versão/conflito/uso de comparação; `422` entrada bloqueada ou perfil incompatível; `429` reserva da comparação negada (`request_budget_exceeded` ou `installation_budget_exceeded`). A resposta 429 não salva comparação incompleta nem executa fallback/atendimento. Se a segunda reserva falhar, custo já liquidado pela primeira permanece contabilizado no ledger. `503` provedor indisponível, sem fallback silencioso. Desde a v0.7.0, `POST /messages` exige `Authorization: Bearer` com token de lojista; `user_id` diferente do token retorna `403 identity_mismatch`.

## Acréscimos da v0.6.0

Rotas aditivas aprovadas no [plano v0.6.0](../specs/fechamento-v060-plano.md#apis-ou-interfaces); as rotas acima mantêm o comportamento. Snapshot OpenAPI 0.6.0 no projeto web (31 caminhos).

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `GET /v1/scenarios` | Bearer | catálogo curto de cenários rotulados (ID, título, jornada, idioma, mensagem, verificações e rótulos) |
| `POST /v1/messages` + `scenario_id?` | Bearer | `scenario_id` validado contra o catálogo (`422 unknown_scenario`; `422 scenario_message_mismatch` se a mensagem diferir) e gravado no snapshot; sessão demo limitada por `DEMO_SESSION_MESSAGE_LIMIT` (`429 demo_message_limit_reached`, antes de qualquer chamada ao modelo) |
| `GET /v1/runs/{request_id}` | Bearer/dono | acrescenta `steps` (com `hits`: documento, score, `chunk_id`, trecho), `route`, `prompts_used`, `checks` (origem, resultados, não avaliados, falhas críticas individuais) e `evaluations` |
| `POST /v1/runs/{request_id}/evaluations/estimate` | Bearer/dono | método `model`, rubrica `judge` e versão, avaliador fixo (provedor, modelo, parâmetros), campos de evidência, estimativa e `estimate_digest`; sem chamada paga; preço desconhecido → `503 evaluator_price_unknown` |
| `POST /v1/runs/{request_id}/evaluations` | Bearer/dono | `{confirmed, max_cost_usd, expected_estimate_digest, repeat}`; `422 confirmation_required`/`max_cost_below_estimate`, `409 estimate_stale`; mesma configuração devolve `200` com o registro existente salvo `repeat=true`; nova avaliação `201`; orçamento negado `429` sem registro; falha do avaliador `503 evaluation_failed` com tentativa registrada sem notas |
| `POST /v1/comparisons/estimate` | Bearer | `{profiles[2..3], scenario_ids[1..3], repetitions 1..2, router_mechanism, reuse_recorded}`; células, reaproveitadas, novas, fatores fixos, mudanças entre perfis, `exploratory`, estimativa (teto por atendimento × novas) e `estimate_digest`; sem chamada paga |
| `POST /v1/comparisons` | Bearer | estimativa confirmada (`confirmed`, `max_cost_usd`, `expected_estimate_digest`); `202 {comparison_id, state: running}`; `409 comparison_running`, `409 estimate_stale`, `429` orçamento ou limite demo |
| `GET /v1/comparisons/{comparison_id}` | Bearer/dono | estado (`running`, `completed`, `partial`, `failed`; `interrupted` desde a v0.10.0), configuração, células, falhas e agregados (`profiles`, `cost_by_agent_model`) |

Dados: migração 0008 reversível (`run_evaluations`, `comparisons`, `api_sessions.message_count`). O campo `evaluation` dos perfis permanece no esquema e não é usado no atendimento.

Correções da v0.6.0 (tarefa 60): `POST /v1/runs/{id}/evaluations` responde `409 evaluation_running` quando há uma avaliação em andamento com a mesma configuração (reserva atômica; `run_evaluations.state` aceita `running`, liberada como `failed`/`interrupted` após 10 minutos); `POST /v1/router/compare` e `POST /v1/runs/{id}/evaluations` passam a contar no limite demo (`429 demo_message_limit_reached`), e recusas sem inferência não contam; o reuso da comparação só aceita execuções sem histórico de conversa (`history_turns = 0` no snapshot); custos ausentes aparecem como desconhecidos (`cost_mean_usd`/`cost_total_usd` nulos, `cost_unknown_runs`).

## Acréscimos da v0.10.0

`GET /metrics` (público, como `/ready`): métricas agregadas em texto de exposição Prometheus 0.0.4, calculadas dos traces e do ledger, só com rótulos de conjuntos fechados ([especificação v0.10.0](../specs/rubrica-operacao-v0100.md), D4, CA-59; tarefa 85). Regras de alerta em `alerts/rules.yml`.

Comparação retomável ([especificação v0.10.0](../specs/rubrica-operacao-v0100.md), D3, CA-58; tarefa 84). As rotas acima mantêm o comportamento; a resposta de `GET /v1/comparisons/{comparison_id}` ganha um estado e campos opcionais nas células.

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `GET /v1/comparisons/{comparison_id}` | Bearer/dono | `state` passa a poder ser `interrupted`: a API reiniciou (ou o processo morreu) com a comparação em execução. No startup toda comparação `running` sem thread viva vira `interrupted`, e a leitura faz o mesmo. As células concluídas são preservadas; as que faltavam continuam `pending`. A célula cuja execução estava em curso guarda `interrupted_attempts: [{request_id, cost_usd}]` (custo lido do ledger, somado ao `cost_usd` da comparação). Antes da v0.10.0 esse caso virava `failed` com as células pendentes `skipped` |
| `POST /v1/comparisons/{comparison_id}/resume?retry_failed=false` | Bearer/dono | retoma uma comparação `interrupted`, `partial` ou `failed` com a mesma configuração e o mesmo teto confirmado: células com resultado (`request_id`) não rodam de novo; células `failed` só rodam de novo com `retry_failed=true` (o `request_id` anterior vai para `previous_request_ids`); `cost_usd` acumula. Orçamento e limite demo verificados só para as células que faltam. `202 {comparison_id, state: running, resumed_cells}`; `404` ausente ou de outro dono; `409 comparison_running`, `409 comparison_completed`, `409 nothing_to_resume`, `409 fixed_factors_changed` (base de conhecimento, prompts ou modo de execução mudaram); `429 installation_budget_exceeded` ou `demo_message_limit_reached` |

Dados: migração 0012 reversível (`comparisons.state` aceita `interrupted`; a tabela é recriada porque o SQLite não altera `CHECK`). O rollback converte `interrupted` em `failed` e restaura o `CHECK` anterior. Versão do esquema 12, reportada em `/ready`. A interface web não muda nesta versão: `interrupted` aparece como está.

## Acréscimos da v0.11.0

Resumo da busca no trace ([especificação v0.11.0](../specs/juiz-retrieval-v0110.md), D1; tarefa 87). Campos aditivos; nada muda nas rotas nem nos outros campos.

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `GET /v1/runs/{request_id}` | Bearer/dono | os passos de busca web (`knowledge` em modo `web` e `web`) passam a mostrar `web_summary` (texto da busca escrito pelo modelo, mascarado, até 4 000 caracteres; é o resumo do assistente, não a página), `web_summary_truncated` (booleano) e `web_urls` (lista de `{title, url}` citados, mascarados) |

Dados: sem migração; os campos vivem no `detail` de cada passo do trace.
