# Passagens do Developer — v0.7.0

## Tarefa 63, rodada 1

- **Papel e responsável:** Developer (Time A), subagente despachado pelo Supervisor.
- **Objetivo e critérios:** [tarefa 63](../tasks/63-identidade-principal-escopos.md) na forma reescrita em `fe9d12b` ([spec v0.7.0, versão 2](../specs/identidade-hitl-v070.md): JWT com emissor próprio). Critérios ligados a CA-46.
- **Escopo:** só o backend (`ai-getnet-case`). Arquivos: `src/merchant_assistant/api/identity.py` (novo: `Principal`, tabela papel → escopos, contas com hash PBKDF2, chave RS256, emissor, verificador único, revogação, rate limit), `api/app.py`, `api/v1.py`, `api/schemas.py`, `config.py`, `tools/base.py`, `tools/registry.py`, `tools/domain.py` (só a anotação de recurso da auditoria), `agents/escalation.py`, `orchestration/graph.py`, `orchestration/run.py`, `mcp_server.py`, `cli.py`, `testing.py`, `data/migrations.py` (0009), `pyproject.toml` (`pyjwt[crypto]>=2.10` logo depois de `mcp>=2.3`), `.env.example`, `docker-compose.yml` (só acréscimos no bloco `api`), testes (`tests/unit/test_identity.py` e `tests/integration/test_v070_identity.py` novos; os testes existentes foram migrados de `/v1/sessions` para token). Nada em `merchant_assistant/ticketing/`, no projeto web nem em `docs/raw/`.
- **Estado:** em andamento → pronta para revisão.
- **Branch e PR:** `codex/v0.7.0-identidade-hitl`; sem PR e sem push.
- **Base e versão final:** base `fe9d12b` (a rodada começou em `220878e`; o Supervisor commitou a spec v2 por cima sem tocar no trabalho local). Código em `59f0311`; esta passagem e a seção Validação da tarefa no commit seguinte. Árvore limpa, exceto `Claude outputs/` e `_tmp/`, que não são meus.
- **Independência:** não se aplica (implementação).

### Evidência

- `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v070-a-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **código 0, 406 passed** (304 s), Ruff ok, skills ok. Antes da rodada: 349 testes na v0.6.0; antes da troca para JWT, o estado intermediário tinha 376.
- Uma execução estrita anterior falhou num teste meu (`test_verifier_refuses_bad_claims[changes3]`): o `nbf` futuro era calculado na coleta e, 4 min depois, já estava no passado. Corrigido: os tempos agora são relativos ao momento do teste.
- `docker compose -f <cópia>/docker-compose.yml config --quiet` → 0, numa cópia do compose num diretório sem `.env` (para não imprimir segredos locais). Ambiente resolvido: `JWT_ISSUER=http://api:8000`, `DEMO_USER_PASSWORDS` e `TICKETING_CLIENT_SECRET` com os valores fictícios.
- `uv pip install --python .venv/Scripts/python.exe "pyjwt[crypto]>=2.10"` → "Audited 1 package". A biblioteca já estava no `.venv` (pyjwt 2.15.1, cryptography 50.0.2, dependências do `mcp`).
- Nenhuma chamada paga. Não li `.env`, não subi Docker e não rodei `ingest`, `eval --judge` nem o smoke real.

### Critérios (para o Supervisor marcar depois da revisão e do QA)

O mapa critério → teste está na seção Validação da tarefa. Resumo:

- **CA-46:** pedido sem token, com token inválido ou expirado → `401` com `WWW-Authenticate: Bearer`. Adulterado, outra chave, `kid` desconhecido, `typ` diferente de `at+jwt`, HS256, outro `iss`, outra `aud`, `exp`/`nbf` fora de 30 s e `jti` revogado → `InvalidToken`. `identity_mismatch` → `403`. B recebe `404` nas rotas de demo e `/v1` (conversa, trace, run) de A.
- **N tool calls → N linhas de auditoria** com principal, escopo e resultado, inclusive `forbidden_scope` e `forbidden_customer`.
- Operador e serviço em `POST /messages` → `403`; lojista sem `handoff:operate`.
- JWKS da rota valida o token com `jwt.PyJWKSet`. JWKS externo testado com chave gerada no teste (`fetch_data` substituído, sem rede).
- `client_credentials` do `ticketing-demo` dá `handoff:integrate`, 600 s e nenhum `customer_id`. Segredo errado ou vazio → `401 invalid_client`.
- Rate limit `429` com `Retry-After` sem chamada a modelo, em `/messages` e `/v1/messages`.
- O MCP recusa token inválido, de operador ou de serviço e deriva o lojista do token. `--customer` saiu.
- Senhas só como hash no banco e fora do log; chave privada em `data/runtime/jwt/` (ignorado pelo Git). Nos testes, a chave é gerada em diretório temporário.
- Compose válido, smoke programado com token, suíte estrita com código 0.

### Decisões tomadas além do texto (todas reversíveis)

1. **Erro do `/v1/auth/token` no envelope do projeto** (`{"error": {"code": "invalid_grant", "message", "request_id"}}`), e não no formato plano da RFC 6749 (`{"error": "invalid_grant"}`). Motivo: é o formato que o web já trata em todas as rotas. `unsupported_grant_type` e pedido sem `grant_type` → `400`. As respostas levam `Cache-Control: no-store`. **Interessa ao Time B (67).**
2. **Usuários `demo` e `admin`** para o password grant (senhas `API_DEMO_PASSWORD`/`API_ADMIN_PASSWORD`). A spec não dava o nome.
3. **`client_id` do password grant:** clientes públicos `merchant-assistant-web` (padrão) e `merchant-assistant-cli`; outro valor → `401 invalid_client`. O claim `client_id` precisava de um valor.
4. **`client_credentials`** aceita o segredo no formulário e em HTTP Basic (RFC 6749 §2.3.1).
5. **Escopos do token limitados pela tabela de papéis:** escopo fora do papel é descartado na verificação. Protege contra um emissor externo mal configurado.
6. **Lojista de `demo` e `admin`** vem de `API_DEMO_CUSTOMER_ID` no servidor (o claim `customer_id` é só do lojista, conforme o contrato). `admin` continua com esse lojista nas rotas `/v1`, como na v0.6.0. `POST /messages` aceita só `merchant` e `demo`; `admin` recebe `403`.
7. **Limite de ações pagas da demo por token:** a linha contadora em `api_sessions` agora tem `session_id = jti`, criada na primeira ação. O limite por "sessão" virou limite por token.
8. **`api_principals` atualizado a cada token verificado** (as FKs de runs e comparações exigem a linha). `access_key_digest` ficou opcional na 0009.
9. **Uma linha de auditoria por tool call.** O registro escreve a linha e anota nela o recurso que o domínio tocou (`note_resource`, antes uma linha à parte em `domain.py`); assim, contagem de auditoria = contagem de tool calls. A recusa por limite de tool calls do pedido também é auditada. A gravação do caso pelo Escalation tem linha própria, `tool = handoff_case.create`, escopo `handoff:create`. Os testes de contagem a separam. Ferramenta desconhecida → linha com escopo nulo.
10. **As duas ferramentas de bootstrap** (`get_complaint_history`, `run_customer_healthcheck`) também declaram `support:read`.
11. **Códigos `401`:** `token_required` e `invalid_token` (RFC 6750), no lugar de `session_required`/`session_invalid`. **Interessa ao Time B (67).**
12. **Operador e serviço recebem `403`** também em `POST /v1/messages` e `POST /v1/router/compare`. Antes, um operador em `/v1/messages` cairia num `422 admin_scope_required` enganoso.
13. **`CustomerContext` sem principal não tem escopo:** toda chamada é recusada.
14. **Conta e sincronização:** uma tabela `auth_accounts` (`user`/`client`). As contas configuradas viram hash na primeira autenticação e só são refeitas quando a configuração muda (impressão digital em memória). Conta retirada da configuração fica `active=0`. Nome de usuário fora dos quatro da D1 impede a subida.
15. **Migração 0009 descendente** apaga principais `merchant`/`operator`/`service`, com suas linhas em `api_sessions`, `router_comparisons` e `run_snapshots`, além de `auth_accounts` e `revoked_tokens`, porque o esquema 0008 não os comporta. Demo e admin ficam.
16. **`API_DEMO_ACCESS_KEY`/`API_ADMIN_ACCESS_KEY` saíram** de `config.py` e do `.env.example`. Um `.env` antigo com elas é ignorado e demo e admin ficam desligados até `API_*_PASSWORD` ser definido. **Interessa ao QA.**

