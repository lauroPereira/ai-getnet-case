# Contrato da API v0.4.0

A interface web usa somente esta API HTTP. O projeto irmão `C:\workspace\ai-getnet-case-web` mantém o snapshot OpenAPI consumido pela interface em `openapi-v1.json`; o mapa Python é gerado por `tools/generate_client.py` nesse projeto. Esse arquivo não pertence ao repositório backend.

## Sessões e autorização

- `POST /v1/sessions` aceita `{"access_key":"..."}` e devolve um Bearer opaco com prazo de 60 minutos e papel `demo` ou `admin`. O backend compara a chave configurada em tempo constante e armazena somente digest SHA-256 do token.
- `DELETE /v1/sessions/current` revoga a sessão autenticada e retorna `204` sem corpo. Token ausente, revogado, expirado ou inválido retorna `401`; a resposta segue íntegra na mesma conexão persistente.
- As rotas protegidas documentam `SessionBearer` no OpenAPI e verificam papel e dono no backend. Sessão demo não publica perfis. As chaves de provedor não fazem parte do contrato nem da interface.

## Rotas

| Rota | Acesso | Efeito |
| --- | --- | --- |
| `POST /v1/sessions` | público | cria sessão a partir de chave configurada no backend |
| `DELETE /v1/sessions/current` | Bearer | revoga sessão atual |
| `GET /v1/catalog/models` | Bearer | catálogo datado com preço, capacidades, parâmetros por agente e links para documentação oficial |
| `GET /v1/profiles` | Bearer | perfis publicados visíveis ao papel |
| `POST /v1/profiles` | admin | cria rascunho compatível |
| `PUT /v1/profiles/{profile_id}/draft` | admin | atualiza versão de rascunho por controle otimista de versão |
| `POST /v1/profiles/{profile_id}/publish` | admin | publica uma versão imutável |
| `POST /v1/router/compare` | Bearer | executa somente os Routers LLM e JEV para o mesmo snapshot |
| `POST /v1/messages` | Bearer | atende usando o método escolhido; pode consumir uma comparação vinculada |
| `GET /v1/runs/{request_id}` | Bearer/dono | consulta snapshot saneado de execução |
| `GET /v1/conversations/{conversation_id}` | Bearer/dono | consulta conversa do cliente vinculado |

## Comparação e uso

A comparação valida input guard, perfil publicado, papel/dono da conversa e limite de orçamento antes de chamar os dois Routers. O `comparison_id` fica associado ao principal, cliente, conversa, digest da mensagem, digest do estado, perfil/versão, método escolhido e expiração de cinco minutos. `POST /v1/messages` valida esses campos e consome a comparação em uma única transação `BEGIN IMMEDIATE`; decisão ausente, vencida, incompatível ou já consumida retorna `409`. A decisão selecionada vai direto ao Router do atendimento, evitando nova chamada ao Router. As ferramentas dos agentes restantes pertencem somente ao atendimento.

O snapshot da execução registra perfil e digest, versões de prompt/base, mecanismo e modelos efetivos, modo, chamadas, ferramentas, fontes e duração quando disponíveis. `effective_parameters_by_agent` inclui somente parâmetros de fato enviados pelo adaptador; valores internos usados apenas para estimar reserva não são descritos como parâmetro efetivo. Custos são apresentados como estimativas com faixa/tarifa registrada, nunca como fatura exata. Respostas não incluem chave de provedor ou chave de acesso.

## Parâmetros de modelos por agente

O catálogo permite configurar `max_output_tokens` somente para `openai:gpt-6-luna` e `deepseek:deepseek-flash`, com a faixa de 16 até o limite existente do agente: Router 300, Knowledge 500, Support 1200, Escalation 400 e Personality 600. A aplicação aceita apenas inteiros estritos, rejeita chaves desconhecidas e valores fora da faixa antes de persistir uma nova versão. Evaluation permanece reservado à v0.6.0; JEV/TypeSafe não expõe esse parâmetro.

O adaptador aplica o menor valor entre o limite configurado e o limite da chamada. O mesmo valor efetivo é reservado no medidor antes de construir o payload ao provedor; o parâmetro não pode ampliar uma reserva nem contornar a guarda de orçamento. Versão publicada e digest incluem a configuração, e o snapshot expõe `effective_parameters_by_agent`. Fontes e limites por agente estão em [evidência de parâmetros](../evidence/v040-parametros-modelo-fontes.md); a validação usa adaptador fake e não envia inferência paga.

## Erros e compatibilidade

`401` sessão inválida/ausente; `403` papel sem permissão; `404` recurso ausente ou de outro dono; `409` versão/conflito/uso de comparação; `422` entrada bloqueada ou perfil incompatível; `429` reserva da comparação negada (`request_budget_exceeded` ou `installation_budget_exceeded`). A resposta 429 não salva comparação incompleta nem executa fallback/atendimento. Se a segunda reserva falhar, custo já liquidado pela primeira permanece contabilizado no ledger. `503` provedor indisponível, sem fallback silencioso. O endpoint legado `POST /messages` mantém seu request/response v0.3.0 e não depende de sessão `/v1`.

## Escopo de validação

OpenAPI e integração usam dados e modelo programados. Não foi enviada inferência real para OpenAI, DeepSeek ou TypeSafe. CA-32 de execução JEV real continua pendente; também não foi enviado `GET /models` autenticado de conta de provedor.

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
| `GET /v1/comparisons/{comparison_id}` | Bearer/dono | estado (`running`, `completed`, `partial`, `failed`), configuração, células, falhas e agregados (`profiles`, `cost_by_agent_model`) |

Dados: migração 0008 reversível (`run_evaluations`, `comparisons`, `api_sessions.message_count`). O campo `evaluation` dos perfis permanece no esquema e não é usado no atendimento.

Correções da revisão r1 (tarefa 60): `POST /v1/runs/{id}/evaluations` responde `409 evaluation_running` quando há uma avaliação em andamento com a mesma configuração (reserva atômica; `run_evaluations.state` aceita `running`, liberada como `failed`/`interrupted` após 10 minutos); `POST /v1/router/compare` e `POST /v1/runs/{id}/evaluations` passam a contar no limite demo (`429 demo_message_limit_reached`), e recusas sem inferência não contam; o reuso da comparação só aceita execuções sem histórico de conversa (`history_turns = 0` no snapshot); custos ausentes aparecem como desconhecidos (`cost_mean_usd`/`cost_total_usd` nulos, `cost_unknown_runs`).
