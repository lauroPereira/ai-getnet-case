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

---

# Passagem de papel: Reviewer, tarefa 84 (comparação retomável), rodada 2

- Papel e responsável: Reviewer (subagente, contexto frio). Não li `docs/evidence/v0100-developer.md`.
- Objetivo e critérios: spec `docs/specs/rubrica-operacao-v0100.md` D3, D6, CA-58; tarefa 84 (passos e critérios de conclusão); achados P2-1, P2-2, P2-3 e P3-1 a P3-3 da rodada 1; decisões do Supervisor para a rodada 2 (a thread remove só a própria entrada, depois de gravar o estado final; `resume` recusa 409 com thread viva, qualquer que seja o estado gravado; registro antes de `running` ficar visível no `start` e dentro do `BEGIN IMMEDIATE` no `resume`; thread registrada e não iniciada conta como viva; marcação `interrupted` em transação própria que relê a linha e consulta o registro; teste com custo não nulo; célula `failed` só com `retry_failed`; OpenAPI com 404/409/422/429).
- Escopo: commits `873007c` (decorator da rota em `api/v1.py`, +5/−1), `c097f90` (`comparisons.py` +103/−52 e `tests/integration/test_v0100_comparison_resume.py` +308) e `205336b` (mesmo arquivo de teste, +27). Nos arquivos do escopo, nada mais mudou em `ee7774a..205336b` (o `api/app.py` só recebeu `/metrics` da tarefa 85, commit `29add9c`), e nada em `src/` ou `tests/` mudou entre `205336b` e `5005d81`.
- Estado: **apto para QA**.
- Branch e PR: `codex/v0.10.0-rubrica-operacao`, sem PR.
- Base e versão final: base da rodada 1 `ee7774a`; revisado o export limpo de `5005d81` (`git archive`, fora da raiz do repositório), nunca a árvore de trabalho. Impressão digital (sha256 da lista de sha256 de `src/**/*.py` e `tests/**/*.py` do export): `5b7f8af40aea…c85bb82a`, igual no início e no fim. Durante a revisão a branch avançou para `0b1a637` (`4195468`, `0b1a637`: só documentos das tarefas 83 e 85; nada em `src/`, `tests/` nem neste arquivo).
- Independência: independente quanto ao Developer (sem a passagem dele nem diagnóstico do Supervisor além das decisões listadas no despacho). **Desvio registrado:** a leitura da tarefa 84 trouxe o arquivo inteiro, inclusive "## Validação" (rodada 2) e "## Status". Tratei aquele texto como afirmação a verificar: cada item abaixo foi re-derivado com comando, sonda ou mutante próprios, e as sondas usam construções diferentes das do candidato (gancho em `Thread.__init__` e `Thread.start`, barreira em `prompt_versions`, três pedidos concorrentes em vez de dois, ABA).

## Comandos e números

Tudo no export limpo, com o `.venv` do projeto e `PYTHONPATH` no `src` do export (conferido por `merchant_assistant.__file__`). `--basetemp` em forma Windows, por argumento de linha de comando, sob `.pytest_cache` do export (nunca `PYTEST_ADDOPTS`); a raiz do repositório não ganhou diretório.

| Etapa | Comando | Resultado |
| --- | --- | --- |
| Estrutura | `lint_and_tests.validate_structure()` | válida |
| Caminhos pessoais | `checar-caminhos-pessoais.py` com a lista de `git ls-tree -r --name-only 5005d81` (o export não é repositório Git) | 772 arquivos, nenhuma ocorrência, exit 0 |
| pytest | `python -m pytest --basetemp=<export>/.pytest_cache/rv2-full -p no:cacheprovider -rs` (forma Windows) | **2148 passed, 0 skipped** em 929,14 s; exit 0 (o teste de `test_v070_identity_r2.py` que costuma pular rodou, porque o basetemp está sob `.pytest_cache`) |
| ruff | `ruff check` nos 168 arquivos de `python_files()` | All checks passed, exit 0 |
| ruff format | `ruff format --check` nos 3 arquivos do escopo | já formatados |
| Skills | `validate_skills()` | válidas |
| OpenAPI | rota `/v1/comparisons/{comparison_id}/resume` no `router` | `POST`, 202, `{404, 409, 422, 429}` com `ErrorBody` |

