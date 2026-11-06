# História: a rubrica aprende a ver a frase genérica, e a operação sobrevive a um reinício

Versão 1, 2026-11-05; roteiro aprovado com a spec. Spec: [rubrica-operacao-v0100.md](../specs/rubrica-operacao-v0100.md).

## Pessoas e objetivo

- **Responsável** (Lauro): quer saber se a lacuna encontrada na v0.9.0 era mesmo da rubrica, com as mesmas 24 notas que já deu.
- **Operador da plataforma** (papel vivido pelo QA): inicia uma comparação de perfis, perde a API no meio, e quer retomar sem pagar de novo pelo que já rodou; quer ver as métricas que um alerta usaria.
- **Avaliador técnico**: procura `/metrics` e regras de alerta versionadas, e uma comparação que não morre no reinício.

## Critérios e candidato

CA-57, CA-58, CA-59; tarefas 83 a 86. Candidato fixado em `docs/evidence/v0100-candidato-rN.json`.

## Condições iniciais

`main` com a v0.9.0 (tag) e o CI verde. Runtime de QA `.pytest_cache/qa-v080-r1/runtime` preservado (notas humanas, julgamentos v3 dos dois juízes). Ledger Anthropic com US$2,52 do cap; ledger do projeto em US$1,42 de US$2,00. Seed ressemeada antes de qualquer fase real após a meia-noite.

## Momentos da história

| Momento | Ação pela entrada normal | Resultado esperado | Critério | Evidência | Ponto de retorno |
| --- | --- | --- | --- | --- | --- |
| 1. v4 com DeepSeek | `eval --judge-repeat 3 --answers-from docs/evidence/v080-all-r3.json --only-sample docs/evidence/v080-calibracao-amostra.csv --rubric v4 --name v0100-juiz-deepseek-v4` (juiz padrão) | 72 julgamentos `judge.v4` do DeepSeek | CA-57 | relatório da execução, ledger do projeto | Não se aplica |
| 2. v4 com Opus | Mesmo comando com `JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5 --name v0100-juiz-opus-v4` e o ledger Anthropic | 72 julgamentos `judge.v4` do Opus | CA-57 | relatório, ledger Anthropic | Não se aplica |
| 3. v3 × v4 | `eval-calibrate --import <csv> --rater lauro --judge deepseek/deepseek-flash --judge-run v0100-juiz-deepseek-v4 --rubric v4 --campaign v0100-juiz-v4 --out docs/evidence/v0100-juiz-v4.md` e o mesmo para o Opus | Relatório com os quatro blocos (DeepSeek v3, DeepSeek v4, Opus v3, Opus v4) contra as mesmas 24 notas; condição (b) reavaliada; regra D2 aplicada pelo Supervisor | CA-57 | `docs/evidence/v0100-juiz-v4.md` | Não se aplica |
| 4. Comparação interrompida | Operador inicia uma comparação (2 perfis × 3 cenários) pela API; o QA mata a API quando a primeira célula terminou; reinicia | A comparação aparece `interrupted`, com a célula concluída preservada e custo coerente | CA-58 | `GET /v1/comparisons/{id}`, ledger | Não se aplica |
| 5. Retomada | `POST /v1/comparisons/{id}/resume` | Só as células sem resultado rodam; estado final `completed`; nenhuma célula paga duas vezes (ledger antes/depois) | CA-58 | API, ledger, trace | Não se aplica |
| 6. Métricas | `GET /metrics` depois dos momentos 4 e 5 | Texto Prometheus válido com `requests_total{route,status}`, `model_calls_total`, `cost_usd_total`, `tool_failures_total`, `handoffs_total`, `request_duration_seconds`; valores coerentes com o trace | CA-59 | saída HTTP | Não se aplica |
| 7. Regras de alerta | Leitura de `alerts/rules.yml` | Quatro regras, cada uma sobre métrica existente, com `runbook` para o README | CA-59 | arquivo e teste | Não se aplica |
| 8. Regressão | Suíte estrita; 44 casos e 4 conversas offline iguais | Verde; nada muda para o lojista | Regressão | suíte | Não se aplica |

Momentos 1 a 3 só dependem da tarefa 83; 4 a 7 das tarefas 84 e 85.

## Experiência e exceções

Nenhuma nota humana nova. Se o Opus recusar algum julgamento, vale a regra operacional da v0.9.0 (copiar o relatório, rejulgar só os IDs). Se o `CHECK` da tabela impedir `interrupted`, a migração 0012 entra e é testada nos dois sentidos. Se a API for morta antes de qualquer célula terminar, a retomada roda tudo e o relatório diz isso.

## Resultado da rodada

(Preenchido pelo Supervisor após o QA.)

## Como terminou

(Preenchido pelo Supervisor após o QA.)
