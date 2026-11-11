# Resultado da v0.10.0

Rubrica `judge.v4`, comparação retomável e métricas. Spec: [rubrica-operacao-v0100.md](../specs/rubrica-operacao-v0100.md); história: [rubrica-operacao-v0100.md](../historias/rubrica-operacao-v0100.md); [ADR 0022](../architecture/decisions/0022-rubrica-v4-operacao-retomavel.md).

## Capacidades

- Rubrica `judge.v4`, com a `judge.v3` intacta: a afirmação sem suporte passa a incluir a generalização dita como fato sem fonte na evidência. `--rubric v3|v4` em `eval --judge-repeat` e `eval-calibrate --import`; cada julgamento grava a rubrica usada, e `eval-calibrate` compara vários blocos (juiz, execução e rubrica) com as mesmas notas humanas.
- Comparação retomável: se o processo morre, a comparação fica `interrupted`, com as células concluídas preservadas e a tentativa em andamento registrada pelo custo reservado; `POST /v1/comparisons/{id}/resume` roda só as células que faltam e reserva só o que falta.
- `GET /metrics` no formato de texto do Prometheus, calculado dos traces e do ledger, com todo rótulo vindo de um conjunto fechado no código; quatro regras de alerta em `alerts/rules.yml` (orçamento, falha de ferramenta, taxa de encaminhamento e p95 de duração).

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte estrita | 2.148 testes aprovados, Ruff e skills limpos; candidato [r1](v0100-candidato-r1.json) |
| Revisão independente | Tarefas 83, 84 e 85 aptas ([83](v0100-reviewer-t83.md), [84](v0100-reviewer-t84.md), [85](v0100-reviewer-t85.md)) |
| Rubrica `judge.v4` (24 respostas calibradas, 3 julgamentos cada, dois juízes) | 144 de 144 julgamentos válidos. DeepSeek, v4 contra v3: acordo no veredito de 0,667 para 0,792 e critérios dentro de 0,05, mas 0 das 4 frases genéricas marcadas. `claude-opus-5-5`, v4 contra v3: de 0,875 para 0,917 e 2 das 4 genéricas marcadas (S01 e S21), sem critério pior que 0,05 ([relatório](v0100-juiz-v4.md), [validação](v0100-qa-juiz-r1.md)) |
| Comparação interrompida e retomada | 2 perfis × 3 cenários; a API foi derrubada depois de 1 de 6 células; na subida, a comparação estava `interrupted`, com a célula concluída intacta e o custo reservado da tentativa registrado; `resume` respondeu `202` com 5 células e a comparação terminou `completed`, com uma linha de ledger por célula; um segundo `resume` recebeu `409 comparison_completed` ([validação](v0100-qa-ops-r1.md)) |
| `/metrics` | Conferiu com os traces e o ledger: 6 requisições, 24 chamadas de modelo, custo por provedor igual ao ledger liquidado e `budget_remaining_usd` igual ao `/ready`; nenhum rótulo com identificador ([validação](v0100-qa-ops-r1.md)) |

## Gasto

| Item | US$ |
| --- | ---: |
| `judge.v4` com DeepSeek, ledger do projeto | 0,02514668 |
| `judge.v4` com `claude-opus-5-5`, ledger Anthropic separado | 1,374132 |
| Comparação retomada e `/metrics`, ledger isolado | 0,00566829 |
| **Total** | **1,40494697** |

## Decisão

Pela regra escrita antes da medição (D2), a `judge.v4` não passou a padrão: com o DeepSeek, nenhuma das 4 frases genéricas foi marcada. A diferença entre os juízes vinha da rubrica e do modelo juntos ([ADR 0022](../architecture/decisions/0022-rubrica-v4-operacao-retomavel.md)). Na v0.11.0, o `judge.v5`, que julga afirmação por afirmação, passou a padrão ([v0110-resultado.md](v0110-resultado.md)).