A suíte rodou junto com as sondas e os mutantes (em outra cópia), com CPU disputada; nenhuma falha.

## Re-derivado e como

1. **Diff (`git show` de cada commit)**: o `pop` do `finally` de `_run` virou `_release(id, current_thread())`, que só apaga a entrada se ela for da própria thread, e fica depois do `_save` com o estado final (`comparisons.py:445-451`). O `resume` recusa com 409 quando `row.state == running or _alive(id)` (`:579`). O `start` cria e registra a thread antes do `INSERT` com `running` (`:263-289`), e o `resume` registra dentro do `BEGIN IMMEDIATE` da reivindicação, antes do `COMMIT` (`:636-658`). `_registered` conta como viva a thread registrada com `ident is None` (`:459-464`). `_interrupt_if_orphan` abre `BEGIN IMMEDIATE`, relê a linha e consulta o registro antes de `_mark_interrupted` (`:524-541`); `read`, `resume` e `interrupt_orphans` passam por ela. As falhas entre registrar e iniciar (`INSERT`, reivindicação, `thread.start()`) liberam a entrada. A ordem de travas não fecha ciclo: `_ACTIVE_LOCK` nunca é mantido enquanto se espera o SQLite (`connect` usa `isolation_level=None`, autocommit). Mecanismo equivalente procurado (registro, `_ACTIVE`, `is_alive`, `BEGIN IMMEDIATE` em `comparisons`, sem distinguir maiúsculas): o registro é o mesmo da rodada 1, só corrigido; nada duplicado.
2. **Janelas da rodada 1, com threads reais** (sondas em cópia separada do export, modelo programado, admin ou demo sintéticos):
   - P1, um segundo `resume` aninhado na construção da `Thread` do primeiro (a reprodução da rodada 1 que dava 6 execuções): primeiro 409, aninhado 202, **3 execuções, uma por célula**, `completed`.
   - P2, `GET` + `resume?retry_failed=true` entre o `INSERT` do `start` e o `thread.start()` (gancho em `Thread.start`): banco `running`, `GET` `running`, `409 comparison_running`, **4 execuções, uma por célula** (a rodada 1 dava 8).
   - P3, o mesmo entre o `COMMIT` da reivindicação do `resume` e o `thread.start()`: 202, `running`, 409, **3 execuções**.
   - P4, três `resume` concorrentes em threads reais com `Barrier(3)` depois da checagem de vida (em `prompt_versions`): `[202, 409, 409]`, **3 execuções, uma por célula**, `completed`.
3. **Thread antiga terminando** (P5): com a thread parada depois de gravar `partial` e antes de sair do registro, 5 `GET` dão `partial` e 3 `resume?retry_failed=true` dão `409 comparison_running`. Com uma thread mais nova registrada no mesmo id e a linha em `running`, a antiga sai: 10 `GET` seguidos dão `running`, **nunca `interrupted`**, e a entrada da nova continua no registro.
4. **Custo da tentativa interrompida** (P6, valores diferentes dos do teste do candidato): ledger da tentativa morta com as linhas `settled` a 0,0031 e uma `reserved` a 0,0017. Resultado: `interrupted_attempts = [{request_id, cost_usd: 0,0141}]`; `cost_usd` = anterior + 0,0141 em três leituras seguidas e depois de um **segundo reinício** (lifespan de novo); depois do `resume`, `cost_usd` = soma das células + 0,0141, com uma única entrada em `interrupted_attempts`. **Somado uma vez.**
5. **Mutantes** (cópia separada, um por vez, arquivo restaurado ao fim com sha256 igual ao do export). Conjunto do candidato: `test_v0100_comparison_resume.py` (13), `test_v060_api.py` (17), `test_v060_r2.py` (13), `test_v060_r4.py` (9) = 52 testes, controle verde. As sondas P1 a P6 também passam no controle (P7 é o achado P3-4 e falha já no controle).

