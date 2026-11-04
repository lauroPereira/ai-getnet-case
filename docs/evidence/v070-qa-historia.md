# QA real v0.7.0: evidência da história, momento a momento

Rodada r1, 2026-11-04, candidato `v0.7.0-local-r1` (backend `e97d7f0`, web `932aeb6`, fingerprint `12adae52…ad8f`). Saídas HTTP copiadas do que o `curl` devolveu, com o token **mascarado** (`<JWT-masked>`); senhas fictícias e chaves de provedor não aparecem. Cada ação do operador usou um caso novo:

| Caso | Protocolo | Quem pediu | Ação do operador | Superfície |
| --- | --- | --- | --- | --- |
| A | `HO-20261104-4881A6` | interface (lojista) | assumir, `reply`, resolver; `op_bruno` tenta assumir | tela de ticketing |
| B | `HO-20261104-FC3BB9` | `curl` | assumir e `approve` | tela de ticketing |
| C | `HO-20261104-82421D` | `curl` | assumir e `reject` | tela de ticketing |
| D | `HO-20261104-666A45` | `curl` | `reply` depois de reiniciar a API (duas vezes) | ticketing por `curl` |
| E | `HO-20261104-8E63B5` | `curl` | `approve` pela CLI `operator act` (API parada) | CLI |
| Docker | `HO-20261104-B8DDCF` | `curl` | assumir, `reply` depois de reiniciar o contêiner, resolver | ticketing por `curl` |

Os ledgers e o custo de cada momento estão em [v070-qa.md](v070-qa.md).

## Momento 1 — sem token (CA-46, UC-22)

```text
POST /messages            (sem Authorization)  -> HTTP 401  www-authenticate: Bearer realm="merchant-assistant"
  x-request-id: req_4690ec2f2235414b9566
  {"error":{"code":"token_required","message":"A bearer access token is required.",...}}
POST /v1/messages (corpo válido, sem token)    -> HTTP 401 token_required        req_81d599cf161944c18061
POST /v1/messages (token "not-a-token")        -> HTTP 401 invalid_token         req_d56798a3953247f68d7e
```

Ledger da campanha antes e depois: 239 entradas, US$0,06929924, sem delta (nenhuma chamada a modelo). Observação O-6: `POST /v1/messages` com corpo inválido e sem token responde `422 invalid_request` (lista os campos) antes de `401`; não vaza dado e não chama modelo.

## Momento 2 — login do lojista (UC-22)

```text
POST /v1/auth/token  grant_type=password  username=cliente1988  client_id=merchant-assistant-web
  HTTP 200  x-request-id: req_66e8d56d0e3f4954b72b
  {"access_token": "<masked>", "token_type": "Bearer", "expires_in": 3600, "scope": "support:read handoff:create conversation:read"}
header: {"alg":"RS256","kid":"3gasS67vkUJKjJtPj25lYSFaxOMANseEM0yMyWOono8","typ":"at+jwt"}
claims: aud=["merchant-assistant"] client_id=merchant-assistant-web customer_id=cliente1988
        iss=http://127.0.0.1:8000 role=merchant scope="support:read handoff:create conversation:read"
        sub=merchant:cliente1988 (jti, iat, nbf, exp presentes) validade 60,0 min
verificação com o JWKS publicado (GET /.well-known/jwks.json, 1 chave, mesmo kid): OK (RS256, aud, iss, folga de 30 s)
```

Descoberta: `GET /.well-known/openid-configuration` 200 (`req_92170ad22c9540b29bf3`) com `issuer`, `jwks_uri`, `token_endpoint`, `grant_types_supported` (`password`, `client_credentials`), `scopes_supported`. Erros no formato RFC 6749: senha errada `400 {"error":"invalid_grant","error_description":"Invalid username or password."}` (`req_672dc95c606f4df6a0cb`), client inexistente `401 invalid_client` com `WWW-Authenticate: Basic` (`req_7997a1995e7748a1946a`). Operadores recebem `aud=["merchant-assistant","ticketing"]`, `scope="handoff:operate support:read"`, `sub=operator:op_ana|op_bruno`, sem `customer_id`; `cliente_demo_002` recebe `sub=merchant:cliente_demo_002`.

## Momento 3 — token adulterado e revogado (CA-46)