### Achados e limitações

- **Produto, para o Supervisor (não decidi):** um token `merchant` vê em `/v1/messages` os perfis que a demo não vê (`demo_allowed`), e o limite de ações pagas só vale para `demo`. O lojista fica limitado só pelo rate limit (30/min) e pelo orçamento. Se o lojista deve ter as mesmas restrições da demo, isso é decisão de produto.
- O rate limit não cobre `POST /v1/auth/token` (a D5 não lista a rota). A força bruta de senha fica contida só pelo custo do PBKDF2 (600 000 iterações por padrão).
- Um token continua válido até expirar mesmo que a conta saia da configuração. A revogação é por `jti`.
- Com `JWT_JWKS_URL` configurado, o emissor local continua emitindo, mas os tokens dele só passam se o JWKS externo tiver a chave dele.
- O MCP rodando fora do Docker valida o token com a chave do runtime local. Para token emitido pela API no Docker, defina `JWT_ISSUER` e `JWT_JWKS_URL` com os valores da API (está na docstring de `cmd_mcp`).
- No Windows, o modo `0600` do arquivo de chave não é aplicado pelo sistema. A proteção ali é o diretório `data/runtime/`, ignorado pelo Git e fora da imagem.
- README e CHANGELOG não foram tocados: a quebra de `POST /messages` e de `/v1/sessions`, com as duas chamadas do avaliador, fica para o fechamento (Supervisor). O projeto web ainda chama `/v1/sessions` até a 67.
- Durante a rodada, o pedido de adiar o formato da credencial chegou antes da decisão por JWT. O estado intermediário (chaves sintéticas) foi salvo como patch em `C:\Users\lauro\AppData\Local\Temp\claude\C--workspace-ai-getnet-case\5e8d3ad9-37a6-4202-a5b5-121938d615be\scratchpad\v070-t63-credencial-chaves-completo.patch`. Ficou superado pela spec v2, nada dele foi commitado e ele pode ser descartado.

### Ação externa, próxima ação e decisão pendente

- **Ação externa:** nenhuma (sem push, sem PR, sem Docker em execução). Os dois commits são locais, com a identidade conferida (`lauroPereira <lauro.s.pereira@gmail.com>`).
- **Próxima ação:** Reviewer revisa `59f0311` e o commit desta passagem. Em seguida vem a tarefa 64 (Time A), que acrescenta a fila à migração 0009. O Time B pode seguir com 66b e 67 contra o contrato; os pontos 1 e 11 acima mudam o que o web trata.
- **Decisão humana pendente:** só a limitação de produto do lojista em `/v1/messages`, se o Supervisor quiser fechá-la nesta versão.

## Tarefa 63, ajustes de contrato (spec `9c24800`)

- **Commit:** `dab83ab` ("task 63 contract"), sobre `3ccde8d`. Suíte estrita antes do commit: **código 0, 408 passed**, Ruff ok, skills ok.
- **Erros do `/v1/auth/token` no formato RFC 6749 §5.2** (`{"error", "error_description"}`). `invalid_grant`, `invalid_request` e `unsupported_grant_type` → `400`; `invalid_client` → `401` com `WWW-Authenticate: Basic`. Pedido sem `grant_type`, sem usuário ou sem segredo → `invalid_request`. Com isso, `client_credentials` com segredo vazio passou de `401 invalid_client` para `400 invalid_request`.
- **D19:** tentativas por conta e endereço (`auth:<user|client>:<id>@<ip>` em `rate_limit_hits`), contadas antes do PBKDF2, inclusive as bem-sucedidas. Padrão `AUTH_ATTEMPTS_PER_MINUTE=10` (decisão minha: a spec não fixa o número). Acima do limite → `429` com `Retry-After` e corpo `{"error": "rate_limited", "error_description"}`. `rate_limited` não é código da RFC; a spec não deu um nome.
- **`403 insufficient_scope`** com `WWW-Authenticate: Bearer error="insufficient_scope"` em toda recusa de rota: operador e serviço em `/messages`, `/v1/messages` e `/v1/router/compare`; rotas de admin; `/v1/conversations` sem lojista. Substitui o antigo `forbidden`.
- **D18:** `profile_role()` mapeia `merchant` → visibilidade de perfil da `demo`, e `LIMITED_ROLES = ("demo", "merchant")` aplica o limite de ações por token (`/v1/messages`, comparações, avaliações). Teste: `test_merchant_sees_the_demo_profiles_and_shares_the_action_limit`.
- **Contrato `3ccde8d`:** o `operator_id` sem prefixo (`op_ana`) já era o formato da fila; o principal `operator:op_ana` fica na auditoria. Os segredos de webhook ficam para a 66.

## Tarefa 64, rodada 1

- **Papel e responsável:** Developer (Time A), subagente.
- **Objetivo e critérios:** [tarefa 64](../tasks/64-fila-operador.md) (spec v0.7.0 versão 2: D6, D7, D9, D10, D14 e a tabela "Ticketing → assistente"; RF-80, RF-81, RF-83, RF-85).
- **Escopo:** `src/merchant_assistant/handoffs.py` (novo: serviço único da fila), `data/migrations.py` (parte da fila na 0009, sem 0010), `agents/escalation.py` (`HO-…`, `queue_state=open`, `channel`, `thread_id`, rascunho, sem `simulated`), `api/v1.py` (rotas `/v1/handoffs`), `api/schemas.py` (`Handoff` sem `simulated`), `api/app.py` e `orchestration/{graph,run}.py` (canal), `cli.py` (`operator list|show|act`), testes (`tests/integration/test_v070_handoffs.py` novo, `test_migrations.py`, `test_use_cases.py`). Nada em `merchant_assistant/ticketing/` nem no projeto web.
- **Estado:** pronta para revisão.
- **Branch e PR:** `codex/v0.7.0-identidade-hitl`; sem PR e sem push.
- **Base e versão final:** base `dab83ab`; o commit da tarefa vem depois desta passagem (o SHA vai no relatório ao Supervisor). Árvore limpa, exceto `Claude outputs/` e `_tmp/`.
- **Independência:** não se aplica.

### Evidência

