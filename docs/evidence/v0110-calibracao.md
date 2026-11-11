# Calibração do juiz contra rótulos de referência (v0.11.0)

**Resultado:** nas 36 respostas seladas, o `judge.v5` (`deepseek/deepseek-flash`) teve κ **0,647** (IC 95% 0,28 a 0,92) no veredito `unsupported_claim` contra os rótulos de referência, contra 0,538 (IC 95% −0,04 a 0,89) do `judge.v3`. No acordo ±1 por critério, o `judge.v5` ficou em 0,972 / 0,972 / 1,000 / 1,000 (fundamentação, correção factual, relevância, utilidade), contra 0,944 / 0,917 / 0,972 / 0,917 do `judge.v3`. A regra escrita antes da medição (κ ≥ 0,6 e nenhum critério caindo mais de 0,05) foi cumprida, e o `judge.v5` passou a rubrica padrão ([ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md)). Nas 60 respostas (seladas e ajuste), o κ do `judge.v5` foi 0,628 (IC 95% 0,36 a 0,85); por afirmação, 0,498 nas quatro marcas (210 afirmações).

O relatório abaixo foi recalculado a partir dos arquivos versionados, sem chamada a modelo, e reproduz os números da decisão.

## Método

- **Amostra.** 36 respostas sorteadas com a semente 20261107 das campanhas `v0110-qa` e `v0110-qa-holdout-v080` ([relatório](v0110-qa.md), [holdout](v0110-qa-holdout-v080.md)), estratificadas por rota e split, enriquecidas em `knowledge` e `knowledge_and_support` e seladas por hash antes de qualquer julgamento: [selo](../../tests/scenarios/calibration_v0110.sha256), [respostas](v0110-calibracao-amostra.csv) e [afirmações](v0110-calibracao-amostra-claims.csv) em branco, como foram entregues aos rotuladores. O conjunto de ajuste são as 24 respostas rotuladas na v0.8.0 ([amostra](v080-calibracao-amostra.csv)), usadas para ajustar o `judge.v5` antes das seladas ([ajuste](v0110-v5-ajuste.md)).
- **Rótulos.** O responsável rotulou as 36 seladas (notas de 1 a 5 e uma marca por afirmação) e as 24 de ajuste (notas da v0.8.0). Um painel de dois modelos, `gpt-6-luna` (modelo A) e `claude-opus-5-5` (modelo B), rotulou as mesmas 60 respostas, cada modelo em sessão própria, com a mesma instrução e sem ver nota de ninguém. O rótulo do painel é o valor em que os dois membros concordam (`eval-calibrate --merge-panel`).
- **Referência.** Onde o responsável e o painel concordam, o rótulo de referência é esse valor. As divergências de 43 respostas foram adjudicadas a partir das propostas de um terceiro modelo (`gpt-6.1-sol`), aprovadas pelo responsável. No veredito das seladas, o responsável e o painel concordaram em 31 de 32 respostas (κ 0,871).
- **Juiz.** O `judge.v5` foi congelado no blob `5430b33` antes do primeiro julgamento das 36 e julgou as 60 respostas três vezes, com a lista de afirmações selada: 201 julgamentos, 180 completos e 21 falhas de formato rejulgadas só nas respostas afetadas. A comparação usa o primeiro julgamento completo de cada resposta. O `judge.v3` entra com o julgamento de cada resposta na campanha em que ela foi gravada.
- **Candidatos.** A regra comparou o juiz padrão (DeepSeek) sob `judge.v3` e `judge.v5`. A sonda de custo com `claude-sonnet-5-5` não rodou: a reserva de saída de cinco chamadas (até US$0,036 cada, US$0,18) passava do saldo da campanha (US$0,087). Sem um segundo juiz, o ensemble não se aplica.

## Arquivos

| Arquivo | Conteúdo | Notas de |
| --- | --- | --- |
| [v0110-calibracao-responsavel-seladas.csv](v0110-calibracao-responsavel-seladas.csv), [afirmações](v0110-calibracao-responsavel-seladas-claims.csv) | Notas e marcas por afirmação nas 36 seladas | Responsável |
| [v0110-calibracao-responsavel-ajuste.csv](v0110-calibracao-responsavel-ajuste.csv) | Notas nas 24 de ajuste: as da v0.8.0, com o veredito da S04 adjudicado para "sim" em 2026-11-08 ([ajuste](v0110-v5-ajuste.md)) | Responsável |
| [v0110-calibracao-modelo-a-seladas.csv](v0110-calibracao-modelo-a-seladas.csv), [afirmações](v0110-calibracao-modelo-a-seladas-claims.csv), [ajuste](v0110-calibracao-modelo-a-ajuste.csv), [afirmações do ajuste](v0110-calibracao-modelo-a-ajuste-claims.csv) | Notas e marcas nas 60 respostas | Modelo A do painel, `gpt-6-luna` |
| [v0110-calibracao-modelo-b-seladas.csv](v0110-calibracao-modelo-b-seladas.csv), [afirmações](v0110-calibracao-modelo-b-seladas-claims.csv), [ajuste](v0110-calibracao-modelo-b-ajuste.csv), [afirmações do ajuste](v0110-calibracao-modelo-b-ajuste-claims.csv) | Notas e marcas nas 60 respostas | Modelo B do painel, `claude-opus-5-5` |
| [v0110-calibracao-painel-seladas.csv](v0110-calibracao-painel-seladas.csv), [afirmações](v0110-calibracao-painel-seladas-claims.csv), [ajuste](v0110-calibracao-painel-ajuste.csv), [afirmações do ajuste](v0110-calibracao-painel-ajuste-claims.csv) | Junção dos dois membros: o valor em que concordam, vazio onde divergem | Painel (A e B) |
| [v0110-calibracao-adjudicacao.csv](v0110-calibracao-adjudicacao.csv) | Valor adotado e motivo em 43 respostas | Proposta de `gpt-6.1-sol`, aprovada pelo responsável |
| [v0110-calibracao-rotulos-referencia.csv](v0110-calibracao-rotulos-referencia.csv) | Rótulo de referência das 60 respostas, com os campos que vieram da adjudicação | Calculado dos arquivos acima |
| `v0110-calibracao-juiz/` (29 relatórios JSON) | Julgamentos `judge.v5`: 13 lotes e 16 rejulgamentos de falhas de formato, numerados na ordem em que rodaram | Juiz `deepseek/deepseek-flash` |
| [v0110-qa.json](v0110-qa.json), [v0110-qa-holdout-v080.json](v0110-qa-holdout-v080.json), [v080-all-r3.json](v080-all-r3.json) | Julgamentos `judge.v3` das respostas seladas e das de ajuste | Juiz `deepseek/deepseek-flash` |

## Como reproduzir

Sem chamada a modelo, a partir de `docs/evidence/`, com um runtime novo (`RUNTIME_DIR` e `BUDGET_RUNTIME_DIR` numa pasta vazia). `eval-calibrate --import` lê os julgamentos de `run_evaluations`; o trecho `carga.py` abaixo grava ali, num banco novo, os julgamentos guardados nos relatórios JSON.

