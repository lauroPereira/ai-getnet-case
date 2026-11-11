# Contrato da API v1

A interface web usa somente esta API HTTP. O projeto irmão [ai-getnet-case-web](https://github.com/lauroPereira/ai-getnet-case-web) mantém o snapshot OpenAPI consumido pela interface em `openapi-v1.json`; o mapa Python é gerado por `tools/generate_client.py` nesse projeto. Esse arquivo não pertence ao repositório backend.

## Identidade e autorização

- `GET /v1/auth/authorize` (v0.13.0, tarefa 97): login por redirecionamento. Parâmetros `response_type=code`, `client_id` e `redirect_uri` registrados (`OAUTH_REDIRECT_URIS`, comparação exata), `code_challenge` com `code_challenge_method=S256` (PKCE obrigatório) e `state` (obrigatório). Mostra a página de login do emissor; depois dela o navegador volta a `redirect_uri` com `code` (uso único, 60 s), o mesmo `state` e `iss`. Cliente ou `redirect_uri` não registrado recebe página de erro, sem redirecionamento; os demais erros voltam ao cliente com `error`, `state` e `iss`. O formulário da página faz `POST /v1/auth/authorize` com os mesmos parâmetros, `username` e `password`: repete as verificações do `GET`, conta as tentativas nos limites de `/v1/auth/token` e responde `303` para `redirect_uri` com `code`, `state` e `iss`; senha errada mostra a página de novo (`400`), excesso de tentativas `429` com `Retry-After`.
- `POST /v1/auth/token` (OAuth 2.0, corpo `application/x-www-form-urlencoded`): `grant_type=authorization_code` (com `code`, `redirect_uri`, `client_id` e `code_verifier`) e `refresh_token` (com `refresh_token` e `client_id`) para a interface, ambos devolvendo também `refresh_token`; o refresh é rotativo, e um refresh já usado que reaparece revoga a família inteira (refresh e acessos emitidos com ele). `grant_type=password` continua para os usuários de demonstração (smoke e CLI, marcado como demonstração no `/docs`) e `client_credentials` para o serviço de ticketing. Devolve um JWT RS256 do emissor próprio; as chaves públicas estão em `/.well-known/jwks.json` e a descoberta em `/.well-known/openid-configuration`.
- `POST /v1/auth/revoke` revoga o token; com o campo de formulário opcional `token` contendo um refresh do mesmo principal, revoga também a família dele. Token ausente, inválido, expirado ou revogado retorna `401`.
- Papéis `merchant`, `operator`, `service`, `demo` e `admin`, com escopos. O lojista vem do token; o backend verifica papel, escopo e dono em cada rota. Sessão demo não publica perfis. As chaves de provedor não fazem parte do contrato nem da interface.
- `POST /v1/sessions` e `DELETE /v1/sessions/current` (v0.4.0 a v0.6.0) deram lugar a essas rotas na v0.7.0 ([decisão 0017](../architecture/decisions/0017-identidade-principal-escopos.md)). O contrato completo de identidade, fila e webhooks está na [especificação v0.7.0](../specs/identidade-hitl-v070.md), seção "Contrato entre os times".

## Rotas

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `GET /v1/auth/authorize` | público | página de login do emissor; devolve `code` ao `redirect_uri` registrado (PKCE S256) |
| `POST /v1/auth/authorize` | público (formulário da página de login) | confere a senha e devolve `303` com `code`, `state` e `iss` ao `redirect_uri` registrado; fora do OpenAPI |
| `POST /v1/auth/token` | público | emite JWT pelas concessões `authorization_code` e `refresh_token` (com refresh rotativo), `password` (demonstração) e `client_credentials` |
| `POST /v1/auth/revoke` | Bearer | revoga o token atual e, com `token`, a família de um refresh do mesmo principal |
| `GET /v1/catalog/models` | Bearer | catálogo datado com preço, capacidades, parâmetros por agente e links para documentação oficial |
| `GET /v1/profiles` | Bearer | perfis publicados visíveis ao papel; desde a v1.1.0, com a disponibilidade de cada perfil e dos motores de Router (abaixo) |
| `POST /v1/profiles` | admin | cria rascunho compatível |
| `PUT /v1/profiles/{profile_id}/draft` | admin | atualiza versão de rascunho por controle otimista de versão |
| `POST /v1/profiles/{profile_id}/publish` | admin | publica uma versão imutável |
| `POST /v1/router/compare` | Bearer | executa somente os Routers LLM e JEV para o mesmo snapshot |
| `POST /v1/messages` | Bearer | atende usando o método escolhido; pode consumir uma comparação vinculada |
| `GET /v1/runs/{request_id}` | Bearer/dono | consulta snapshot saneado de execução |
| `GET /v1/conversations/{conversation_id}` | Bearer/dono | consulta conversa do cliente vinculado; operadores leem conversas com caso |
| `GET /v1/conversations` | Bearer/dono | conversas do lojista do token, sem texto de mensagem (v1.1.0, abaixo) |
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
| `POST /v1/comparisons/{comparison_id}/resume?retry_failed=false` | Bearer/dono | retoma uma comparação `interrupted`, `partial` ou `failed` com a mesma configuração e o mesmo teto confirmado: células com resultado (`request_id`) não rodam de novo; células `failed` só rodam de novo com `retry_failed=true` (o `request_id` anterior vai para `previous_request_ids`); `cost_usd` acumula. Orçamento e limite demo verificados só para as células que faltam. `202 {comparison_id, state: running, resumed_cells}`; `404` ausente ou de outro dono; `409 comparison_running`, `409 comparison_completed`, `409 nothing_to_resume`, `409 fixed_factors_changed` (base de conhecimento, prompts ou modo de execução mudaram); `429 installation_budget_exceeded` ou `demo_message_limit_reached`. Desde a v0.13.0 também `409 execution_cost_unknown` e `202` com `resumed_cells: 0` (ver os acréscimos da v0.13.0) |

Dados: migração 0012 reversível (`comparisons.state` aceita `interrupted`; a tabela é recriada porque o SQLite não altera `CHECK`). O rollback converte `interrupted` em `failed` e restaura o `CHECK` anterior. Versão do esquema 12, reportada em `/ready`. A interface web não muda nesta versão: `interrupted` aparece como está.

## Acréscimos da v0.11.0

Resumo da busca no trace ([especificação v0.11.0](../specs/juiz-retrieval-v0110.md), D1; tarefa 87). Campos aditivos; nada muda nas rotas nem nos outros campos.

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `GET /v1/runs/{request_id}` | Bearer/dono | os passos de busca web (`knowledge` em modo `web` e `web`) passam a mostrar `web_summary` (texto da busca escrito pelo modelo, mascarado, até 4 000 caracteres; é o resumo do assistente, não a página), `web_summary_truncated` (booleano) e `web_urls` (lista de `{title, url}` citados, mascarados) |

Dados: sem migração; os campos vivem no `detail` de cada passo do trace.

## Acréscimos da v0.12.0

Memória de conversa e escrita com confirmação ([especificação v0.12.0](../specs/memoria-escrita-v0120.md), D1, D2, D5, D6; tarefas 92 e 94). Campos, escopo e passos aditivos; as rotas mantêm o comportamento.

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `GET /v1/conversations/{conversation_id}` e `GET /conversations/{conversation_id}` (demo) | Bearer/dono | acrescentam `summary` (resumo rolante da conversa longa, texto ou `null`; o cursor interno não aparece) e `facts` (registro de fatos lidos de resultados de ferramenta e de casos, nunca de texto de modelo: `[{kind, value, source_tool, source_message_id, created_at}]`, `kind` em `protocol`, `amount`, `percent`, `date`, `status` ou `product`, na ordem em que foram registrados) |
| `POST /v1/auth/token` | público | o token do papel `merchant` passa a trazer o escopo `support:write` (pedir o cancelamento de uma venda, executado só depois de um sim explícito); `demo`, `operator`, `service` e `admin` não recebem. Token emitido antes da v0.12.0, sem o escopo, consulta mas não pede nem confirma: a recusa é auditada como `forbidden_scope` |
| `GET /v1/runs/{request_id}` | Bearer/dono | `steps` pode listar `summary` (atualização do resumo, com `prompt`; primeiro passo do turno, só para mensagem que a guarda de entrada deixa passar, com folga própria de uma chamada fora de `max_model_calls`) e `confirmation` (logo depois de `router`, enquanto um pedido de cancelamento espera resposta; confirma ou recusa por código quando o sim ou o não é validado) |
| `GET /v1/scenarios` | Bearer | acrescenta `SC-CANCEL-CONFIRM` (jornada `cancellation_confirm`, três turnos: pedido, "Sim", consulta do status) |
| `POST /v1/messages` e `POST /messages` | Bearer | `get_sale_cancellation_context` aceita filtros como `payment_type`, `installments`, `channel`, `sale_date` e `amount` (centavos), e retorna os itens selecionados e as vendas com dados de pagamento, valor, data, cancelamento e pedido mais recente. Cada cancelamento inclui a venda relacionada e recebe `protocol` após confirmação. Em turnos de cancelamento, o status é composto em código a partir das consultas daquela conversa; sem venda identificada, o assistente pede qual venda consultar. Pedidos pendentes, recusados, expirados ou sem escopo usam respostas fixas; uma resposta de operador não é substituída. Uma pergunta com rótulo `acknowledgement` segue para Support. |

Dados: migração 0014 reversível (`conversations.summary` e `summary_until_message_id`, `conversation_facts`, `sale_cancellation_requests` com índice único parcial por chave de idempotência para pedido pendente ou confirmado). A descida é recusada enquanto houver pedido `confirmed`, cujo protocolo foi entregue ao lojista e não existe em outra tabela; nada é alterado. Versão do esquema 14, reportada em `/ready`.

## Acréscimos da v0.13.0: dois workers, reenvio de webhook e caso órfão

[Especificação v0.13.0](../specs/identidade-operacao-v0130.md), D4, D5, CA-70, CA-71; tarefa 99. Uma rota nova; as demais mantêm o contrato.

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `POST /v1/webhooks/deliveries/{delivery_id}/resend` | operador (`handoff:operate`) | reenvia a entrega esgotada por trás da tentativa `delivery_id` (as tentativas aparecem em `GET /v1/handoffs/{case_id}`, campo `deliveries`): a intenção volta a `pending` com mais uma rodada de tentativas. `202 {delivery_id, event_id, target, case_id, status: pending, resend_count}`; `404 delivery_not_found`; `409 delivery_not_exhausted` (pendente, entregue ou recusada pelo receptor); `409 delivery_target_not_configured` (o destino está sem URL ou segredo agora); `429 rate_limited`. Auditada como `webhook.resend` |
| `GET /v1/handoffs/{case_id}` | operador (`handoff:operate`) | aditivo: cada item de `deliveries` (uma tentativa) traz `intent_status`, o estado da intenção por trás dela (`pending`, `delivered`, `rejected` ou `exhausted`), e `resend_count`; numa tentativa sem intenção gravada, os dois vêm `null`. O reenvio vale para a tentativa cuja intenção está `exhausted`. Um evento que espera a intenção esgotada do mesmo caso e destino ainda não tem tentativa e não aparece em `deliveries` |
| `GET /v1/comparisons/{comparison_id}`, `POST /v1/comparisons/{comparison_id}/resume` | Bearer/dono | mesma forma de resposta, com novos códigos de célula e de falha (abaixo). Uma comparação `running` passa a `interrupted` quando a lease do worker que a executa vence (20 s sem renovação), em qualquer worker; a retomada pode acontecer em outro worker. A retomada responde `409 execution_cost_unknown` enquanto o custo de uma execução anterior não puder ser lido no ledger, e `202` com `resumed_cells: 0` para fechar uma comparação em que todas as células já têm resultado |

Reservas sob a lease: cada reserva paga de uma célula, de chamada de modelo ou de embedding da consulta, só é gravada no ledger dentro de uma transação que confirma que a comparação continua `running` sob o mesmo worker, com a lease em dia e aquela célula em curso. Se a confirmação falhar, a execução da célula para antes da reserva, sem chamada ao provedor, e o worker não grava mais nada na comparação; quem a assumir concilia a célula pelo snapshot e pelo ledger.

Célula interrompida: quando a comparação passa a `interrupted`, um resultado durável em `run_snapshots` da mesma requisição, dono, comparação, perfil e cenário é restaurado na célula sem nova chamada de modelo. Sem resultado durável, a célula interrompida guarda `interrupted_attempts: [{request_id, cost_usd}]` e:

- fica `pending` só quando o ledger, lido com segurança, não tem tentativa paga daquela requisição;
- fica `failed` com `error: interrupted_after_paid_attempt` e o `request_id` preservado quando o ledger tem reserva ou liquidação; o custo conhecido entra no `cost_usd`;
- fica `failed` com `error: interrupted_cost_unknown` quando o ledger não pode ser lido, com a falha `execution_cost_unknown`; quando a leitura volta, a retomada preenche o custo da tentativa e troca o erro por `interrupted_after_paid_attempt` (ou `interrupted`, se não houve tentativa paga).

Uma célula `failed` com tentativa paga só roda de novo com `retry_failed=true`; o `request_id` anterior vai para `previous_request_ids`.

Falhas registradas em `failures` (as que trazem `request_id` apontam a execução):

| Código | Quando | Efeito |
| --- | --- | --- |
| `execution_cost_unknown` | o custo de uma execução não pôde ser lido no ledger (traz `cost_estimate_usd` quando há estimativa) | durante a execução, as células seguintes ficam `skipped` com esse erro; a comparação não termina `completed`; a retomada responde `409 execution_cost_unknown`, com ou sem `retry_failed`, até o ledger poder ser lido |
| `execution_cost_recovered` | a retomada leu o custo antes desconhecido | o custo entra no `cost_usd` da comparação uma vez; a retomada segue |
| `budget_denied` | o trace mostra que a guarda de orçamento recusou uma chamada paga da execução | a célula passa a `failed` com esse erro e fica fora de `sample_size`; o custo continua contado; durante a execução, as células seguintes ficam `skipped` com esse erro. A estimativa não oferece para reaproveitamento uma execução cujo trace falta, não pode ser lido ou mostra recusa: oferece a execução válida mais antiga ou uma célula `new`. Se a execução oferecida passar a ter recusa ou trace indisponível antes de rodar, a célula `recorded` fica `failed` com o erro correspondente, sem parar as seguintes; com `retry_failed=true`, a retomada reaproveita a mesma execução e a célula falha de novo, sem pagar nada, enquanto uma comparação nova recebe a execução válida mais antiga ou `new`. Se o trace mudar entre a estimativa e a confirmação, a confirmação responde `409 estimate_stale` e o cliente estima de novo |
| `trace_unavailable` | o trace de uma execução falta (a gravação falhou) ou não pôde ser lido | a célula concluída passa a `failed` com esse erro, sem `checks`, pois uma recusa do orçamento não pode ser descartada; o custo continua contado; durante a execução, as células seguintes ficam `skipped` com esse erro; nova tentativa só com `retry_failed=true`. Uma célula reaproveitada (`recorded`) também fica `failed`, sem parar as seguintes, porque não fez chamada paga; com `retry_failed=true` reaproveita a mesma execução |

O custo da comparação conta cada execução uma vez, pelo maior valor entre a estimativa durável e o custo comprometido conhecido no ledger (que inclui os embeddings da consulta); para uma tentativa sem resultado, usa o custo conhecido do ledger.

Comportamento: uma entrega cujas tentativas acabaram fica `exhausted` (antes `failed`); os eventos seguintes do mesmo caso e destino esperam por ela e saem, na ordem, depois do reenvio, de modo que uma resposta nunca chega ao ticketing antes da criação do ticket. Uma entrega recusada pelo receptor é final e não segura os seguintes; outros casos nunca esperam. A subida de um worker reenvia uma vez as esgotadas há mais de 1 h. Caso `open` aberto por um turno que salvou o fluxo e parou antes de avisar o ticketing (sem ticket, sem evento recebido do ticketing, sem intenção no outbox, com mais de 2 min) recebe a intenção de `handoff.created` na subida; o caso cujo fluxo não chegou a ser salvo se completa quando o lojista reenvia a mesma mensagem.

Dados: migração **0016** (reversível): `comparisons.worker_id`, `comparisons.heartbeat_at`; `webhook_outbox.status` aceita `exhausted` no lugar de `failed`; `webhook_outbox.resend_count`. A descida converte `exhausted` em `failed` e remove as três colunas; rode-a com a API parada.

## Acréscimos da v0.13.0: emissor OIDC externo

[Especificação v0.13.0](../specs/identidade-operacao-v0130.md), D2, CA-68; tarefa 98. Nenhuma rota nova; o emissor próprio continua o padrão e suas respostas não mudam.

- **Tokens de emissores externos.** Toda rota com Bearer aceita também o token de um emissor listado em `OIDC_ISSUERS` (lista JSON com `issuer`, `audience`, `groups` e, opcionalmente, `algorithms`, `groups_claim` e `customer_id_claim`). O `iss` é comparado exatamente; a assinatura é conferida com a JWKS publicada pela descoberta do emissor (`/.well-known/openid-configuration`), só com os algoritmos assimétricos configurados para ele (padrão `RS256`); `aud` precisa conter a audiência configurada; `exp` e `iat` são obrigatórios e `nbf` é conferido quando presente, com tolerância de 30 s; vida (`exp - iat`) de no máximo 24 h.
- **Papel e escopos.** A claim de grupos (padrão `groups`) precisa conter grupos de exatamente um papel entre `merchant`, `operator` e `admin`; os escopos são os do papel, e o `scope` do token não amplia nada. Com `groups_claim` igual a `email`, as chaves de `groups` são endereços exatos (sem curinga nem domínio), comparados sem normalização; o e-mail precisa vir como um único texto com `email_verified: true`, e um token sem `email_verified`, com outro valor nela ou com `email` em lista fica sem papel (`403`). O lojista de um token `merchant` vem da claim configurada em `customer_id_claim`, que precisa ser uma claim controlada pelo administrador do emissor (nunca editável pelo próprio usuário). A revogação (`POST /v1/auth/revoke`) e os contadores por token usam o `jti` prefixado com o emissor (`<issuer>#<jti>`): revogar um token externo nunca revoga um token local nem de outro emissor com o mesmo `jti`.
- **Principal externo.** O identificador segue o formato `<papel>:<sub percent-encoded>@<issuer percent-encoded>` e fica gravado com o `issuer`. O `sub` e a URL exata do emissor configurado são codificados separadamente em UTF-8, incluindo o esquema e a barra final da URL. Nos handoffs, o identificador do operador externo é o sufixo do principal depois de `operator:`. Trate esse valor como opaco, pois uma alteração na URL do emissor produz outro identificador.
- **Erros.** `401 invalid_issuer`: o `iss` não é o do emissor próprio nem de um emissor configurado. `403 insufficient_scope`: token válido de emissor externo sem grupo reconhecido, com grupos de mais de um papel ou, no mapeamento por e-mail, sem `email_verified: true`. `401 invalid_token`: assinatura, algoritmo, `kid`, audiência, validade ou lojista recusados, ou emissor externo indisponível sem chave em cache (só os tokens daquele emissor; a API e os demais emissores seguem atendendo). As chaves em cache continuam valendo enquanto a renovação falha, por até 24 h; com emissor `http`, a JWKS precisa estar na mesma origem do emissor.
- **Demonstração.** `docker compose --profile oidc up` sobe o Dex com usuários sintéticos ([configuração](../../docker/dex/config.yaml)); o valor de `OIDC_ISSUERS` para ele está comentado no `.env.example` e mapeia o e-mail verificado (`groups_claim` `email`), porque os usuários estáticos do Dex v2.41.1 não emitem `groups`; o lojista vem de `name` (o `username` do usuário estático, definido pelo administrador).

## Acréscimos da v0.13.0: operador no Telegram

[Especificação v0.13.0](../specs/identidade-operacao-v0130.md), D3, CA-69; tarefa 100. Nenhuma rota nova; o adaptador usa as rotas da fila como qualquer operador.

- **Destino de webhook `telegram`.** Com `TELEGRAM_WEBHOOK_URL` e `TELEGRAM_WEBHOOK_SECRET` configurados, o assistente entrega `handoff.created` também ao adaptador, com o mesmo envelope e a mesma assinatura dos outros destinos; `data` leva só `case_id`, `protocol` e `summary` (mascarado). As tentativas aparecem em `deliveries` com `target: telegram` e têm reenvio como as demais. URL vazia: nada vai ao Telegram.
- **Operador de serviço.** O adaptador obtém o token pela concessão `client_credentials` do cliente `telegram-operator` (`TELEGRAM_CLIENT_SECRET`), com papel `operator` e principal `operator:telegram`; as ações aparecem na fila e na auditoria com `operator_id` `telegram`. A chave de idempotência de cada ação é `telegram-<update_id>`.
- **Adaptador** (`python -m merchant_assistant.integrations.telegram`, perfil `telegram` do compose). Recebe em `POST /webhooks/assistant` (`200 accepted|replayed`; `401 invalid_signature`, assinatura ausente, inválida ou fora da janela; `400 invalid_event`, corpo que não é um envelope de evento com `id` e `data`; `422 unsupported_event`, evento diferente de `handoff.created`; `422 invalid_event`, sem `case_id` ou protocolo válidos; `503 telegram_unavailable`, Telegram indisponível, que o despachante repete); envia ao chat `TELEGRAM_OPERATOR_CHAT_ID` o protocolo e o resumo; lê `/claim`, `/approve`, `/reply <texto>` e `/reject <instrução>` por long polling, só desse chat, sem sufixo ou com o `username` do próprio bot (`/approve@<bot>`, lido por `getMe` antes da primeira leitura); comando com o sufixo de outro bot é ignorado. Sem `TELEGRAM_BOT_TOKEN` não sobe.

Dados: migração 0015 reversível acrescenta `auth_codes`, `refresh_tokens` e `api_principals.issuer`; migração 0016 acrescenta leases em `comparisons` e o reenvio em `webhook_outbox`. Schema 16 é reportado em `/ready`. O downgrade de 0015 remove os códigos e as famílias de refresh, então clientes web fazem novo login; o downgrade de 0016 converte `exhausted` em `failed` e remove os campos de lease e reenvio.

## Acréscimos da v1.1.0: lista de conversas

[Especificação v1.1.0](../specs/tickets-retomada-v110.md), D2, CA-77; tarefa 110. Uma rota nova e dois campos aditivos; as demais rotas mantêm o contrato.

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `GET /v1/conversations?limit=5` | Bearer/dono | `200 {conversations: [...]}`: conversas do lojista do token (o mesmo lojista da rota por id: `merchant` e `demo` pelo token, `admin` pelo lojista sintético da demonstração), da atividade mais recente para a mais antiga (`updated_at` decrescente). `limit` de 1 a 20, padrão 5; fora disso, `422 invalid_request`. Cada item traz `conversation_id`, `state`, `created_at`, `updated_at`, `handoff_protocol` (protocolo do caso de encaminhamento mais recente da conversa, ou `null`) e `pending_operator_reply` (há resposta de atendente gravada e ainda não entregue numa mensagem do lojista). Nenhum texto de mensagem: a conversa completa continua em `GET /v1/conversations/{conversation_id}`. Token sem lojista vinculado (operador, serviço): `403 insufficient_scope`; sem token, `401` |
| `GET /v1/conversations/{conversation_id}` e `GET /conversations/{conversation_id}` | Bearer/dono | aditivo: cada turno de `messages` traz `message_id`, inteiro estável e crescente na ordem da conversa |
| `POST /v1/messages` + `displayed_operator_message_id?` | Bearer | campo opcional, inteiro a partir de 1 (fora disso, `422 invalid_request`): o `message_id` do turno de atendente que a interface já exibiu. Se for um turno de atendente desta conversa ainda não entregue, ele e os turnos de atendente anteriores ainda não entregues da mesma conversa (exibidos acima dele no mesmo histórico) passam a contar como entregues, e a mensagem é atendida normalmente pelo Router e pelos agentes, sem repetir a resposta. Turno de outra conversa ou de outro lojista, turno que não é de atendente, já entregue ou inexistente não muda nada e não gera erro. Uma resposta de atendente mais nova que a exibida continua sendo entregue como resposta desta mensagem (`route=human_reply`). Sem o campo, a entrega é a de antes |

A interface web usa a rota para retomar a última conversa depois de um novo login: lê a mais recente, carrega o histórico pela rota por id e continua na mesma `conversation_id`. Quando a conversa retomada tem resposta de atendente pendente, a primeira mensagem seguinte leva o `message_id` do último turno de atendente exibido.

Dados: sem migração; a rota lê `conversations`, `messages` e `handoff_cases`.

## Acréscimos da v1.1.0: disponibilidade de perfis e motores

[Especificação v1.1.0](../specs/tickets-retomada-v110.md), D3, CA-78; tarefa 111. Campos aditivos; as rotas mantêm o comportamento.

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `GET /v1/profiles` | Bearer | cada perfil ganha `available` (o provedor de cada agente do atendimento tem chave configurada no backend) e `missing_providers` (nomes dos provedores sem chave, em ordem alfabética; vazio quando disponível); a resposta ganha `router_mechanisms: {"llm": true, "jev": <TYPESAFE_API_KEY configurada>}`. A chave conta como configurada quando não está vazia, a mesma regra usada para construir os clientes de modelo. O campo `evaluation` do perfil, que o atendimento não usa, não torna o perfil indisponível. Nenhum valor de chave sai da API |

A interface web marca o perfil indisponível, desabilita o JEV indisponível no atendimento e nas comparações, diz qual chave falta no backend (`DEEPSEEK_API_KEY`, `TYPESAFE_API_KEY`) e escolhe por padrão um perfil e um motor disponíveis. Uma escolha indisponível enviada mesmo assim continua recusada com `503 provider_unavailable`. Uma resposta sem os campos novos (backend anterior à v1.1.0) é tratada como tudo disponível.

Dados: sem migração.