- `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v070-a-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **código 0, 422 passed** (293 s), Ruff ok, skills ok.
- Duas falhas na rodada local, antes da suíte final. Uma estava no meu teste novo: esperava `claimed_by_other` ao reivindicar um caso fechado e nunca reivindicado; o serviço responde `case_closed`, que é o correto. A outra é a mudança esperada do protocolo `SIM-` → `HO-` (D7) em `test_use_cases.py`.
- O mapa critério → teste está na seção Validação da tarefa.
- Nenhuma chamada paga, sem Docker, sem `.env`.

### Decisões tomadas além do texto (todas reversíveis)

1. **Retomada fora da trava.** A ação grava o evento, o estado da fila e `resume_count = 1` na mesma transação `BEGIN IMMEDIATE`; é isso que impede a retomada dupla. O ponto único de retomada (`orchestrator.resume_handoff(case, record)`, ausente até a 65) só é chamado depois do commit. Rodar o grafo dentro da trava bloquearia o banco que o próprio grafo escreve. **Consequência para a 65:** se a retomada falhar, o caso já está `answered`/`rejected`; a 65 precisa registrar a falha e definir como tentar de novo.
2. **Ordem das verificações em `act`:** chave já usada → registro existente. Se essa chave foi usada para outro caso, ação ou operador → `409 idempotency_conflict`. Depois vêm `already_resumed`, `case_closed` e `claimed_by_other`. Assim, a mesma chave reenviada depois da retomada devolve o registro, como pede o D10.
3. **`text` obrigatório em `reply` e `reject`** (`422 text_required`). Em `approve`, o rascunho é a resposta e o texto, se vier, só é guardado.
4. **`200` para ação nova e para a repetida**, distinguidas por `replayed`. É o formato que a entrada do ticketing (66) devolve.
5. **`close` existe no serviço** (para o `ticket.solved` da 66) e não tem rota nesta tarefa. Caso fechado recusa reivindicação e ação com `409 case_closed`.
6. **Auditoria da fila:** cada `claim`, ação ou `close`, aceito, repetido ou recusado, grava `audit_events` com `tool = handoff.<ação>`, escopo `handoff:operate`, `principal_id` de quem age, `on_behalf_of` (para a 66) e o lojista do caso.
7. **Rotas da fila exigem papel `operator` e escopo `handoff:operate`.** Admin recebe `403`. O `operator_id` sai do `sub` do token (`operator:op_ana` → `op_ana`). Só os `POST` têm rate limit (D5); as leituras não.
8. **`channel`** = origem da conversa: `api` (`POST /messages`), `web` (`/v1/messages`), `in_process` (CLI e avaliação). O plano não definia o valor.
9. **Rascunho determinístico** a partir dos pontos de Support e Knowledge, no idioma da decisão do Router (fallback do D15), até o `escalation.v2` da 65.
10. **Casos anteriores à 0009 entram na fila como `open`**, sem `thread_id` (não há checkpoint). A 65 precisa tratá-los na retomada.
11. **`webhook_deliveries` com as colunas do plano.** A 66 pode acrescentar colunas à mesma 0009 (por exemplo, id do evento e sentido).
12. **CLI `operator act`** gera `cli-<uuid>` quando `--idempotency-key` falta e o devolve no registro, para repetir a ação com segurança. O token (`MERCHANT_ASSISTANT_TOKEN`, D12) precisa ser de operador.
13. **Conversa no detalhe:** os 10 últimos turnos mascarados pela guarda de entrada.

### Achados e limitações

- O texto ao lojista ainda diz "simulação" (`agents/personality.py`, arquivo da 65). Nesta tarefa saiu só o campo `simulated` do payload e do caso. A parte de texto do D7 fica para a 65.
- Ainda não há retomada do grafo, nem mudança do estado do caso na conversa (D14, lado do caso): a 65 implementa `resume_handoff`. A resposta da ação traz `case_state` como está na conversa.
- `422 unknown_operator`, para o `operator_id` vindo do ticketing, é da 66. Na API e na CLI o operador vem do token.
- README e CHANGELOG não foram tocados (fechamento).

### Ação externa, próxima ação e decisão pendente

- **Ação externa:** nenhuma; commits locais com a identidade conferida.
- **Próxima ação:** Reviewer revisa `dab83ab` e o commit da 64. A 65 implementa `resume_handoff` no orquestrador e trata a falha de retomada e os casos sem `thread_id`.
- **Decisão humana pendente:** nenhuma.

## Tarefa 65, rodada 1

- **Papel e responsável:** Developer (Time A), subagente.
- **Objetivo e critérios:** [tarefa 65](../tasks/65-interrupcao-retomada-grafo.md) (spec v0.7.0 versão 2: D4, D6, D8, D14, D15, a tabela "Ticketing → assistente" e o risco de serialização; ADR 0018; plano, decisões 4 a 6; contrato de `via` em `6f24cbb`), além dos três pontos do Supervisor: falha da retomada recuperável, casos pré-0009 e texto sem "simulação".
- **Escopo:** `pyproject.toml` (`langgraph-checkpoint-sqlite>=3.0`, instalado no `.venv`: 3.1.3), `orchestration/graph.py` (grafo de revisão, `human_review`, suspensão, `resume_handoff`, entrega D8, `/ready`), `orchestration/state.py`, `agents/escalation.py` (`escalation.v2`), `agents/personality.py` (`personality.v4`, contribuição do operador, texto sem simulação), `agents/support.py` (instrução do operador), `cases.py` (saída de `handoff` só por operador), `conversations.py` (`via`, `meta`, entrega), `handoffs.py` (`not_resumable`, estado da retomada, nova tentativa), `api/schemas.py` (`via`, `human_reply`), `cli.py` (`operator act` com o ponto de retomada), `config.py` (`CHECKPOINTS_PATH`), `data/migrations.py` (0009: `messages.meta`, `delivered_at`, `handoff_cases.resume_*`), `evaluation/scripted_policy.py` (o modelo programado devolve o rascunho e entrega o texto do operador), `prompts/escalation.v2.md` e `prompts/personality.v4.md` (novos; v1 e v3 intactos), testes (`tests/integration/test_v070_resume.py` novo; ajustes em `test_v070_handoffs.py` e `test_v070_identity.py`).
- **Estado:** pronta para revisão.
- **Branch e PR:** `codex/v0.7.0-identidade-hitl`; sem PR e sem push.
- **Base e versão final:** base `0dc1ea5` (com `f6da518`, `6f24cbb` e `f2a6b60`, só docs, do Supervisor). O commit da tarefa vem depois desta passagem.
- **Independência:** não se aplica.

### Evidência

- **Serialização, primeiro passo:** uma sonda com o `GraphState` completo (decisão, Knowledge com citações, Support, Escalation, histórico, caso), interrompida num processo e retomada noutro, preserva os tipos. Em `LANGGRAPH_STRICT_MSGPACK=true` funciona desde que os tipos estejam registrados no serializador; eles estão (`CHECKPOINT_TYPES`). Sem o registro, o langgraph avisa que vai bloqueá-los numa versão futura. O plano B da ADR 0018 não foi necessário.
- `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v070-a-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **código 0, 437 passed** (343 s), Ruff ok, skills ok.
- **Instabilidade encontrada e corrigida:** a primeira execução estrita teve 1 falha, em `test_queue_routes_are_rate_limited` (tarefa 64). A janela de 60 s era real, e as duas requisições caíram em janelas diferentes. O teste de D19 (`test_token_attempts_are_limited_per_account_and_address`) tinha o mesmo risco. Os dois usam agora relógio fixo (`identity.utc_seconds`). Os arquivos são da 64 e dos ajustes da 63; a correção entrou neste commit porque apareceu agora.
- Nenhuma chamada paga, sem Docker, sem `.env`.

### Decisões tomadas além do texto (todas reversíveis)

1. **Dois grafos com as mesmas funções de nó.** O grafo de atendimento continua sem checkpointer. Quando o Escalation abre um caso, o estado do fim do turno encaminhado entra no grafo de revisão, compilado com `SqliteSaver` em `CHECKPOINTS_PATH` (padrão `<runtime>/checkpoints.sqlite3`). Esse grafo começa em `human_review` e para lá num `interrupt()` real, com `thread_id` = `request_id` do encaminhamento (D6). A retomada continua esse grafo: `approve`/`reply` → Personality → guarda; `reject` → Support → Personality → guarda. **Motivo:** com um grafo só, todo turno leria o checkpoint na entrada e gravaria um na saída, o que fere "o caminho sem encaminhamento não lê checkpoint". A ADR fala em `human_review` "depois de `escalation`"; aqui ele vem depois da resposta do encaminhamento, porque a requisição do lojista precisa terminar com essa resposta.
2. **`human_review` fica fora do `_traced`.** O `interrupt()` funciona levantando exceção, e o `_traced` engole toda `Exception`. O nó grava o próprio passo de trace na retomada; a suspensão grava `human_review` com estado `interrupted`.
3. **Falha da retomada (pedido a):**
   - A ação grava `resume_status = pending` na mesma transação do evento.
   - Retomada concluída → `done`, com `resume_request_id` apontando para o trace da retomada.
   - Exceção → `failed`, `resume_error`, linha `handoff.resume` na auditoria e `503 resume_failed`. O estado da retomada aparece na lista e no detalhe da fila.
   - Repetir com a **mesma chave** reivindica nova tentativa: atualização atômica de `failed`, ou de `pending` parado há mais de 5 min (processo morto).
   - Outra chave continua `409 already_resumed`.
   - A retomada repetida é segura: com a interrupção pendente usa `Command(resume)`; com o grafo parado no meio, continua do último checkpoint; com o grafo terminado, usa os valores finais. O turno do operador é gravado uma vez só (verificação pelo `event_id` em `messages.meta`).
   - **Por que `503` e não `200`:** a resposta deixa claro ao cliente, e à caixa de saída do ticketing na 66, que é preciso repetir com a mesma chave.
