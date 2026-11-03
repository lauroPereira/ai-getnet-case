<!-- Papel: especificação complementar curta da v0.7.0 (identidade e HITL real), derivada da evolução pós-feedback. -->

# Especificação: v0.7.0 — identidade e HITL real

Versão 2 — 2026-11-03 — aberta pelo Supervisor sob a "Autorização por versão" do AGENTS.md; versão 2 com duas decisões do responsável no mesmo dia: **JWT com emissor próprio** no lugar de chave sintética com sessão opaca, e **serviço de ticketing próprio com tela no projeto web** no lugar do receptor passivo. Deriva da [especificação 0.2](evolucao-pos-feedback.md) (RF-76 a RF-85, RF-100; CA-46 a CA-48) e do [plano](evolucao-pos-feedback-plano.md) (decisões técnicas 1 a 8). História em [identidade-hitl-v070.md](../historias/identidade-hitl-v070.md); decisões em [ADR 0017](../architecture/decisions/0017-identidade-principal-escopos.md) e [ADR 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).

Esta spec não repete a 0.2: fixa o que o plano deixou aberto, o que mudou com as decisões do responsável e o **contrato entre os dois times**.

## Problema

Hoje `POST /messages` aceita qualquer `user_id` do payload, as ferramentas não sabem quem é o principal e o encaminhamento grava um caso `SIM-…` que nenhum humano responde. O avaliador deu 4,0 em HITL e 7,8 em identidade por isso, e pediu integração operacional com humano/ticketing que devolva a resposta ao agente.

## Resultado desejado

1. Toda requisição traz um JWT assinado pelo emissor do assistente; o lojista vem do principal do token; cada tool call verifica escopo e lojista e deixa auditoria com o principal. Trocar o emissor por um provedor OIDC externo é configurar emissor e JWKS.
2. O encaminhamento interrompe o grafo e abre um ticket num sistema de ticketing separado; o operador trabalha o ticket na tela de ticketing (recepção, atendimento, envio, finalização); o ticketing devolve a ação ao assistente por webhook assinado; o mesmo fluxo retoma do ponto salvo, a resposta chega ao lojista e volta ao ticket; resolver o ticket fecha o caso.

## Escopo

| Bloco | Conteúdo | Requisitos | Tarefa | Time |
| --- | --- | --- | --- | --- |
| Identidade | Emissor JWT (RS256, JWKS, descoberta), login de usuários sintéticos, client credentials, revogação, papéis e escopos, `identity_mismatch`, auditoria por tool call, rate limit, MCP e CLI com token | RF-76 a RF-79 | 63 | A |
| Fila | Migração 0009, estados, eventos, reivindicação, ações idempotentes na API e na CLI | RF-80, RF-81, RF-83, RF-85 | 64 | A |
| Interrupção e retomada | Checkpointer SQLite, `human_review`, `Command(resume)`, `approve`/`reply`/`reject`, turno `via=operator`, entrega na próxima mensagem e no GET, retomada após reinício | RF-82, RF-84 | 65 | A |
| Integração no assistente | Eventos de saída assinados, endpoint de entrada do ticketing, entregas registradas, receptor do lojista no `mocks`, compose da API | RF-84, RF-100 | 66 | A |
| Serviço de ticketing | Serviço próprio (banco, API, ciclo do ticket), validação de JWT por JWKS, receptor e emissor de webhooks, bloco no compose | RF-81, RF-85, RF-100 | 66b | B |
| Interface | Login por usuário e senha, áreas por papel, tela de ticketing no projeto web | RF-85 | 67 | B |
| Fechamento | Regressão integrada (assistente + ticketing), campanha `v070-qa` | CA-46 a CA-48 | 68 | A |

## Fora do escopo

Provedor OIDC externo rodando na demo (Keycloak, Auth0, Entra): o assistente valida por emissor e JWKS configuráveis, e a demo usa o emissor próprio. Fluxo de autorização com redirecionamento (authorization code + PKCE) e refresh token. Ticketing comercial (o contrato segue o estilo Zendesk/Freshdesk). Replanejamento (v0.8.0). Mudança de regras financeiras, de ferramentas de Support ou de snapshots públicos.

