# Reviewer v0.7.0 (Time A)

Pareceres do Reviewer independente do Time A. Gravado pelo Supervisor a partir do relatório do Reviewer (que não tem escrita).

## Tarefa 63, rodada 1 — correções necessárias

- **Papel:** Reviewer em contexto frio, independente; não leu `v070-developer.md`. Limite declarado: as seções Validação e Status estão no arquivo da tarefa e vieram na leitura inicial; não foram usadas como evidência.
- **Critérios:** tarefa 63 (passos 1 a 8 e critérios), spec v0.7.0 versão 2 ("Contrato entre os times / Identidade", D1 a D5, D12, D13, CA-46), RF-76 a RF-79, ADR 0017.
- **Candidato:** checkout de revisão `C:\workspace\ai-getnet-case-wt\review-a`, HEAD destacado `de3a760` (código em `59f0311`), base `220878e`/`fe9d12b`; árvore limpa; sha256 de `identity.py`, `v1.py`, `app.py`, `registry.py` e `migrations.py` idênticos antes e depois. `9c24800` (posterior) não revisado.
- **Parecer:** correções necessárias — 1 P1, 3 P2, 7 P3.

### Comandos e números

- Suíte estrita (`PYTHONPATH=src`, `--basetemp .pytest_cache/v070-a-review-strict`): **406 passed**, Ruff e skills ok, código 0 (a primeira execução teve 302 erros de ambiente porque `.pytest_cache` não existia no checkout de revisão; criado e repetido).
- Sondas próprias (TestClient, modelo programado, chaves e senhas geradas na sonda, banco isolado): autenticação 59/59; autorização 24/24; escopo, rate limit e MCP 15/15; migração 13/14 (diferença cosmética: aspas no `CREATE TABLE` após o rename); OpenAPI e subida 7/7; rotas pagas (P2-3).
- Mutação manual (cópia por `git archive`): **11/11 mortos** (typ, audience, issuer, leeway, revogação, corte de escopo pelo papel, sub/customer, senha, lojista na ferramenta, escopo na ferramenta, auditoria no execute). M12 a M21 não rodaram (interrompidos); identity_mismatch, rate limit, MCP por papel e escopo antes do allowlist foram re-derivados por execução direta.

### Re-derivado

1. **Autenticação:** password (lojista, operador, demo, admin) e client_credentials por formulário e Basic; serviço só com `handoff:integrate`, 600 s, sem `customer_id`; `invalid_client`/`invalid_grant` sem revelar o campo; grants cruzados recusados. Validação sem PyJWT (chave reconstruída de n/e do JWKS, RS256 PKCS1v15 com `cryptography`, `kid` = thumbprint RFC 7638, JWKS sem membros privados). **401** para: ausente, payload ou assinatura adulterados, `exp` vencido além de 30 s, `nbf` +120 s, outro `iss` (inclusive barra final), `aud` sem `merchant-assistant` ou ausente, `typ` errado ou ausente, `alg=none`, **HS256 assinado com o PEM público e com o JWK**, RS512, `kid` desconhecido ou com outra chave, sem `kid`, `jku`/`jwk` injetados, `sub` divergente de `customer_id`, papel desconhecido ou trocado, sem `jti`, sem `exp`, lixo e 9000 caracteres. Revogado: 401 em `/v1` e `/messages`. Escopo inflado em token válido é cortado pela tabela de papéis. `/v1/sessions` respondem 404 e saíram do OpenAPI.
2. **Autorização:** B recebe 404 nas rotas de A (`/conversations`, `/traces`, `/v1/conversations`, `/v1/runs`, estimativa de avaliação, continuação em `/messages` e `/v1/messages`); anônimo 401; `403 identity_mismatch`; operador, serviço e admin em `POST /messages` 403; operador e serviço em `/v1/messages` 403; `registry.execute` recusa por escopo **antes** do allowlist, recusa lojista diferente (`FORBIDDEN_CUSTOMER`) e falha fechada sem principal. 7 calls → 7 linhas de auditoria (com recusas); execução programada pela API: 10 tool calls → 10 linhas, na ordem do trace.
3. **Segredos:** `auth_accounts` só com `pbkdf2_sha256$iter$sal$hash` (7 sais distintos); nenhuma senha, segredo, token ou chave privada em banco, runtime ou log DEBUG; `hmac.compare_digest`; chave em `data/runtime/jwt/` (ignorado), nenhum PEM no repositório.
4. **Migração 0009:** 0008 → 0009 preserva demo/admin e a sessão, FK íntegra, `foreign_key_check` limpo; desce removendo merchant e mantendo demo/admin; sobe, desce a 0 e sobe de novo sem erro.
5. **Rate limit e MCP:** com limite 2, a 3ª requisição recebe 429 `rate_limited` com `Retry-After: 60` e **0 chamadas a modelo**; a janela seguinte volta a 200. MCP recusa operador, serviço, admin, demo, lixo e ausente, e deriva o lojista do token. OpenAPI com segurança Bearer JWT e exemplo token + mensagem. Valor fictício gera aviso; usuário desconhecido em `DEMO_USER_PASSWORDS` impede a subida.
6. **Mecanismo único:** um verificador (`Identity.verify`), nenhum outro `jwt.decode`, nenhum caminho por `access_key` ou `/v1/sessions`; todo `CustomerContext` por `for_principal`; única escrita em `audit_events` em `tools/base.py`.

