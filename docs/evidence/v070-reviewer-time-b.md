# Reviewer v0.7.0 (Time B)

Pareceres do Reviewer independente do Time B sobre as tarefas da v0.7.0. Gravado pelo Supervisor a partir do relatório do Reviewer (que não tem escrita).

## Tarefa 66b, rodada 1 — correções necessárias

- **Papel:** Reviewer em contexto frio; não leu `v070-developer-time-b.md` nem diagnóstico do Supervisor. Independência parcial declarada: a leitura do arquivo da tarefa trouxe Validação e Status antes do parecer; todas as afirmações centrais foram re-derivadas com comandos próprios.
- **Critérios:** `docs/tasks/66b-servico-ticketing.md`, contrato da spec em `3ccde8d` (Identidade, Webhooks, Serviço de ticketing, D16, CA-47, CA-48), ADRs 0017 e 0018.
- **Candidato:** worktree `time-b-v070`, branch `codex/v0.7.0-ticketing`, HEAD `cffb0993e9150f3f9d7ce63eeff95856300e5c9e`, base `fe9d12b`; HEAD e `git status` iguais antes e depois.
- **Parecer:** correções necessárias — 1 P1 (configuração), nenhum P2, 7 P3. O código atende o contrato em tudo o que foi executado.

### Comandos e números

- `merchant_assistant` importa do `src/` do worktree; PyJWT 2.15.1; Python 3.13.3.
- Suíte estrita (`--basetemp .pytest_cache/v070-b-review-strict`): **383 passed**, nenhum pulado, Ruff limpo, estrutura e skills válidas, código 0.
- `docker compose config --quiet` numa cópia sem `.env`: código 0; `ticketing` em `127.0.0.1:8002`, `uvicorn merchant_assistant.ticketing.service:app`, volume `ticketing_runtime`. Docker não subido.
- Diff contra `fe9d12b`: só acréscimos em compose, `.env.example` e `pyproject.toml` (linha `pyjwt[crypto]>=2.10` idêntica à da branch da versão); nenhum arquivo do Time A tocado.

### Re-derivado

1. **Isolamento:** importação num processo novo traz só `merchant_assistant` (com `__version__`) e `ticketing.*`; nenhum `importlib`/`__import__`/import do assistente fora do pacote; banco não criado na importação; nenhum mecanismo equivalente no assistente.
2. **Webhooks recebidos** (recusas sem nenhuma linha gravada): sem cabeçalho, segredo errado, `t` a ±301 s, só `v0=`, corpo alterado → `401 invalid_signature`; `t` a −290 s aceito; mesmo `id` com outro corpo → `200 duplicate` sem efeito; `X-Webhook-Id` diferente do corpo ou JSON inválido → `400` sem efeito; `hmac.compare_digest` (`signing.py:28`).
3. **JWT do operador:** `401 invalid_token` com `WWW-Authenticate: Bearer` para `alg=none`/`None`, HS256 com o PEM público, `kid` desconhecido, lojista, serviço, admin, outro emissor, expirado há 31 s, `nbf`/`iat` +120 s, sem `exp`, lixo; expirado há 20 s aceito (tolerância de 30 s); `403 insufficient_scope` sem `handoff:operate`, `sub` `operator:` vazio, `role=operator` com `sub` de lojista; sem token ou `Basic` → `401 token_required`; `request_id` no envelope; `kid` novo recarrega o JWKS; vinte `kid` desconhecidos em 5 s não geram busca extra (limite de frequência).
4. **Ciclo e caixa de saída:** `409 claimed_by_other` deixa o ticket idêntico byte a byte; `already_resumed` repetido com a mesma chave → `409` sem novo POST; chave de outro ticket → `409 idempotency_key_reused`. Concorrência: 10 POSTs simultâneos com a mesma chave → 1 envio; 10 chaves diferentes → 1 envio e `409` nos demais; 8 `dispatch_due` concorrentes → 1 envio. Token `client_credentials` renovado aos 541 s (600 − 60 de margem) e após revogação.
5. **Mutação manual (cópia isolada):** 19/20 mortas (janela, compare, deduplicação, audiência, emissor, escopo, papel, `typ`, tolerância, recarga por `kid`, renovação em 401, busy, passthrough, tentativas, `Retry-After`, fingerprint, 409 alterando o ticket, `WWW-Authenticate`, chave repassada). Sobreviveu a remoção do lease em `store.claim` (e a da checagem redundante de `alg`, ainda protegida por `jwt.decode(algorithms=["RS256"])`).

### P1-1 — `TICKETING_CLIENT_SECRET` diverge do contrato `3ccde8d`

`docker-compose.yml:57` (`${TICKETING_CLIENT_SECRET:-ticketing-client-secret-fictitious}`) e `.env.example:44` usam `ticketing-client-secret-fictitious`; o contrato e o bloco `api` da branch da versão fixam `ticketing-demo-secret-fictitious`. Impacto: com `docker compose up` sem `.env`, `client_credentials` → `invalid_client`, cada ato vira `502 assistant_rejected` e a caixa de saída fica `rejected` sem novas tentativas (CA-47 falha no Docker); no merge, o `.env.example` teria a chave duas vezes com valores diferentes. Os outros valores fixados conferem. Reprodução: `docker compose config` numa cópia sem `.env`. Correção: valor do contrato no compose; no `.env.example`, não repetir a chave que a branch da versão já define.

