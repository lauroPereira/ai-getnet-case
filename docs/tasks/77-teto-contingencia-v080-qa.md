# Tarefa 77 — Teto de contingência da campanha `v080-qa` (v0.8.0)

## Objetivo

Permitir que a campanha `v080-qa`, já montada com o cap fixo de US$1,10, receba a contingência de até US$0,30 autorizada pelo responsável em 2026-11-05, pelo mesmo rito da ampliação de 2026-11-04: código revisado, suíte estrita e transição validada em cópia sintética antes de tocar os ledgers reais.

## Especificação relacionada

[Orquestração e avaliação v0.8.0](../specs/orquestracao-avaliacao-v080.md), "Requisitos não funcionais", item "Contingência autorizada em 2026-11-05"; [plano](../specs/evolucao-pos-feedback-plano.md), "Decisão aprovada em 2026-11-04". Precedente: commit `27add60` e [transição](../evidence/v080-orcamento-transicao.md).

## Motivo registrado

Após o reteste r4 ([parecer](../evidence/v080-d12-pre-holdout-r4.md)), o cap tem US$0,51835345 restantes e as fases reservadas (juiz repetido US$0,07709880 e holdout US$0,36062993) deixam US$0,08062472 livres. O reteste r5 (8 jornadas datadas, `REPLAN-PROCEDURE`, `REPLAN-TOOL-DOWN`, `PRICE-INSUFFICIENT` EN/PT e `CONTRACT-TERMINATION`, três repetições) custou entre US$0,09 e US$0,12 nas rodadas anteriores. Sem a contingência, o reteste ou o holdout ficariam bloqueados pela guarda.

## Pré-condições

Candidato `4c3c8a9` mais as correções das tarefas 75 e 76 na mesma branch. Ledgers: primário `data/runtime/budget.sqlite3` (teto 1,70; comprometido US$1,14385079; último ID 2733; zero reservas) e campanha `data/runtime/budget-v080-qa.sqlite3` (cap fixo `v080-qa` 1,10; comprometido US$0,58164655; último ID 1117; zero reservas).

## Escopo

1. **CLI e guarda.** Aceitar um quarto valor de `--campaign-cap-usd`, **1,40**, somente quando (a) já existir o cap persistido `v080-qa` com 1,10 ou 1,40 no ledger da campanha, (b) a estimativa medida for revalidada como hoje e (c) o teto primário persistido cobrir o novo cap. Nunca montar campanha nova com 1,40; o valor existe só para continuar a campanha já montada. Mensagens de recusa claras.
2. **Transição.** Procedimento idempotente, em script versionado em `tools/scripts/`, que: faz backup do SQLite e dos bytes do sidecar `.limit`; confere zero reservas e nenhum processo do projeto ativo; grava `fixed_budget_cap.limit_usd = 1.40` para `cap_id = 'v080-qa'` e o sidecar da campanha; eleva o sidecar do primário de 1,70 para **2,00** (a contingência é a mesma soma; o primário é a guarda combinada que a limita); registra `prepared.json` e `applied.json` com SHA-256 lógico das entradas antes e depois, que devem ser idênticos. Modo `--dry-run` por padrão; `--apply` exige caminho explícito dos ledgers. Validar o procedimento numa cópia sintética dos dois ledgers em `.pytest_cache/` antes de qualquer uso real. O Developer **não aplica** nos ledgers reais: a aplicação é do Supervisor depois da revisão.
3. **Testes.** Unidade e integração programada: aceitação de 1,40 só com cap persistido e estimativa válida; recusa de montagem nova com 1,40; recusa quando o primário não cobre; transição sobe em cópia sintética com histórico preservado e é recusada com reserva aberta. Sem rede, sem chamada paga.

## Fora do escopo

Alterar 0,50, 1,00 e 1,10; mudar a estimativa, o seletor do QA ou a forma de contabilizar; relaxar qualquer guarda existente; tocar `data/runtime/`.

## Critérios de conclusão

- Suíte estrita verde; a CLI recusa 1,40 em todos os casos fora das condições acima.
- O script de transição passa no ensaio em cópia sintética com os números desta tarefa e produz os registros de auditoria.
- Passagem em `docs/evidence/v080-developer.md` com arquivos, decisões e números.

## Validação

Developer (2026-11-05), branch `codex/v0.8.0-replan`:

- **CLI** (`src/merchant_assistant/cli.py`): quarto valor `1.40` em `--campaign-cap-usd`. Exige `--campaign-estimate` revalidada pelo mesmo verificador e na mesma faixa que justificou o cap 1,10 (acima de US$1,00 e até US$1,10). Antes de abrir qualquer ledger para escrita, recusa quando o ledger da campanha ainda está em 1,10 ("apply the reviewed contingency transition") ou quando não há cap `v080-qa` persistido com sidecar ("nothing was mounted"). Depois, recusa quando o teto primário persistido (sidecar) menos o comprometido não cobre o restante da campanha. Após a transição, `1.10` deixa de montar (registro e sidecar não batem mais).
- **Guarda** (`src/merchant_assistant/orchestration/budget.py`): `FixedBudgetGuard` aceita teto até 1,40 só para `v080-qa` e só como continuação. Acima de 1,10 exige ledger e sidecar existentes e um registro de cap já gravado; nunca insere um cap novo acima de 1,10. Os valores 0,50, 1,00 e 1,10 não mudam.
- **Transição** (`tools/scripts/v080_contingency_transition.py`): dry-run por padrão (somente leitura); `--apply` exige `--primary`, `--campaign` e `--audit-dir` novo. Faz backup SQLite verificado e dos bytes dos sidecars, confere zero reservas e nenhum processo do projeto (`merchant_assistant`, `merchant-assistant`, `uvicorn`), grava `prepared.json`, aplica (cap 1,10 → 1,40, sidecar da campanha 1,40, sidecar do primário 1,70 → 2,00, preservando o terminador de linha de cada sidecar), confere e grava `applied.json`. É idempotente e retoma uma aplicação interrompida.
- **Ensaio em cópia** (`.pytest_cache/t77-rehearsal-20261105/`, cópia byte a byte dos quatro arquivos de `data/runtime/`): antes, primário 1,70 com 2.733 entradas (último ID 2733), US$1,14385079 e 0 reservas; campanha 1,10 com 1.117 entradas (último ID 1117), US$0,58164655 e 0 reservas. Depois, 2,00 e 1,40, com entradas, últimos IDs, comprometidos e SHA-256 lógico iguais (primário `845ee88e…6181`, campanha `9fae30f5…e100`). Folga após a transição: primário US$0,85614921 ≥ campanha US$0,81835345. A segunda execução retornou `already_applied` sem escrever. Com a cópia, a CLI aceitou 1,40 (estimativa verificada US$1,03174096, restante combinado US$0,81835345) e recusou 1,10. Os ledgers reais conferem por SHA-256 com os valores anteriores à cópia. **Não aplicado nos ledgers reais.**
- `tests/unit/test_t77_contingency_cap.py` (22 testes); regressão de orçamento e história da v0.8.0 (`test_budget_and_router`, `test_v080_story`, `test_campaign`): 51 passed. Suíte estrita no `HEAD` `94bf7b3`: 1247 passed, ruff e skills ok, exit 0 ([passagem](../evidence/v080-developer.md)).
- Pendente: revisão independente, aplicação pelo Supervisor e QA.

## Status

implementada; aguarda revisão e aplicação pelo Supervisor