```python
# carga.py: grava em run_evaluations os julgamentos dos relatórios JSON (sem chamada a modelo)
import glob, json, sys
from merchant_assistant.data.db import connect

# relatório JSON -> nome da execução do juiz (None: julgamento da v0.8.0, sem nome, lido como "legado")
runs = [("v080-all-r3.json", None), ("v0110-qa.json", "v0110-qa"), ("v0110-qa-holdout-v080.json", "v0110-qa-holdout-v080")]
runs += [(p, "v0110-juiz-deepseek-v5-" + ("ajuste" if "ajuste" in p else "seladas"))
         for p in sorted(glob.glob("v0110-calibracao-juiz/*.json"))]  # lotes e rejulgamentos, na ordem em que rodaram
conn, order = connect(sys.argv[1]), 0
for path, run in runs:
    for case in json.load(open(path, encoding="utf-8"))["cases"]:
        for rec in case.get("judge_runs") or [case["judge"]]:
            order += 1
            done = rec["state"] == "completed"
            evaluator = {"provider": rec["provider"], "model": rec["model"]} | ({"run": run} if run else {})
            conn.execute(
                "INSERT INTO run_evaluations (evaluation_id,request_id,principal_id,method,rubric,rubric_version,"
                "evaluator,config_digest,result,evidence,critical_failures,cost_usd,state,error,created_at,scores,"
                "repetition,unsupported_claim,claims) VALUES (?,?,'cli:eval','model','judge',?,?,'-',?,'{}','[]',"
                "?,?,?,?,?,?,?,?)",
                (rec["evaluation_id"], case["request_id"], rec["rubric_version"], json.dumps(evaluator),
                 json.dumps({"usage": rec.get("usage")}), rec.get("cost_usd"), rec["state"], rec.get("error"),
                 f"{order:06d}", json.dumps(rec["scores"]) if done else None, rec.get("repetition", 1),
                 int(rec["unsupported_claim"]) if done else None,
                 json.dumps(rec["claims"], ensure_ascii=False) if done and rec.get("claims") else None))
print(f"julgamentos gravados: {order}")
```

```bash
cd docs/evidence
export RUNTIME_DIR=<pasta vazia> BUDGET_RUNTIME_DIR=<outra pasta vazia>
python carga.py "$RUNTIME_DIR/merchant.sqlite3"          # julgamentos gravados: 540
merchant-assistant eval-calibrate --import \
  --rater lauro:human v0110-calibracao-responsavel-seladas.csv v0110-calibracao-responsavel-seladas-claims.csv \
  --rater lauro:human v0110-calibracao-responsavel-ajuste.csv \
  --rater painel:model:claude-opus-5-5+gpt-6-luna v0110-calibracao-painel-seladas.csv v0110-calibracao-painel-seladas-claims.csv \
  --rater painel:model:claude-opus-5-5+gpt-6-luna v0110-calibracao-painel-ajuste.csv v0110-calibracao-painel-ajuste-claims.csv \
  --adjudication v0110-calibracao-adjudicacao.csv \
  --judge deepseek/deepseek-flash --judge-run v0110-qa+v0110-qa-holdout-v080+legado --rubric v3 \
  --judge deepseek/deepseek-flash --judge-run v0110-juiz-deepseek-v5-seladas+v0110-juiz-deepseek-v5-ajuste --rubric v5 \
  --out v0110-calibracao.md
```

Saída do import: 60 respostas avaliadas, 59 pelos dois rotuladores, 60 com rótulo de referência, 36 seladas, 43 adjudicadas. A junção do painel também se reproduz byte a byte a partir dos arquivos de cada membro:

```bash
merchant-assistant eval-calibrate --merge-panel v0110-calibracao-modelo-a-seladas-claims.csv v0110-calibracao-modelo-b-seladas-claims.csv \
  --sample-csv v0110-calibracao-modelo-a-seladas.csv v0110-calibracao-modelo-b-seladas.csv --out <pasta>/seladas.csv
```

(e o mesmo com `ajuste` no lugar de `seladas`).

O recálculo dá os mesmos números da medição de 2026-11-09 em todas as tabelas de concordância, κ, rótulos de referência, adjudicação e na regra D6(g). Mudam a data, os nomes dos arquivos e, no bloco A (`judge.v3`), a consistência entre repetições e o custo por julgamento: o banco da campanha guardava outros 48 julgamentos `judge.v3`, anteriores à v0.9.0, sobre as 24 respostas de ajuste, que não estão em relatório versionado. Com eles, o bloco A somava 108 julgamentos e US$0,000398 por julgamento; com os 60 julgamentos versionados, soma US$0,000519 por julgamento. Esses julgamentos não entram no κ, que usa o primeiro julgamento de cada resposta.

A seguir, a saída do comando, sem edição além dos títulos, um nível abaixo.

## Calibração a dois rotuladores (v0.11.0)

Gerado em 2026-11-11T11:34:05+00:00. Rotuladores `lauro` (humano) e `painel` (painel de modelos: `claude-opus-5-5` + `gpt-6-luna`); rótulo ouro = valor adjudicado, senão o valor em que os dois concordam (spec v0.11.0 D4).

| Rotulador | Tipo | Arquivo | Campanha | Semente | Avaliadas | Afirmações | Selo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `lauro` | humano | `v0110-calibracao-responsavel-seladas.csv` | `v0110-qa` | 20261107 | 36 | `v0110-calibracao-responsavel-seladas-claims.csv` | `calibration_v0110` conferido |
| `lauro` | humano | `v0110-calibracao-responsavel-ajuste.csv` | `v080-all-r3` | 20261104 | 24 | sem CSV (veredito do CSV de notas) | - |
| `painel` | painel de modelos: `claude-opus-5-5` + `gpt-6-luna` | `v0110-calibracao-painel-seladas.csv` | `v0110-qa` | 20261107 | 35 | `v0110-calibracao-painel-seladas-claims.csv` | `calibration_v0110` conferido |
| `painel` | painel de modelos: `claude-opus-5-5` + `gpt-6-luna` | `v0110-calibracao-painel-ajuste.csv` | `v080-all-r3` | 20261104 | 24 | `v0110-calibracao-painel-ajuste-claims.csv` | - |

> `painel` é um painel de modelos, declarado em `--rater`: suas notas e marcas são rótulo de modelo, não humano, e aparecem nas tabelas como `painel`.

Respostas avaliadas por pelo menos um rotulador: 60; pelos dois: 59; com rótulo ouro: 60; adjudicadas: 43. Seladas: 36.

| Bloco | Juiz | Rubrica | Execuções |
| --- | --- | --- | --- |
| A | `deepseek/deepseek-flash` | `judge.v3` | `v0110-qa`, `v0110-qa-holdout-v080`, `legado` |
| B | `deepseek/deepseek-flash` | `judge.v5` | `v0110-juiz-deepseek-v5-seladas`, `v0110-juiz-deepseek-v5-ajuste` |

> Ressalva de amostra pequena (D19): 60 respostas. Os intervalos (95%) mostram a margem; leia como indicação de quanto confiar em cada juiz, não como prova.

### Seladas (36 respostas)

Avaliadas pelos dois: 35; com rótulo ouro: 36.

#### Por critério

