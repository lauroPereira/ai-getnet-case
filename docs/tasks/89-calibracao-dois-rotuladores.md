# Tarefa 89 — Calibração por afirmação a dois rotuladores e amostra selada

## Objetivo

Dar aos rotuladores a mesma unidade de julgamento do juiz (a lista de afirmações com a evidência completa), aceitar dois rotuladores com adjudicação, e produzir amostras enriquecidas e seladas.

## Especificação relacionada

[Juiz por afirmação, evidência da web e retrieval — v0.11.0](../specs/juiz-retrieval-v0110.md): D4, D5, D6, CA-61, CA-62. Plano do ciclo: [decisões 4 a 6](../specs/roadmap-v0110-v100-plano.md#decisões-técnicas). Base: `evaluation/calibration.py` (`draw_sample`, `sample_rows`, `write_csv`, `read_filled`, `link`, `store`, `analyze`, `quadratic_kappa`, `kappa_interval`), `cli.py` (`eval-calibrate`), `docs/evidence/v080-calibracao.md` (formato do relatório).

## Pré-condições

A calibração usa as afirmações estruturadas por `judge_claims.v1`.

## Arquivos prováveis

`evaluation/calibration.py`, `evaluation/calibration_packets.py` (novo: pacotes Markdown e CSV de afirmações), `cli.py` (`--exclude`, `--enrich`, `--seed`, `--rater` repetível, `--adjudication`, `--seal`), `tests/scenarios/calibration_v0110.sha256` (selo SHA-256 da amostra), `data/migrations.py` (0013: `calibrations.rater`, `calibration_claims` se necessário), testes.

## Passos

1. **Amostra.** `eval-calibrate --sample N --from <relatório> --exclude <csv> --enrich <rotas> --seed N`: exclui respostas já calibradas, aplica estratos e rotas enriquecidas configurados e grava `sample.csv`, `sample-claims.csv` e um pacote `<id>.md` por resposta com pergunta, rota, resposta, evidência por item e afirmações numeradas. `--seal` grava o SHA-256 do conjunto em `tests/scenarios/calibration_v0110.sha256`; `--import` recusa amostras cujo hash não confere. O selo inclui a identidade da amostra, os dois CSVs e os pacotes Markdown; os pacotes permanecem locais e não são distribuídos. Os hashes dos [CSV de respostas](../evidence/v0110-calibracao-amostra.csv) e [CSV de afirmações](../evidence/v0110-calibracao-amostra-claims.csv) publicados podem ser conferidos pelas entradas correspondentes do selo.
2. **Importação.** `--rater <nome>:human <sample.csv> [<sample-claims.csv>]` e `--rater <nome>:model:<modelos> <sample.csv> [<sample-claims.csv>]` declaram o tipo do rótulo. Para humano, o veredito é derivado das marcas: `generic` ou `not_found` em afirmação não `standard` (ou acrescentada) marca a resposta; no formato legado sem CSV de afirmações, usa-se `unsupported_claim` de `sample.csv`. Para painel de modelos, o veredito vem da coluna `unsupported_claim` do CSV combinado; vazio permanece sem rótulo e nunca é recalculado a partir das marcas. `--merge-panel <member1-claims.csv> <member2-claims.csv> [--sample-csv <a.csv> <b.csv>] --out <panel.csv>` combina exatamente dois membros do mesmo sample, mantendo consenso e deixando vazias as divergências. Quando há dois raters, são exatamente um humano e um painel de dois modelos. `--adjudication <csv>` (`request_id`, `gold_verdict`, `gold_scores`, `reason`) registra o rótulo ouro e é obrigatório nas divergências; o ouro é o valor adjudicado ou o valor em que ambos concordam.
3. **Medidas.** Relata concordância e kappa por resposta e por afirmação, compara cada rotulador e juiz com o rótulo ouro e registra o tamanho da amostra analisada. A regra de seleção do juiz usa o conjunto selado e o rótulo ouro adjudicado.
4. **Testes:** amostra enriquecida e exclusão; selo e recusa; derivação do veredito; dois rotuladores e adjudicação obrigatória nas divergências; kappa por afirmação; relatório da v0.8.0 regenerado idêntico com um rotulador e sem CSV de afirmações; CSV inválido recusado sem gravar.

## Critérios de conclusão

- Pacotes, CSVs e selo gerados; importação de dois rotuladores, adjudicação divergente e rótulo ouro disponíveis; medidas por afirmação e por resposta.
- Relatório da v0.8.0 inalterado com as entradas antigas.
- As amostras e formatos anteriores continuam aceitos quando não incluem o CSV de afirmações.