| Mutante | Candidato | Teste que caiu | Sondas |
| --- | --- | --- | --- |
| M02 custo da tentativa não somado | morto | `test_restart_…` | P6 |
| M08 `_mark_interrupted` sem a guarda `running` no `UPDATE` | morto | `test_marking_interrupted_never_overwrites_a_final_state` | — |
| M12 reivindicação sem `AND state=?` | morto | `test_two_concurrent_resumes_claim_the_comparison_once` | P1, P4 |
| M13 `resume` sem recontar o limite demo | morto | `test_resume_recounts_given_back_cells_…` | — |
| M14 devolução demo sem conferir `demo_refunded` | morto | `test_resume_recounts_given_back_cells_…` | — |
| `pop` sem conferir identidade | morto | `test_a_leaving_thread_…`, `test_two_concurrent_resumes_…` | P1, P4, P5 |
| `resume` ignora thread viva (só olha `running`) | morto | `test_a_leaving_thread_…` | P5 |
| thread não iniciada tratada como morta | morto | `test_read_and_resume_while_start_…`, `…_while_resume_…` | P2, P3 |
| marcação sem consultar o registro na transação | morto | `test_a_stale_liveness_check_…` | — |
| `start` registra depois do `INSERT` | morto | `test_read_and_resume_while_start_is_registering_…` | — (o gancho de P2 fica depois do registro mutado) |
| `resume` registra depois do `COMMIT` | morto | `test_read_and_resume_while_resume_is_registering_…` | — (idem P3) |
| P3-1 desfeito (condição antiga) | morto | `test_a_failed_recorded_cell_runs_again_only_with_retry_failed` | — |
| `_release` antes de gravar o estado final | morto | `test_a_leaving_thread_…` | P5 |

6. **P3-1** (célula `failed` sem `request_id`): a condição agora pula toda célula `failed` sem `retry_failed` (`comparisons.py:606-610`); mutante morto. **P3-3**: decorator com os quatro códigos e teste do OpenAPI.

## Achados

### P1

Nenhum.

### P2

Nenhum. P2-1, P2-2 e P2-3 da rodada 1 estão fechados (itens 2 a 5 acima).

### P3

**P3-4. A reivindicação do `resume` compara só o `state`: um `resume` que leu `partial` ou `failed` aceita depois de outro `resume` ter rodado e voltado ao mesmo estado (ABA), com `cells` e `cost_usd` velhos.**
- Condição: o `UPDATE … WHERE comparison_id=? AND state=?` (`comparisons.py:638-641`) usa o `state` lido no começo e grava o `cells` calculado dessa leitura. Se, entre a checagem de vida (`:579`) e a reivindicação, outro `resume` reivindicar, rodar e terminar de novo em `partial` ou `failed`, a reivindicação velha passa, porque o registro já está vazio. A thread nova roda de novo as células que a anterior concluiu e começa com o `spent` velho.
- Impacto: uma célula paga duas vezes, e o `cost_usd` fica abaixo do gasto. Os `request_id` da execução intermediária somem de `cells` (nem `request_id` nem `previous_request_ids`), embora continuem no ledger. Alcance prático baixo: a pausa precisa durar mais que uma execução inteira com chamadas pagas (segundos), contra uma janela de milissegundos. Não achei ponto de espera longo nesse trecho: `capture_active` só lê depois do bootstrap, `prompt_versions` lê arquivos e não há escrita até o `BEGIN IMMEDIATE`. O fluxo sequencial do QA (D6) não passa por aqui. Fica em P3 por isso; o Supervisor pode elevar, porque o texto de CA-58 é "sem célula paga duas vezes".
- Reprodução: sonda `test_p7_aba_stale_claim`, em cópia do export. Uma comparação `partial` com duas células `failed`. R2 (`resume?retry_failed=true`, em outra thread) para dentro de `prompt_versions`. R1 (`resume?retry_failed=true`) roda até o fim: uma célula concluída a 0,01, a outra falha de novo, e o estado volta a `partial`. R2 é liberado e recebe **202** (esperado: 409). As duas células rodam 2 vezes cada. `cost_usd` final 0,02 para 0,03 executado, e os dois `request_id` de R1 desaparecem de `cells`.
- Correção sugerida: a reivindicação compara também o `cells` lido (`AND cells=?` com o `cells` da linha lida); o `updated_at` não serve, porque `_now()` tem resolução de segundos. Além disso, consultar `_registered(id)` dentro da transação da reivindicação. Teste com a pausa forçada, como a sonda.