| Critério | Par | n | Exata | ±1 | Kappa quadrático | Viés |
| --- | --- | --- | --- | --- | --- | --- |
| groundedness (fundamentação) | humano × painel | 26 | 0.962 (IC 95%: 0.81 a 0.99) | 1.000 (IC 95%: 0.87 a 1.00) | 0.954 (IC 95%: 0.92 a 1.00) | -0.04 |
| groundedness (fundamentação) | humano × juiz A | 36 | 0.722 (IC 95%: 0.56 a 0.84) | 0.944 (IC 95%: 0.82 a 0.98) | 0.778 (IC 95%: 0.68 a 0.85) | +0.06 |
| groundedness (fundamentação) | painel × juiz A | 26 | 0.846 (IC 95%: 0.66 a 0.94) | 1.000 (IC 95%: 0.87 a 1.00) | 0.879 (IC 95%: 0.00 a 0.97) | -0.08 |
| groundedness (fundamentação) | ouro × juiz A | 36 | 0.722 (IC 95%: 0.56 a 0.84) | 0.944 (IC 95%: 0.82 a 0.98) | 0.789 (IC 95%: 0.66 a 0.89) | +0.11 |
| groundedness (fundamentação) | humano × juiz B | 36 | 0.833 (IC 95%: 0.68 a 0.92) | 0.972 (IC 95%: 0.86 a 1.00) | 0.868 (IC 95%: 0.77 a 0.95) | +0.08 |
| groundedness (fundamentação) | painel × juiz B | 26 | 0.962 (IC 95%: 0.81 a 0.99) | 1.000 (IC 95%: 0.87 a 1.00) | 0.965 (IC 95%: 0.79 a 1.00) | -0.04 |
| groundedness (fundamentação) | ouro × juiz B | 36 | 0.833 (IC 95%: 0.68 a 0.92) | 0.972 (IC 95%: 0.86 a 1.00) | 0.875 (IC 95%: 0.75 a 0.96) | +0.14 |
| factual_correctness (correção factual) | humano × painel | 26 | 0.923 (IC 95%: 0.76 a 0.98) | 1.000 (IC 95%: 0.87 a 1.00) | 0.814 (IC 95%: -0.05 a 1.00) | +0.00 |
| factual_correctness (correção factual) | humano × juiz A | 36 | 0.722 (IC 95%: 0.56 a 0.84) | 0.889 (IC 95%: 0.75 a 0.96) | 0.562 (IC 95%: 0.20 a 0.81) | -0.17 |
| factual_correctness (correção factual) | painel × juiz A | 26 | 0.808 (IC 95%: 0.62 a 0.91) | 1.000 (IC 95%: 0.87 a 1.00) | 0.735 (IC 95%: -0.08 a 0.88) | -0.12 |
| factual_correctness (correção factual) | ouro × juiz A | 36 | 0.722 (IC 95%: 0.56 a 0.84) | 0.917 (IC 95%: 0.78 a 0.97) | 0.622 (IC 95%: 0.31 a 0.84) | -0.14 |
| factual_correctness (correção factual) | humano × juiz B | 36 | 0.778 (IC 95%: 0.62 a 0.88) | 0.944 (IC 95%: 0.82 a 0.98) | 0.707 (IC 95%: 0.36 a 0.90) | -0.11 |
| factual_correctness (correção factual) | painel × juiz B | 26 | 0.962 (IC 95%: 0.81 a 0.99) | 1.000 (IC 95%: 0.87 a 1.00) | 0.926 (IC 95%: 0.79 a 1.00) | -0.04 |
| factual_correctness (correção factual) | ouro × juiz B | 36 | 0.778 (IC 95%: 0.62 a 0.88) | 0.972 (IC 95%: 0.86 a 1.00) | 0.770 (IC 95%: 0.50 a 0.91) | -0.08 |
| relevance (relevância) | humano × painel | 31 | 0.903 (IC 95%: 0.75 a 0.97) | 1.000 (IC 95%: 0.89 a 1.00) | -0.045 (IC 95%: -0.09 a 0.00) | -0.03 |
| relevance (relevância) | humano × juiz A | 36 | 0.694 (IC 95%: 0.53 a 0.82) | 0.917 (IC 95%: 0.78 a 0.97) | -0.037 (IC 95%: -0.17 a 0.18) | -0.25 |
| relevance (relevância) | painel × juiz A | 31 | 0.839 (IC 95%: 0.67 a 0.93) | 0.968 (IC 95%: 0.84 a 0.99) | 0.271 (IC 95%: 0.00 a 0.75) | -0.23 |
| relevance (relevância) | ouro × juiz A | 36 | 0.722 (IC 95%: 0.56 a 0.84) | 0.972 (IC 95%: 0.86 a 1.00) | 0.196 (IC 95%: -0.08 a 0.56) | -0.22 |
| relevance (relevância) | humano × juiz B | 36 | 0.611 (IC 95%: 0.45 a 0.75) | 0.972 (IC 95%: 0.86 a 1.00) | -0.168 (IC 95%: -0.29 a 0.00) | -0.19 |
| relevance (relevância) | painel × juiz B | 31 | 0.774 (IC 95%: 0.60 a 0.89) | 1.000 (IC 95%: 0.89 a 1.00) | 0.289 (IC 95%: 0.00 a 0.62) | -0.23 |
| relevance (relevância) | ouro × juiz B | 36 | 0.667 (IC 95%: 0.50 a 0.80) | 1.000 (IC 95%: 0.90 a 1.00) | 0.073 (IC 95%: -0.19 a 0.38) | -0.17 |
| usefulness (utilidade) | humano × painel | 23 | 0.739 (IC 95%: 0.54 a 0.87) | 1.000 (IC 95%: 0.86 a 1.00) | 0.594 (IC 95%: 0.02 a 0.87) | -0.17 |
| usefulness (utilidade) | humano × juiz A | 36 | 0.667 (IC 95%: 0.50 a 0.80) | 0.917 (IC 95%: 0.78 a 0.97) | 0.392 (IC 95%: 0.07 a 0.69) | +0.19 |
| usefulness (utilidade) | painel × juiz A | 23 | 0.696 (IC 95%: 0.49 a 0.84) | 1.000 (IC 95%: 0.86 a 1.00) | 0.447 (IC 95%: 0.02 a 0.71) | +0.22 |
| usefulness (utilidade) | ouro × juiz A | 36 | 0.667 (IC 95%: 0.50 a 0.80) | 0.917 (IC 95%: 0.78 a 0.97) | 0.392 (IC 95%: 0.07 a 0.69) | +0.19 |
| usefulness (utilidade) | humano × juiz B | 36 | 0.556 (IC 95%: 0.40 a 0.70) | 1.000 (IC 95%: 0.90 a 1.00) | 0.529 (IC 95%: 0.21 a 0.72) | +0.06 |
| usefulness (utilidade) | painel × juiz B | 23 | 0.826 (IC 95%: 0.63 a 0.93) | 1.000 (IC 95%: 0.86 a 1.00) | 0.734 (IC 95%: 0.29 a 0.95) | +0.09 |
| usefulness (utilidade) | ouro × juiz B | 36 | 0.556 (IC 95%: 0.40 a 0.70) | 1.000 (IC 95%: 0.90 a 1.00) | 0.529 (IC 95%: 0.21 a 0.72) | +0.06 |

#### Veredito `unsupported_claim`

| Par | n | Exata | Kappa de Cohen | Ambos sim | Só o 1º | Só o 2º | Nenhum |
| --- | --- | --- | --- | --- | --- | --- | --- |
| humano × painel | 32 | 0.969 (IC 95%: 0.84 a 0.99) | 0.871 (IC 95%: 0.48 a 1.00) | 4 | 0 | 1 | 27 |
| humano × juiz A | 36 | 0.889 (IC 95%: 0.75 a 0.96) | 0.538 (IC 95%: -0.04 a 0.89) | 3 | 3 | 1 | 29 |
| painel × juiz A | 32 | 0.969 (IC 95%: 0.84 a 0.99) | 0.871 (IC 95%: 0.48 a 1.00) | 4 | 1 | 0 | 27 |
| ouro × juiz A | 36 | 0.889 (IC 95%: 0.75 a 0.96) | 0.538 (IC 95%: -0.04 a 0.89) | 3 | 3 | 1 | 29 |
| humano × juiz B | 36 | 0.889 (IC 95%: 0.75 a 0.96) | 0.647 (IC 95%: 0.28 a 0.92) | 5 | 1 | 3 | 27 |
| painel × juiz B | 32 | 0.938 (IC 95%: 0.80 a 0.98) | 0.796 (IC 95%: 0.45 a 1.00) | 5 | 0 | 2 | 25 |
| ouro × juiz B | 36 | 0.889 (IC 95%: 0.75 a 0.96) | 0.647 (IC 95%: 0.28 a 0.92) | 5 | 1 | 3 | 27 |

#### Por afirmação

Afirmações listadas nas respostas deste bloco: 210; com marca ouro: 210.

| Par | Afirmações | Exata (4 marcas) | Kappa (4 marcas) | Exata (sem suporte) | Kappa (sem suporte) | Sem par |
| --- | --- | --- | --- | --- | --- | --- |
| humano × painel | 185 | 0.968 (IC 95%: 0.93 a 0.99) | 0.766 (IC 95%: 0.57 a 0.92) | 0.984 (IC 95%: 0.95 a 0.99) | 0.720 (IC 95%: 0.28 a 1.00) | 0 |
| ouro × juiz B | 210 | 0.881 (IC 95%: 0.83 a 0.92) | 0.498 (IC 95%: 0.35 a 0.64) | 0.948 (IC 95%: 0.91 a 0.97) | 0.494 (IC 95%: 0.19 a 0.72) | 0 |

Bloco B: 36 de 36 julgamentos receberam a lista de afirmações da amostra (`eval --claims-from`) e pareiam pelo número; os demais, pelo texto.