### P1-1 — o fluxo documentado (`cp .env.example .env`) quebra o emissor

`.env.example:37` tem `JWT_PRIVATE_KEY_PATH=` vazio; `Settings` converte `""` em `Path('.')` (`config.py:30`); `Identity.key` (`identity.py:281-285`) tenta ler um diretório e lança `PermissionError`/`IsADirectoryError`, não capturado (`identity.py:414`, uso em `identity.py:399`). O compose injeta a variável vazia pelo `env_file`. Impacto: token, JWKS e qualquer Bearer → **500** no caminho do README e do avaliador; smoke falha. O teste `test_env_example_credentials_are_fictitious_valid_and_match_compose` (`tests/unit/test_identity.py:132`) não monta `Settings` a partir do arquivo. Reprodução: copiar `.env.example` como `.env`, `Settings(_env_file=".env", …)`, `create_app`, `POST /v1/auth/token` → 500; `GET /.well-known/jwks.json` → 500. Correção: vazio como `None` (ou linha comentada) e teste que monta `Settings` do `.env.example` e emite token.

### P2

- **P2-1 — `JWT_ISSUER` do `.env.example` anula o emissor do compose.** `.env.example:36` (`http://127.0.0.1:8000`) prevalece sobre `${JWT_ISSUER:-http://api:8000}` (`docker-compose.yml:41`) quando o `.env` existe; a API emitiria `iss` diferente do contrato e o ticketing (que valida `http://api:8000`) recusaria todos os tokens. Derivado da interpolação do compose; não executado (sem Docker). Correção: não definir `JWT_ISSUER` ativo no exemplo ou separar a variável do compose.
- **P2-2 — MCP verifica o token só na subida** (`cli.py:344`; `mcp_server.py:39-40` não verifica de novo): token revogado ou expirado continua autorizando tool calls. Reprodução: emitir token de lojista, montar o ambiente do MCP, revogar o `jti`; `execute("get_device_status")` seguinte → ok. Correção: verificar (decode + revogação) a cada call, com teste.
- **P2-3 — lojista alcança rotas pagas sem limite por token nem rate limit:** `/v1/comparisons` (`v1.py:1331`), `/v1/router/compare` (`v1.py:792`), `/v1/runs/{id}/evaluations` (`v1.py:1283`); `consume_demo_messages` só limita `demo` (`v1.py:899`). Com as senhas fictícias públicas, qualquer cliente local dispara comparações de até 18 células e `router/compare` ilimitado; o teto fica só no BudgetGuard. Reprodução (modelo programado): lojista estimate 200, create 202, `router/compare` 3× 201; demo com limite 1: create 429, `router/compare` 201, 429, 429.

### P3

