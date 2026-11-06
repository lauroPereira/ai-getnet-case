# Tarefa 84 — Comparação retomável após reinício

## Objetivo

Uma comparação de perfis interrompida por reinício da API não vira `failed`: fica `interrupted`, preserva as células concluídas e pode ser retomada pela API, executando só o que falta e sem pagar duas vezes.

## Especificação relacionada

[Rubrica `judge.v4` e operação v0.10.0](../specs/rubrica-operacao-v0100.md): D3, D6, CA-58; especificação 0.2 RF-104. Código: `src/merchant_assistant/comparisons.py` (`start`, `_run`, `_save`, `_alive`, `read`), tabela `comparisons` (`data/migrations.py`, `CHECK` do `state`), `api/v1.py` (rotas de comparação), `api/app.py` (`lifespan`).

## Pré-condições

Tarefa 83 commitada (não precisa estar revisada). Nenhuma chamada paga: testes com modelo programado.

## Arquivos prováveis

`comparisons.py`, `api/v1.py` (rota nova `POST /v1/comparisons/{id}/resume`, só por acréscimo), `api/app.py` (`lifespan`: marcar `interrupted`), `data/migrations.py` (migração 0012 reversível só se o `CHECK` impedir o estado novo), `docs/contracts/` se houver contrato de comparação, testes de integração com reinício simulado (novo `TestClient` sobre o mesmo runtime).

## Passos

1. **Estado `interrupted`.** Se o `CHECK` da coluna `state` não aceitar, migração 0012 reversível que amplia o `CHECK` (recriação da tabela), testada nos dois sentidos; `read()` deixa de marcar `failed` uma comparação `running` sem thread viva: marca `interrupted` e preserva `cells`.
2. **Startup.** No `lifespan`, toda comparação `running` vira `interrupted` (nenhuma thread sobrevive ao processo); log estruturado com o id.
3. **Retomada.** `POST /v1/comparisons/{id}/resume` (mesmas regras de principal da leitura; idempotente: `resume` de uma `running` ou `completed` devolve `409` com código claro): relê `config` e `cells`, pula células com `request_id` (resultado gravado), reserva orçamento só para as restantes com o mesmo `estimate` por célula, roda na thread como `start`, e no fim calcula `completed`/`partial`/`failed` como hoje. Uma célula que já tinha falhado (`status=failed`) é reexecutada só se `?retry_failed=true`.
4. **Custo.** O `cost_usd` acumula; nenhuma célula com `request_id` gera nova chamada (teste com contador de chamadas do modelo programado).
5. **Contrato.** `GET /v1/comparisons/{id}` passa a poder devolver `interrupted`; OpenAPI e `docs/contracts/` atualizados por acréscimo; a interface web (projeto irmão) não muda nesta versão: `interrupted` é exibido como está.
6. **Testes:** interrupção simulada (marcar `running` e abrir novo app sobre o runtime → `interrupted`), retomada completa, retomada idempotente, `retry_failed`, célula concluída não reexecutada (contador), migração 0012 ida e volta se existir.

## Critérios de conclusão

- Comparação `running` sem processo vivo aparece `interrupted` com as células preservadas.
- `resume` termina `completed` sem reexecutar células com resultado; ledger coerente.
- Suíte estrita verde; `checar-caminhos-pessoais.py` limpo.

## Validação

Developer, 2026-11-05, branch `codex/v0.10.0-rubrica-operacao`, base `f4dfb97`. Commits `4b6891b` (migração 0012), `b6f7e19` (retomada), `ee7774a` (contrato). Tudo com modelo programado, embedder de hash, Qdrant em memória e SQLite temporário; nenhuma chamada paga, `.env` não lido.

- **Migração 0012** (`comparison_interrupted`): o `CHECK` original não aceitava `interrupted`, então a tabela `comparisons` é recriada com o `CHECK` ampliado. O rollback converte `interrupted` em `failed` e restaura o `CHECK` anterior. Testes `test_0012_accepts_interrupted_and_still_refuses_unknown_states` e `test_0012_round_trip_turns_interrupted_into_failed_and_keeps_every_row` (ida, volta e ida de novo, linhas e índice preservados, `integrity_check` ok). Esquema 12, reportado em `/ready` (asserções de versão e listas de passos dos testes de migração seguem o 12).
- **Interrupção e reinício** (`tests/integration/test_v0100_comparison_resume.py`, 4 testes): a comparação roda de verdade até a segunda execução nova; depois disso nada mais do thread chega ao banco, como depois de um `taskkill`. Um app novo (orquestrador e modelo programado novos) sobre o mesmo runtime, com `lifespan`, marca `interrupted` antes de qualquer leitura e registra um log estruturado com o id. A célula concluída fica preservada; as três restantes ficam `pending`; a tentativa em curso fica em `interrupted_attempts` com o custo do ledger.
- **Retomada completa:** `POST /v1/comparisons/{id}/resume` → `202 {resumed_cells: 3}`, estado final `completed` com as 4 células. Só as três células sem resultado executam, e todas as chamadas do modelo programado depois do reinício acontecem dentro delas. A célula concluída e a tentativa interrompida mantêm exatamente as linhas de ledger que tinham. O ledger só ganha os três `request_id` novos, e o `cost_usd` acumula.
- **Idempotência e regras de dono:** `409 comparison_running` com o thread vivo (e um app novo no mesmo processo não marca essa comparação); `409 comparison_completed` depois do fim; `404` para id ausente e para outro principal; `401` sem token.
- **`retry_failed`:** comparação `partial` com uma célula `failed`. Sem o parâmetro → `409 nothing_to_resume`; com `?retry_failed=true` → só aquela célula roda (o `request_id` anterior vai para `previous_request_ids`), as concluídas mantêm o `request_id` e o estado final é `completed`.
- **Orçamento só do que falta:** com três células faltando, um orçamento restante abaixo de 3 × teto por célula dá `429 installation_budget_exceeded`; exatamente 3 × teto basta. Prompts diferentes dos da configuração dão `409 fixed_factors_changed`, e as recusas não mudam o estado.
- Testes focados: `test_v0100_comparison_resume.py`, `tests/unit/data/test_migrations.py` e `test_v1_api.py` com **49 passed**. Vizinhos (`test_v060_api`, `test_v060_r2`, `test_v060_r4`, `test_v070_identity_r2`, `test_use_cases`, `test_v070_story`, `test_v070_webhooks`): verdes depois da correção da lista de passos de `test_migration_0006_round_trip_preserves_legacy_synthetic_records`.
- OpenAPI (gerado pelo FastAPI): `/v1/comparisons/{comparison_id}/resume` com `retry_failed`, `202`/`409`/`422` e `SessionBearer`; 37 caminhos.
- `checar-caminhos-pessoais.py`: nenhuma ocorrência em 766 arquivos.
- Suíte estrita: `python tools/scripts/lint_and_tests.py --strict` (`.venv`) no HEAD `ee7774a`, com `basetemp` no scratchpad da sessão: **2121 passed, 1 skipped** (2115 da tarefa 83 + 6 novos) em 945,84 s; ruff `All checks passed!`; caminhos pessoais limpos; "Validação estrita concluída sem falhas", exit 0, 971 s no total.

## Status

Implementada pelo Developer em 2026-11-05; aguarda revisão independente e o QA real da D6 (CA-58 com `taskkill`). Critérios de aceite da spec não marcados (cabe ao Supervisor).