4. **Casos pré-0009 (pedido b):** `act` recusa com `409 not_resumable` antes de qualquer mudança (fila, eventos e `resume_count` ficam como estavam) e grava a recusa na auditoria. O mesmo vale para um caso cujo `thread_id` foi apagado.
5. **Retomada só no processo da API ou da CLI.** `resume_handoff` roda na requisição da ação, depois do commit, fora da trava. A CLI `operator act` monta o orquestrador real (`operator_orchestrator`, que os testes substituem) e passa o mesmo ponto de retomada. Isso também fecha o P2-2 da revisão da 64.
6. **D8:** a próxima `POST /messages` (e `/v1/messages`, que usa o mesmo `handle`) devolve o turno pendente com `route = human_reply`, `via = operator` e `status = answered`, sem modelo. A mensagem do lojista fica registrada, mascarada pela guarda, e o turno é marcado `delivered_at`. A mensagem seguinte volta ao fluxo normal. O webhook da 66 não marca o turno como entregue; isso fica para a 66 decidir.
7. **`via` conforme `6f24cbb`:** a resposta tem `via` = `agent` ou `operator`. Nas conversas, cada turno do assistente traz `via` e, quando é do operador, `operator_action` e `protocol`, guardados em `messages.meta` (que também tem `case_id`, `event_id` e idioma). O `operator_id` não aparece para o lojista.
8. **D14:** `Turn(via_operator=True)` tira o caso de `handoff` para `awaiting_customer`, ou para `resolved` se a ferramenta verificar a solução. Nunca volta para `handoff`. No `reject`, o Support roda com `escalate` forçado para falso, inclusive se falhar, e não há aresta para `escalation`.
9. **Rascunho do `escalation.v2`:** resumo e pergunta pendente em português, para o operador; rascunho no idioma do lojista. Se o modelo falhar, o rascunho determinístico da 64 é usado. `EscalationDraft.draft_reply` passou a ser obrigatório; o modelo programado foi atualizado para devolvê-lo.
10. **`personality.v4`:** confirma o encaminhamento sem "simulação" e entrega fielmente o texto do operador. No `reject`, escreve a partir do Support. O texto do operador é evidência válida para a guarda de saída. O `HANDOFF_LINE` agora diz "atendente da nossa equipe, que vai responder por aqui"; `"simulated": True` saiu das contribuições.
11. **Comparações isoladas não suspendem:** uma execução com `db_path` temporário (comparação) não deixa caso para retomar.
12. **`/ready`** ganhou `pending_handoffs` (`open` + `claimed`) e `checkpoints` (`threads` distintos, leitura somente nessa rota).

### Achados e limitações

- A retomada corre no processo e no tempo da requisição da ação, com chamada a modelo (Personality, e Support no `reject`). Uma ação demorada segura o cliente até a resposta. Uma fila de trabalho seria o passo seguinte, fora do escopo.
- O limite de 5 min para considerar parada uma retomada `pending` é fixo no código.
- Retomada pela CLI em processo exige `OPENAI_API_KEY` (chamada paga), como o `ask`.
- O webhook `conversation.replied` e a marca de entrega por webhook são da 66.
- README e CHANGELOG não foram tocados (fechamento).

### Ação externa, próxima ação e decisão pendente

- **Ação externa:** nenhuma; commit local com a identidade conferida.
- **Próxima ação:** Reviewer revisa o commit da 65. Eu sigo com "task 63 round 2" e "task 64 round 2" (em commits separados) e depois com a 66.
- **Decisão humana pendente:** nenhuma.

## Tarefa 63, rodada 2

- **Papel e responsável:** Developer (Time A), subagente; correções da revisão (rodada 1, [parecer](v070-reviewer.md), `f6da518`) e das decisões D18 ampliada, D20 e D21.
- **Base:** `868a07f` (tarefa 65). Commit próprio, "task 63 round 2". Suíte estrita antes do commit: **código 0, 448 passed** (325 s), Ruff ok, skills ok.
- **P1-1:** `KEY=` vazio no `.env` (como no `.env.example`) vale "não definido". Um validador em `Settings` converte o vazio em `None` em `runtime_dir`, `checkpoints_path`, `jwt_private_key_path` e `jwt_jwks_url`; antes virava `Path(".")` ou uma URL vazia. Teste novo monta `Settings` a partir do próprio `.env.example` (só o custo do hash é sobrescrito), publica o JWKS, emite o token de `cliente1988` com a senha fictícia e o usa numa rota (`test_env_example_as_copied_issues_and_verifies_tokens`).
- **P2-1:** `JWT_ISSUER` saiu do `.env.example` como linha ativa; ficou um comentário explicando que o compose define `http://api:8000`. Teste de coerência: sem `JWT_ISSUER` ativo no exemplo, compose com `${JWT_ISSUER:-http://api:8000}`, padrão local `http://127.0.0.1:8000`.
- **P2-2:** `build_server(..., authorize=...)` verifica o token de novo a cada tool call (assinatura, validade, revogação), com o mesmo verificador. Se a verificação falha, a ferramenta não roda; a recusa vai para a auditoria (`invalid_token`) e volta como erro `INVALID_TOKEN`. Teste: token revogado depois da subida → a chamada seguinte é recusada.
- **P2-3 e D18 ampliada:** `/v1/router/compare`, `/v1/comparisons` e `/v1/runs/{id}/evaluations` agora passam pelo rate limit do D5. O limite de ações por token já valia para `merchant` (`LIMITED_ROLES` em `dab83ab`). Testes: `router/compare` do lojista com limite 1 → `429 demo_message_limit_reached`; as três rotas → `429 rate_limited` com relógio fixo.
- **D20:**
  - O admin não tem lojista no token nem no principal.
  - `/v1/messages` atribui ao admin o lojista da demo, só nessa rota; as ferramentas são autorizadas para esse lojista.
  - `POST /messages` responde "accepts only merchant and demo tokens", sem citar outros papéis.
  - Consequência: `/v1/conversations` e a criação de comparações para o admin passam a recusar (`403` e `422 admin_scope_required`, como já estava no código para principal sem lojista). As rotas de demo continuam abertas ao admin.
- **D21:** dependência `READER`. Perfis, KB, catálogo, cenários, runs, comparações, `/v1/messages` e `router/compare` só para `merchant`, `demo` e `admin`; `operator` e `service` recebem `403 insufficient_scope`. Teste parametrizado com 9 rotas.
- **P3:**
  - Exceção inesperada dentro de uma ferramenta grava a linha de auditoria com resultado `error` e continua sendo levantada, como antes.
  - `tools/scripts/run_synthetic_v040_api.py` usa `api_demo_password`/`api_admin_password`, com teste de login. O teste é pulado se o `basetemp` não estiver em `.pytest_cache`.
  - Docstring de `can_read` corrigida de D14 para D13.
  - README e CHANGELOG ficam com o Supervisor.
- **Limitação:** a criação de comparações pelo admin deixou de funcionar por causa da D20. Se a demonstração precisar disso, é decisão de produto.

## Tarefa 64, rodada 2

- **Papel e responsável:** Developer (Time A), subagente; correções da revisão da 64 e de `dab83ab` (rodada 1, [parecer](v070-reviewer.md), `f2a6b60`) e decisões D19 ampliada, D22 e D23.
- **Base:** `d612d30` (63, rodada 2). Commit próprio, "task 64 round 2". Suíte estrita antes do commit: **código 0, 462 passed** (361 s), Ruff ok, skills ok.
- **P2-1 (simulação):** corrigido na 65 (`868a07f`: `personality.v4`, `HANDOFF_LINE` novo, sem `"simulated"`). Teste novo confere que nem a resposta ao lojista, nem o `transcript` do operador, nem o detalhe do caso contêm "simula"/`"simulated"`.
- **P2-2 (CLI sem retomada):** corrigido na 65 (`operator act` passa `orchestrator.resume_handoff`). Teste novo conta a chamada: um `act` pela CLI → uma retomada, `resume_status = done` e turno do operador na conversa.
- **D23:**
  - `GET /v1/handoffs` → `handoff.list`.
  - `GET /v1/handoffs/{id}` → `handoff.read`, com o caso como recurso e `case_not_found` quando não existe.
  - Recusas no portão das quatro rotas (`insufficient_scope`) também geram linha com o principal e o escopo `handoff:operate`.
  - A CLI (`list`, `show`) também audita.
  - O 401 sem token não gera linha (não há principal).