- **P3-1:** contrato do admin em `/messages` inconsistente: 403 com mensagem "Operators and services…" (`app.py:27,115`), mas 200 em `/v1/messages`; ADR 0017 diz `customer_id` só lojista e demo, mas `identity.py:197,427-428` dão ao admin o lojista da demo.
- **P3-2:** operador e serviço leem `/v1/profiles`, `/v1/kb/documents`, `/v1/kb/versions`, `/v1/catalog/models` e `/v1/scenarios` (`v1.py:424,459,477,563,1080`); fere o mínimo privilégio (serviço só tem `handoff:integrate`).
- **P3-3:** exceção inesperada de ferramenta não deixa auditoria (`registry.py:213-217` só cobre `ToolError`, `ValidationError`, `JSONDecodeError`).
- **P3-4:** `/v1/auth/token` sem limite de tentativas (resolvido pela D19 em `dab83ab`, ainda não revisado).
- **P3-5:** `tools/scripts/run_synthetic_v040_api.py:33-34` ainda passa `api_demo_access_key`/`api_admin_access_key`, ignorados em silêncio.
- **P3-6:** README e CHANGELOG com o contrato antigo (dono: Supervisor no fechamento).
- **P3-7:** docstring de `can_read` cita D14 em vez de D13 (`app.py:103`).
- Observação: recusas por `LIMIT_REACHED` são auditadas, mas não entram no `tool_calls` do trace.

### Critérios

Comprovados por execução: CA-46 (401, `identity_mismatch`, B não lê A, N calls = N auditorias com recusas), operador/serviço → 403, lojista sem `handoff:operate`, JWKS validado de forma independente, client_credentials e `invalid_client`, rate limit sem chamada a modelo, MCP por token, nenhuma senha em texto, migração 0009 nos dois sentidos, suíte estrita com código 0. Não verificados: `docker compose config` e Docker; `ask` real; JWKS externo por rede; mutantes M12 a M21. Quebrados no ambiente documentado: emissão de token e smoke (P1-1).

### Próxima ação

Developer corrige P1-1 e P2-1 a P2-3 com teste e avalia os P3; o mesmo Reviewer revê o novo HEAD (e os mutantes M12 a M21). Decisões de contrato do Supervisor sobre P2-3, P3-1 e P3-2 na spec (D18 ampliada, D20, D21).

## Tarefa 64 e ajustes de contrato da 63 (`dab83ab`), rodada 1 — correções necessárias

- **Papel:** mesmo Reviewer do Time A, contexto frio; não leu `v070-developer.md` nem Validação e Status da 64. Independente.
- **Critérios:** tarefa 64; spec no candidato (D6, D7, D9, D10, D14, D19, tabela "Ticketing → assistente", CA-47 e CA-48 na parte da fila); plano (decisões 7 e 8, 0009); ADR 0018; contrato esclarecido da 63 (RFC 6749, `insufficient_scope`, D18, D19). D18 ampliada, D20 e D21 (posteriores) não cobertas.
- **Candidato:** `review-a` destacado em `0dc1ea5` (contém `dab83ab`), base `de3a760`; árvore limpa; sha256 de `handoffs.py`, `v1.py`, `app.py`, `migrations.py`, `escalation.py` e `cli.py` iguais antes e depois.
- **Parecer:** correções necessárias — 0 P1, 2 P2, 5 P3.

### Comandos e números

- Suíte estrita (`PYTHONPATH=src`): **422 passed**, Ruff e skills ok, código 0.
- Sondas próprias: fila pela API 30/31 (falha = P2-1); concorrência 5/5; migração 13/13; RFC 6749 e D19 15/15; CLI em processo separado 10/10; mascaramento 2/2.
- Mutação manual (cópia de `0dc1ea5`): **19/20 mortos** (`BEGIN` adiado, segunda retomada, conflito de chave ignorado, `claimed_by_other` na reivindicação e na ação, sem reivindicação implícita, ação em caso fechado, `reject`→`answered`, portão das rotas, protocolo `SIM-`, `thread_id` = conversa, recusa não auditada, retomada no replay, D19 desligado, `invalid_grant` como 401, descida mantendo `queue_state`, `simulated` no payload, reivindicação repetida gravando, replay como novo). Sobreviveu: regex da `idempotency_key` afrouxado no serviço (P3-4).

### Re-derivado