## Contrato entre os times

Fixado aqui antes do código. Mudança neste contrato só pelo Supervisor, nesta spec, avisando os dois times.

### Identidade (emissor no assistente, tarefa 63)

- `POST /v1/auth/token`, `application/x-www-form-urlencoded` (RFC 6749): `grant_type=password` com `username` e `password` (usuários da demo; o fluxo com redirecionamento é o caminho de produção via provedor externo) e `grant_type=client_credentials` com `client_id` e `client_secret` (serviços). Resposta: `{"access_token", "token_type": "Bearer", "expires_in", "scope"}`. Falha: `401 invalid_grant` ou `invalid_client`, sem dizer qual campo errou.
- `POST /v1/auth/revoke` (Bearer): revoga o `jti` do próprio token até expirar.
- `GET /.well-known/jwks.json` (chaves públicas com `kid`) e `GET /.well-known/openid-configuration` (`issuer`, `jwks_uri`, `token_endpoint`, `grant_types_supported`, `scopes_supported`).
- Token (perfil RFC 9068): cabeçalho `alg=RS256`, `typ=at+jwt`, `kid`; claims `iss`, `sub` (principal), `aud` (lista), `exp`, `iat`, `nbf`, `jti`, `client_id`, `role`, `scope` (escopos separados por espaço) e `customer_id` só para `merchant`. Validade: 60 min para pessoas, 10 min para serviços. Tolerância de relógio: 30 s.
- `aud`: `merchant-assistant` para todos; operadores também `ticketing`.
- `iss`: `JWT_ISSUER`, padrão `http://127.0.0.1:8000`; no compose, `http://api:8000`, e o ticketing usa `ASSISTANT_ISSUER=http://api:8000` e `ASSISTANT_JWKS_URL=http://api:8000/.well-known/jwks.json`. `ASSISTANT_URL=http://api:8000` para os eventos de entrada.
- Principais e escopos:

| Principal | `role` | `aud` | `scope` |
| --- | --- | --- | --- |
| `merchant:cliente1988`, `merchant:cliente_demo_002` | `merchant` | `merchant-assistant` | `support:read handoff:create conversation:read` |
| `operator:op_ana`, `operator:op_bruno` | `operator` | `merchant-assistant ticketing` | `handoff:operate support:read` |
| `service:ticketing` (client `ticketing-demo`) | `service` | `merchant-assistant` | `handoff:integrate` |
| `demo:default` | `demo` | `merchant-assistant` | como `merchant` (lojista `API_DEMO_CUSTOMER_ID`) |
| `admin:default` | `admin` | `merchant-assistant` | `kb:admin profiles:admin support:read handoff:create conversation:read` |

### Webhooks (nos dois sentidos)

- Envelope: `{"id": "evt_…", "type": "<evento>", "created_at": "<ISO 8601 UTC>", "data": {…}}`.
- Cabeçalhos: `X-Webhook-Id` (= `id`), `X-Webhook-Event` (= `type`), `X-Signature: t=<unix>,v1=<hex>`, com `v1 = HMAC-SHA256(segredo, "<t>.<corpo bruto>")`. O receptor recusa assinatura inválida ou `t` fora de 300 s (`401 invalid_signature`) e trata `id` repetido como entrega já recebida (`200`, sem efeito novo).
- Um segredo por sentido: `TICKETING_WEBHOOK_SECRET` (assistente → ticketing), `ASSISTANT_WEBHOOK_SECRET` (ticketing → assistente), `CONVERSATION_WEBHOOK_SECRET` (assistente → lojista).
- Tentativas: até três, esperas de 1 s e 2 s (configuráveis), timeout de 3 s; cada tentativa registrada pelo emissor.

**Assistente → ticketing** (`TICKETING_WEBHOOK_URL`, padrão no compose `http://ticketing:8002/webhooks/assistant`):

