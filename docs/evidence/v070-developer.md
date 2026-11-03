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