1. Encaminhamento: `status=handoff`, protocolo `^HO-\d{8}-[0-9A-F]{6}$`, sem `simulated` no JSON nem no payload; fila `open` com resumo; detalhe com rascunho, pergunta pendente, `thread_id` = `request_id` (D6), `channel=api`, `deliveries=[]`, conversa mascarada (cartão e CPF removidos).
2. Rotas de fila: lojista, admin e serviço 403 `insufficient_scope` (com `WWW-Authenticate`), anônimo 401, nas quatro.
3. Reivindicação 200, repetida `replayed: true`, outro operador `409 claimed_by_other` (reivindicação e ação); ação K → 200 `answered`; K de novo → `replayed: true` e mesmo `event_id`; outra chave → `409 already_resumed`; retomada chamada **1 vez**; chave em outro caso → `409 idempotency_conflict` sem tocar o outro caso; caso fechado → `409 case_closed`; 422 e 404 nos inválidos; auditoria em cada chamada ao serviço, inclusive recusas do serviço.
4. Concorrência real (threads com conexões próprias e barreira): 5 rodadas × 12 threads com chaves diferentes → sempre 1 vencedor, 11 `already_resumed`, 1 retomada; mesma chave em 10 threads → 1 evento, 1 retomada; 8 threads por HTTP → um 200, sete 409, 1 retomada; corrida de reivindicação com 10 threads → um dono.
5. 0009 com dados: caso pré-0009 entra `open`; UNIQUE na chave, CHECK em `queue_state`, FK de `handoff_events`; `foreign_key_check` limpo em 9 e 8; descida preserva casos e mensagens; subidas 8→9 e 0→9.
6. CLI `operator` em processo separado com `MERCHANT_ASSISTANT_TOKEN`: `list`/`show` veem o caso da API; recusa token de lojista e inválido; `act` como `op_bruno` (do token) e replay pela mesma chave; a API enxerga a ação da CLI; auditoria `operator:op_bruno`.
7. Token: `{error, error_description}` e `Cache-Control: no-store`; 400 `invalid_request`/`unsupported_grant_type`/`invalid_grant` (mensagem idêntica para senha errada e usuário inexistente); 401 `invalid_client` com `WWW-Authenticate: Basic`; D19 (limite 3): 4ª tentativa 429 com `Retry-After`, inclusive com a senha certa; outra conta no mesmo endereço não é afetada; vale para `client_credentials` e Basic. Demais rotas: `token_required`/`invalid_token` com `WWW-Authenticate: Bearer`, `insufficient_scope`. D18 (época) implementada (`LIMITED_ROLES`).

### P2

- **P2-1 — texto ainda diz simulação (D7):** `agents/personality.py:24-25` ("(simulação desta demonstração)", "(simulated in this demo)") e `personality.py:59` (`"simulated": True` nos dados entregues à Personality). Aparece na resposta ao lojista e no `transcript` do operador. Reprodução: `POST /messages` "Quero falar com um atendente humano, por favor" → `answer` termina em "(simulação desta demonstração). Protocolo: HO-…".
- **P2-2 — CLI `operator act` contorna o ponto único de retomada:** `cli.py:432` chama `handoffs.act(...)` sem `resume`, enquanto a API passa `resume_handoff` (`v1.py:1537`). A ação pela CLI consome a única retomada sem retomar o grafo; depois da 65 o caso ficaria sem entrega e qualquer nova ação `409 already_resumed`. Reprodução: `operator act <caso> --action reply …` → 200; ação pela API em seguida → 409; nenhum hook chamado. Correção: a CLI usa o mesmo ponto de retomada, com teste.

### P3

- **P3-1:** `GET /v1/handoffs` e `GET /v1/handoffs/{id}` (`v1.py:1453,1468`) não auditam, embora exponham conversas mascaradas; recusas no portão (`_operator_id`, `v1.py:1439`) também não (16 recusas, 0 linhas).
- **P3-2:** mesma chave com texto diferente devolve o registro antigo sem aviso (`handoffs.py:257-263`).
- **P3-3:** D19 por par conta@endereço deixa *spraying* livre (`v1.py:429`): 12 usuários diferentes do mesmo endereço, 12 × 400 sem 429, cada um com PBKDF2 de 600 mil iterações.
- **P3-4:** regex da `idempotency_key` no serviço (`handoffs.py:28`), única validação no caminho da CLI e do ticketing, sem teste.
- **P3-5:** casos pré-0009 entram sem `thread_id` (a 65 trata); `list_cases` com `LIMIT 100` sem paginação (`handoffs.py:138`).