#### Afirmações marcadas pelo ouro

Afirmações que não são `standard` e que o rótulo ouro marca `generic` ou `not_found`, e o que cada juiz fez: a marca do juiz na afirmação pareada (`judge.v5`), `sem par` quando o juiz não listou a mesma afirmação, ou o veredito da resposta (`resposta: sim/não`) para rubricas sem afirmações e para o ensemble.

| Amostra | nº | Tipo | Afirmação | `lauro` | `painel` | Ouro | A | B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v0110-qa:S06 | 2 | fact | a previsão para Porto Alegre é de pancadas de chuva pela manhã | not_found | - | not_found | resposta: não | partial |
| v0110-qa:S06 | 3 | fact | céu nublado depois | not_found | - | not_found | resposta: não | partial |
| v0110-qa:S06 | 4 | value | A temperatura deve cair de cerca de 20 °C para 16 °C | not_found | - | not_found | resposta: não | partial |
| v0110-qa:S14 | 1 | value | O parcelamento pode chegar a até 48x | not_found | not_found | not_found | resposta: sim | not_found |
| v0110-qa:S19 | 3 | fact | Não é necessariamente uma conta bancária tradicional. | partial | not_found | not_found | resposta: sim | not_found |
| v0110-qa:S19 | 4 | fact | Pode ser conta corrente, poupança ou conta de pagamento pré-paga. | not_found | not_found | not_found | resposta: sim | not_found |
| v0110-qa:S19 | 5 | guidance | Para receber vendas, você pode informar sua chave Pix ou os dados da conta. | not_found | - | not_found | resposta: sim | partial |
| v0110-qa:S21 | 7 | fact | As condições específicas dependem do seu contrato. | generic | generic | generic | resposta: sim | generic |
| v0110-qa:S23 | 1 | fact | Sim. | not_found | - | not_found | resposta: não | partial |
| v0110-qa:S23 | 2 | date | Para sábado, 14 de novembro de 2026 | not_found | - | not_found | resposta: não | not_found |
| v0110-qa:S23 | 3 | fact | a previsão indica pancadas de chuva pela manhã e no fim da tarde ou à noite em Curitiba | not_found | - | not_found | resposta: não | partial |
| S25 | 3 | fact | Your conditions depend on your contract. | generic | generic | generic | resposta: não | generic |

Rotas: clarify 1, general_web 4, human_handoff 3, knowledge 14, knowledge_and_support 8, out_of_scope 2, support 4.

### Todas (60 respostas)

Avaliadas pelos dois: 59; com rótulo ouro: 60.

#### Por critério

| Critério | Par | n | Exata | ±1 | Kappa quadrático | Viés |
| --- | --- | --- | --- | --- | --- | --- |
| groundedness (fundamentação) | humano × painel | 43 | 0.907 (IC 95%: 0.78 a 0.96) | 1.000 (IC 95%: 0.92 a 1.00) | 0.869 (IC 95%: 0.69 a 0.96) | -0.05 |
| groundedness (fundamentação) | humano × juiz A | 60 | 0.667 (IC 95%: 0.54 a 0.77) | 0.900 (IC 95%: 0.80 a 0.95) | 0.521 (IC 95%: 0.23 a 0.71) | -0.10 |
| groundedness (fundamentação) | painel × juiz A | 43 | 0.814 (IC 95%: 0.67 a 0.90) | 1.000 (IC 95%: 0.92 a 1.00) | 0.796 (IC 95%: 0.27 a 0.92) | +0.00 |
| groundedness (fundamentação) | ouro × juiz A | 60 | 0.667 (IC 95%: 0.54 a 0.77) | 0.933 (IC 95%: 0.84 a 0.97) | 0.753 (IC 95%: 0.61 a 0.85) | +0.22 |
| groundedness (fundamentação) | humano × juiz B | 60 | 0.733 (IC 95%: 0.61 a 0.83) | 0.917 (IC 95%: 0.82 a 0.96) | 0.627 (IC 95%: 0.35 a 0.82) | -0.13 |
| groundedness (fundamentação) | painel × juiz B | 43 | 0.953 (IC 95%: 0.85 a 0.99) | 1.000 (IC 95%: 0.92 a 1.00) | 0.943 (IC 95%: 0.78 a 1.00) | +0.00 |
| groundedness (fundamentação) | ouro × juiz B | 60 | 0.733 (IC 95%: 0.61 a 0.83) | 0.900 (IC 95%: 0.80 a 0.95) | 0.730 (IC 95%: 0.60 a 0.84) | +0.18 |
| factual_correctness (correção factual) | humano × painel | 43 | 0.837 (IC 95%: 0.70 a 0.92) | 1.000 (IC 95%: 0.92 a 1.00) | 0.543 (IC 95%: -0.07 a 0.84) | -0.12 |
| factual_correctness (correção factual) | humano × juiz A | 60 | 0.683 (IC 95%: 0.56 a 0.79) | 0.867 (IC 95%: 0.76 a 0.93) | 0.356 (IC 95%: 0.03 a 0.61) | -0.27 |
| factual_correctness (correção factual) | painel × juiz A | 43 | 0.814 (IC 95%: 0.67 a 0.90) | 1.000 (IC 95%: 0.92 a 1.00) | 0.685 (IC 95%: 0.19 a 0.85) | -0.05 |
| factual_correctness (correção factual) | ouro × juiz A | 60 | 0.717 (IC 95%: 0.59 a 0.81) | 0.933 (IC 95%: 0.84 a 0.97) | 0.647 (IC 95%: 0.41 a 0.80) | -0.05 |
| factual_correctness (correção factual) | humano × juiz B | 60 | 0.700 (IC 95%: 0.57 a 0.80) | 0.883 (IC 95%: 0.78 a 0.94) | 0.487 (IC 95%: 0.18 a 0.70) | -0.32 |
| factual_correctness (correção factual) | painel × juiz B | 43 | 0.953 (IC 95%: 0.85 a 0.99) | 1.000 (IC 95%: 0.92 a 1.00) | 0.915 (IC 95%: 0.82 a 1.00) | -0.05 |
| factual_correctness (correção factual) | ouro × juiz B | 60 | 0.783 (IC 95%: 0.66 a 0.87) | 0.983 (IC 95%: 0.91 a 1.00) | 0.806 (IC 95%: 0.66 a 0.90) | -0.10 |
| relevance (relevância) | humano × painel | 54 | 0.907 (IC 95%: 0.80 a 0.96) | 1.000 (IC 95%: 0.93 a 1.00) | -0.031 (IC 95%: -0.07 a 0.00) | -0.06 |
| relevance (relevância) | humano × juiz A | 60 | 0.717 (IC 95%: 0.59 a 0.81) | 0.950 (IC 95%: 0.86 a 0.98) | -0.018 (IC 95%: -0.13 a 0.14) | -0.25 |
| relevance (relevância) | painel × juiz A | 54 | 0.833 (IC 95%: 0.71 a 0.91) | 0.981 (IC 95%: 0.90 a 1.00) | 0.314 (IC 95%: 0.05 a 0.67) | -0.20 |
| relevance (relevância) | ouro × juiz A | 60 | 0.733 (IC 95%: 0.61 a 0.83) | 0.983 (IC 95%: 0.91 a 1.00) | 0.168 (IC 95%: -0.05 a 0.44) | -0.23 |
| relevance (relevância) | humano × juiz B | 60 | 0.700 (IC 95%: 0.57 a 0.80) | 0.983 (IC 95%: 0.91 a 1.00) | -0.105 (IC 95%: -0.19 a 0.00) | -0.18 |
| relevance (relevância) | painel × juiz B | 54 | 0.833 (IC 95%: 0.71 a 0.91) | 1.000 (IC 95%: 0.93 a 1.00) | 0.403 (IC 95%: 0.11 a 0.68) | -0.17 |
| relevance (relevância) | ouro × juiz B | 60 | 0.733 (IC 95%: 0.61 a 0.83) | 1.000 (IC 95%: 0.94 a 1.00) | 0.086 (IC 95%: -0.12 a 0.34) | -0.17 |
| usefulness (utilidade) | humano × painel | 39 | 0.692 (IC 95%: 0.54 a 0.81) | 1.000 (IC 95%: 0.91 a 1.00) | 0.589 (IC 95%: 0.20 a 0.79) | -0.26 |
| usefulness (utilidade) | humano × juiz A | 60 | 0.633 (IC 95%: 0.51 a 0.74) | 0.917 (IC 95%: 0.82 a 0.96) | 0.251 (IC 95%: -0.03 a 0.53) | +0.05 |
| usefulness (utilidade) | painel × juiz A | 39 | 0.615 (IC 95%: 0.46 a 0.75) | 0.949 (IC 95%: 0.83 a 0.99) | 0.230 (IC 95%: -0.07 a 0.50) | +0.23 |
| usefulness (utilidade) | ouro × juiz A | 60 | 0.617 (IC 95%: 0.49 a 0.73) | 0.917 (IC 95%: 0.82 a 0.96) | 0.383 (IC 95%: 0.13 a 0.59) | +0.23 |
| usefulness (utilidade) | humano × juiz B | 60 | 0.517 (IC 95%: 0.39 a 0.64) | 1.000 (IC 95%: 0.94 a 1.00) | 0.422 (IC 95%: 0.19 a 0.59) | -0.08 |
| usefulness (utilidade) | painel × juiz B | 39 | 0.769 (IC 95%: 0.62 a 0.87) | 1.000 (IC 95%: 0.91 a 1.00) | 0.694 (IC 95%: 0.40 a 0.87) | +0.08 |
| usefulness (utilidade) | ouro × juiz B | 60 | 0.567 (IC 95%: 0.44 a 0.68) | 1.000 (IC 95%: 0.94 a 1.00) | 0.563 (IC 95%: 0.38 a 0.70) | +0.10 |

