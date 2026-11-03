# Passagem do Developer do Time B: v0.7.0

## Tarefa 66b, rodada 1

- Papel e responsável: Developer do Time B (subagente), despachado pelo Supervisor.
- Objetivo e critérios: [tarefa 66b](../tasks/66b-servico-ticketing.md). Serviço de ticketing próprio, conforme "Contrato entre os times" e D16 da [spec v0.7.0, versão 2](../specs/identidade-hitl-v070.md) e a [ADR 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).
- Escopo:
  - Novos: `src/merchant_assistant/ticketing/{__init__,config,signing,store,auth,outbox,service}.py`, `tests/unit/test_ticketing_units.py` e `tests/integration/test_ticketing_service.py`.
  - Só acréscimos: `pyproject.toml` (linha `"pyjwt[crypto]>=2.10",` depois de `"mcp>=2.3",`), `docker-compose.yml` (bloco `ticketing` e volume `ticketing_runtime`) e `.env.example` (bloco "Ticketing service" no fim).
  - Também a tarefa 66b e esta passagem.
  - Intocados: `api/`, `orchestration/`, `agents/`, `tools/`, `data/migrations.py`, `cli.py`, `config.py`, `mocks/` e o Dockerfile.
- Estado: implementação concluída pelo Developer; em andamento até a revisão.
- Branch e PR: `codex/v0.7.0-ticketing` no worktree `C:\workspace\ai-getnet-case-wt\time-b-v070`, sem PR, sem push.
- Base e versão final: base `fe9d12b`; commits `103bca4` (pacote e testes), `7af123a` (pyproject, compose e `.env.example`) e o commit de documentação que traz esta passagem.
- Independência: não-independente (relato do autor).

### O que o serviço faz

- **Receptor** `POST /webhooks/assistant`:
  - Verifica `X-Signature` com `TICKETING_WEBHOOK_SECRET` (HMAC-SHA256 de `"<t>.<corpo>"`, janela de 300 s nos dois sentidos, aceita mais de um `v1` para rotação). Falha → `401 invalid_signature`.
  - `id` já recebido → `200 {"status": "duplicate"}`, sem efeito novo.
  - `handoff.created` cria o ticket `new` com todos os campos do contrato, inclusive a transcrição.
  - `conversation.replied` grava a resposta entregue (`reply_text`, `reply_delivered_at`) e um evento no histórico.
  - `handoff.closed` grava `closed_at` e `closed_by`.
- **API do operador**, todas as rotas com `Bearer`: `GET /tickets?status=`, `GET /tickets/{id}` (caso, histórico e entregas nos dois sentidos com as tentativas), `POST /tickets/{id}/assign`, `POST /tickets/{id}/actions` e `POST /tickets/{id}/solve`.
- **Validação do JWT:**
  - Exige RS256, `typ` `at+jwt`, `kid` presente no JWKS de `ASSISTANT_JWKS_URL` (cache; `kid` desconhecido recarrega, no máximo uma vez a cada 5 s).
  - Confere `iss` = `ASSISTANT_ISSUER`, `aud` contendo `ticketing`, `exp`/`nbf`/`iat` com tolerância de 30 s, `role=operator`, `sub` = `operator:<id>` e escopo `handoff:operate`.
  - Falha de token → `401 invalid_token`; papel ou escopo → `403 insufficient_scope`, ambos com `WWW-Authenticate`.
- **Envio ao assistente:**
  - Cada ato vira um envelope `{id, type, created_at, data}` gravado na caixa de saída e enviado a `POST {ASSISTANT_URL}/v1/integrations/ticketing/events` com `X-Webhook-Id`, `X-Webhook-Event`, `X-Signature` (`ASSISTANT_WEBHOOK_SECRET`) e `Authorization: Bearer`.
  - O token `client_credentials` é obtido em `/v1/auth/token`, reaproveitado e renovado 60 s antes de expirar ou após um `401`.
  - Campos de `data`: `ticket_id`, `case_id` e `operator_id`. Em `ticket.action`, também `action`, `text` e `idempotency_key` (esta repassada sem alteração).
  - O ticket só muda de estado com a resposta `2xx` do assistente, e grava `case_state` e `queue_state`.

### Decisões além do texto da tarefa