### Próxima ação

Developer corrige P2-1 e P2-2 com teste e, por decisão do Supervisor, P3-1 a P3-4 (D19 e D22 na spec); P3-5 fica com a 65 e como limitação. Nova rodada do mesmo Reviewer sobre o novo HEAD, com mutante para a CLI com retomada.

## Tarefa 65, rodada 1 — correções necessárias

- **Papel:** mesmo Reviewer do Time A, contexto frio; não leu `v070-developer.md` nem Validação e Status da 65. Independente.
- **Critérios:** tarefa 65; spec no candidato (D4, D6, D8, D14, D15, "Mensagens e conversa", risco de serialização); plano (decisões 4 a 6); ADR 0018; pedidos do Supervisor (falha da retomada recuperável, casos pré-0009 recusados, texto sem simulação).
- **Candidato:** `review-a` destacado em `868a07f` (diff `0dc1ea5..868a07f`), base `f2a6b60`; árvore limpa; sha256 de `graph.py`, `handoffs.py`, `agents/*.py`, `conversations.py`, `cli.py`, `migrations.py` e `prompts/*.md` iguais antes e depois. langgraph 1.2.18, langgraph-checkpoint 4.3.1, langgraph-checkpoint-sqlite 3.1.3.
- **Parecer:** correções necessárias — 0 P1, 3 P2 (lacunas de teste em isolamento e dinheiro; auditoria apagada na subida, anterior à 65), 4 P3. Comportamento central correto em tudo o que foi executado.

### Comandos e números

- Suíte estrita (`PYTHONPATH=src`): **437 passed**, Ruff e skills ok, código 0.
- Sondas próprias: fluxo em processo 20/20; reinício e queda reais em processos novos com msgpack estrito 8/8; falhas injetadas 7/7; entrega sem consumir o limite 1/1.
- Mutação manual (cópia de `868a07f`): **16/20 mortos** (reject pulando o support, instrução ignorada, sem suspensão, suspensão em todo turno, D8 desligado, entrega sem marcar, turno sem `via=operator`, retomada como lojista (D4), `via_operator` ignorado nos estados, sem nova tentativa no replay, pendente vencida nunca retentada, falha não registrada, valor do resume ignorado, texto de simulação, `thread_id` = conversa, `not_resumable` removido). Sobreviveram: R07 (turno regravado a cada tentativa), R16 (texto do operador fora da evidência da guarda), R19 (thread interrompida no meio não continua), R20 (turno pendente entregue a qualquer conversa).

### Re-derivado

1. Checkpoint só no encaminhamento: três mensagens comuns não criam `checkpoints.sqlite3` nem constroem o grafo de revisão; o encaminhamento cria o checkpoint (thread = `request_id`, parada em `human_review` com payload `case_id`, `protocol`, `summary`, `pending_question`, `draft_reply`); texto sem simulação; checkpoint (inclusive `-wal`) sem cartão nem CPF crus nem `RunContext`/`TraceRecorder`.
2. `reply` com "R$ 1.234,56": 200, `answered`, caso `awaiting_customer`, `resume_status=done`, 1 chamada a modelo; turno `via=operator`, `operator_action=reply`, protocolo; valor e data exatos.
3. D8: próxima mensagem `route=human_reply`, `via=operator`, **0 chamadas a modelo**, entrega única; pelo `/v1/messages` também sem modelo e sem consumir o limite; `/ready` com `pending_handoffs` e `checkpoints`.
4. Mensagem nova com o caso aberto não gera `human_reply`, mantém `handoff`, não cria segunda thread; segunda ação `409 already_resumed`, um turno só.
5. Lojista B: 404 em `/v1/conversations` e na rota de demo; não recebe o turno de A nem na própria conversa já aberta; 404 ao postar na conversa de A.
6. Reinício real (subprocessos, `LANGGRAPH_STRICT_MSGPACK=true`): processo 1 encaminha; processo 2 faz `reject` e morre (`os._exit(3)`) dentro da Personality depois do commit da ação (caso `rejected`, `pending`, visível); processo 3 com a mesma chave em < 5 min → `replayed`, sem retomada dupla; processo 4 com a retomada vencida continua a thread sem repetir o Support e termina `done`; 1 turno de operador, nenhum caso novo; trace `human_review`, `support`, `get_device_status` (1×), `personality`, `output_guard`.
7. Falha injetada → `503 resume_failed`, fila `resume_status=failed` com erro; outra chave 409; mesma chave retoma até `done` com um turno; replay depois de `done` não retoma; checkpoint apagado → 503 `checkpoint_missing` visível; caso sem `thread_id` → `409 not_resumable` sem consumir nada.
8. D4 na auditoria: coberto pelo teste do candidato e confirmado pela mutação R09.
9. `prompts/escalation.v2.md` e `prompts/personality.v4.md` como arquivos novos; versões anteriores intactas.