#### Veredito `unsupported_claim`

| Par | n | Exata | Kappa de Cohen | Ambos sim | Só o 1º | Só o 2º | Nenhum |
| --- | --- | --- | --- | --- | --- | --- | --- |
| humano × painel | 51 | 0.980 (IC 95%: 0.90 a 1.00) | 0.935 (IC 95%: 0.75 a 1.00) | 9 | 0 | 1 | 41 |
| humano × juiz A | 60 | 0.783 (IC 95%: 0.66 a 0.87) | 0.191 (IC 95%: -0.11 a 0.48) | 3 | 8 | 5 | 44 |
| painel × juiz A | 51 | 0.863 (IC 95%: 0.74 a 0.93) | 0.463 (IC 95%: 0.11 a 0.77) | 4 | 6 | 1 | 40 |
| ouro × juiz A | 60 | 0.817 (IC 95%: 0.70 a 0.89) | 0.421 (IC 95%: 0.13 a 0.67) | 6 | 9 | 2 | 43 |
| humano × juiz B | 60 | 0.933 (IC 95%: 0.84 a 0.97) | 0.792 (IC 95%: 0.56 a 0.96) | 10 | 1 | 3 | 46 |
| painel × juiz B | 51 | 0.961 (IC 95%: 0.87 a 0.99) | 0.884 (IC 95%: 0.67 a 1.00) | 10 | 0 | 2 | 39 |
| ouro × juiz B | 60 | 0.867 (IC 95%: 0.76 a 0.93) | 0.628 (IC 95%: 0.36 a 0.85) | 10 | 5 | 3 | 42 |

#### Por afirmação

Afirmações listadas nas respostas deste bloco: 341; com marca ouro: 210.

| Par | Afirmações | Exata (4 marcas) | Kappa (4 marcas) | Exata (sem suporte) | Kappa (sem suporte) | Sem par |
| --- | --- | --- | --- | --- | --- | --- |
| humano × painel | 185 | 0.968 (IC 95%: 0.93 a 0.99) | 0.766 (IC 95%: 0.57 a 0.92) | 0.984 (IC 95%: 0.95 a 0.99) | 0.720 (IC 95%: 0.28 a 1.00) | 0 |
| ouro × juiz B | 210 | 0.881 (IC 95%: 0.83 a 0.92) | 0.498 (IC 95%: 0.35 a 0.64) | 0.948 (IC 95%: 0.91 a 0.97) | 0.494 (IC 95%: 0.19 a 0.72) | 0 |

Bloco B: 60 de 60 julgamentos receberam a lista de afirmações da amostra (`eval --claims-from`) e pareiam pelo número; os demais, pelo texto.

#### Afirmações marcadas pelo ouro

Afirmações que não são `standard` e que o rótulo ouro marca `generic` ou `not_found`, e o que cada juiz fez: a marca do juiz na afirmação pareada (`judge.v5`), `sem par` quando o juiz não listou a mesma afirmação, ou o veredito da resposta (`resposta: sim/não`) para rubricas sem afirmações e para o ensemble.

| Amostra | nº | Tipo | Afirmação | `lauro` | `painel` | Ouro | A | B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v0110-qa:S06 | 2 | fact | a previsão para Porto Alegre é de pancadas de chuva pela manhã | not_found | - | not_found | resposta: não | partial |
| v0110-qa:S06 | 3 | fact | céu nublado depois | not_found | - | not_found | resposta: não | partial |
| v0110-qa:S06 | 4 | value | A temperatura deve cair de cerca de 20 °C para 16 °C | not_found | - | not_found | resposta: não | partial |
| v0110-qa:S14 | 1 | value | O parcelamento pode chegar a até 48x | not_found | not_found | not_found | resposta: sim | not_found |
| v0110-qa:S19 | 3 | fact | Não é necessariamente uma conta bancária tradicional. | partial | not_found | not_found | resposta: sim | not_found |
| v0110-qa:S19 | 4 | fact | Pode ser conta corrente, poupança ou conta de pagamento pré-paga. | not_found | not_found | not_found | resposta: sim | not_found |
| v0110-qa:S19 | 5 | guidance | Para receber vendas, você pode informar sua chave Pix ou os dados da conta. | not_found | - | not_found | resposta: sim | partial |
| v0110-qa:S21 | 7 | fact | As condições específicas dependem do seu contrato. | generic | generic | generic | resposta: sim | generic |
| v0110-qa:S23 | 1 | fact | Sim. | not_found | - | not_found | resposta: não | partial |
| v0110-qa:S23 | 2 | date | Para sábado, 14 de novembro de 2026 | not_found | - | not_found | resposta: não | not_found |
| v0110-qa:S23 | 3 | fact | a previsão indica pancadas de chuva pela manhã e no fim da tarde ou à noite em Curitiba | not_found | - | not_found | resposta: não | partial |
| S25 | 3 | fact | Your conditions depend on your contract. | generic | generic | generic | resposta: não | generic |

Rotas: clarify 2, general_web 8, human_handoff 5, knowledge 20, knowledge_and_support 12, out_of_scope 4, support 9.

### Regra D6(g) da v0.11.0 (informativa)

Calculada com os números das respostas seladas, sem decidir. Vira padrão o candidato com kappa do veredito ≥ 0.6 contra o rótulo ouro (adjudicado pelo rotulador humano) nas seladas, sem piorar o ±1 de nenhum critério em mais de 0.05 em relação ao juiz padrão (`judge.v3` com `deepseek/deepseek-flash`); empate decide pelo custo. A decisão é registrada na ADR 0023.

n = 36 respostas seladas com rótulo ouro e avaliadas pelo rotulador humano (`lauro`).

| Candidato | Kappa do veredito | ≥ 0.6 | ±1 por critério (diferença para a base) | Não piora > 0.05 | Custo por julgamento (US$) |
| --- | --- | --- | --- | --- | --- |
| A `deepseek/deepseek-flash` judge.v3 | 0.538 (IC 95%: -0.04 a 0.89) | não | groundedness 0.944 (+0.000), factual_correctness 0.917 (+0.000), relevance 0.972 (+0.000), usefulness 0.917 (+0.000) | sim | 0.000519 |
| B `deepseek/deepseek-flash` judge.v5 | 0.647 (IC 95%: 0.28 a 0.92) | sim | groundedness 0.972 (+0.028), factual_correctness 0.972 (+0.056), relevance 1.000 (+0.028), usefulness 1.000 (+0.083) | sim | 0.000945 |