**P3-5. O registro de threads é por processo, e esse limite não está documentado no contrato nem no README. O README ainda descreve o comportamento antigo.**
- Condição: `_ACTIVE` vale só para o processo (o comentário de `comparisons.py:32-34` diz isso). Com dois processos sobre o mesmo runtime, o processo B não vê a thread viva do processo A: o lifespan ou um `GET` de B marca `interrupted` uma comparação que ainda roda em A, e um `resume` em B roda de novo as células que A está executando. Isso vale para mais de um worker ou para uma segunda API subindo com a primeira viva. `docker/entrypoint.sh:5` fixa `--workers 1`, que é a guarda operacional, e o teste do candidato só cobre dois apps no mesmo processo. `README.md:685` ainda diz que reiniciar a API marca a comparação em execução como `failed`.
- Impacto: documentação. O uso previsto (um processo; no QA, `taskkill` e depois reinício) não é afetado.
- Correção sugerida (tarefa 86, junto do README e do CHANGELOG): registrar no contrato ("Acréscimos da v0.10.0") e no README que a detecção de thread viva é por processo e exige um único processo da API por runtime, e atualizar `README.md:685`.

Rodada 1, P3: P3-1 corrigido; P3-2 coberto (M08, M13 e M14 mortos); P3-3 corrigido.

## Critérios comprovados e não verificados

- Comprovados offline: uma execução por célula nas janelas do `start` e do `resume`, com `resume` aninhado e com três `resume` concorrentes; o `GET` nunca mostra `interrupted` enquanto há thread registrada, nem quando a thread antiga sai; o `resume` recusa enquanto a thread que gravou o estado final não saiu; a tentativa interrompida tem custo não nulo, somado uma vez em leituras, reinício e retomada; célula `failed` só roda com `retry_failed`; OpenAPI com 404, 409, 422 e 429; os mutantes pedidos estão mortos; suíte estrita verde; caminhos pessoais limpos.
- Não verificados aqui (QA, D6): reinício real com `taskkill` e modelo real; ledger antes e depois na campanha real.

## Limitações

- O `lint_and_tests.py --strict` não roda inteiro no export, porque o verificador de caminhos chama `git ls-files`. As quatro etapas rodaram em separado com os mesmos comandos do script, e o verificador recebeu a lista de arquivos do commit.
- As sondas P2 e P3 usam gancho em `Thread.start`, então não matam os mutantes que movem o registro para logo antes do `start`. Os testes `Window` do candidato, com gancho no `close` da conexão, matam esses mutantes.
- Sondas, mutantes e logs ficaram em cópias no `<scratchpad da sessão>`. Nada foi gravado na árvore do Developer além deste arquivo. Nenhuma chamada paga, nenhum Docker, nenhum Git de escrita.

## Ação externa

Nenhuma. Arquivo não commitado.

## Próxima ação

QA da D6 (CA-58 com `taskkill` e modelo real) sobre `5005d81` ou um sucessor sem mudança em `src/`. P3-4 (reivindicação também por `cells` e registro consultado dentro da transação) e P3-5 (limite por processo no contrato e no README, `README.md:685`) ficam para o Developer, a critério do Supervisor: P3-4 tem correção de uma linha, P3-5 entra na tarefa 86.

## Decisão humana pendente

Nenhuma. O Supervisor decide se eleva P3-4 por causa do texto literal de CA-58.
