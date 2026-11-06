# Passagem de papel: Reviewer, tarefa 84 (comparação retomável), rodada 1

- Papel e responsável: Reviewer (subagente, contexto frio). Não li `docs/evidence/v0100-developer.md` nem a tarefa depois de "## Validação".
- Objetivo e critérios: spec `docs/specs/rubrica-operacao-v0100.md` D3, D6, CA-58; tarefa 84 (passos 1 a 6 e critérios de conclusão); história `docs/historias/rubrica-operacao-v0100.md`, momentos 4 e 5; contrato `docs/contracts/api-v040.md`, "Acréscimos da v0.10.0".
- Escopo: `src/merchant_assistant/comparisons.py`, `src/merchant_assistant/data/migrations.py`, `src/merchant_assistant/api/app.py`, `src/merchant_assistant/api/v1.py`, `tests/integration/test_v0100_comparison_resume.py`, `tests/unit/data/test_migrations.py`, ajustes de versão de esquema em quatro testes, contrato.
- Estado: **correções necessárias**.
- Branch e PR: `codex/v0.10.0-rubrica-operacao`, sem PR.
- Base e versão final: base `f4dfb97`; candidato `4b6891b`, `b6f7e19`, `ee7774a`; revisado o export limpo de `023dc61` (`git archive`, fora da raiz do repositório), nunca a árvore de trabalho. Impressão digital (sha256 da lista de sha256 de `src/**/*.py` e `tests/**/*.py` do export): `541065d83631ca21…ff4a0ecb`, igual no início e no fim da revisão. Os arquivos do escopo em `HEAD` (`34d7f6a`) não diferem de `023dc61`.
- Independência: independente (contexto novo, sem a passagem do Developer nem diagnóstico do Supervisor).

## Comandos e números

Tudo no export limpo, com o `.venv` do projeto e `PYTHONPATH` apontando para o `src` do export (o pacote instalado em modo editável aponta para a árvore de trabalho; conferido por `merchant_assistant.__file__`).

| Etapa | Comando | Resultado |
| --- | --- | --- |
| Estrutura | `lint_and_tests.validate_structure()` | válida |
| Caminhos pessoais | `checar-caminhos-pessoais.py` com a lista de `git ls-tree -r --name-only 023dc61` (o export não é repositório Git, então o `lint_and_tests.py --strict` direto para em `git ls-files`) | 766 arquivos, nenhuma ocorrência |
| pytest | `python -m pytest --basetemp=<scratchpad da sessão>/bt1 -p no:cacheprovider -rs` | **2121 passed, 1 skipped** em 1132,8 s; exit 0 |
| Teste pulado | `test_v070_identity_r2.py::test_synthetic_v040_script_logs_in_with_passwords` com basetemp sob `.pytest_cache` do export (o teste exige isso) | 1 passed |
| ruff | `ruff check` nos 166 arquivos de `python_files()` | All checks passed, exit 0 |
| Skills | `validate_skills()` | válidas |

A suíte rodou com outras suítes do time concorrendo pela CPU (daí a duração); nenhuma falha.

## Re-derivado e como