### P2

- **P2-1 — cada subida do container apaga a auditoria:** `docker/entrypoint.sh:4` roda `bootstrap` → `seed` (`cli.py:154`), que apaga `SYNTHETIC_TABLES` (`data/seed.py:66-67`), lista que inclui `audit_events` (`data/db.py:16`). Anterior à 65 (v0.3.0), mas na v0.7.0 a auditoria é prova de segurança (CA-46, D23) e o QA reinicia o container entre encaminhar e agir (CA-48). Reprodução: processos sucessivos com `seed` → `SELECT COUNT(*) FROM audit_events` = 0.
- **P2-2 — sem teste de que o turno do operador não vaza para outra conversa:** o filtro de `pending_operator_turn` (`conversations.py:148`) não é exercitado (R20 sobrevive). Reprodução: B abre conversa, A encaminha, operador responde A, B escreve na própria conversa → candidato `clarify` (correto); mutante → `human_reply` com o texto de A.
- **P2-3 — sem teste de que valor e data do operador passam pela guarda:** remover a evidência do texto do operador (`personality.py:111`) passa na suíte (R16). Reprodução: `reply` "Seu repasse de R$ 1.234,56 cai em 28/10/2026." intacto no candidato, trocado por "Não consegui concluir a consulta agora…" no mutante.

### P3

- **P3-1:** sem teste de continuar thread interrompida no meio (`graph.py:466`, R19) e da guarda de turno único com falha depois de gravar o turno (`graph.py:473`, R07).
- **P3-2:** falha ao gravar o checkpoint em `_suspend` (`graph.py:283`) é engolida; o caso entra `open` e só falha quando o operador age, repetidamente.
- **P3-3:** retomada pendente espera 5 min (`STALE_RESUME`) sem forma de forçar; `pending_handoffs` não conta `answered` com retomada falha; checkpoints nunca podados.
- **P3-4:** desenho em dois grafos difere da letra da ADR 0018 (alinhar o texto).

### Decisão do Supervisor

P2-1 entra na v0.7.0 (D27: `audit_events` sai das tabelas recriadas pelo `seed`, com teste de que um segundo `seed` preserva a auditoria). P2-2, P2-3 e P3-1 com testes. P3-2: o caso nasce marcado (`resume_status=checkpoint_failed`, visível na fila) quando o checkpoint não grava (D28); caminho sem grafo fica como limitação. P3-3: limitação registrada. P3-4: ADR alinhada no fechamento (D25). Correções pelo Developer do Time A ativo no checkout, depois da 66 (o Developer original encerrou por contexto longo).

## Tarefas 63 e 64, rodada 2 — apto para QA

- **Papel:** mesmo Reviewer do Time A; independente (não leu `v070-developer.md`; critérios: os pareceres das rodadas 1 e a spec do candidato).
- **Candidato:** `review-a` destacado em `29f08d8` (contém `d612d30`, 63 r2, e `29f08d8`, 64 r2); diff `868a07f..29f08d8`; árvore limpa; sha256 dos 86 arquivos rastreados em `src`, `prompts`, `.env.example` e `docker-compose.yml` iguais antes e depois.
- **Números:** suíte estrita (`PYTHONPATH=src`) **462 passed**, Ruff e skills ok, código 0; sondas próprias s1–s6 passam; mutação manual **20/23 mortos**.