Atendem às duas condições: B (em ordem de custo por julgamento).

### Adjudicação

| Amostra | Veredito | Notas | Afirmações | Motivo |
| --- | --- | --- | --- | --- |
| v0110-qa:S01 | - | usefulness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Dá próximos passos para as duas negativas registradas, mas não pede o código da tela para orientar sobre um possível Erro ADQ. |
| v0110-qa:S02 | não | groundedness=4 factual_correctness=3 relevance=4 usefulness=3 | 1=supported 2=supported 3=partial 4=supported 5=supported | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O registro confirma conta ativa e terminal indisponível. A página apoia a orientação geral sobre POS e TEF. \| factual_correctness: A frase de prontidão do POS pode ser lida como liberação do Mastercard, apesar de o registro indicar disponibilidade falsa. \| relevance: Responde à pergunta sobre o Mastercard no terminal, mas acrescenta orientação geral de POS e TEF que deixa margem a dúvida. \| usefulness: Informa a indisponibilidade, mas a frase de prontidão cria ambiguidade e só oferece um próximo passo para TEF. \| unsupported_claim: As duas condições da conta vêm da ferramenta, e a prontidão do POS tem suporte apenas no sentido geral da página. \| afirmação 1: O item 1 registra Mastercard com status ativo. \| afirmação 2: O item 1 registra device_availability.available como false. \| afirmação 3: O item 2 descreve a prontidão geral do POS, mas o item 1 registra Mastercard indisponível no terminal da conta. \| afirmação 4: O item 2 diz que POS não requer atualização. \| afirmação 5: O item 2 manda quem usa TEF procurar a própria TEF house para suporte. |
| v0110-qa:S03 | não | factual_correctness=4 | 6=partial | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. factual_correctness: O item 1 confirma uso, criação e migração do link, mas o valor atribuído à página não aparece no trecho visível. \| unsupported_claim: O item 1 sustenta o uso e a migração. O preço fica parcial porque o trecho termina na abertura da lista de vantagens do pacote. \| afirmação 6: O item 1 termina ao introduzir as vantagens do novo pacote, sem mostrar a lista onde a cobrança poderia constar. |
| v0110-qa:S04 | - | groundedness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: Agenda, repasses e procedimento sustentam a maior parte da resposta. A agenda cortada oculta a modalidade Pix, embora o total permita inferir o valor. |
| v0110-qa:S05 | - | usefulness=5 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: A pergunta breve solicita exatamente o detalhe que falta para começar a ajudar. |
| v0110-qa:S06 | sim | groundedness=1 factual_correctness=3 usefulness=3 | 1=partial 2=not_found 3=not_found 4=not_found | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O pacote não contém o texto da previsão. A fonte meteorológica consta apenas na lista de citações. \| factual_correctness: Chuva, nebulosidade e temperaturas não são verificáveis com a fonte listada. Nenhum item contradiz a previsão. \| usefulness: Oferece horários e temperaturas úteis para planejar o dia, mas o texto da previsão citada não foi gravado. \| unsupported_claim: Chuva, nebulosidade e temperaturas são afirmações materiais sem item de evidência. \| afirmação 1: A data apenas situa o amanhã pedido e nenhum item indica outro dia. \| afirmação 2: O provedor é apenas citado. Nenhum item registra chuva pela manhã em Porto Alegre. \| afirmação 3: O pacote não registra previsão de nebulosidade para o restante do dia. \| afirmação 4: O pacote não traz previsão com os valores de 20 °C e 16 °C. |
| v0110-qa:S07 | - | usefulness=5 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Compara recursos de cada modelo e destaca pagamentos e comprovantes comuns, com apoio dos itens 1 e 2. |
| v0110-qa:S08 | - | usefulness=5 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Pede o código exato e dá um procedimento completo, limitado aos três códigos ADQ documentados. |
| v0110-qa:S09 | - | - | 9=partial | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. afirmação 9: O item 3 confirma o perfil administrativo, mas o segundo requisito aparece ocultado como credencial. |
| v0110-qa:S14 | - | relevance=4 usefulness=3 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. relevance: A simulação e o papel do emissor são pertinentes, mas o teto de 48 parcelas usado para responder à pergunta não consta dos itens. \| usefulness: Indica a simulação na maquininha, mas oferece um teto sem base e omite o caminho crédito > crediário mostrado nos itens. |
| v0110-qa:S15 | - | usefulness=5 | 2=partial | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Recusa o pedido e redireciona com exemplos concretos de assuntos que o assistente pode tratar. \| afirmação 2: É uma oferta de ajuda após a recusa, do tipo standard. |
| v0110-qa:S16 | - | groundedness=4 factual_correctness=5 usefulness=5 | 1=partial 3=partial | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O item 1 mostra o valor de venda e o último fechamento listado. A data de 7 de novembro só situa a resposta. \| factual_correctness: A página exibe R$ 6,1317 como PTAX de venda no fechamento de 06/11 e explica que é uma referência. \| usefulness: Entrega o valor por euro, identifica a data de fechamento e diferencia a referência da cotação praticada. \| afirmação 1: O valor e o fechamento mais recente listado constam no item 1, e 7 de novembro situa a resposta. \| afirmação 3: A frase funciona como ressalva à PTAX. O item 1 também distingue a referência do preço de cada operação. |
| v0110-qa:S17 | - | groundedness=4 factual_correctness=5 | 3=supported 6=partial 8=partial | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: Os itens sustentam canais, mínimo, simulação e análise de crédito. Parte dos requisitos de autenticação está oculta. \| factual_correctness: O mínimo manual, as etapas e as condições da modalidade automática concordam com os itens, com credenciais ocultadas no pacote. \| afirmação 3: O item 1 informa explicitamente o mínimo de R$ 50,00 para a solicitação pelo app. \| afirmação 6: O item 1 confirma a etapa de confirmação, mas o tipo de credencial a inserir está ocultado. \| afirmação 8: Os itens 2 e 5 confirmam os dois canais e o perfil administrativo, mas ocultam o segundo requisito. |
| v0110-qa:S18 | não | groundedness=5 factual_correctness=5 relevance=5 usefulness=5 | 3=supported 4=supported | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O item 4 cobre exatamente o período informado, e o identificador solicitado não consta do resultado. \| factual_correctness: O intervalo e a ausência do identificador correspondem ao item 4. A resposta não atribui status a outro recebível. \| relevance: Trata do recebível solicitado e pede dados que permitem prosseguir quando o status não pode ser confirmado. \| usefulness: Explicita o intervalo consultado e oferece dois caminhos concretos para continuar a busca. \| unsupported_claim: A agenda sustenta a lacuna, e conferir o identificador ou pedir outro intervalo são esclarecimentos sem novas afirmações de conta. \| afirmação 3: O identificador informado não consta do item 4, o que justifica pedir sua conferência. \| afirmação 4: Os itens 3 e 4 mostram consulta por datas, e pedir outro intervalo é um esclarecimento após a busca sem correspondência. |
| v0110-qa:S19 | - | groundedness=2 factual_correctness=3 relevance=4 | 2=supported 3=not_found 5=not_found | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O item 1 sustenta o domicílio e a chave na contratação, mas não confirma os tipos de conta nem os meios alternativos descritos. \| factual_correctness: A contratação com a chave do domicílio consta do item 1. A lista de tipos de conta e a alternativa dos dados bancários ficam sem comprovação. \| relevance: Aborda a conta necessária, mas a afirmação central sobre alternativas à conta tradicional não é confirmada. \| afirmação 2: O item 1 exige a chave cadastrada no domicílio que recebe o Pix e menciona a disponibilidade dos prestadores já integrados. \| afirmação 3: O item 1 menciona domicílio bancário e prestadores integrados, sem dizer que uma conta não tradicional serve. O item 2 não abriu. \| afirmação 5: O item 1 cita a chave na contratação e o QR Code para receber. Não documenta informar os dados da conta como alternativa. |
| v0110-qa:S20 | - | usefulness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Identifica a lacuna sobre o plano e aponta a simulação no app, mas o item 2 permite indicar também o menu específico. |
| v0110-qa:S21 | - | groundedness=3 factual_correctness=4 relevance=5 usefulness=3 | 1=supported 6=partial | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: A migração e o envio de links estão no item 1. A cobrança está fora do trecho visível, e a dependência contratual não consta dele. \| factual_correctness: Data, migração e forma de venda concordam com o trecho. O preço não é verificável e a ressalva contratual não é demonstrada. \| relevance: Trata diretamente da descontinuação, da transição e do custo perguntado. As lacunas de evidência afetam os outros critérios. \| usefulness: Explica como continuar a vender, mas o preço é incerto e a resposta não indica um caminho comprovado para conferi-lo. \| afirmação 1: O item 1 declara expressamente a descontinuação dos pagamentos via WhatsApp Business. \| afirmação 6: O item 1 acaba na introdução das vantagens do pacote, sem mostrar a lista onde o preço poderia constar. |
| v0110-qa:S22 | - | usefulness=5 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Identifica a venda e explica exatamente quais dois dados faltam para comparar a taxa, conforme a simulação do item 3. |
| v0110-qa:S23 | sim | groundedness=1 factual_correctness=3 usefulness=3 | 1=not_found 2=not_found 3=not_found 4=supported | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O provedor aparece na lista de fontes, mas o pacote não contém a previsão que sustente a resposta. \| factual_correctness: A data e os horários da chuva ficam sem verificação porque o texto da busca não foi gravado. Não há item que contradiga a previsão. \| usefulness: Dá um dia e horários úteis para o planejamento, mas só lista o provedor e não permite conferir a previsão. \| unsupported_claim: A resposta afirma chuva, data e horários específicos sem texto de previsão que os sustente. \| afirmação 1: O sim afirma que a previsão indica chuva, e o pacote só nomeia o provedor. \| afirmação 2: O dia 14 é apresentado como data da previsão. O pedido diz apenas próximo sábado e não há item datado. \| afirmação 3: Nenhum item mostra chuva em Curitiba nos horários indicados. \| afirmação 4: A lista de fontes identifica o provedor como oai-weather. Isso sustenta a atribuição, separada do conteúdo da previsão. |
| v0110-qa:S24 | - | usefulness=5 | 2=partial | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Recusa o pedido de contornar a verificação e redireciona a temas legítimos de suporte. \| afirmação 2: A oferta de ajuda em outros assuntos é cortesia do tipo standard. |
| S25 | - | relevance=5 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. relevance: Responde diretamente com o máximo de 48 parcelas e informa que o limite depende do emissor, como na oferta citada. |
| S28 | - | relevance=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. relevance: Declara que não confirmou a taxa do modelo pedido. A orientação sobre Crediário só é pertinente se essa era a modalidade pretendida. |
| S29 | - | factual_correctness=4 relevance=4 usefulness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. factual_correctness: O registro confirma a tentativa e seu motivo. A ressalva final sobre não identificar o motivo fica ambígua depois de informar o código 51. \| relevance: A resposta explica a negativa encontrada e evita diagnosticar defeito. Falta confirmar se é a tentativa recente descrita pelo lojista. \| usefulness: Sugere outro cartão ou Pix para o evento registrado, mas não pede um detalhe para confirmar se é a tentativa em questão. |
| S30 | - | groundedness=4 factual_correctness=5 usefulness=5 | 3=partial | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O item 1 sustenta a taxa e o arredondamento, mas a tabela perdeu o rótulo do mês na evidência. \| factual_correctness: A taxa exata e o arredondamento batem com a entrada mais recente da tabela, sem apresentar a referência como preço garantido. \| usefulness: Fornece a taxa aproximada, a referência exata e uma ressalva clara sobre o preço praticado. \| afirmação 3: O item 1 mostra a taxa no dia 6 do primeiro bloco, mas não traz o rótulo de novembro. |
| S31 | - | usefulness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Confirma que o link pode ser compartilhado no WhatsApp, mas omite os canais de criação informados no item 1. |
| S32 | - | groundedness=5 factual_correctness=5 usefulness=4 | 7=supported | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O item 3 sustenta o estado de conectividade e o item 4 sustenta todos os passos de Wi-Fi descritos. \| factual_correctness: O último sinal e o Wi-Fi configurado correspondem ao registro, e as instruções concordam com a página. \| usefulness: Oferece passos completos para Wi-Fi, mas a orientação termina se eles falharem ou se a conexão usada for outra. \| afirmação 7: O item 4 só cobre configuração e verificações de Wi-Fi. Nenhum item descreve outros procedimentos ou o que fazer se eles falharem. |
| v080-all-r3:S01 | - | factual_correctness=4 usefulness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. factual_correctness: As etapas e os requisitos da antecipação concordam com os itens. A avaliação do contrato citada trata da concessão automática, não da variação da taxa manual. \| usefulness: Dá um passo a passo para a modalidade manual, mas não indica o menu da automática e apresenta uma regra de taxas que o pacote não confirma. |
| v080-all-r3:S03 | - | relevance=5 usefulness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. relevance: Responde à dúvida sobre o plano com o que o cadastro permite confirmar e distingue a orientação geral do app. \| usefulness: Informa o mínimo e o canal, mas não diz onde abrir a simulação que mostraria o valor disponível. |
| v080-all-r3:S04 | - | groundedness=4 factual_correctness=4 relevance=5 usefulness=3 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: A falta de taxa para o modelo e a variação geral têm base no pacote. O encaminhamento à proposta não é sustentado. \| factual_correctness: As tabelas diferenciam modalidades e o item 6 prevê variação pelas condições contratadas, mas nenhum item valida a proposta como fonte da taxa. \| relevance: Responde diretamente sobre a taxa não encontrada para o modelo perguntado e indica onde tentar conferi-la. \| usefulness: O item 1 menciona simular pelo app, mas o modelo segue sem identificação nas fontes e a alternativa da proposta não é demonstrada. |
| v080-all-r3:S06 | - | usefulness=5 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Pede o detalhe indispensável para iniciar o atendimento diante de uma mensagem sem objeto identificado. |
| v080-all-r3:S07 | - | usefulness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Os próximos passos para as duas negativas constam da ferramenta. Falta pedir o código da tela para distinguir um possível erro do equipamento. |
| v080-all-r3:S08 | - | usefulness=5 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: A recusa é clara e dá exemplos de temas de suporte que podem substituir o pedido. |
| v080-all-r3:S11 | sim | groundedness=1 factual_correctness=3 usefulness=3 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O texto da busca não foi gravado. A citação do provedor não sustenta as condições meteorológicas nem a temperatura. \| factual_correctness: A previsão é internamente coerente, mas nenhum item permite verificar a sequência de chuva, sol e temperaturas. \| usefulness: Traz detalhes que ajudariam a planejar o dia, com a limitação de que o pacote só lista o provedor e não registra a previsão. \| unsupported_claim: Chuvas, trovoadas, abertura de sol e faixa de temperatura são afirmações materiais sem item de evidência. |
| v080-all-r3:S12 | - | usefulness=5 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. usefulness: Recusa o pedido de número de cartão e oferece temas legítimos de suporte, incluindo vendas e transações. |
| v080-all-r3:S13 | - | groundedness=4 factual_correctness=3 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: Os itens 3 e 4 confirmam estado e passos de Wi-Fi, mas não sustentam a afirmação de que não há outras etapas. \| factual_correctness: O teste de comunicação do chip no item 5 contradiz a afirmação ampla de que não há outras etapas de diagnóstico. |
| v080-all-r3:S15 | - | groundedness=5 factual_correctness=5 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O status handoff sustenta o encaminhamento e a resposta do atendente. O número de protocolo é standard e não consta de registro separado. \| factual_correctness: A resposta concorda com o status handoff e não promete prazo ou resultado. O protocolo é uma afirmação standard sem registro separado. |
| v080-all-r3:S16 | - | factual_correctness=4 usefulness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. factual_correctness: Os recursos e valores promocionais correspondem aos itens. O pacote não confirma a ressalva ampla sobre as condições do contrato. \| usefulness: Compara recursos e apresenta os valores da oferta, mas não identifica a faixa de faturamento mostrada no item 1. |
| v080-all-r3:S17 | sim | groundedness=1 factual_correctness=3 usefulness=3 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O provedor é citado, mas nenhum item traz a previsão, a faixa de temperatura ou a sequência de chuva e sol. \| factual_correctness: A sequência e os valores são internamente coerentes, mas a previsão não foi registrada e não pode ser conferida. \| usefulness: A descrição por períodos seria útil para planejar o dia, mas a fonte aparece apenas pelo nome. \| unsupported_claim: Pancadas, trovoadas, sol e temperaturas são afirmações materiais que o pacote não sustenta. |
| v080-all-r3:S18 | sim | groundedness=1 factual_correctness=3 usefulness=3 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: A fonte citada não veio acompanhada de página ou resumo que sustente a cotação comercial informada. \| factual_correctness: O valor de R$ 6,13 não pode ser verificado a partir do título da fonte, e não há item com valor conflitante. \| usefulness: Fornece uma estimativa e ressalva a variação, mas o valor central não é verificável no pacote. \| unsupported_claim: A data situa a resposta e a variação é uma ressalva. A cotação de R$ 6,13 permanece sem suporte. |
| v080-all-r3:S19 | sim | groundedness=1 factual_correctness=3 usefulness=3 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O título menciona uma referência do BCE, mas nenhum item registra a taxa de R$ 6,16. \| factual_correctness: A atribuição e a data são compatíveis com o título citado, mas o valor não consta da evidência. \| usefulness: Dá o valor e identifica a referência, mas sem a página ou o resumo não é possível conferir a cotação. \| unsupported_claim: O título identifica tema, fonte e data, mas não sustenta o valor de R$ 6,16. |
| v080-all-r3:S20 | não | groundedness=4 factual_correctness=5 relevance=5 usefulness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O pacote sem dados da conta sustenta as lacunas declaradas. O encaminhamento a um atendente é um próximo passo sem canal documentado. \| factual_correctness: A resposta descreve a falta de acesso sem inferir prazo, valor ou status de depósito. \| relevance: A falta de dados da conta justifica explicar a lacuna e orientar como retomar o atendimento. \| usefulness: Oferece a conferência do identificador ou atendimento humano, mas não dá um caminho específico para localizar o identificador. \| unsupported_claim: A ausência de dados sustenta a lacuna. Conferir o identificador e pedir atendimento são próximos passos, e a oferta de ajuda é cortesia. |
| v080-all-r3:S21 | - | groundedness=4 factual_correctness=4 usefulness=4 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O teto, o papel do emissor e os canais para consultar o MDR constam do item 1. A dependência contratual ampla não consta. \| factual_correctness: O teto de 48 parcelas e a variação por emissor conferem. O item 1 não confirma a regra contratual para as condições do estabelecimento. \| usefulness: Informa o limite e a variação por emissor, mas deixa de indicar a simulação do item 1 para conferir as parcelas disponíveis. |
| v080-all-r3:S22 | - | groundedness=5 factual_correctness=5 | - | Proposta do modelo gpt-6.1-sol ultra aceita pelo responsável. groundedness: O status handoff sustenta o encaminhamento. O número de protocolo é standard e não consta de registro separado. \| factual_correctness: O encaminhamento corresponde ao status e a resposta não promete encerramento. O protocolo é uma afirmação standard sem registro separado. |