1. **Tentativas:** a 1ª é síncrona, na própria requisição da tela. As seguintes, depois de 1 s e 2 s (`TICKETING_WEBHOOK_RETRY_WAITS_S`), vêm de um laço em segundo plano (`TICKETING_OUTBOX_POLL_S`, 1 s). Falha de rede, timeout de 3 s, `5xx` ou `429` mantêm o envio pendente; a API responde `202` com `delivery.status = "pending"`, que a tela mostra como "envio pendente". Após 3 tentativas o envio fica `failed`. Uma lease no registro impede que a requisição e o laço enviem o mesmo evento ao mesmo tempo.
2. **Reenvio após `failed`:** repetir a mesma `idempotency_key` recoloca na fila **o mesmo evento**, com o mesmo `id`, para o assistente deduplicar. `assign` e `solve` não têm chave, então um novo clique cria um evento novo.
3. **Um envio pendente por ticket:** um ato novo enquanto outro está pendente → `409 delivery_pending`. Isso preserva a ordem dos eventos.
4. **Idempotência local:** mesma chave com o mesmo conteúdo devolve o registro (`replayed: true`) sem novo evento. Mesma chave com outro conteúdo ou outro ticket → `409 idempotency_key_reused`. Ticket `solved` → `409 ticket_solved`.
5. **Erros do assistente:** `404`, `409` e `422` voltam com o mesmo código e o mesmo corpo. `401`, `403` e outros `4xx` indicam credencial do serviço, não erro do operador, e viram `502 assistant_rejected` com `upstream_status`.
6. **Ação sobre ticket `new`** é permitida (D9: reivindicação implícita no assistente). O histórico então passa direto de `new` a `pending`.
7. **Receptor:** `conversation.replied` ou `handoff.closed` de um caso sem ticket → `404 ticket_not_found`, sem registrar o `id`, para que uma nova tentativa do assistente funcione depois. `handoff.created` repetido para o mesmo `case_id` com outro `id` não cria segundo ticket. Tipo desconhecido → `422 unknown_event`. `X-Webhook-Id` diferente do `id` → `400`. Segredo vazio → `503`, e o serviço não envia nada.
8. **Formato de erro** `{"error": {"code", "message"}}`, igual ao `api/v1`.
9. **Compose:**
   - Volume próprio `ticketing_runtime` montado em `/app/runtime`, diretório que a imagem já cria com dono `app`; o banco fica em `/app/runtime/ticketing.sqlite3`. Montar em outro caminho criaria diretório do root sem permissão de escrita, e o Dockerfile não estava na lista de arquivos permitidos.
   - Healthcheck próprio em `:8002/health`, porque o da imagem olha a `:8000`.
   - Sem `depends_on`: o JWKS e o token são buscados sob demanda.
10. **Banco sem efeito no import:** importar `service.py` não cria o banco. A conexão é preguiçosa, e há teste para isso.

### Perguntas ao Supervisor (lacunas do contrato; não inventei comportamento do assistente)

1. **Valores padrão dos segredos no compose.** O bloco `api` (Time A) e o bloco `ticketing` precisam usar os mesmos padrões fictícios para `TICKETING_WEBHOOK_SECRET`, `ASSISTANT_WEBHOOK_SECRET` e `TICKETING_CLIENT_SECRET`; senão `docker compose up` sem `.env` não integra. Usei `ticketing-webhook-secret-fictitious`, `assistant-webhook-secret-fictitious` e `ticketing-client-secret-fictitious`; o contrato não fixa esses valores. As mesmas variáveis podem aparecer também no bloco do Time A no `.env.example`. Peço que o contrato fixe os valores ou que a integração alinhe os dois blocos.
2. **`operator_id` nos eventos.** Li "`service:ticketing` agindo em nome de `operator:<id>`" e "`422 unknown_operator` se `operator_id` não for operador ativo" como `operator_id` = `op_ana`, ou seja, o `sub` sem o prefixo `operator:`. Se o assistente esperar `operator:op_ana`, basta mudar uma linha em `auth.py`.
3. **Corpo de erro do assistente.** O contrato fixa só os códigos (`claimed_by_other`, `already_resumed`, `unknown_operator`), não o formato do corpo. Repasso o corpo sem alteração. O assistente falso usa `{"error": {"code": ...}}`, mas a tela da tarefa 67 deve ler o formato real do Time A.

### Evidência

