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

### Rodada 2 (correções do [parecer da rodada 1](../evidence/v0100-reviewer-t84.md))

Developer, 2026-11-05, mesma branch, base `5d1ea89`. Commits `873007c` (OpenAPI da rota, P3-3), `c097f90` (registro da thread, P2-1, P2-2, P2-3, P3-1, P3-2) e `205336b` (teste da checagem de vida antiga). Tudo offline, com o modelo programado; nenhuma chamada paga, `.env` não lido.

- **P2-1:** a thread que termina tira do registro só a própria entrada (`_release` compara a identidade) e só depois de gravar o estado final. O `resume` recusa com `409 comparison_running` sempre que há uma thread registrada, qualquer que seja o estado gravado. Teste `test_a_leaving_thread_keeps_resume_refused_and_unregisters_only_itself`: com a thread antiga parada depois do estado final, o `GET` mostra `partial` (nunca `interrupted`) e o `resume?retry_failed=true` dá 409. Uma thread registrada no mesmo id nesse meio-tempo continua no registro depois que a antiga sai. Depois, o `resume` dá 202, um segundo dá 409 e a célula refeita roda uma vez.
- **P2-2:** o `start` registra a thread antes do `INSERT` com `running`. O `resume` registra a thread dentro da transação `BEGIN IMMEDIATE` da reivindicação, antes do `COMMIT`. Uma thread registrada e ainda não iniciada conta como viva. A marcação `interrupted` (`read`, `resume`, `lifespan`) roda numa transação de escrita própria, que relê a linha e consulta o registro. Um teste simula uma checagem de vida feita antes do registro: o `GET`, o `resume` e o `lifespan` de outro app não marcam a comparação. Testes com threads reais: dois `resume` simultâneos com barreira depois da leitura da linha `interrupted` dão um 202 e um `409 comparison_running`, e as 3 células faltantes rodam uma vez cada (mata o M12). Um `GET` e um `resume` dentro da janela do `start` (entre o `COMMIT` do `INSERT` e o `thread.start()`) dão `running` e 409, e as 4 células rodam uma vez. O mesmo vale dentro da janela do `resume`: `running`, 409 e 3 execuções. No código da rodada 1, os três testes das janelas e o de P3-1 falham.
- **P2-3:** no teste de reinício, a tentativa interrompida tem custo no ledger (linhas `settled` a 0,004 e uma `reserved` a 0,002). `interrupted_attempts` traz esse valor, que entra uma vez no `cost_usd` depois do reinício e não entra de novo numa segunda leitura. No fim do `resume`, o `cost_usd` é a soma das células mais a tentativa (mata o M02).
- **P3-1:** uma célula `failed` sem `request_id` (`recorded_run_missing`) só roda de novo com `retry_failed=true`. Sem o parâmetro, o resultado é `409 nothing_to_resume`. Com ele, a célula usa a execução gravada, sem execução nova.
- **P3-2:** testes para o M08 (`_mark_interrupted` com visão antiga não sobrescreve um estado final), o M13 (o `resume` volta a contar no limite demo a célula devolvida: 3 → 4) e o M14 (a célula devolvida não é devolvida de novo: continua 3).
- **P3-3:** o OpenAPI da rota declara `404`, `409`, `422` e `429` com `ErrorBody` (teste).
- **Mutantes** numa cópia da árvore no scratchpad (`PYTHONPATH` na cópia, módulo conferido), com os testes da tarefa e de `test_v060_r2.py`; controle verde. Mortos: M02, M08, M12, M13, M14; P3-1 desfeito; `pop` sem identidade; `resume` sem recusar thread viva; thread não iniciada tratada como morta; marcação sem consultar o registro dentro da transação (morto pelo teste de `205336b`).
- Focados: `test_v0100_comparison_resume.py` com **13 passed** (4 da rodada 1 + 9 novos); com `test_v060_r2`, `test_v060_api` e `test_v060_r4`, verdes; ruff check e format limpos nos arquivos tocados.
- Suíte estrita: `python tools/scripts/lint_and_tests.py --strict` (`.venv`) no HEAD `205336b` (com os commits da tarefa 85 que estavam na branch), com `-p no:cacheprovider -rs`: **2147 passed, 1 skipped** em 1049,36 s (o skip é o de sempre, `test_v070_identity_r2.py:277`, que exige basetemp sob `.pytest_cache`); ruff `All checks passed!`; caminhos pessoais: nenhuma ocorrência em 772 arquivos; estrutura e skills válidas; "Validação estrita concluída sem falhas", exit 0. Log no scratchpad da sessão (não versionado), SHA-256 `888851ee…7bbf`. Bloqueio de ambiente, não defeito: o `--basetemp` em `PYTEST_ADDOPTS` perdeu as barras invertidas na passagem pelo Git Bash, e o pytest criou o basetemp como diretório relativo na raiz do repositório (não versionado, 175 diretórios temporários de teste). Removi esse diretório depois da suíte; nada versionado foi afetado.

## Status

Rodada 2 implementada pelo Developer em 2026-11-05 (P2-1, P2-2 e P2-3 fechados, P3-1 a P3-3 tratados); aguarda a rodada 2 da revisão e o QA real da D6 (CA-58 com `taskkill`). Critérios de aceite da spec não marcados (cabe ao Supervisor).

## Fechamento (Supervisor, 2026-11-06)

Concluída: revisão r2 apta (P3-4 e P3-5 declarados como limites); QA operacional apto (taskkill real, `interrupted`, `resume`, uma linha de ledger por célula).