| Evento | `data` |
| --- | --- |
| `handoff.created` | `case_id`, `protocol`, `conversation_id`, `customer_id`, `language`, `reason`, `summary`, `pending_question`, `draft_reply`, `transcript` (até 10 turnos `{role, text, at}`, mascarados) |
| `conversation.replied` | `case_id`, `protocol`, `conversation_id`, `action`, `operator_id`, `reply_text`, `via` (`operator`), `request_id`, `delivered_at` |
| `handoff.closed` | `case_id`, `protocol`, `closed_at`, `closed_by` |

`conversation.replied` também vai a `CONVERSATION_WEBHOOK_URL` (lojista; no compose, receptor `POST/GET /merchant/events` do `mocks`).

**Ticketing → assistente**: `POST /v1/integrations/ticketing/events`, com assinatura **e** `Authorization: Bearer <token client_credentials>` com escopo `handoff:integrate`.

| Evento | `data` | Efeito no assistente |
| --- | --- | --- |
| `ticket.assigned` | `ticket_id`, `case_id`, `operator_id` | Reivindica o caso para o operador; outro operador já com o caso → `409 claimed_by_other` |
| `ticket.action` | `ticket_id`, `case_id`, `operator_id`, `action` (`approve`\|`reply`\|`reject`), `text`, `idempotency_key` | Mesma regra de `POST /v1/handoffs/{id}/actions`: retoma o grafo; mesma chave → registro existente (`replayed: true`); caso já retomado → `409 already_resumed` |
| `ticket.solved` | `ticket_id`, `case_id`, `operator_id` | Fecha o caso na fila (`closed`) e emite `handoff.closed` |

Resposta síncrona do assistente: `200 {"status": "accepted"|"replayed", "case_state", "queue_state"}`; `401` assinatura ou token; `403 insufficient_scope`; `404 case_not_found`; `409` conforme a tabela; `422 unknown_operator` se `operator_id` não for operador ativo. A auditoria registra `service:ticketing` agindo em nome de `operator:<id>`.

### Serviço de ticketing (tarefa 66b)

Pacote `src/merchant_assistant/ticketing/` como o `mocks`: mesma imagem, entrada própria, **banco SQLite próprio** (`TICKETING_DB_PATH`) e **nenhum import** de outros módulos do assistente (teste de arquitetura). Fala com o assistente só por HTTP. Compose: serviço `ticketing` em `127.0.0.1:8002` (a tela do web roda no host). Ciclo do ticket no estilo Zendesk:

| Estado | Entra quando | Momento da tela |
| --- | --- | --- |
| `new` | `handoff.created` recebido | Recepção |
| `open` | operador assume (`ticket.assigned` aceito) | Atendimento |
| `pending` | ação enviada e aceita (`ticket.action`); `conversation.replied` recebido marca a resposta como entregue | Envio |
| `solved` | operador resolve (`ticket.solved` aceito) | Finalização |

API para a tela, todas com JWT de operador validado pelo JWKS do assistente (`ASSISTANT_JWKS_URL`, cache com recarga por `kid` desconhecido), `aud` contendo `ticketing` e escopo `handoff:operate`: `GET /tickets?status=`, `GET /tickets/{id}` (dados do caso, eventos, entregas nos dois sentidos), `POST /tickets/{id}/assign`, `POST /tickets/{id}/actions` (`{"action", "text", "idempotency_key"}`), `POST /tickets/{id}/solve`. Erros do assistente (`409`, `422`) voltam à tela com o mesmo código. Falha de rede ao chamar o assistente: o evento fica numa caixa de saída com novas tentativas e a tela mostra "envio pendente".

## Decisões que o plano não fixou

Todas reversíveis; registradas também no relatório do Supervisor.

