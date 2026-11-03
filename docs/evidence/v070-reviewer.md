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
