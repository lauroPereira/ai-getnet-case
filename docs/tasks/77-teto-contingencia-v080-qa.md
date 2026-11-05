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

Pendente (Developer, revisão, aplicação pelo Supervisor e QA).

## Status

pendente