| ID | Decisão | Motivo | Como reverter |
| --- | --- | --- | --- |
| D1 | **Credenciais da demo:** usuários sintéticos `cliente1988`, `cliente_demo_002`, `op_ana`, `op_bruno` com senhas fictícias em `DEMO_USER_PASSWORDS` (`usuario:senha,…`), client `ticketing-demo` com `TICKETING_CLIENT_SECRET`; `demo` e `admin` só com `API_DEMO_PASSWORD`/`API_ADMIN_PASSWORD` configurados (vazios por padrão = desligados). Senhas guardadas como hash PBKDF2-SHA256 da biblioteca padrão (iterações configuráveis; 600 000 por padrão); valores do `.env.example` com sufixo `-fictitious`; a API avisa na subida quando um valor de exemplo está em uso | Responsável: JWT com emissor próprio; `docker compose up` funciona sem edição; admin não ganha senha pública | — |
| D2 | **Chave de assinatura RS256** gerada na primeira subida em `<runtime>/jwt/` (fora do Git, no volume do compose) ou lida de `JWT_PRIVATE_KEY_PATH`; `kid` = impressão digital da chave pública; `JWT_ISSUER` configurável. O verificador aceita emissor e JWKS externos (`JWT_JWKS_URL`) | Nenhum segredo de assinatura versionado; ponto de troca por OIDC | — |
| D3 | **`POST /v1/sessions` e `DELETE /v1/sessions/current` saem**, substituídos por `/v1/auth/token` e `/v1/auth/revoke`; quebra do `/v1` documentada no CHANGELOG ao lado da de `POST /messages`. O único cliente (web) migra na 67 | Uma forma de autenticação só | Manter `/v1/sessions` como alias |
| D4 | **Operador no caminho `reject`:** o Support roda com o principal do operador e o `customer_id` do caso, lido do caso pelo servidor; o registro exige `support:read` e lojista igual ao do caso | Escopo e lojista verificados também quando quem age é o humano | — |
| D5 | **Rate limit:** janela fixa de 60 s por principal em `rate_limit_hits`, `RATE_LIMIT_PER_MINUTE=30`, em `POST /messages`, `POST /v1/messages`, `POST /v1/handoffs/*` e na entrada do ticketing; `429 rate_limited` com `Retry-After`, antes de qualquer chamada a modelo | Simples e testável com relógio fixo | Trocar o cálculo da janela |
| D6 | **`thread_id` do checkpoint = `request_id` da execução que encaminhou**, gravado em `handoff_cases.thread_id` (o plano dizia `conversation_id`) | Nova mensagem do lojista com o caso aberto não colide com a interrupção pendente | Coluna única a trocar |
| D7 | **Protocolo `HO-AAAAMMDD-XXXXXX`**; `simulated` sai do payload e do texto | Plano, item 7 | — |
| D8 | **Entrega na próxima mensagem:** havendo turno de operador não entregue, `POST /messages` registra a mensagem do lojista, devolve o turno com rota `human_reply` e `via=operator`, sem chamada a modelo, e o marca como entregue | Resposta humana nunca escondida atrás de uma automática | — |
| D9 | **Ação sobre caso `open` reivindica implicitamente** para o operador que age; caso de outro → `409 claimed_by_other`; reivindicar de novo o próprio caso é idempotente. A reivindicação vale igual pela API do assistente e pelo ticketing | Uma fonte de verdade (o assistente) | Exigir `claim` explícito |
| D10 | **`idempotency_key` obrigatória** nas ações (8 a 80 caracteres `[A-Za-z0-9_-]`) | RF-83 | — |
| D11 | **Webhook ao lojista só por `CONVERSATION_WEBHOOK_URL`**: com JWT não há sessão no servidor onde registrar uma URL (RF-100 previa também a URL da sessão) | Evita que um token faça o servidor chamar qualquer URL | Guardar URL por usuário |
| D12 | **MCP e CLI (`operator …`)** recebem um token por `MERCHANT_ASSISTANT_TOKEN` (fora da lista de processos), validado pelo mesmo verificador; `--customer` sai do MCP; `merchant-assistant auth token` obtém o token | RF-78 | Reintroduzir `--customer` |
| D13 | **Rotas de demo `GET /traces/{id}` e `GET /conversations/{id}` exigem token:** lojista e demo só o que é seu; operador só conversas com caso; admin tudo | Hoje abertas com `DEMO_MODE=true`, o padrão do compose | — |
| D14 | **Estados depois da ação:** `approve`/`reply` → fila `answered`, caso `awaiting_customer`; `reject` → fila `rejected`, caso conforme o Support reexecutado, nunca de volta a `handoff` no mesmo ciclo; `ticket.solved` → fila `closed`. A máquina de estados ganha a saída de `handoff` só por ação de operador | RF-80, RF-84 | — |
| D15 | **Rascunho do operador** vem do Escalation (`escalation.v2`: resumo, pergunta pendente e rascunho no idioma do lojista); falha do modelo → rascunho determinístico a partir das contribuições | Plano, item 4 | — |
| D16 | **Serviço de ticketing dentro do pacote** (`merchant_assistant.ticketing`, como o `mocks`), isolado por teste de arquitetura e banco próprio | Mesma imagem e mesmo compose; o avaliador sobe tudo com um comando | Extrair para repositório próprio |
| D17 | **Ordem do Time B:** 72a já entregue; depois 66b (serviço, worktree próprio na v0.7.0) e 67 (tela). Nenhum dos dois depende do código do Time A, só deste contrato | Paralelismo real | — |

