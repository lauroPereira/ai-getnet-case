# Comandos de teste e avaliação

Referência completa dos comandos de teste, avaliação, calibração do juiz e medição de retrieval do backend. O método e os resultados medidos estão em [Testing and evaluation](../../README.md#testing-and-evaluation), no README; os relatórios de cada execução ficam em [docs/evidence](../evidence/README.md).

Os comandos usam o ambiente de [desenvolvimento local](../../README.md#locally-development) (`uv sync --frozen --extra ingest --extra dev`). Os que chamam modelos reais são pagos e reservam o gasto no ledger de orçamento antes de cada chamada (`BUDGET_LIMIT_USD`); os marcados como "sem chamada de modelo" têm custo zero.

## Testes

```bash
pytest                                   # testes do backend
ruff check .
python tools/scripts/lint_and_tests.py --strict   # validação estrita: pytest, Ruff, links, caminhos pessoais e metadados das skills
uv lock --check                          # confere se o uv.lock está atualizado
```

A mesma suíte roda dentro da imagem, sem rede:

```bash
docker build --target test -t ai-getnet-case:test .   # rede só aqui, para construir
docker run --rm --network none ai-getnet-case:test    # suíte estrita (pytest, Ruff, links, skills); basetemp em /tmp
docker image rm ai-getnet-case:test
```

Argumentos depois do nome da imagem vão ao pytest e substituem o padrão `--basetemp=/tmp/pytest-image` (por exemplo, `docker run --rm --network none ai-getnet-case:test --basetemp=/tmp/t -x`).

## Avaliação offline, com o modelo roteirizado

```bash
merchant-assistant eval --scripted       # avaliação ponta a ponta offline: rotas, ferramentas, guardas, persistência e trace; custo zero
merchant-assistant eval --scripted --split dev --limit 5 --no-conversations --out "${TMPDIR:-/tmp}/ai-getnet-case-walkthrough"   # amostra de cinco casos, com o caminho do relatório
```

## Avaliação com modelos reais

`eval --judge` usa o juiz independente (`JUDGE_PROVIDER`, `JUDGE_MODEL`), que precisa ser diferente do modelo do agente.

```bash
merchant-assistant eval --judge          # avaliação real; paga, dentro do ledger de orçamento
merchant-assistant eval --judge --include-replan --split dev --limit 5 --no-conversations --name v080-cost-sample  # amostra de custo com cinco casos
merchant-assistant eval-estimate --from docs/evidence/v080-cost-sample.json --out docs/evidence/v080-cost-estimate.json  # estimativa de custo da campanha; sem chamada de modelo
merchant-assistant eval --campaign v080-qa --include-replan --judge --repeat 3 --split all  # campanha com teto fixo, além do ledger da instalação
merchant-assistant eval --campaign v080-qa --judge-repeat 3 --answers-from docs/evidence/v080-all.json --name v080-all-judge  # variação do juiz; o agente não roda
merchant-assistant eval --campaign v080-qa --judge --repeat 3 --split holdout_v080  # holdout selado: uma vez, como último passo técnico
```

| Opção | O que mede ou controla |
| --- | --- |
| `--repeat 3` | Variação do assistente: o agente roda cada caso três vezes e o juiz avalia cada resposta uma vez |
| `--judge-repeat 3 --answers-from <relatório.json>` | Variação do juiz sobre respostas gravadas; o agente não roda |
| `--campaign v080-qa` | Aplica o teto fixo da campanha uma única vez: US$0,50; US$1,00 ou US$1,10 com `--campaign-estimate` e uma `eval-estimate` verificada |
| `--split holdout_v080` | Holdout selado de 25 casos; roda uma vez, por último |
| `--rubric v3`, `--rubric v4` | Seleciona uma rubrica anterior do juiz; o padrão é `judge.v5` |

Os 10 exemplos do desafio contra a API em execução (≈ US$0,03; o comando obtém o token):

```bash
docker compose exec api merchant-assistant smoke --url http://localhost:8000
```

## Calibração do juiz

```bash
merchant-assistant eval-calibrate --sample 24 --from docs/evidence/v080-all-r3.json   # CSV para a avaliação humana, sem as notas do juiz; sem chamada de modelo
merchant-assistant eval --judge-repeat 3 --answers-from docs/evidence/v080-all-r3.json --only-sample docs/evidence/v080-calibracao-amostra.csv --rubric v4 --name my-run  # rejulga a amostra de calibração com outra rubrica ou outro juiz
merchant-assistant eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv  # concordância humano × juiz e kappa; sem chamada de modelo
```

## Retrieval

```bash
merchant-assistant eval-retrieval        # Recall@k do índice RAG; o reranker vem ligado por padrão e sai com RERANK=off
merchant-assistant eval-retrieval --mode hybrid --split dev --out docs/evidence/retrieval.md   # Recall@6, MRR e nDCG@6 por modo; --split holdout_v090 uma vez, por último
```

## Replanejamento, com e sem

```bash
merchant-assistant eval --judge --replan off --name ablation-off   # avalia os mesmos casos sem replanejamento (REPLAN=off)
merchant-assistant eval-compare --a docs/evidence/ablation-off.json --b docs/evidence/ablation-on.json --out docs/evidence  # relatório pareado; sem chamada de modelo
```

`eval-compare` pareia os dois relatórios por caso e repetição, por critério e por rota, com intervalo bootstrap da diferença e as decisões de replanejamento contadas por origem.

## Coleta das páginas oficiais

```bash
merchant-assistant ingest                # coleta de novo as páginas oficiais para os snapshots (usa a rede)
```