- **D22:** a mesma chave com outro caso, ação, operador **ou texto** → `409 idempotency_conflict`, sem efeito. Só a repetição idêntica devolve o registro.
- **D19 ampliada:** além do par conta@endereço, conta-se o endereço somado entre contas (`AUTH_ATTEMPTS_PER_IP_PER_MINUTE`, padrão 30). As duas contagens acontecem a cada tentativa; vale a espera maior. Teste: quatro contas diferentes do mesmo endereço com limite 3 → a quarta recebe `429`.
- **P3-4:** testes do regex da `idempotency_key` direto no serviço: vazia, 7 e 81 caracteres, espaço, acento e `;` recusados sem evento; 8 e 80 caracteres e `[A-Za-z0-9_-]` aceitos.
- **P3-5:** casos pré-0009 recusados com `409 not_resumable` (65). A fila sem paginação (`LIMIT 100`) fica como limitação.
- **Ajuste de teste:** `test_queue_calls_are_audited_with_the_operator` (rodada 1) passou a filtrar as ações, porque a lista também é auditada agora.

## Tarefa 63, ajuste D20

- **Papel e responsável:** Developer (Time A), subagente novo (o anterior encerrou por contexto longo); pedido do Supervisor depois da D20 revista (`bb1659c`).
- **Base:** `bb1659c`. Commit próprio, "task 63 D20".
- **Mudança:** `acting_merchant()` em `api/v1.py`. No admin, o dicionário do principal da rota recebe `customer_id = API_DEMO_CUSTOMER_ID`; o token e a linha de `api_principals` continuam sem lojista. É aplicada na dependência `READER` (mensagens, comparação de Routers, comparações, avaliações, runs) e em `GET /v1/conversations/{id}`. Saiu o caso especial que existia só em `/v1/messages`. `POST /messages` não mudou: aceita só `merchant` e `demo`.
- **Teste:** `test_admin_acts_on_the_demo_merchant_in_v1_but_not_in_post_messages` substitui `test_admin_uses_the_demo_merchant_only_in_v1_messages`. O teste antigo esperava `403` na conversa do admin, comportamento que a D20 revista retirou. O novo cobre: claim sem `customer_id`; `POST /messages` → `403` sem citar papéis; `/v1/messages` grava a conversa no lojista da demo; `GET /v1/conversations/{id}` → `200`; `POST /v1/router/compare` → `201`, com o lojista da demo em `router_comparisons`; estimativa de avaliação → `200`; comparação de perfis → `202` e leitura `200`; `admin:default` sem lojista em `api_principals`.
- **Validação:** `pytest` em `test_v070_identity_r2.py`, `test_v070_identity.py`, `test_v1_api.py`, `test_v060_api.py`, `test_v060_r2.py` e `test_v060_r4.py` → todos passam. Ruff ok. A suíte estrita roda no fim da tarefa 66 (números lá).
- **Limitação:** com `API_DEMO_CUSTOMER_ID` vazio, o admin volta a `422 admin_scope_required` nessas rotas, como na v0.6.0.

## Tarefa 66, rodada 1

- **Papel e responsável:** Developer (Time A), subagente novo.
- **Objetivo e critérios:** [tarefa 66](../tasks/66-webhooks-assinados-ticketing.md). Spec v0.7.0: "Contrato entre os times / Webhooks", D9, D10, D11, D14, D22, D24, D25, D26; ADR 0018; CA-47 e CA-48.
- **Escopo:**
  - `src/merchant_assistant/api/webhooks.py` (novo): assinatura, envelope, eventos de saída, entrega em thread com tentativas, uma linha por tentativa.
  - `src/merchant_assistant/api/integrations.py` (novo): `POST /v1/integrations/ticketing/events`.
  - `api/app.py`: `app.state.webhooks`, rota nova e `handoff.created` depois de `POST /messages`.
  - `api/v1.py`: `handoff.created` em `execute_run`; `conversation.replied` em `POST /v1/handoffs/{id}/actions`.
  - `api/identity.py`: `active_operator`.
  - `cli.py`: `operator act` emite `conversation.replied`.
  - `config.py`: URLs, segredos, tentativas, esperas e timeout.
  - `conversations.py`: `webhook_deliveries` na conversa.
  - `handoffs.py`: entregas com `event_id` e `error` no detalhe.
  - `data/migrations.py`: 0009 com `webhook_deliveries.event_id`/`error`, índice por conversa e `webhook_inbox`.
  - `mocks/service.py`: `POST/GET /merchant/events`.
  - `testing.py`: `AppTransport`.
  - `docker-compose.yml`: acréscimos só nos blocos `api` e `mocks`.
  - `.env.example`: acréscimo no bloco da API.
  - Testes: `tests/integration/test_v070_webhooks.py` e `tests/integration/test_v070_ticketing_integration.py`, ambos novos, e `tests/unit/data/test_migrations.py`.
  - **Nada** em `merchant_assistant/ticketing/`, no bloco `ticketing` do compose nem no bloco do ticketing do `.env.example`.
- **Estado:** pronta para revisão.
- **Branch e PR:** `codex/v0.7.0-identidade-hitl`; sem PR e sem push.
- **Base e versão final:** base `c7affe5` (ajuste D20), com `d55ce35` (parecer da 65, do Supervisor) por cima. O commit da tarefa vem logo depois desta passagem.
- **Independência:** não se aplica.

### Evidência

- `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v070-a-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **1 failed, 523 passed** (363 s), Ruff ok, skills ok, código 1. A falha (`test_ticketing_events_resume_reply_and_close[reply]`) era do meu teste: a variável do laço que confere o corpo sombreava o texto da resposta. Corrigido; `test_v070_webhooks.py` de novo → 14 passed. A suíte estrita completa com código 0 está registrada na rodada 2 da 65, sobre esta mesma base mais a 65 r2.
- Integração com o serviço de ticketing real da 66b, em processo e sem alterá-lo: as três ações passam de ponta a ponta (`test_v070_ticketing_integration.py`, 3 casos). **Não encontrei divergência** entre o contrato e o serviço do Time B.
- `docker compose -f <cópia>/docker-compose.yml config --quiet` → 0, numa cópia sem `.env`. Valores resolvidos: `TICKETING_WEBHOOK_URL=http://ticketing:8002/webhooks/assistant`, `CONVERSATION_WEBHOOK_URL=http://mocks:8001/merchant/events` e os três segredos fictícios, iguais nos blocos `api`, `mocks` e `ticketing`.
- Achados durante a rodada, corrigidos antes do commit:
  - Uma recusa de validação (`422`) gravava o `ticket_id` no caso. Agora ele só é gravado no evento aceito.
  - O transporte do `TestClient` não serve a um `httpx.Client` comum. A falha ficava escondida porque a thread de entrega engole exceções. Daí veio o `AppTransport`, e o teste do `mocks` passou a conferir a linha `delivered`.
  - O teste de janela calculava o `t` futuro cedo demais. Agora o deslocamento é aplicado na hora da assinatura, e o limite exato de 300 s tem teste próprio com relógio fixo.
- Nenhuma chamada paga, sem Docker em execução, sem `.env`.

### Decisões tomadas além do texto (todas reversíveis)