1. **Diff (`git diff f4dfb97..ee7774a --stat`)**: 11 arquivos, +627/−31. `api/v1.py` só acrescenta a rota (18 linhas, nenhuma removida); `api/app.py` acrescenta a varredura no `lifespan`. Nada em `evaluation/`, `prompts/`, rótulos, holdouts ou `orchestration/budget.py`; a reserva por chamada continua a do guarda; o `resume` só consulta `remaining()`, como o `start`. Procurei mecanismo equivalente (`interrupted`, `orphan`, `resume`, custo por `request_id` no ledger) sem distinguir maiúsculas: o `_ledger_cost` reproduz por `request_id` a fórmula de `BudgetGuard._committed` (`budget.py:92`) e reutiliza `paid_attempts` para resolver o ledger; não há helper equivalente a reaproveitar.
2. **Migração 0012** (sonda própria em banco sintético isolado): 11→12→11→12→11→12. DDL de `comparisons` depois da descida é idêntico ao da versão 11 (normalizado); `interrupted` vira `failed` na descida, as demais linhas, custos e células ficam iguais; o `CHECK` anterior volta (`IntegrityError` para `interrupted`); índice `comparisons_owner_v060` recriado e usado pelo plano de consulta; `integrity_check` = ok, `foreign_key_check` vazio, sem tabela `comparisons_rebuild` sobrando; `schema_version` termina em 12. `/ready` reporta 12 (`test_use_cases.py::test_readiness`, na suíte).
3. **Interrupção**: `lifespan` → `interrupt_orphans` marca `interrupted` só sem thread viva, com log `event={"comparison_id": …}` sem texto (teste do candidato, conferido). `read()` usa o mesmo `_mark_interrupted`. Sonda de custo com valor não nulo: ledger da tentativa morta com 4 linhas `settled` a 0,004 e uma `reserved` a 0,002 → `interrupted_attempts[0].cost_usd = 0,018`; `cost_usd` da comparação = anterior + 0,018; segunda leitura não soma de novo; depois do `resume`, `cost_usd` final = soma das células + 0,018. Sem dupla contagem.
4. **Retomada**: 202 com `resumed_cells`; 409 `comparison_running`, `comparison_completed`, `nothing_to_resume`, `fixed_factors_changed`; 404 de outro principal; 401 sem token; 429 quando o restante não cabe (3 células cabem, 4 não); sonda própria: 422 `admin_scope_required` para admin sem cliente sintético e 422 para `retry_failed=maybe`; rota presente no OpenAPI. Contador do modelo programado prova que a célula concluída não roda de novo. Limite demo (sonda): início consome 4, a célula que falhou sem chamada é devolvida (3), `retry_failed=true` reconta 1 (4) e a célula paga não é devolvida: sem dupla contagem.
5. **Concorrência**: três sondas com o modelo programado, abaixo (P2-1, P2-2).
6. **Mutantes** (cópia separada do export, um por vez, restaurando o arquivo; controle sem mutação verde nos três arquivos de teste):

| Mutante | Resultado | Teste que caiu |
| --- | --- | --- |
| M01 `_run` não pula célula com `request_id` | morto | `test_restart_…`, `test_failed_cells_…` |
| M02 custo da tentativa não somado em `cost_usd` | **sobreviveu** | — (P2-3) |
| M03 custo da tentativa = `None` | morto | `test_restart_…` |
| M04 `retry_failed` ignorado (nunca reexecuta) | morto | `test_failed_cells_…` |
| M05 `retry_failed` ignorado (sempre reexecuta) | morto | `test_failed_cells_…` |
| M06 descida sem restaurar o `CHECK` | morto | `test_0012_round_trip_…` |
| M07 descida sem converter `interrupted` | morto | `test_0012_round_trip_…` |
| M08 `_mark_interrupted` sem a guarda de estado `running` no `UPDATE` | **sobreviveu** | — (P3-2) |
| M09 `lifespan` sem a varredura | morto | `test_restart_…` |
| M10 orçamento contando todas as células | morto | `test_resume_reserves_…` |
| M11 sem conferir `prompt_set` | morto | `test_resume_reserves_…` |
| M12 reivindicação sem `AND state=?` | **sobreviveu** | — (P2-2) |
| M13 `resume` sem recontar o limite demo | **sobreviveu** | — (P3-2) |
| M14 devolução demo sem a marca `demo_refunded` | **sobreviveu** | — (P3-2) |
| M15 sem `previous_request_ids` | morto | `test_failed_cells_…` |
| M16 sem gravar `in_flight_request_id` antes da chamada | morto | `test_restart_…` |
| M17 sem o 409 de `running` viva | sobreviveu (equivalente: o laço seguinte devolve o mesmo 409) | — |