```text
GET /v1/profiles  token com 1 caractere da assinatura trocado -> HTTP 401 invalid_token  req_13ea2780f1fa44d98954
GET /v1/profiles  token original (controle)                   -> HTTP 200
POST /v1/auth/revoke  (token novo)                            -> HTTP 200               req_f185f6c1e52b409f9123
GET /v1/profiles  o mesmo token depois de revogar             -> HTTP 401 invalid_token  req_0a2052b79dcd4a0b92b6
novo login (ponto de retorno)                                 -> HTTP 200               req_671988bdd242407c81b1
```

## Momento 4 — identidade forjada (CA-46, UC-22)

```text
POST /messages  token de cliente1988 + {"user_id":"cliente_demo_002", ...}
  HTTP 403  x-request-id: req_af81fc6aa1a241aabd8c
  {"error":{"code":"identity_mismatch","message":"user_id does not match the session's merchant.",...}}
POST /v1/messages com user_id -> HTTP 422 invalid_request ("Invalid fields: user_id"): o /v1 não aceita user_id.
```

Ledger sem delta.

## Momento 5 — pergunta normal (CA-46, UC-22)

`POST /messages` com o token de `cliente1988`, sem `user_id`: "Quando cai meu próximo recebimento?" -> `HTTP 200`, `request_id req_53ab01622e244ce3a187`, rota `support`, `status answered`, `via agent`, `conversation_id conv_ffc1b0cc70cd4fe39ad6`.

```text
answer: "O próximo recebimento está previsto para hoje, no valor líquido de R$ 148,06. ... outro recebimento previsto para
         05/11/2026, no valor líquido de R$ 1.162,20."   (dados de cliente1988)
trace (GET /traces/req_53ab..., token do próprio lojista): model_calls 5, tool_calls 4, user_id cliente1988
audit_events (4 linhas novas, soma = tool_calls do trace):
  1 get_complaint_history     merchant:cliente1988  support:read  ok
  2 run_customer_healthcheck  merchant:cliente1988  support:read  ok
  3 get_receivables_schedule  merchant:cliente1988  support:read  ok
  4 get_payout_status         merchant:cliente1988  support:read  ok
```

Custo: US$0,00061128.

## Momento 6 — pedido de atendente (UC-20, CA-47)

Pela interface (lojista `cliente1988`, Atendimento, mensagem livre): "Minha máquina não conecta, quero falar com um atendente". Resposta na tela: "Encaminhei seu caso para um atendente da nossa equipe, que responderá por aqui. Protocolo: HO-20261104-4881A6." Estado do caso: `handoff · status handoff · rota human_handoff`. Nenhuma palavra "simulação" nem protocolo `SIM-`. Log da API: `req_966f9c0269444063aee6`, rota `human_handoff`, 3 chamadas de modelo, custo US$0,00033956.

```text
GET /v1/handoffs  (token op_ana)  -> HTTP 200  req_bb3d4b32bbb244e4892a
  cases: [{"case_id":"hc_154e13748dc742da","protocol":"HO-20261104-4881A6","customer_id":"cliente1988",
           "conversation_id":"conv_bb05b89c257042c9a923","reason":"customer_request","queue_state":"open",
           "claimed_by":null,"resume_count":0,"resume_status":null,"channel":"web","ticket_id":null, ...}]
```

Os casos B a E (via `curl`) devolvem o corpo HTTP do mesmo caminho: `{"status":"handoff","route":"human_handoff","via":"agent","handoff":{"protocol":"HO-20261104-FC3BB9","reason":"customer_request"},...}` (`req_3ef8f046bcb24dafaf26`), sem campo `simulated` e sem texto de simulação. Observação O-8: `ticket_id` do caso no assistente permanece `null` durante todo o ciclo.

## Momento 7 — recepção no ticketing (CA-47)

`op_ana` entra na interface (Real (API), usuário e senha) e a barra lateral mostra "Sessão ativa · papel operator · operator:op_ana"; só a aba **Ticketing** existe. Fila Recepção: "HO-20261104-4881A6 · Recepção", ticket `tkt_c6d9b62237d4`, caso `hc_154e13748dc742da`, lojista `cliente1988`, idioma `pt`, resumo, pergunta pendente, rascunho do atendente e, expandida, a conversa mascarada (2 turnos).