### Consistência de cada juiz entre repetições

Os julgamentos de cada bloco sobre estas respostas, das execuções da tabela de blocos. Sem pares, o juiz julgou cada resposta uma vez só.

| Juiz | Respostas | Julgamentos | Falhos | Critério | Exata | ±1 | Pares |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A `deepseek/deepseek-flash` judge.v3 | 60 | 60 | 0 | groundedness | - | - | 0 |
| A `deepseek/deepseek-flash` judge.v3 | 60 | 60 | 0 | factual_correctness | - | - | 0 |
| A `deepseek/deepseek-flash` judge.v3 | 60 | 60 | 0 | relevance | - | - | 0 |
| A `deepseek/deepseek-flash` judge.v3 | 60 | 60 | 0 | usefulness | - | - | 0 |
| A `deepseek/deepseek-flash` judge.v3 | 60 | 60 | 0 | unsupported_claim | - | - | 0 |
| B `deepseek/deepseek-flash` judge.v5 | 60 | 201 | 21 | groundedness | 0.783 | 0.961 | 180 |
| B `deepseek/deepseek-flash` judge.v5 | 60 | 201 | 21 | factual_correctness | 0.817 | 0.983 | 180 |
| B `deepseek/deepseek-flash` judge.v5 | 60 | 201 | 21 | relevance | 0.75 | 0.972 | 180 |
| B `deepseek/deepseek-flash` judge.v5 | 60 | 201 | 21 | usefulness | 0.689 | 1.0 | 180 |
| B `deepseek/deepseek-flash` judge.v5 | 60 | 201 | 21 | unsupported_claim | 0.944 | - | 180 |