Os quatro mutantes pedidos: pular célula com `request_id` removido, morto; `interrupted_attempts` sem custo, morto quando o custo vira `None` (M03) e **vivo** quando só deixa de somar (M02); `retry_failed` ignorado, morto nos dois sentidos; migração sem restaurar o `CHECK`, morto.

## Achados

### P1

Nenhum.

### P2

**P2-1. A thread antiga desregistra a thread retomada; a comparação aparece `interrupted` em execução e um segundo `resume` paga a mesma célula de novo.**
- Condição: no `finally` de `_run`, o estado final é gravado (`comparisons.py:437`) antes de `shutil.rmtree(workdir)` (`:440`) e de `_ACTIVE.pop(comparison_id)` (`:442`). Um `resume` nessa janela vê `partial`/`failed`, não confere `_alive(comparison_id)` para estados diferentes de `running` (`:534-546`) e registra a thread nova em `_ACTIVE[comparison_id]` (`:614`); a thread antiga, ao terminar, remove essa entrada (o `pop` não confere se a entrada é dela). A thread nova fica invisível: `read()` a marca `interrupted` (`:628`) e um novo `resume` é aceito.
- Impacto: a mesma célula executa duas vezes com chamadas pagas (CA-58: "sem célula paga duas vezes"); estado e `cost_usd` exibidos incoerentes durante a execução. O teto global do guarda continua valendo; o teto da comparação vale por thread. O mecanismo é novo nesta tarefa (o `start` usa id novo, sem essa colisão). Um cliente que "retoma até completar" percorre exatamente esse caminho.
- Reprodução (sonda `test_probe_old_thread_pop_unregisters_resumed_thread`, em cópia do export): `fail_at=2`; o `shutil.rmtree` da comparação espera um evento; `POST …/resume?retry_failed=true` → 202; libera a thread antiga → `_alive=False` com a thread nova viva; `GET` → `interrupted`; segundo `POST …/resume` → 202; execuções da célula refeita: 2 (esperado 1).
- Correção sugerida: o `pop` só remove a própria thread (`_ACTIVE.get(id) is threading.current_thread()`); `resume` recusa com 409 quando `_alive(comparison_id)`, qualquer que seja o estado; teste de regressão com a janela forçada.

**P2-2. Janela entre gravar `running` e registrar a thread: `resume` concorrente (ou `read` + `resume` durante o `start`) roda as mesmas células em duas threads.**
- Condição: `resume` faz `COMMIT` do estado `running` (`comparisons.py:599`) e só depois cria e registra a thread (`:607-615`); o `start` faz o mesmo entre o `INSERT` com estado `running` (`:261`), `capture_active()` (`:278`) e o registro (`:286`). Nessa janela, outro `resume` (ou um `GET`, via `read()`) vê `running` sem thread viva, marca `interrupted` e reivindica de novo. A reivindicação `WHERE … AND state=?` só protege dois pedidos que leram o mesmo estado; não cobre essa janela, e nenhum teste exercita a reivindicação (M12 sobrevive).
- Impacto: dupla execução paga de todas as células restantes. A janela do `start` já existia (antes, um `GET` nela rotulava `failed` e a thread sobrescrevia no fim); com o `resume`, a consequência passou de rótulo errado a pagamento em dobro: piorou.
- Reprodução: sonda `test_probe_nested_resume_in_registration_window` (a construção da primeira `Thread` do `resume` chama um segundo `resume`): primeiro 202, segundo 202, execuções 6 (esperado 3). Sonda `test_probe_get_and_resume_in_start_window` (`read` + `resume` dentro da janela do `start`): execuções 8 (esperado 4).
- Correção sugerida: registrar em `_ACTIVE` (sob `_ACTIVE_LOCK`) antes de o `running` ficar visível, ou manter o lock do `COMMIT` até o registro; `read()` e `resume` consultam o mesmo registro. Teste de concorrência que mate M12.