1. **Ordem das verificações na entrada:** token (`401`), papel `service` com `handoff:integrate` (`403`, auditado), rate limit (D5), segredo configurado (`503 webhook_not_configured` se `ASSISTANT_WEBHOOK_SECRET` estiver vazio), assinatura (`401 invalid_signature`), envelope (`400 invalid_payload`), `id` já respondido, tipo (`422 unknown_event`), campos (`400 invalid_payload`), operador ativo (`422 unknown_operator`, auditado) e, por fim, o serviço da fila.
2. **`id` repetido:** a resposta de cada evento abaixo de `500` fica em `webhook_inbox`. O mesmo `id` recebe `200 {"status": "replayed", ...}` com os estados atuais, ou o mesmo erro `4xx`. Um `5xx` (por exemplo `503 resume_failed`) **não** fica guardado: a nova tentativa da caixa de saída do ticketing, com o mesmo `id`, processa de novo e retoma pela mesma chave (D26).
3. **"Operador ativo"** = conta `operator:<id>` configurada em `DEMO_USER_PASSWORDS` (D1).
4. **`ticket_id`** gravado no caso no primeiro evento aceito; recusa não grava.
5. **Auditoria da entrada:** as linhas de `claim`/ação/`close` usam as do serviço da fila (`principal_id = service:ticketing`, `on_behalf_of = operator:<id>`, escopo `handoff:operate`, que é o escopo da ação do operador). A recusa no portão vai como `tool = handoff.integrate`.
6. **Tentativas:** erro de rede, timeout, `5xx`, `408` e `429` levam a nova tentativa. Outro `4xx` é final (`rejected`), porque repetir não muda nada. Estados por tentativa: `delivered`, `rejected` e `error`. `target` grava o nome do receptor (`ticketing`, `merchant`), não a URL. A assinatura é refeita a cada tentativa (`t` novo).
7. **`conversation.replied`:** um envelope só (mesmo `id`) para os dois receptores, cada um assinado com o seu segredo. `reply_text` = resposta produzida pela retomada, mascarada pela guarda de entrada; `request_id` = trace da retomada; `delivered_at` = hora da emissão. Sai só de uma retomada bem-sucedida: replay não emite de novo, e retomada que falha não emite. **Para o Supervisor:** pelo contrato, o evento ao lojista leva `operator_id`. A 65 tinha decidido não mostrar o `operator_id` ao lojista na conversa. Segui o contrato; se o lojista não deve receber o identificador, a mudança é no contrato.
8. **`handoff.created`** sai depois de uma resposta `status = handoff` em `POST /messages` e `POST /v1/messages`, para o caso com `thread_id` = `request_id` (D6). Execuções isoladas (comparações) não emitem. Avaliação em processo e CLI `ask` também não, porque o disparo está na camada HTTP.
9. **CLI `operator act`** também emite `conversation.replied` e espera as entregas antes de sair, até o tempo máximo das tentativas.
10. **`.env.example`:** URLs de execução no host (`http://127.0.0.1:8002/webhooks/assistant`, `http://127.0.0.1:8001/merchant/events`), como faz o bloco do ticketing. O compose fixa as URLs de container sem interpolação, como `MOCKS_URL`, para que o `.env` copiado não as troque dentro do container. `TICKETING_WEBHOOK_SECRET` e `ASSISTANT_WEBHOOK_SECRET` não foram repetidos: estão no bloco do ticketing do `.env.example` e valem para os dois serviços.
11. **Receptor do lojista no `mocks`:** em memória (some quando o container reinicia), `id` repetido → `{"status": "duplicate"}`, sem `CONVERSATION_WEBHOOK_SECRET` → `503`. O `GET` não exige autenticação: o `mocks` não é publicado fora da rede do compose (`expose`).
12. **Entregas visíveis:** `deliveries` no detalhe do caso (todos os receptores) e `webhook_deliveries` na conversa (só as do lojista).

### Achados e limitações

- As entregas correm em threads do processo da API, sem fila persistente: se a API cair no meio das tentativas, o evento se perde, mas as tentativas feitas ficam registradas. O ticketing tem caixa de saída; o assistente, não.
- `handoff.closed` sai só pelo `ticket.solved`. Não há rota de fechamento na API do assistente.
- Banco local já na versão 9 (criado antes desta rodada) não ganha `webhook_inbox` nem as colunas novas, porque a 0009 foi ampliada no lugar. É preciso recriar o runtime (`data/runtime/`) ou descer e subir a 0009. Interessa ao QA.
- README e CHANGELOG não foram tocados (fechamento).

### Ação externa, próxima ação e decisão pendente

- **Ação externa:** nenhuma; commits locais com a identidade conferida.
- **Próxima ação:** Reviewer revisa a 66 (e o ajuste D20). Sigo com a rodada 2 da 65 (pedido do Supervisor).
- **Decisão humana pendente:** `operator_id` no evento ao lojista (decisão 7).

## Tarefa 65, rodada 2

- **Papel e responsável:** Developer (Time A), subagente novo, no lugar do Developer original da 65 (encerrou por contexto longo). Corrige o [parecer da 65, rodada 1](v070-reviewer.md) (`d55ce35`) e implementa as decisões D27 e D28.
- **Base:** `7e4416c` (tarefa 66). Commit próprio, "task 65 round 2".
- **P2-1 / D27:** `audit_events` saiu de `SYNTHETIC_TABLES` (`data/db.py`). O `seed`, que o `bootstrap` roda a cada subida do container, recria os dados sintéticos de domínio e preserva a auditoria. Teste: `tests/unit/data/test_seed.py::test_second_seed_keeps_the_audit` (segundo `seed` mantém a linha de auditoria e recria `devices`).
- **P2-2:** `test_operator_turn_is_not_delivered_in_another_merchants_open_conversation`. B abre a conversa primeiro; A encaminha e recebe `reply`; B escreve na própria conversa já aberta e não recebe `human_reply` nem o texto de A; A recebe o turno. Exercita o filtro de `pending_operator_turn` (mutante R20).
- **P2-3:** `test_reply_with_an_amount_and_a_date_passes_the_guard_intact`. "Seu repasse de R$ 1.234,56 cai em 28/10/2026." fica intacto no turno do operador e na entrega da próxima mensagem (mutante R16).
- **P3-1:**
  - `test_thread_stopped_half_way_continues_without_repeating_support`: o processo "morre" na Personality depois do Support. Simulei com uma `BaseException`, que nada no caminho captura, no lugar de `os._exit`. A thread fica parada no meio (`next` sem interrupção), a retomada vencida com a mesma chave continua do checkpoint, `get_device_status` roda uma vez só e sai um turno (mutante R19).
  - `test_turn_written_before_a_failure_is_not_written_again_on_retry`: a falha vem depois de gravar o turno (no registro do trace). A resposta é `503`, a nova tentativa termina `done` e o turno continua único (mutante R07). O teste existente falhava antes de gravar, por isso não pegava o R07.
- **D28:** se `_suspend` não consegue gravar o checkpoint, o caso fica `resume_status = checkpoint_failed`, com `resume_error`, e aparece na fila desde a abertura. Ação nele → `503 checkpoint_missing` antes de qualquer mudança (fila, eventos e `resume_count` intactos), com a recusa auditada. A 0009 aceita o valor novo no `CHECK` de `resume_status`. Teste: `test_checkpoint_failure_marks_the_case_and_refuses_actions`.
- **Limitações (P3-2 a P3-4, conforme a decisão do Supervisor):**
  - O caso com `checkpoint_failed` não tem caminho de resolução sem grafo: o operador só pode fechá-lo (`ticket.solved`).
  - A retomada `pending` espera 5 min antes de nova tentativa.
  - `pending_handoffs` não conta caso `answered` com retomada falha.
  - Checkpoints nunca são podados.
  - A ADR 0018 é alinhada no fechamento (D25).