### Tarefa 63, rodada 2 — apto

| Achado | Situação | Confirmação |
| --- | --- | --- |
| P1-1 `.env` vazio derrubava o emissor | Corrigido | `.env.example` copiado como `.env`, `Settings(_env_file=".env")`: chave `None`; `POST /v1/auth/token` 200, JWKS 200, `/messages` com o token 200; validador `_empty_is_unset` (N01 morto) |
| P2-1 `JWT_ISSUER` do exemplo | Corrigido | Exemplo não define `JWT_ISSUER`; vale o padrão do compose (Docker não executado) |
| P2-2 MCP só na subida | Corrigido | MCP real por stdio: chamada ok, revogação do `jti` no meio, chamada seguinte `INVALID_TOKEN`; auditoria da recusa (N03 morto) |
| P2-3 rotas pagas sem limite (D18 ampliada) | Corrigido | Lojista com limite 1: comparação 429 `demo_message_limit_reached`; `router/compare` `[201, 429, 429]`; rate limit em `router/compare`, `comparisons`, `evaluations` (N09, N10 mortos) |
| P3-1 admin (D20 da época) | Corrigido | Admin em `/messages` 403 "POST /messages accepts only merchant and demo tokens." (N12 morto) |
| P3-2 leituras (D21) | Corrigido | Operador e serviço 403 em profiles, kb, catalog, scenarios, runs, comparisons e nos POST pagos; lojista e admin 200 (M18b morto) |
| P3-3, P3-5, P3-7 | Corrigidos | N11 morto; script com senhas e teste; docstring D13 |
| P3-4 | Corrigido pela D19 | Ver 64 r2 |
| P3-6 README/CHANGELOG | Pendente por desenho | Supervisor no fechamento |

Mutantes pendentes da rodada 1: M12, M14, M15, M16, M17, M19, M21 mortos; M13 não rodou (equivalente desde a D20); M18 sobreviveu e é equivalente (`operator_forbidden` redundante depois do `READER`, `v1.py:860,1162`); M20 sobreviveu (lacuna de teste; comportamento correto: `limit_reached` auditado com principal).

P3 novos: **P3-A** ligação do `authorize` por chamada na CLI (`cli.py:353`) sem teste (N02 sobreviveu; caminho real verificado); **P3-B** auditoria de `LIMIT_REACHED` (`run.py`) sem teste (M20); **P3-C** `operator_forbidden` redundante nas rotas `READER` (documentar ou remover).

### Tarefa 64, rodada 2 — apto

| Achado | Situação | Confirmação |
| --- | --- | --- |
| P2-1 texto de simulação | Corrigido (na 65) | Resposta ao lojista sem "simula" |
| P2-2 CLI sem retomada | Corrigido | `operator act` em processo separado: 1 chamada à retomada, `resume_status=done`, turno "Pela CLI" com `via=operator`; mutante C01 morto por `test_cli_act_uses_the_single_resume_point` |
| P3-1 / D23 leituras e recusas auditadas | Corrigido | 7 chamadas → 7 linhas com principal e `handoff:operate` (list, read, `case_not_found`, `invalid_state`, recusas de lojista, admin e claim); N07, N08 mortos |
| P3-2 / D22 mesma chave, outro texto | Corrigido | `409 idempotency_conflict` sem efeito; diferença só de espaços nas pontas = repetição idêntica (`replayed`); N06 morto |
| P3-3 / D19 ampliada | Corrigido | Limite 5 por endereço: contas diferentes `[400×5, 429, 429]`, janela seguinte aceita; N05 morto |
| P3-4 regex | Corrigido | H17 morto por `test_service_validates_the_idempotency_key` |
| P3-5 | Parcial | Pré-0009 `409 not_resumable` (65); `list_cases` sem paginação (limitação) |

P3 novo: **P3-D** o limite por endereço da D19 conta também logins bem-sucedidos; atrás de um único endereço (proxy ou interface no servidor), mais de 30 logins por minuto somados bloqueiam todos por até 60 s. Aceitável na demo; nota para o QA e a 67.