**P2-3. O custo da tentativa interrompida somado em `cost_usd` não tem teste que o discrimine.**
- Condição: o teste do candidato usa o modelo programado, custo 0,0 (`test_v0100_comparison_resume.py`, `expected_cost = … + 0.0`); remover `cost += attempt_cost or 0.0` (`comparisons.py:494`, M02) deixa a suíte verde.
- Impacto: a afirmação de dinheiro de CA-58 ("ledger coerente", custo da tentativa no `cost_usd`) fica sem guarda de regressão. O comportamento atual está certo (sonda de custo acima: 0,018 somado uma vez, sem dupla contagem).
- Correção sugerida: no teste, gravar custo não nulo no ledger da tentativa morta (uma linha `settled` e uma `reserved`), como na sonda, e conferir `interrupted_attempts`, `cost_usd` depois do reinício, depois de duas leituras e depois do `resume`.

### P3

- **P3-1.** Célula `failed` sem `request_id` (`recorded_run_missing`, fonte `recorded`) volta a `pending` sem `retry_failed` (`comparisons.py:562`: a condição só pula quem tem `request_id`). O contrato diz que células `failed` só rodam de novo com `retry_failed=true`. Sem custo (célula reaproveitada); registrar ou ajustar a condição para olhar o `status`.
- **P3-2.** Lacunas de teste sem defeito observado: M08 (guarda de estado `running` em `_mark_interrupted`, que impede sobrescrever um estado final), M13 (recontagem do limite demo no `resume`; a sonda confirmou 3 → 4) e M14 (célula devolvida não é devolvida de novo) sobrevivem.
- **P3-3.** O OpenAPI da rota declara só `409` (`api/v1.py:1442`); `404`, `422` e `429` estão no contrato em texto. Mesmo padrão da rota irmã de criação (declara só `429`).

## Critérios comprovados e não verificados

- Comprovados offline: estado `interrupted` no startup e na leitura com células preservadas; tentativa em curso em `interrupted_attempts` com custo do ledger, somada uma vez; retomada pula células com resultado (contador do modelo); `retry_failed`; recusas 404/401/409/422/429; reserva só do que falta; migração 0012 reversível; esquema 12; suíte estrita verde; caminhos pessoais limpos.
- Não verificados aqui (QA, D6): reinício real com `taskkill` e modelo real; ledger antes e depois na campanha real.
- Concorrência: o contrato não promete idempotência sob pedidos simultâneos, mas "nenhuma célula paga duas vezes" (CA-58) falha nas três sondas de P2-1 e P2-2. O fluxo sequencial do QA (matar, reiniciar, retomar) não passa por essas janelas.

## Limitações

- O `lint_and_tests.py --strict` não roda inteiro no export (o verificador de caminhos chama `git ls-files`); as quatro etapas rodaram em separado com os mesmos comandos do script, e o verificador recebeu a lista de arquivos do commit.
- Sondas e mutantes ficaram em cópias no `<scratchpad da sessão>`; nada foi gravado na árvore do Developer além deste arquivo. Nenhuma chamada paga, nenhum Docker, nenhum Git de escrita.
- Primeira tentativa de mutantes descartada: rodava só com `src` copiado e a configuração resolve `prompts/` e `data/` pela raiz do pacote; refeita sobre uma cópia completa, com controle verde.

## Ação externa

Nenhuma. Arquivo não commitado.

## Próxima ação

Developer: corrigir P2-1 e P2-2 (registro da thread antes de `running` ficar visível, `pop` só da própria thread, `resume` recusa com thread viva) e P2-3 (teste com custo não nulo), com testes de regressão que matem M02 e M12; P3 a critério. Depois, Reviewer rodada 2 sobre o novo SHA (afetados: `comparisons.py` e os testes da tarefa 84).

## Decisão humana pendente

Nenhuma. P2-1 e P2-2 tocam dinheiro (CA-58); ficaram em P2 por dependerem de corrida estreita e o teto global do guarda continuar valendo. O Supervisor pode elevar para P1.