- **Mutação manual dos dois sobreviventes que a revisão apontou como só de teste:** R07 (gravar o turno a cada tentativa) e R20 (turno pendente de qualquer conversa) agora morrem com os testes novos. Arquivos restaurados depois.
- **Validação:** `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v070-a-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **código 0, 530 passed** (356 s), Ruff ok, skills ok. Cobre a árvore da 66 (`7e4416c`) mais esta rodada: 524 da rodada da 66, mais os 5 novos de `test_v070_resume_r2.py` e o de `test_seed.py`.

## Tarefa 66, D29

- **Pedido:** decisão D29 do Supervisor (`0e73335`). A cópia de `conversation.replied` ao lojista (`CONVERSATION_WEBHOOK_URL`) omite `operator_id`; a do ticketing o mantém.
- **Base:** `0e73335`. Commit próprio, "task 66 D29".
- **Mudança:** em `api/webhooks.py`, `emit` monta um corpo por receptor (`HIDDEN_FROM = {"merchant": ("operator_id",)}`), e cada corpo é assinado com o segredo do seu sentido. Os dois corpos mantêm o mesmo `id` de evento, porque é o mesmo evento, e diferem só pelo campo omitido. O registro em `webhook_deliveries` não muda. Isto substitui a decisão 7 da rodada 1 e fecha a decisão pendente que levei ao Supervisor.
- **Testes:**
  - `test_ticketing_events_resume_reply_and_close[*]`: mesmo `id` e tipo; `operator_id = op_ana` só no corpo do ticketing; nenhum `op_ana` no corpo do lojista; o resto do `data` igual; as duas assinaturas conferem, cada uma com o seu segredo.
  - `test_case_becomes_a_ticket_worked_on_the_ticketing_and_closed[*]` (ticketing real): o evento recebido pelo `mocks` não tem `operator_id`.
- **Validação:** `test_v070_webhooks.py` e `test_v070_ticketing_integration.py` → 17 passed; Ruff ok. A suíte estrita roda com o commit (número registrado na passagem da 68).

## Tarefa 66, correção dos P2 e avaliação dos P3

- **Papel:** Developer; a revisão independente e o QA continuam pendentes.
- **Candidato:** branch `codex/v0.7.0-identidade-hitl`, base `70f8f14`; alterações locais em `api/integrations.py`, `api/webhooks.py`, `tests/integration/test_v070_webhooks.py` e esta passagem. Sem commit: `.git` está somente para leitura neste ambiente.
- **Assinatura:** timestamp aceita somente dígitos decimais ASCII limitados em tamanho e o digest deve ter 64 caracteres hexadecimais minúsculos, preservando `compare_digest` e a janela. Os testes HTTP incluem `t=²`, timestamp excessivo e `v1=é`, com bytes Latin-1, e conferem `401 invalid_signature` sem efeito.
- **Concorrência e recuperação:** cada evento autenticado e assinado reserva seu ID na inbox antes do efeito, junto ao SHA-256 do envelope canônico, sem persistir o texto do envelope na reserva. Um banco SQLite de coordenação por hash do ID, separado do banco principal, mantém a exclusão entre processos enquanto a fila faz seus próprios commits e a retomada ocorre. IDs diferentes não aguardam um ao outro; um ID arbitrário não compõe caminho de arquivo. O SQLite libera a exclusão após queda. Uma reserva pendente só pode aplicar o envelope original; uma resposta final transforma toda repetição do ID em `200 replayed`, inclusive após recusa `4xx`, conforme o contrato. Até que o resultado seja conhecido, contenção por mais de cinco segundos ou conteúdo divergente de uma reserva pendente responde `503 resume_failed`. Um `503` não é resposta final: a mesma entrega pode tentar de novo, inclusive após `resume_failed` (D26). Se uma ação foi registrada mas a retomada segue `pending`, não se confirma sucesso antecipadamente.
- **Testes:** corrida do mesmo ID com casos distintos verifica uma só aplicação, um só efeito, uma linha de inbox e uma auditoria; há teste de IDs distintos em paralelo, recusa final repetida, espera vencida, ID contendo `../`, falha depois da ação, falha depois da reivindicação e encerramento de processo com bloqueio adquirido. A sonda de mutação que elimina a leitura da inbox ainda precisa ser executada independentemente; a contagem de aplicações e auditorias foi incluída para detectá-la.
- **P3-1:** coberto pelos testes de repetição e concorrência; mutação ainda não executada. **P3-2:** uma ação já registrada retorna `replayed` ao finalmente retomar, preservando o significado da chave da ação e evitando alterar a resposta contratual. **P3-3:** alinhado ao `200` do contrato após uma recusa final; o teste garante ausência de novo efeito e auditoria.
- **P3-4:** `claimed_by_other` ao fechar caso de outro operador permanece; mudar essa regra da fila exige decisão de contrato. **P3-5:** saídas do assistente continuam sem caixa persistente; esgotamento das tentativas ou queda no envio pode deixar o caso sem ticket. Correção durável exige desenho próprio. **P3-6:** continua obrigatório runtime novo para a 0009; nenhum volume foi apagado ou recriado. **P3-7:** assinatura inválida continua sem auditoria; não foi alterada a política de segurança. **P3-8:** o `GET` do receptor do lojista permanece sem autenticação no `mocks`; alterar acesso ou limites exige decisão de segurança/contrato.
- **Limitações operacionais:** a coordenação pressupõe que processos compartilhem o mesmo runtime e que o sistema de arquivos respeite os bloqueios SQLite. Cada ID autenticado e assinado cria um arquivo de coordenação cujo nome é hash, sujeito ao limite de requisições já existente; os arquivos acumulam e não há poda segura automática. Em uma queda entre o commit da ação e a retomada, a política existente aguarda até cinco minutos para retomada `pending` envelhecida; as três tentativas automáticas do ticketing podem terminar antes e exigir reenvio posterior. A espera do bloqueio termina em cinco segundos, enquanto clientes podem desistir antes. Uma resposta `200 replayed` após `4xx` confirma apenas que o ID foi tratado, não que o efeito foi aplicado.
- **Validação observada:** Supervisor executou a suíte focada `tests/integration/test_v070_webhooks.py` com acesso apropriado: **24 testes passaram, código 0**. `ruff check` nos três arquivos Python alterados: **código 0**. O teste isolado de janela da assinatura passou localmente. A tentativa local da suíte focada parou no primeiro teste por `PermissionError: [WinError 5]` no hard link da guarda de orçamento; nenhuma guarda foi contornada. A suíte estrita completa permanece para o Supervisor em cópia fiel isolada, pois a raiz contém cópias de revisão deliberadamente mutadas que o script varreria. Nenhuma chamada paga ou de rede foi feita nesta passagem.
- **Próximo responsável:** Supervisor fixa o candidato e executa suíte estrita e mutação em ambiente adequado; depois, Reviewer independente. Não há aprovação própria nem ação externa.

## Tarefa 66, correção da revisão do candidato `b252523`

- **Papel e base:** Developer, branch `codex/v0.7.0-identidade-hitl`, base `b25252333f12d1e4678c9add77254e1458643cf6`; alterações locais sem commit. Esta rodada substitui as limitações e a decisão de repetição de `4xx` descritas na passagem anterior.
- **Recusa repetida:** por decisão expressa do responsável, `409`/`422` final é repetido com o corpo original, inclusive `request_id`, sem novo efeito ou auditoria. A alteração correspondente da spec foi limitada a esse ponto. Teste integrado: a primeira resposta `409` é perdida no transporte; o ticketing repete o mesmo evento e registra a recusa, mantendo o operador e o estado anteriores. Há regressões diretas para `409` e `422`.
- **Exclusão e retomada:** 64 arquivos de bloqueio por faixas substituem um arquivo por `event_id`; outras 64 faixas coordenam a ação por caso entre API, CLI e integração. O detentor exclusivo pode retomar imediatamente uma ação `pending` cujo processo terminou, sem esperar cinco minutos; outra chamada viva do mesmo caso não executa a retomada em paralelo. Testes cobrem processo terminado de fato, ticketing real com configuração padrão, uma única ação e turno, e chamadas simultâneas com IDs de evento distintos.
- **Outbox durável:** autorizada expressamente pelo responsável. A migração nova `0010_webhook_outbox` preserva a 0009 e os dados existentes. Cada evento e destinatário tem corpo mascarado e ID estável, com omissão do operador ao lojista. `handoff.created` é gravado na mesma transação das mensagens do turno, após concluir ou registrar a falha do checkpoint; `conversation.replied`, na mesma transação do turno do operador; `handoff.closed`, na mesma transação do fechamento. No início da API, o despachante recupera intenções pendentes e casos de fechamento pendentes anteriores à 0010. A entrega é assinada e o receptor deduplica pelo ID estável; a contagem e o registro da tentativa são persistidos antes do envio. Cada destinatário tem no máximo três tentativas totais, inclusive após reinícios. A ordenação por caso e destinatário impede que resposta ou fechamento ultrapasse uma criação ainda não entregue. No máximo 16 threads de entrega por instância e 64 faixas de bloqueio de entrega; colisões serializam.
- **Provas:** testes locais de transação injetam erro ao gravar a intenção e verificam rollback da mensagem ou do fechamento. Testes em subprocessos encerrados após commit exercitam recuperação de `handoff.created`, `conversation.replied` e `handoff.closed`; outra queda durante a entrega comprova preservação da contagem. Uma resposta de entrega perdida é reenviada com ID e corpo iguais. Testes verificam migração 0009→0010 sem perda de inbox, máscara por destinatário, ordem e limite de tentativas. Esses testes usam dados e receptores sintéticos, sem rede externa ou chamadas pagas.
- **Resultados observados:** Supervisor executou em cópia isolada ampliada **72 testes focados passaram**, incluindo migração, integração, retomada e o ticketing real. Depois, o teste de recusa completa passou nas **2 parametrizações**. O ajuste subsequente `IF NOT EXISTS` na criação 0010 foi seguido localmente por **11 testes unitários de migração/outbox aprovados**; Ruff nos arquivos alterados passou. A suíte estrita completa e nova revisão independente permanecem pendentes.
- **Limitações e riscos:** tentativa esgotada fica `failed` e bloqueia eventos posteriores do mesmo caso/destinatário; não há reenvio automático após o teto. Se o processo cair na terceira tentativa após o receptor aplicar o evento e antes da confirmação, o resultado é incerto e não há quarta tentativa automática; o ID estável permite reenvio idempotente explícito. Uma retomada legítima que fique viva além do prazo das três tentativas do ticketing pode deixar a entrega do ticketing como falha antes de o modelo terminar; a recuperação imediata aqui trata a morte do processo, não limita a duração da chamada. A recuperação exige runtime compartilhado e bloqueios SQLite funcionais; todas as instâncias devem rodar a nova versão antes de receber tráfego, pois a versão anterior usa arquivos de bloqueio diferentes. A 0009 ampliada continua exigindo runtime compatível; a 0010 não corrige instalações anteriores cuja 0009 já foi marcada sem seus campos. O downgrade da 0010 remove a outbox e, portanto, não preserva intenções nela guardadas; não foi executado sobre dados existentes do usuário.
- **Próxima ação:** Supervisor fixa o candidato incluindo os dois arquivos novos `src/merchant_assistant/data/webhook_outbox.py` e `tests/unit/test_webhook_outbox.py`, executa a suíte estrita isolada e despacha Reviewer independente. Não houve commit, publicação ou aprovação própria.

## Tarefa 66, rodada 4 (descida da 0010)

- **Papel e base:** Developer, branch `codex/v0.7.0-identidade-hitl`, base `fa4f0d4` (produto igual ao candidato `5ebbfa6`; o commit seguinte só mexeu em docs). Um commit local, identidade conferida (`lauroPereira`, `lauro.s.pereira@gmail.com`). Corrige o P2 do [parecer da rodada 3](v070-reviewer-t66-r3.md) conforme a decisão do responsável, mais dois testes da suíte estrita que ainda esperavam o esquema 9 (pedido do Supervisor).
- **Arquivos alterados:** `src/merchant_assistant/data/migrations.py`, `src/merchant_assistant/cli.py`, `tests/unit/data/test_migrations.py`, `tests/integration/test_use_cases.py`, `tests/integration/test_v060_api.py`, `docs/tasks/66-webhooks-assinados-ticketing.md` e esta passagem.
- **Mudança (P2):**
  - `Migration` ganhou o campo opcional `guard_down` (função que recebe a conexão). As outras migrações não mudam. `migrate` roda os `guard_down` das migrações que vão descer **antes do primeiro passo**; a recusa levanta `RollbackRefused` (`RuntimeError`) e não altera tabela, linhas nem `schema_version`, mesmo numa descida mais funda (`--to 0`).
  - `_outbox_down_guard` (0010) conta as linhas de `webhook_outbox` com `status != 'delivered'`, por estado. Estados do código da outbox: `pending` (inclui "em tentativa": `attempts > 0` sem estado próprio), `delivered`, `rejected` e `failed` (falha esgotada). Mensagem: `cannot roll back 0010_webhook_outbox: webhook_outbox still holds 3 event(s) not delivered (failed: 1, pending: 1, rejected: 1). Deliver them or resolve them first, then roll back again. Nothing was changed.`
  - Tabela vazia ou só com `delivered`: a descida segue com o mesmo `DROP TABLE webhook_outbox` de antes.
  - `merchant-assistant migrate --to N` converte a recusa em `SystemExit` com a mensagem (padrão do `cli.py`, código 1, sem traceback). Foi o único acréscimo além do texto da decisão; só afeta o caminho de recusa.
- **Decisão além do texto:** `rejected` (o receptor recusou o evento, final) também bloqueia, porque a regra é "qualquer linha que não esteja entregue" e o corpo só existe na outbox. Se o responsável quiser tratar `rejected` como resolvido, basta trocar o filtro do guarda; não alterei nada por inferência.
- **Testes novos** (`tests/unit/data/test_migrations.py`, 8):
  - `test_rollback_of_0010_is_refused_while_an_event_is_pending` (pendente sem tentativa e pendente em tentativa; a linha `delivered` não é contada);
  - `test_rollback_of_0010_is_refused_while_an_event_has_failed`;
  - `test_refused_rollback_reports_each_state_and_leaves_the_database_as_it_was` (mensagem por estado; linhas, versão 10, `schema_version` 1..10, dados do seed e `integrity_check` intactos, nas descidas para 9, 8 e 0);
  - `test_rollback_of_0010_with_an_empty_outbox_drops_the_table`;
  - `test_rollback_of_0010_with_only_delivered_events_drops_the_table`;
  - `test_0010_comes_up_again_after_a_rollback`;
  - `test_rollback_goes_through_once_the_blocking_events_are_resolved`;
  - `test_cli_migrate_refuses_the_rollback_with_a_clear_message` (`SystemExit`, nada em stdout, banco intacto).
- **Prova de que os testes pegam o defeito:** sonda em processo que remove o `guard_down` da 0010 (sem editar arquivo): 5 dos testes novos falham (pendente, falha, intacto, resolvidos, CLI); os de tabela vazia, só entregues e subir de novo passam, como esperado.
- **Testes herdados da 0010 (pedido do Supervisor):** `test_use_cases.py::test_readiness` passou a esperar `schema == 10` (a versão do app, 0.6.0, fica para a T68); `test_v060_api.py::test_migration_0008_round_trip_on_a_synthetic_database` passou a esperar `current_version == 10`. Nesse cenário a outbox está vazia (uma mensagem sem encaminhamento) e o teste continua descendo a 0010 com o guarda, sem afrouxá-lo.
- **Comandos e números** (todos com `-p no:cacheprovider` e `--basetemp .pytest_cache/t66-r4-dev-*` novo; sem rede nem chamada paga):
  - `pytest tests/unit/data/test_migrations.py tests/unit/test_webhook_outbox.py` → **19 passed** (17 de migração, 9 antigos mais 8 novos, e 2 da outbox; 14,80 s);
  - `pytest tests/integration/test_v070_webhooks.py` → **36 passed** (82,30 s, código 0); o `WinError 5` do hardlink do orçamento **não** ocorreu nesta máquina;
  - `pytest test_use_cases.py::test_readiness test_v060_api.py::test_migration_0008_round_trip_on_a_synthetic_database test_v1_api.py::test_migration_0006_round_trip_preserves_legacy_synthetic_records tests/unit/data/test_migrations.py tests/unit/test_webhook_outbox.py` → **22 passed** (23,52 s). Antes do ajuste dos dois números, o de `test_v060_api.py` falhava com `assert 10 == 9`;
  - `ruff check` e `ruff format --check` nos 5 arquivos de código alterados → ok.
  - A suíte estrita completa não foi rodada (fica com o Supervisor).
- **Limitações:**
  - A verificação e o `DROP TABLE` não estão na mesma transação (`executescript` confirma antes de rodar): com a API ainda enfileirando eventos, uma linha pode entrar entre os dois. O procedimento do CHANGELOG já manda parar a pilha antes de `migrate --to N`; o guarda não tenta substituir isso.
  - Não existe comando para "resolver" eventos. O código só reentrega linhas `pending` (no início da API, com o receptor configurado); `failed` e `rejected` são finais e só saem da outbox por intervenção direta no banco, depois de conferidos. A mensagem diz "entregar ou resolver" sem apontar um comando que não há. Se o responsável quiser um caminho de reenvio ou de baixa, é uma tarefa nova.
  - `pending` sem URL ou segredo configurado nunca é entregue; nesse caso o operador precisa configurar o receptor e subir a API, ou resolver à mão.
  - README e CHANGELOG não foram tocados: a nota de retorno (`migrate --to 8` ou menos) deve citar a recusa no fechamento (T68).
- **Próximo responsável:** Supervisor roda a suíte estrita no candidato desta rodada; depois, Reviewer independente (o parecer da rodada 3 só liberou o P2 por esta correção; CA-47 e CA-48 seguem para revalidação). Sem aprovação própria, push ou ação externa.