```text
GET ticketing /tickets/tkt_c6d9b62237d4  -> HTTP 200  status=new  assignee=None
  deliveries.received: [{"event_id":"evt_84218a735b00cbd49405ae6a2a32a5aa","event_type":"handoff.created","received_at":"2026-11-04T04:12:11.642+00:00"}]
  events: created (null -> new)
GET /v1/handoffs/hc_154e13748dc742da (assistente) -> deliveries:
  [{"event":"handoff.created","target":"ticketing","attempt":1,"status":"delivered","response_code":200,
    "event_id":"evt_84218a735b00cbd49405ae6a2a32a5aa"}]
```

O mesmo `event_id` aparece nos dois lados.

## Momento 8 — lojista insiste (CA-48)

Interface, mesma conversa: "Já reiniciei a máquina e ela continua sem conectar, alguém pode me ajudar?" (`req_e22c0ce1408744c89f06`, rota `knowledge_and_support`, status `handoff`, 3 chamadas, US$0,00055836). Resposta: "Seu caso já foi encaminhado para um atendente da nossa equipe, que responderá por aqui. Protocolo: HO-20261104-4881A6." Mesmo protocolo.

```text
GET /v1/handoffs         -> 1 caso (hc_154e..., open); nenhum caso novo
GET ticketing /tickets   -> 1 ticket (tkt_c6d9b62237d4)
GET /ready               -> "pending_handoffs":1, "checkpoints":{"store":"sqlite","threads":1}
```

## Momento 9 — atendimento e conflito (CA-48)

1. `op_ana` clica **Assumir** na tela: "Ticket assumido. Ele aparece na fila Atendimento." O ticketing registra `ticket.assigned` entregue (200); o assistente: `claimed_by=op_ana`, `queue_state=claimed`.
2. `op_bruno` (outra sessão do navegador) vê o ticket em Atendimento com "responsável op_ana · caso no assistente handoff · fila claimed". Por `curl`:

```text
POST ticketing /tickets/tkt_c6d9b62237d4/assign  (token op_bruno) -> HTTP 409
  {"error":{"code":"claimed_by_other","message":"Another operator already holds this case.","request_id":"req_20b43efeee054827a842"}}
POST /v1/handoffs/hc_154e13748dc742da/claim     (token op_bruno) -> HTTP 409 claimed_by_other  req_8837c297da504f8f899c
```

3. Na tela, `op_bruno` tenta **Responder** (texto "Teste do QA...") e a interface mostra: "Another operator already holds this case. — Outro operador já assumiu este caso. Atualize a fila e escolha outro ticket. (código: claimed_by_other)". O ticketing registra `ticket.action` `rejected 409`; o caso continua com `op_ana`, sem turno novo.

Auditoria (D23): a reivindicação válida (`handoff.claim` `ok`, `service:ticketing` em nome de `operator:op_ana`) e as três recusas aparecem em `audit_events` (`handoff.claim` `claimed_by_other` por `operator:op_bruno` e por `service:ticketing` em nome de `operator:op_bruno`; `handoff.reply` `claimed_by_other` por `service:ticketing` em nome de `operator:op_bruno`).

## Momento 10 — envio `reply` (UC-20, CA-47)

`op_ana`: Responder, texto próprio, confirmação, **Enviar ação** ("Ação enviada e aceita pelo assistente."). Chave de idempotência gerada pela tela: `web-646b7ce569934086ae38fe00e496cd5b`.

```text
ticketing: POST /tickets/tkt_c6d9b62237d4/actions -> 200 ; ticket status=pending, queue_state=answered, case_state=awaiting_customer,
           reply_delivered_at=2026-11-04T04:16:02+00:00 ; ticket.action delivered (1 tentativa)
retomada: req_resume_8736836d0f664038  2722 ms  1 chamada de modelo  US$0,0001024  route=human_reply
GET /v1/conversations/conv_bb05b89c257042c9a923 (token do lojista): novo turno
  {"role":"assistant","route":"human_reply","via":"operator","operator_action":"reply","protocol":"HO-20261104-4881A6","text":"Olá! Aqui é a Ana, ..."}
  (texto idêntico ao digitado; sem operator_id no turno) ; state=awaiting_customer
GET mocks /merchant/events?conversation_id=conv_bb05...  (webhook ao lojista)
  {"id":"evt_6923c303e47e863d98774a74515223ff","type":"conversation.replied","data":{"case_id":"hc_154e...","protocol":"HO-20261104-4881A6",
   "action":"reply","reply_text":"Olá! Aqui é a Ana, ...","via":"operator","request_id":"req_resume_8736836d0f664038","delivered_at":"2026-11-04T04:16:02+00:00"}}
  (sem operator_id, D29)
ticketing received: handoff.created, conversation.replied ; assistente deliveries: conversation.replied -> merchant (200) e -> ticketing (200)
```

