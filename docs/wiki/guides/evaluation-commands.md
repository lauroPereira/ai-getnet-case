# Test and evaluation commands

Tests and the scripted evaluation run offline at zero cost; the commands that call real models are paid and reserve
their spend in the budget ledger before each call (`BUDGET_LIMIT_USD`). This reference lists every command for tests,
evaluation, judge calibration and retrieval measurement of the backend. The method and the measured results are in
[Testing and evaluation](../../../README.md#testing-and-evaluation); the reports of each run are in
[docs/evidence](../../evidence/README.md).

The commands use the [local development](local-development.md) environment
(`uv sync --frozen --extra ingest --extra dev`). The ones marked "no model call" cost nothing.

## Tests

```bash
pytest                                   # backend tests
ruff check .
python tools/scripts/lint_and_tests.py --strict   # strict validation: pytest, Ruff, links and personal paths
uv lock --check                          # checks that uv.lock is current
```

The same suite runs inside the image, with no network:

```bash
docker build --target test -t ai-getnet-case:test .   # network only here, to build
docker run --rm --network none ai-getnet-case:test    # strict suite (pytest, Ruff, links); basetemp in /tmp
docker image rm ai-getnet-case:test
```

Arguments after the image name go to pytest, replacing the default `--basetemp=/tmp/pytest-image` (for example
`docker run --rm --network none ai-getnet-case:test --basetemp=/tmp/t -x`).

## Offline evaluation, with the scripted model

```bash
merchant-assistant eval --scripted       # end-to-end evaluation offline: routes, tools, guards, persistence and trace; zero cost
merchant-assistant eval --scripted --split dev --limit 5 --no-conversations --out "${TMPDIR:-/tmp}/ai-getnet-case-walkthrough"   # five-case sample, with the path of the report
```

## Evaluation with real models

`eval --judge` uses the independent judge (`JUDGE_PROVIDER`, `JUDGE_MODEL`), which must differ from the agent model.

```bash
merchant-assistant eval --judge          # real evaluation; paid, within the budget ledger
merchant-assistant eval --judge --include-replan --split dev --limit 5 --no-conversations --name v080-cost-sample  # cost sample with five cases
merchant-assistant eval-estimate --from docs/evidence/v080-cost-sample.json --out docs/evidence/v080-cost-estimate.json  # cost estimate of the campaign; no model call
merchant-assistant eval --campaign v080-qa --include-replan --judge --repeat 3 --split all  # campaign with a fixed cap, in addition to the installation ledger
merchant-assistant eval --campaign v080-qa --judge-repeat 3 --answers-from docs/evidence/v080-all.json --name v080-all-judge  # judge variation; the agent does not run
merchant-assistant eval --campaign v080-qa --judge --repeat 3 --split holdout_v080  # sealed holdout: once, as the last technical step
```

| Option | What it measures or controls |
| --- | --- |
| `--repeat 3` | Assistant variation: the agent runs each case three times and the judge scores each answer once |
| `--judge-repeat 3 --answers-from <report.json>` | Judge variation over recorded answers; the agent does not run |
| `--campaign v080-qa` | Applies the campaign's fixed cap once: US$0.50; US$1.00 or US$1.10 with `--campaign-estimate` and a verified `eval-estimate` |
| `--split holdout_v080` | Sealed holdout of 25 cases; runs once, last |
| `--rubric v3`, `--rubric v4` | Selects an earlier judge rubric; the default is `judge.v5` |

The 10 challenge examples against the running API (≈ US$0.03; the command gets the token itself):

```bash
docker compose exec api merchant-assistant smoke --url http://localhost:8000
```

## Judge calibration

```bash
merchant-assistant eval-calibrate --sample 24 --from docs/evidence/v080-all-r3.json   # CSV for the human rating, without the judge's scores; no model call
merchant-assistant eval --judge-repeat 3 --answers-from docs/evidence/v080-all-r3.json --only-sample docs/evidence/v080-calibracao-amostra.csv --rubric v4 --name my-run  # judges the calibration sample again with another rubric or another judge
# v0.11.0 calibration against reference labels: script and command in docs/evidence/v0110-calibracao.md
merchant-assistant eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv  # human × judge agreement and kappa; no model call
```

## Retrieval

```bash
merchant-assistant eval-retrieval        # Recall@k of the RAG index; reranking is on by default (RERANK=off disables it)
merchant-assistant eval-retrieval --mode hybrid --split dev --out docs/evidence/retrieval.md   # Recall@6, MRR and nDCG@6 per mode; --split holdout_v090 once, last
```

## Replanning, with and without

```bash
merchant-assistant eval --judge --replan off --name ablation-off   # evaluates the same cases without replanning (REPLAN=off)
merchant-assistant eval-compare --a docs/evidence/ablation-off.json --b docs/evidence/ablation-on.json --out docs/evidence  # paired report; no model call
```

`eval-compare` pairs the two reports by case and repetition, per criterion and per route, with a bootstrap interval of
the difference and the replanning decisions counted by origin.

## Collecting the official pages

```bash
merchant-assistant ingest                # re-collect the official pages into snapshots (network)
```
