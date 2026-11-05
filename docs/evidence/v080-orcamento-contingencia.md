# Contingência da campanha `v080-qa` aplicada

Aplicada em 2026-11-05 às 03h44 (São Paulo; `2026-11-05T06:44:24+00:00`) pelo Supervisor, com o candidato r7 `658c70adc69cb956c931737b8a1caf38ed638dd5` apto na [revisão independente](v080-reviewer-t75-77.md) (rodadas 2 e 3), depois do dry-run conferido contra o ensaio do Developer e do Reviewer. Autorização: responsável, 2026-11-05, até US$0,30 adicionais ([spec](../specs/orquestracao-avaliacao-v080.md#requisitos-não-funcionais), [plano](../specs/evolucao-pos-feedback-plano.md#decisão-aprovada-em-2026-11-04)). Motivo: após o reteste r4 ([parecer](v080-d12-pre-holdout-r4.md)) o cap tinha US$0,51835345 restantes e as fases reservadas (juiz repetido US$0,07709880, holdout US$0,36062993) deixavam US$0,08062472 livres, abaixo do custo do reteste r5 (13 IDs × 3, entre US$0,09 e US$0,12 nas rodadas anteriores) mais o smoke.

| Verificação | Antes | Depois |
| --- | ---: | ---: |
| Teto primário persistido (`budget.sqlite3.limit`) | US$1,70 | US$2,00 |
| Cap fixo `v080-qa` (`fixed_budget_cap` e sidecar) | US$1,10 | US$1,40 |
| Entradas e último ID, primário | 2.733 | 2.733 |
| Entradas e último ID, campanha | 1.117 | 1.117 |
| Comprometido, primário | US$1,14385079 | US$1,14385079 |
| Comprometido, campanha | US$0,58164655 | US$0,58164655 |
| Reservas abertas | 0 / 0 | 0 / 0 |
| SHA-256 lógico das entradas | primário `845ee88e…6181`, campanha `9fae30f5…e100` | iguais |
| Bytes do SQLite primário | `45e5a93a…5320` | iguais |
| Folga | — | primário US$0,85614921, campanha US$0,81835345 |

Procedimento `tools/scripts/v080_contingency_transition.py` (blob LF `570ac505…e607`), `--apply` com auditoria nova em `.pytest_cache/v080-contingency-audit-20261105T034423/` (backups verificados, bytes dos sidecars, `prepared.json`, `applied.json`, todas as checagens verdadeiras). Terminadores dos sidecars preservados (`2.0\n`, `1.4\r\n`). Nova execução em dry-run: `would_change = []`. Nenhum processo do projeto ativo durante a aplicação.

O valor efetivamente liberado é o teto; o gasto da contingência é o que o ledger registrar acima de US$1,10 na campanha, a ser consolidado no relatório da versão. A CLI passa a aceitar `--campaign-cap-usd 1.40` só para continuar esta campanha, com a estimativa revalidada; `1.10` é recusado daqui em diante. O QA fixa `BUDGET_LIMIT_USD` por fase (P3-77a).