### P3

1. Lease da caixa de saída sem teste (mutação de `store.py:386-388` sobrevive; comportamento correto verificado).
2. `alg=none` e HS256 com a chave pública sem teste próprio (`auth.py:87`).
3. Resposta malformada do assistente: token `200` com corpo não JSON (`auth.py:152-153`) → API `500`, evento preso pelo lease (~14 s) e próximo ato `409 delivery_pending`; evento `200` com JSON que não é objeto → `_apply` (`store.py:489`) levanta exceção, a transação reverte depois que o assistente aceitou e o evento é reenviado em laço.
4. `WWW-Authenticate` sem credencial sai `Bearer error="token_required"` (`service.py:49`); a RFC 6750 §3.1 pede nenhum código de erro nesse caso, e o assistente o omite.
5. Chave removida do JWKS continua aceita até reiniciar (`auth.py:71-80`); token de operador revogado segue válido para leitura (`GET /tickets`, com transcrições) até expirar (≤ 60 min); atos passam pelo assistente. Limitação do JWT sem estado a documentar.
6. Fingerprint de idempotência sem o operador (`service.py:184`): `op_bruno` repetindo a chave de `op_ana` no mesmo ticket recebe `200 replayed` com o registro dela.
7. `handoff.closed` não leva o ticket a `solved` (`store.py:194-206`); coerente com o contrato atual, observação para o QA.

### Critérios

Comprovados: CA-47 e CA-48 do lado do ticketing (assistente falso), recusas 401/403, assistente fora do ar (`202`, tentativas, `failed`, reentrega), isolamento, `docker compose config`, suíte estrita. Não verificados: integração com o assistente real (68), Docker, recarga do JWKS com o intervalo padrão de 5 s.

### Efeito colateral registrado pelo Reviewer

No scratchpad compartilhado, apagou `scratchpad\mut` (que outro papel usava) e pode ter sobrescrito `scratchpad\strict.log` e `scratchpad\compose\docker-compose.yml`. Nada fora do scratchpad foi tocado.

### Próxima ação

Developer do Time B corrige P1-1 e, por decisão do Supervisor, também P3-1, P3-3, P3-4 e P3-6; P3-5 vira limitação documentada; P3-2 com teste se barato. O mesmo Reviewer revê o diff de correção e o `docker compose config`.

## Tarefa 66b, rodada 2 — apto para QA

- **Papel:** mesmo Reviewer da rodada 1; não leu a passagem atualizada do Developer.
- **Candidato:** branch `codex/v0.7.0-ticketing`, diff `d505760..e674041` (`.env.example`, `docker-compose.yml`, `ticketing/auth.py`, `outbox.py`, `service.py`, testes de integração); HEAD e árvore iguais antes e depois.
- **Parecer:** apto para QA — sem P1 nem P2; 4 P3 novos.

### Comandos e números

- Suíte estrita (`--basetemp .pytest_cache/v070-b-review-r2-strict`): **393 passed** (eram 383), nenhum pulado, Ruff limpo, código 0.
- `docker compose config --quiet` numa cópia sem `.env`: código 0; `ticketing` resolve `TICKETING_CLIENT_SECRET: ticketing-demo-secret-fictitious`.
- Integração simulada com a branch da versão (`f2a6b60`) por `git merge-file`, sem escrever no Git: compose mescla sem conflito e passa em `docker compose config` com o mesmo segredo em `api` e `ticketing`; `.env.example` tem conflito textual só por acréscimos no fim, resolvido mantendo os dois blocos (uma única `TICKETING_CLIENT_SECRET=ticketing-demo-secret-fictitious`).
- Mutação, rodada 2: 8/10 mortas (sobreviveram `alg-header-off`, redundante, e `broad-except-off`).

### Rodada 1

P1-1 resolvido (valor do contrato no compose, `.env.example` sem repetir a chave); P3-1 resolvido (teste do lease mata a mutação; 10 com a mesma chave → 1 POST; 8 `dispatch_due` → 1 POST); P3-2 resolvido (`alg=none` e HS256 com o PEM público → `401 invalid_token`, com teste); P3-3 resolvido (token `200` não JSON → `502 service_token_malformed`, linha `rejected` sem reenvio; evento `200` com lista → `502 assistant_malformed_response`); P3-4 resolvido (`WWW-Authenticate: Bearer` sem código quando falta credencial); P3-6 resolvido (`op_bruno` com a chave de `op_ana` → `409 idempotency_key_reused`). P3-5 e P3-7 seguem registrados.

### P3 novos

1. Caminho `delivery_error` (`outbox.py:96`, `except Exception`) sem teste.
2. Comentário em `service.py:32-37` preso a `LOCAL_DELIVERY_ERRORS` quando descreve `PASS_THROUGH`.
3. `2xx` sem o corpo do contrato vira `rejected` final mesmo que o assistente tenha aplicado o evento (borda fora do contrato; a mensagem orienta atualizar).
4. Conflito trivial de `.env.example` no merge com a branch da versão (manter os dois blocos).