## Momento 11 — ação repetida (CA-48)

```text
POST ticketing /tickets/.../actions  mesma chave, mesmo texto   -> HTTP 200  delivery.replayed=true (evt_1c95c37b0f074c4dbd42bfa2696513df)
POST /v1/handoffs/hc_154e.../actions mesma chave, mesmo texto   -> HTTP 200  req_811eb626f31b4920a0a1
  {"event_id":"hev_ffbabdf63e9e4e7c","action":"reply","operator_id":"op_ana","idempotency_key":"web-646b...","queue_state":"answered",
   "resume_status":"done","replayed":true}
POST /v1/handoffs/hc_154e.../actions mesma chave, texto diferente -> HTTP 409 idempotency_conflict  req_c340a4400d044466ab73 (D22)
POST ticketing /tickets/.../actions  chave nova (ação nova)      -> HTTP 409 already_resumed         req_a9e003b0d1e5443c8602
POST /v1/handoffs/hc_154e.../actions chave nova (approve)        -> HTTP 409 already_resumed         req_f6b3a258a2f24341b600
```

Depois das repetições: 1 turno `via=operator` na conversa, 1 evento no receptor do lojista e ledger sem delta (252 entradas, US$0,07091128). A "falha simulada de transporte" foi emulada repetindo o pedido sem ter lido a resposta; a falha real (timeout) aparece no momento 15.

## Momento 12 — lojista volta (UC-20, CA-47)

Interface: "Obrigado, vou conferir o chip agora." A tela mostra, sob o ícone de atendente, **"Atendente humano · rota human_reply"** e o texto da Ana; estado do caso "awaiting_customer · status answered · rota human_reply". `POST /v1/messages` 200 sem chamada a modelo: ledger igual ao do momento 11 (252 entradas, US$0,07091128). A mensagem do lojista ficou gravada com rota `human_reply`.

## Momento 13 — finalização (CA-47)

`op_ana`, fila Envio: ticket "Resposta entregue ao lojista em 2026-11-04T04:16:02+00:00"; confirmação "o atendimento terminou" e **Resolver** ("Ticket resolvido; o caso foi fechado no assistente.").

```text
ticketing: status=solved closed_at=2026-11-04T04:17:41+00:00 closed_by=op_ana
           received: handoff.created, conversation.replied, handoff.closed ; sent: ticket.assigned, ticket.action, ticket.solved (delivered)
assistente: queue_state=closed closed_at=2026-11-04T04:17:41+00:00 resume_status=done resume_count=1
            deliveries: handoff.created, conversation.replied (merchant e ticketing), handoff.closed -> ticketing (200)
```

`case_state` da conversa continua `awaiting_customer` (o fechamento é da fila, D14).

## Momento 14 — `approve` (UC-20, CA-47)

Caso B: `curl` "Minha máquina não conecta..." (`req_3ef8f046bcb24dafaf26`, `HO-20261104-FC3BB9`). `op_ana` assume e **Aprovar o rascunho** na tela.

```text
rascunho: "Olá! Verificamos que sua Get Smart consta como offline. Nossa equipe está analisando o caso e responderá por esta conversa."
entregue: "Verificamos que sua Get Smart consta como offline. Nossa equipe está analisando o caso e responderá por esta conversa."  (sem "Olá! ")
ticket: status=pending queue_state=answered reply_delivered_at=2026-11-04T04:18:50+00:00 ; ticket.action delivered
conversa: via=operator operator_action=approve protocol=HO-20261104-FC3BB9 ; mocks: conversation.replied (approve)
```