## Critérios de aceitação e prova

| ID | Critério | Prova determinística (tarefa) | Prova real (QA, campanha `v070-qa`) |
| --- | --- | --- | --- |
| CA-46 | Sem token `401`; token adulterado, expirado, revogado ou de outro emissor/audiência `401`; `user_id` de outro lojista `403 identity_mismatch`; dado de outro lojista nunca aparece; todo tool call com auditoria (principal, escopo, resultado) | Testes de contrato e integração; contagem de auditoria = contagem de tool calls (63, 64) | UC-22 por `curl` e na interface |
| CA-47 | Caso vira ticket; `approve`, `reply` e `reject` feitos no ticketing produzem turno marcado como atendente, entrega ao lojista e volta ao ticket; resolver fecha o caso; entregas registradas nos dois lados | Integração com modelo programado e os dois serviços em processo (65, 66, 66b, 68) | UC-20 e UC-21 na tela de ticketing, na API e no Docker |
| CA-48 | Retomada dupla `409`; mesma chave devolve o registro; evento repetido sem efeito; retomada após reinício da API | Teste concorrente sob `BEGIN IMMEDIATE`; novo processo sobre o mesmo checkpoint (64, 65) | Reinício do container entre encaminhar e agir |

Regressão: 40 casos (`challenge_examples` 10, `core_cases` 17, `business_journeys` 13) e 4 conversas (`followup`) sem piora em relação à v0.6.0, salvo diferença justificada pelo contrato novo.

## Requisitos não funcionais

- Teto da campanha `v070-qa`: US$0,20, montada uma vez, combinada com o ledger primário (acumulado do projeto antes da versão: US$0,69 de US$5,00).
- Testes sem chamada paga e sem rede externa; chaves RSA de teste geradas no teste; migração 0009 reversível; quebras de `POST /messages` e `/v1/sessions` no CHANGELOG com as chamadas do avaliador (token + mensagem).
- O caminho sem encaminhamento não lê checkpoint.
- Nenhum segredo real; senhas, segredos de webhook e client secret do exemplo nomeados como fictícios; chave privada de assinatura nunca no Git.
- Dependências novas: `pyjwt[crypto]` (63 e 66b, mesma linha) e `langgraph-checkpoint-sqlite` (65).

## Riscos

| Risco | Mitigação |
| --- | --- |
| Estado do grafo não serializável pelo `SqliteSaver` | Teste de serialização primeiro na 65; plano B na ADR 0018 |
| Quebra do `curl` do avaliador | README com token + mensagem; smoke e `/docs` com o fluxo de token; senhas fictícias no `.env.example` |
| Contrato entre times divergir | Contrato nesta seção; teste de contrato dos dois lados com os mesmos exemplos; integração na 68 |
| Arquivos compartilhados entre times (`pyproject.toml`, compose, `.env.example`) | Só acréscimos em blocos próprios; o Supervisor integra a branch do B na da versão e resolve |
