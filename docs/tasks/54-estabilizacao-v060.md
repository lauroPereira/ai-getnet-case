# Tarefa: estabilização e contratos da v0.6.0

## Objetivo

Corrigir as pendências que afetam orçamento, integridade e funcionamento demonstrável, e registrar as demais como risco aceito, antes das funcionalidades novas.

## Especificação relacionada

[Spec v0.6.0, bloco E](../specs/fechamento-v060.md#e-estabilização), [plano](../specs/fechamento-v060-plano.md), [tarefa 46](46-pendencias-revisao-v050-r2.md) e [tarefa 48](48-diagnostico-timeout-chat-ui-v050.md).

## Pré-condições

- Branch `codex/v0.6.0-fechamento` nos dois repositórios, a partir das mains com a v0.5.0.
- Sem chamada paga, commit ou push. Ledgers reais, `.limit` gravados e coleções existentes não são tocados.

## Arquivos prováveis

`orchestration/budget.py`, `rag/kb.py`, `orchestration/graph.py`, `cli.py`, `main.py`, `docker-compose.yml`, `api/v1.py` (limite por sessão), web `src/getnet_web/api.py`, `pyproject.toml` do web e testes.

## Passos

1. R2-01: gravar o teto com representação exata ou comparar com tolerância; a primeira montagem nunca recusa o próprio valor.
2. R2-02: publicar o `.limit` de forma atômica, sem sobrescrever um existente.
3. R2-03: prontidão e captura em caminho somente leitura quando o registro da base existe.
4. R2-05: timeout explícito de 30 s no cliente OpenAI do CLI.
5. R2-07: remover `BudgetGuard.record`/`record_embedding` se não houver chamador, ajustando o teste.
6. R2-08: testes de `max_retries == 0` nos três clientes reais (sem rede) e de ativação/retorno com manifesto sem `chunks`/`point_digest` e coleção vazia.
7. Timeout do cliente web para `POST /v1/messages` coerente com `MAX_REQUEST_SECONDS` mais margem, configurável; GET continua curto; recuperação por GET preservada.
8. Compose publica a API só em `127.0.0.1:8000`.
9. Limite configurável de mensagens por sessão demo, recusado no backend com erro claro e testado.
10. Ambiente web com Ruff disponível para o script estrito (dependência de desenvolvimento ou instrução), sem duplicar ambientes.
11. R2-04 registrado como risco aceito no plano/resultado, sem mudança de código.

## Critérios de conclusão

- [ ] Cada correção tem regressão sintética que falha antes e passa depois.
- [ ] Nenhum teto gravado alterado; montagem concorrente não falha.
- [ ] `POST /messages` legado, MCP e contratos `/v1` existentes inalterados.
- [ ] Validação estrita backend e web com código 0; nenhuma chamada paga.

## Validação

- R2-01: teto gravado com `repr(float)` (round-trip exato); regressão `test_first_mount_accepts_its_own_ceiling_and_remounts_with_the_same_value` (1/3, 0.1+0.2, 15 dígitos).
- R2-02: publicação atômica (temporário no mesmo diretório + `os.link`, sem sobrescrever); `test_concurrent_first_mounts_never_see_a_partial_ceiling` (40 rodadas × 8 threads, zero falhas) e `test_an_existing_ceiling_is_never_overwritten`.
- R2-03: `KnowledgeBase.bootstrap` sai por leitura quando documentos e versão ativa existem; `test_capture_and_readiness_do_not_need_the_write_lock_after_registration` (outro escritor segura `BEGIN IMMEDIATE`; captura e `/ready` concluem em < 3 s).
- R2-05/R2-08a: `timeout=30` no cliente OpenAI do CLI; `main.deepseek_client` extraído; `test_real_provider_clients_disable_sdk_retries_and_set_explicit_timeouts` cobre os três clientes sem rede.
- R2-07: `BudgetGuard.record`/`record_embedding` removidos (sem chamadores em `src/`); teste antigo ajustado e `test_budget_guard_has_no_direct_spending_entry_points`.
- R2-08b: `test_activation_with_legacy_manifest_and_empty_collection_is_refused` e `test_rollback_to_legacy_manifest_with_empty_collection_is_refused` (regressão do comportamento já correto).
- Contra o código da `main` (`git archive HEAD`, cópia no scratchpad): 10 dos 14 testes novos falham e os 4 de regressão de comportamento existente passam, como esperado.
- Timeout web: 105 s (`BACKEND_MESSAGE_TIMEOUT_SECONDS`, 90 s + margem) para mensagem, comparação de Routers, avaliação, build e teste de candidata; 20 s (`BACKEND_TIMEOUT_SECONDS`) para leituras; `test_paid_operations_get_the_long_timeout_and_reads_stay_short`. Recuperação por GET preservada (testes existentes de recuperação passam).
- Compose: API em `127.0.0.1:8000`; `test_compose_publishes_the_api_only_on_loopback`.
- Limite por sessão demo: `DEMO_SESSION_MESSAGE_LIMIT` (20) e coluna `api_sessions.message_count` (migração 0008); `test_demo_session_limit_is_enforced_by_the_backend` (429 antes de qualquer chamada ao modelo; admin sem limite; nova sessão recomeça).
- Ruff no ambiente web: `ruff>=0.17,<1` no extra `test`, `ruff==0.17.2` instalado em `.venv-v040`; o script estrito web passou a ignorar `.venv*`. Os dois scripts estritos ignoram `.pytest_cache` e `_tmp` (o backend falhava com arquivos de QA de rodadas anteriores em `.pytest_cache`).
- R2-04: risco aceito, sem mudança de código (registrado na passagem e na preparação do QA).
- Campanha `v060-qa`: `FixedBudgetGuard` aceita até US$0,50 (plano aprovado); `test_campaign_cap_accepts_the_approved_half_dollar_once`.

Validação estrita backend (`PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v060-dev-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`): **326 passed**, Ruff "All checks passed!", estrutura e skills válidas, código 0. Web (`.venv-v040/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`): **30 passed**, Ruff sem achados, código 0. Nenhuma chamada paga, chave de provedor ou build Docker. Passagem: [v060-developer.md](../evidence/v060-developer.md).

## Status

```text
concluída
```

Revisada (Reviewer, rodadas 1–5) e validada no QA real da v0.6.0 (rodada 2, candidato r5); ver [resultado](../evidence/v060-resultado.md).