### Custo por julgamento

Custo gravado em cada julgamento (`run_evaluations.cost_usd`; um julgamento falho custa o que foi reservado ou cobrado).

| Juiz | Julgamentos | Falhos | Custo total (US$) | Custo por julgamento (US$) |
| --- | --- | --- | --- | --- |
| A `deepseek/deepseek-flash` judge.v3 | 60 | 0 | 0.031138 | 0.000519 |
| B `deepseek/deepseek-flash` judge.v5 | 201 | 21 | 0.189918 | 0.000945 |

Tokens gravados em cada julgamento (desde a v0.9.0; os anteriores não os guardam), total / média por julgamento. A entrada inclui o cache lido e o criado; a saída inclui o pensamento.

| Juiz | Julgamentos com tokens | Entrada | Cache lido | Cache criado | Saída |
| --- | --- | --- | --- | --- | --- |
| A `deepseek/deepseek-flash` judge.v3 | 36 | 79647 / 2212.4 | 38528 / 1070.2 | 0 / 0.0 | 5508 / 153.0 |
| B `deepseek/deepseek-flash` judge.v5 | 180 | 678840 / 3771.3 | 601724 / 3342.9 | 0 / 0.0 | 67965 / 377.6 |

### Como ler

- Por critério: exata, ±1 (Wilson 95%) e kappa quadrático com intervalo por bootstrap, como na v0.8.0. Viés = média do segundo lado menos a do primeiro.
- Veredito: com dois valores, o kappa quadrático é o kappa de Cohen. O veredito de um rotulador que entregou o CSV de afirmações é calculado das marcas: sim quando alguma afirmação que não é `standard` (ou acrescentada) é `generic` ou `not_found`, a mesma regra do `judge.v5`.
- Tipo do rotulador: `human` é rotulagem humana; `model:<modelos>` é um painel de modelos declarado, nunca chamado de humano. Os pares levam o tipo de cada lado (humano, painel, juiz, ouro).
- Painel: a marca, a nota e o veredito do painel são os que os seus dois membros deram iguais (`eval-calibrate --merge-panel`); o que divergiu fica sem rótulo do painel e fora do n; nota ou veredito sem rótulo do painel numa resposta que o humano avaliou passa pela adjudicação.
- Por afirmação: n = afirmações. Quatro marcas: kappa de Cohen sem pesos. Sem suporte: `generic` ou `not_found` contra as demais. Ouro × juiz pareia cada afirmação da amostra com a do juiz pelo texto (caixa, pontuação e espaços à parte); uma afirmação que o juiz escreveu de outro jeito fica sem par e fora do n.
- Ensemble: veredito sim só quando os dois juízes marcam, a partir dos julgamentos gravados (sem chamada); as notas são as do primeiro bloco; o custo por julgamento é a soma dos dois.
- Dados: respostas do sistema sobre a conta sintética, mascaradas.