Atrito A-2: a tela promete "sem alterações" e a entrega perdeu a saudação (o `personality.v4` autoriza ajustar a voz).

Caso E (CLI, API parada porque o Qdrant embutido só admite um processo; `MERCHANT_ASSISTANT_TOKEN` de `op_ana` por variável de ambiente):

```text
merchant-assistant operator list --state open  -> [("HO-20261104-8E63B5","hc_bd1b4d4e05924eb9","open")]
merchant-assistant operator show hc_bd1b...    -> protocolo, lojista, pergunta pendente, rascunho
merchant-assistant operator act hc_bd1b... --action approve --idempotency-key qa-cli-approve-0001
  -> queue_state=answered case_state=awaiting_customer resume_status=done replayed=false   (1 chamada de modelo)
mesma chave de novo -> replayed=true (sem nova chamada)
conversa: via=operator operator_action=approve (texto idêntico ao rascunho) ; deliveries: conversation.replied delivered ; mocks recebeu
```

Observação O-4: pelo caminho da CLI o ticket correspondente permanece `new` na Recepção (com `reply_delivered_at` preenchido), porque o ticketing não recebe `ticket.assigned`/`ticket.action`.

## Momento 15 — `reject` (UC-21, CA-47)

Caso C: `curl` (`req_69f2e2c8c2bd42048bc5`, `HO-20261104-82421D`). `op_ana` assume e **Rejeitar com instrução**: "verifique o status do dispositivo e responda" (chave `web-0459199d9960493795a068acffc295ce`).

```text
ticketing: POST /tickets/tkt_c90048981446/actions -> HTTP 202 Accepted (a tela mostra "Envio pendente: o ticketing guardou a ação e vai tentar de novo...")
  ticket.action: tentativa 1 04:20:12.959 network_error "assistant unreachable: ReadTimeout" ; tentativa 2 04:20:16.275 delivered (200)
  events: delivery_pending -> action_accepted -> status_changed open->pending -> reply_delivered
retomada: req_resume_d6751b63748a4c12  6155 ms  3 chamadas de modelo  1 ferramenta  US$0,00045792  route=human_reply
trace (GET /traces/req_resume_d6751b63748a4c12): passos human_review, support, tool:get_device_status, personality, output_guard
auditoria da ferramenta: get_device_status  customer_id=cliente1988  principal=operator:op_ana  scope=support:read  outcome=ok
fila: queue_state=rejected resume_count=1 ; nenhum caso novo na fila (3 casos até aqui: A, B e C)
conversa: via=operator operator_action=reject ; case_state=awaiting_customer
texto: "O Get Smart aparece offline, e o último sinal recebido foi em 03/11/2026 às 21:58:53. A rede Wi-Fi foi reconfigurada no atendimento
        anterior e resolveu o problema naquela ocasião. Como a máquina voltou a aparecer offline, vou encaminhar seu pedido para falar com um atendente."
```

Depois de **Atualizar** o ticket sai da fila Atendimento e fica em Envio. Atritos A-1 (timeout de 3 s do ticketing contra uma retomada de 6,2 s) e A-3 (a resposta promete encaminhar de novo, mas o caso já está com o atendente e nada novo foi aberto).

## Momento 16 — reinício da API (CA-48)

Caso D: `curl` (`req_c47ead3b105a4f43a1ef`, `HO-20261104-666A45`, ticket `tkt_9edce41659d5` em `new`).

```text
ANTES      /ready: pending_handoffs=1 checkpoints.threads=4 ; fila: HO-...666A45 open
reinício   taskkill /F no processo da API (queda abrupta) e novo processo `uvicorn` sobre o mesmo runtime
DEPOIS     /ready: pending_handoffs=1 checkpoints.threads=4 ; fila: HO-...666A45 open
op_ana (ticketing): assign 200, actions(reply, chave qa-m16-reply-0001) 200
           ticket pending/answered, reply_delivered_at=2026-11-04T04:22:06+00:00, ticket.action delivered (1 tentativa)
           caso: queue_state=answered resume_status=done resume_count=1 resume_error=null ; retomada 2788 ms, 1 chamada
2º reinício (taskkill /F de novo): caso continua answered/done/1 ; mesma chave no assistente -> HTTP 200 replayed=true (req_8bfca5966f1e45019c08)
           conversa: 1 turno via=operator (reply) ; /ready pending_handoffs=0 checkpoints.threads=4
```