- Testes novos: 5 unitários (arquitetura, fórmula e janela da assinatura, configuração, import sem efeito) e 26 de integração com parâmetros, 31 no total.
- `docker compose config --quiet` → código 0, sem `.env` no worktree.
- `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v070-b-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → código 0, 380 aprovados (349 da base + 31), ruff limpo, estrutura e skills válidas.
- Duas falhas antes da execução final, corrigidas:
  1. Com `from __future__ import annotations`, o `Annotated[..., Depends]` definido dentro de `create_app` virava parâmetro de query. As rotas de ticket aceitavam requisição sem token, e 8 testes negativos falharam. A dependência foi para o nível do módulo, e um teste novo cobre token obrigatório nas 5 rotas.
  2. O teste de janela a +301 s era instável com a máquina carregada. A margem do teste de integração passou a ±330 s; a fronteira exata continua no teste unitário.
- Ambiente: `.venv` do worktree, PyJWT 2.15.1, cryptography 50.0.2; `merchant_assistant` resolve para `time-b-v070\src`. Nenhuma chamada paga, sem rede externa (assistente falso por `httpx.MockTransport`), sem Docker up.

### Critérios

- Comprovados localmente: CA-47 e CA-48 do lado do ticketing; recusas de assinatura e JWT com `401`/`403`; assistente fora do ar sem exceção, com tentativas registradas; teste de arquitetura; compose válido; suíte estrita com código 0.
- Não verificados: integração com o assistente real do Time A (tarefas 63, 64, 65 e 66, depois 68), Docker em execução e a tela da tarefa 67.

### Limitações

- O ticketing não sabe de revogação (`jti` revogado no assistente): aceita o token do operador até expirar. O assistente continua checando o operador em cada evento (`422 unknown_operator`).
- O laço de tentativas roda dentro do processo (uma réplica). Com mais réplicas, a lease no SQLite evita envio duplo, mas o banco é local ao container.
- `ASSISTANT_*` no `.env.example` também chegam ao `api` pelo `env_file`, sem efeito nele.

### Ação externa e próxima ação

- Ação externa: nenhuma (sem push, sem PR). Commits locais com `lauroPereira <lauro.s.pereira@gmail.com>`, identidade conferida.
- Próxima ação: Reviewer independente da 66b. O Supervisor responde às três perguntas acima, e a tela da tarefa 67 consome a API acima.

### Atualização do contrato de identidade (spec `9c24800`), ainda na rodada 1

Pontos aplicados por aviso do Supervisor, sem merge da spec. Commit `feat(ticketing): follow the updated identity contract`.

- **API do ticketing:** os erros usam o envelope do assistente, `{"error": {"code", "message", "request_id"}}`, com `request_id` por requisição (também no cabeçalho `X-Request-Id`).
  - Sem token → `401 token_required`.
  - Token inválido, expirado, de outro emissor ou audiência, adulterado ou com `kid` desconhecido → `401 invalid_token`.
  - Papel ou escopo → `403 insufficient_scope`.
  - Todos com `WWW-Authenticate: Bearer` (acrescido de `error=…`, conforme RFC 6750).
- **Token de serviço:**
  - Os erros RFC 6749 §5.2 de `/v1/auth/token` (`invalid_client` e semelhantes) viram rejeição de configuração: `502 assistant_rejected`, sem mudar o ticket.
  - `429` deixa o ato pendente e a próxima tentativa espera pelo menos o `Retry-After` numérico.
  - O serviço continua mandando o segredo no formulário (o contrato aceita formulário ou `Basic`).
- **Eventos ao assistente:**
  - `429` com `Retry-After` é respeitado da mesma forma.
  - Um `401` só renova o token de serviço quando o código é `token_required` ou `invalid_token`; `401 invalid_signature` vira rejeição direta.
- **Assistente falso:** responde nos formatos novos e aceita o segredo também em `Basic`.
- **Testes novos:**
  - `test_token_endpoint_errors`: `invalid_client` → 502; `429` espera o `Retry-After`.
  - `test_assistant_rate_limit_waits_retry_after`.
  - `test_service_can_obtain_the_token_with_basic_auth_too`: conformidade do falso.
  - Os negativos de JWT passaram a conferir `token_required`/`invalid_token`/`insufficient_scope` e o `request_id`.
- **Pergunta 3:** está respondida pelo contrato. O repasse de `404`, `409` e `422` com o mesmo código e corpo continua; o corpo agora é o envelope `{"error": {...}}` do assistente.
- **Suíte estrita** (`--basetemp .pytest_cache/v070-b-strict`): código 0, 383 aprovados (380 + 3), ruff limpo.