## Momento 17 — outro lojista (CA-46)

Token de `cliente_demo_002` contra dados de `cliente1988` (caso A):

```text
GET /v1/conversations/conv_bb05...      -> 404 not_found     req_65227ef1e1a847e4abe6
GET /conversations/conv_bb05...  (demo) -> 404 not_found     req_c01e45d1df2a41459c1d
GET /traces/req_53ab...          (demo) -> 404 not_found     req_902a9db19f7f46558d27
GET /v1/runs/req_966f...                -> 404 not_found     req_a946df90360a439aa0d5
GET /v1/handoffs                        -> 403 insufficient_scope ("requires the handoff:operate scope")  req_a2a45d50ecbf460481b5
GET /v1/handoffs/hc_154e...             -> 403 insufficient_scope  req_7af234c40e9141fd8c05
POST /v1/handoffs/hc_154e.../claim      -> 403 insufficient_scope  req_77f1f749e7234e74a2e7
GET ticketing /tickets                  -> 401 invalid_token       req_a38212f338a04b99
GET ticketing /tickets/tkt_c6d9...      -> 401 invalid_token       req_d3539868c653496d
GET ticketing /tickets  (sem token)     -> 401 token_required      req_578ca85b9bd74ce9
POST /messages com conversation_id de cliente1988 -> 404 conversation_not_found  req_bc15eebe4478407a94b1
```

Nenhuma resposta traz dado de `cliente1988`; ledger sem delta (266 entradas, US$0,07253393).

## Momento 18 — Docker (CA-47, CA-48)

`BUDGET_LIMIT_USD=0.05 docker compose -p v070qa up --build -d` (a variável limita o ledger do volume novo; `.env.example` intacto). Imagens `v070qa-api|mocks|ticketing` (362 MB cada) e `qdrant/qdrant:v1.19.2` (200 MB, baixada). Contêineres `api` (healthy, publicada só em `127.0.0.1:8000`), `ticketing` (`127.0.0.1:8002`), `mocks` e `qdrant` sem porta no host.

```text
/ready: ready=true, app 0.7.0, schema 10, 145 chunks, kb_initial, budget_remaining_usd 0.0493
log da API: seeded synthetic data ... ; knowledge index built: 145 chunks ; WARNING example credentials from .env.example are in use ...
smoke com token (merchant-assistant smoke --url http://127.0.0.1:8000, usuário cliente1988):
  token for cliente1988 (scope: support:read handoff:create conversation:read)
  200 knowledge, 200 general_web, 200 support, 200 knowledge, 200 knowledge_and_support, 200 knowledge, 200 general_web,
  200 knowledge_and_support, 200 knowledge, 200 knowledge   -> "smoke ok"
ciclo do ticket (token com iss=http://api:8000):
  POST /messages (cliente1988)  -> handoff HO-20261104-B8DDCF  req_06a3870e21b3406f810e  conv_1f65e4d7109b42058708
  GET ticketing /tickets?status=new -> tkt_f71f5c5fe7d2 (new)
  docker compose restart api  -> /ready: pending_handoffs=1 checkpoints.threads=1 (checkpoint no volume)
  assign 200 ; actions(reply, chave qa-docker-reply-0001) 200 -> ticket pending, reply_delivered_at=2026-11-04T04:32:30+00:00
  conversa: turno via=operator (reply, protocolo HO-...B8DDCF) ; receptor do lojista (docker exec no mocks): conversation.replied recebido
  solve 200 -> ticket solved ; assistente queue_state=closed ; deliveries handoff.created, conversation.replied (x2), handoff.closed delivered
volumes (docker exec): assistente /app/runtime: budget.sqlite3(+.limit), checkpoints.sqlite3, index_manifest.json, jwt/, merchant.sqlite3, traces.sqlite3
                       ticketing /app/runtime (volume próprio): ticketing.sqlite3
```

Encerramento: `docker compose -p v070qa down` (sem `-v`): `docker ps -a` vazio, rede removida; ficam os volumes `v070qa_runtime`, `v070qa_ticketing_runtime`, `v070qa_qdrant_storage` e as imagens para a limpeza do Supervisor.
