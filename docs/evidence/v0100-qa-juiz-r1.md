# Passagem de papel: QA da v0.10.0, momentos 1 a 3 (rubrica `judge.v4`), rodada 1

- **Papel e responsável:** QA nativo, contexto novo, 2026-11-06. Caixa-preta pela CLI (`merchant-assistant eval` e `eval-calibrate`), sem Docker e sem navegador, como pedido.
- **Objetivo e critérios:** CA-57 pelos momentos 1 a 3 de [rubrica-operacao-v0100.md](../historias/rubrica-operacao-v0100.md) (versão 1, 2026-11-05), com a spec [rubrica-operacao-v0100.md](../specs/rubrica-operacao-v0100.md) (D1, D2, "Orçamento") e a regra operacional do P2-4 da v0.9.0 ([v090-qa-juiz-r2.md](v090-qa-juiz-r2.md)).
- **Escopo:**
  - 72 julgamentos DeepSeek sob `judge.v4`;
  - sonda Opus de 3 julgamentos;
  - 72 julgamentos Opus sob `judge.v4`;
  - relatório multi-bloco `eval-calibrate` contra as mesmas 24 notas humanas.

  Não houve nota humana nova nem seed: só o rejulgamento das respostas gravadas.
- **Estado:** **apto** para os momentos 1 a 3. Os três produziram o resultado esperado, sem falha, recusa ou corte. O relatório traz os quatro blocos, a tabela das frases genéricas e a linha D2. A decisão do padrão da rubrica fica com o Supervisor (tarefa 86), e a D2 está verificada abaixo, sem decidir.
- **Branch e PR:** `codex/v0.10.0-rubrica-operacao`, sem PR. Nada commitado pelo QA.
- **Base e versão final:**
  - HEAD `5005d81` no início. Durante a rodada, a branch avançou para `4195468`, com um commit de outro agente que só toca `docs/evidence/v0100-developer.md` e `docs/tasks/85-metrics-e-alertas.md` (`git diff --stat 5005d81 4195468 -- src prompts tests` vazio).
  - Não há manifesto `v0100-candidato-*.json`. Fixei o candidato pelos blobs da tarefa 83, iguais aos do HEAD e aos da revisão r2 ([v0100-reviewer-t83.md](v0100-reviewer-t83.md)): `judge.v3.md 7375786`, `judge.v4.md 2c0f2c9`, `cli.py 210c785`, `calibration.py a037f91`, `judge.py 9b48a14` e `scripted_judge.py 73105e2`.
  - Sem alterações locais nesses arquivos (`git hash-object` = `git rev-parse HEAD:<path>`).
- **Independência:** independente (não implementei nem revisei a tarefa 83).

## Pré-checagens (sem custo)

| Verificação | Resultado |
| --- | --- |
| `git rev-parse HEAD` | `5005d812…`, como pedido |
| `eval --help` | mostra `--rubric {v3,v4}` ("Left out, the configured default (v3 until task 86)") |
| `eval-calibrate --help` | `--judge`, `--judge-run` e `--rubric {v3,v4}` repetíveis, pareados pela ordem |
| `prompts/judge.v4.md` | existe; sha256 `7c416d5d…3e3c` |
| `prompts/judge.v3.md` | blob do HEAD com sha256 `45d59f0c…75152bd`, como pedido. No disco, o arquivo está com CRLF e dá `2cab47d1…69e`; sem o `\r`, dá `45d59f0c…`, e `git diff HEAD -- prompts` sai vazio (observação abaixo) |
| `calibrations`, campanha `v080-all-r3`, avaliador `lauro` | 24 linhas |
| Banco de QA `.pytest_cache/qa-v080-r1/runtime/merchant.sqlite3` antes | sha256 `18968e43…881c87`, o mesmo do fim da v0.9.0 e da revisão. Backup em `.pytest_cache/qa-v0100-backup/merchant.sqlite3` com o mesmo hash, antes da primeira gravação |
| Ledger do projeto `data/runtime/budget.sqlite3` antes | 3826 lançamentos (máx. id 3826), US$1,41870799, todos `settled`, 0 `claude%`; `.limit` = 2.0 |
| Ledger Anthropic `data/runtime/anthropic/budget.sqlite3` antes | 78 lançamentos, US$1,48466, todos `settled`; `.limit` = 4.0 |
| Testes da tarefa 83 | `test_judge_v4.py`, `test_v0100_rubric.py` e `test_judge_v3.py`: 39 testes, rc 0 (basetemp novo fora da raiz) |
| Suíte estrita completa | não rodada: outros agentes usam a árvore, e o despacho é de um agente pesado por vez. A pré-condição vem da revisão r2: 2134 passed sobre os mesmos blobs |

## Momento 1, DeepSeek sob `judge.v4`: conforme

```text
RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime BUDGET_RUNTIME_DIR=data/runtime BUDGET_LIMIT_USD=1.60 \
merchant-assistant eval --judge-repeat 3 --answers-from docs/evidence/v080-all-r3.json \
  --only-sample docs/evidence/v080-calibracao-amostra.csv --rubric v4 --name v0100-juiz-deepseek-v4
```

- Das 03:17:37Z às 03:20:02Z, rc 0. Saída: "grading 24 of 44 recorded answers", `judge_failed: 0`, "judgements stored in run_evaluations: 72 (execution v0100-juiz-deepseek-v4)".
- No banco, 72 julgamentos `deepseek/deepseek-flash`, prompt `judge@4`, `rubric_version` 4, todos `completed`, sobre 24 respostas e 3 repetições. Somam US$0,02514668.
- Ledger do projeto: ids 3827 a 3898, agente `judge`, todos `settled`, **US$0,02514668**.
- Tokens: 146.433 de entrada (109.056 lidos do cache) e 11.066 de saída.
- Médias: groundedness 4,49, factual 4,42, relevance 4,72 e usefulness 4,49. Taxa de `unsupported_claim` 0,097.

## Momento 2, Opus sob `judge.v4`: conforme

Ambiente: `JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5 BUDGET_RUNTIME_DIR=data/runtime/anthropic BUDGET_LIMIT_USD=4.00 RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime`.

### Sonda

```text
merchant-assistant eval --judge-repeat 1 --answers-from docs/evidence/v080-all-r3.json \
  --only-sample docs/evidence/v080-calibracao-amostra.csv --limit 3 --rubric v4 --name v0100-juiz-opus-v4-sonda
```

Das 03:20:30Z às 03:20:59Z, rc 0, `judge_failed: 0`.

| Julgamento | `request_id` | Estado | Prompt | Custo (US$) |
| --- | --- | --- | --- | --- |
| `eval_1f23feded57a4d54b516` | `req_eval0c6f7493f669` (PT06, S01) | completed | `judge@4` | 0,023496 |
| `eval_7649d96cb07649c8907d` | `req_evalda08fa632aaf` | completed | `judge@4` | 0,014664 |
| `eval_ecb8b3313cc44ab2a4d1` | `req_eval4e3529ab6de2` | completed | `judge@4` | 0,020404 |

- Ledger Anthropic: ids 79 a 81, `settled`, **US$0,058564**. Tokens: 9.331 de entrada e 1.062 de saída, sem cache.
- Projeção para 72: US$1,41 pela média e US$1,69 pelo maior custo da sonda. O cap restante era de US$2,456776, então rodei as 3 repetições.

### 72 julgamentos

```text
merchant-assistant eval --judge-repeat 3 --answers-from docs/evidence/v080-all-r3.json \
  --only-sample docs/evidence/v080-calibracao-amostra.csv --rubric v4 --name v0100-juiz-opus-v4
```

- Das 03:21:18Z às 03:25:43Z, rc 0, `judge_failed: 0`, "judgements stored in run_evaluations: 72 (execution v0100-juiz-opus-v4)".
- No banco, 72 julgamentos `anthropic/claude-opus-5-5` (`model_used` igual), `judge@4`, `completed` 72 de 72, sem erro. Somam US$1,315568: média US$0,018272, mínimo US$0,011548 e máximo US$0,036236.
- Ledger Anthropic: ids 82 a 153, todos `settled`, **US$1,315568**. Tokens: 225.927 de entrada e 20.593 de saída (com o pensamento), sem cache.
- Recusas, cortes e erros: nenhum. **A regra do P2-4 não foi usada** (sem cópia `-original` e sem rejulgamento). Nenhuma rodada repetiu um nome.

## Momento 3, v3 × v4 contra as mesmas notas: conforme

```text
RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime BUDGET_RUNTIME_DIR=data/runtime/anthropic BUDGET_LIMIT_USD=4.00 \
merchant-assistant eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv --rater lauro \
  --judge deepseek/deepseek-flash --judge-run v0100-juiz-deepseek-v4 --rubric v4 \
  --judge anthropic/claude-opus-5-5 --judge-run v090-juiz-opus-r3 --rubric v3 \
  --judge anthropic/claude-opus-5-5 --judge-run v0100-juiz-opus-v4 --rubric v4 \
  --campaign v0100-juiz-v4 --out docs/evidence/v0100-juiz-v4.md
```

03:26:06Z, rc 0, sem chamada paga (os dois ledgers não mudaram). Saída: "calibrations: 24 stored, 0 updated, 0 skipped (campaign v0100-juiz-v4, rater lauro)", com os blocos:

- O, `deepseek/deepseek-flash judge.v3` (`legado`);
- A, DeepSeek `judge.v4` (`v0100-juiz-deepseek-v4`);
- B, `anthropic/claude-opus-5-5 judge.v3` (`v090-juiz-opus-r3`);
- C, Opus `judge.v4` (`v0100-juiz-opus-v4`).

O relatório [v0100-juiz-v4.md](v0100-juiz-v4.md) traz:

- os quatro blocos com exata, ±1, kappa e viés por critério;
- a matriz do veredito por bloco;
- a tabela S01/S13/S16/S21;
- a linha D2 para A contra O e para C contra B;
- os julgamentos considerados (24, 72 e 72 em cada bloco);
- a consistência entre repetições;
- o custo e os tokens.

O relatório também diz que não houve avaliação humana nova.

Frases genéricas (repetição 1 de cada bloco, a que o relatório usa):

| Amostra | Caso | Humano | O (DS v3) | A (DS v4) | B (Opus v3) | C (Opus v4) |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | PT06 | sim | não | não | sim | sim |
| S13 | PT05 | sim | não | não | não | não |
| S16 | EX01 | sim | não | não | não | não |
| S21 | PT09 | sim | não | não | não | sim |
| Marcadas | | 4 de 4 | 0 de 4 | 0 de 4 | 1 de 4 | 2 de 4 |

## Regra D2, verificada literalmente (sem decidir)

Texto da spec: a v4 vira padrão se, com o DeepSeek, "a concordância do veredito com o humano não cair e pelo menos 2 das 4 genéricas forem marcadas, sem que a concordância ±1 dos critérios piore em mais de 0,05 em qualquer um"; o Opus "é reportado, não decide".

| Item | DeepSeek v4 (A) contra DeepSeek v3 (O) | Opus v4 (C) contra Opus v3 (B), só reportado |
| --- | --- | --- |
| (i) concordância do veredito não caiu? | 0,792 contra 0,667 (kappa −0,071 contra −0,200): **sim** | 0,917 contra 0,875 (kappa 0,625 contra 0,357): **sim** |
| (ii) ≥ 2 das 4 genéricas marcadas "sim"? | 0 de 4: **não** | 2 de 4 (S01, S21): **sim** |
| (iii) ±1 de nenhum critério piora mais de 0,05? | groundedness 0,792 contra 0,833 (−0,042); factual 0,792 contra 0,833 (−0,042); relevance 1,000 contra 1,000 (0); usefulness 0,958 contra 0,917 (+0,042): **sim** | groundedness 0,917 contra 0,958 (−0,042); factual 0,958 contra 0,958 (0); relevance 0,958 contra 1,000 (−0,042); usefulness 1,000 contra 0,958 (+0,042): **sim** |
| Linha do relatório | "Três condições atendidas: não" | "Três condições atendidas: sim" |

Os −0,042 equivalem a uma resposta em 24 que saiu da faixa ±1.

Dados laterais, fora da regra:

- **Repetições do DeepSeek v4.** O DeepSeek v4 marcou S01 nas repetições 2 e 3, mas não na 1 (vereditos `0,1,1`). Nunca marcou S13, S16 ou S21. A consistência do veredito de A é 0,917, contra 0,969 de O. Mesmo por maioria das 3 repetições, o DeepSeek v4 marcaria 1 de 4.
- **Repetições do Opus v4.** O Opus v4 marcou S01 e S21 em 3 de 3 repetições e nunca S13 ou S16. A consistência do veredito de C é 0,972, e a exata por critério é igual ou maior que a de B.
- **Falsos positivos do DeepSeek v4.** Os vereditos "só juiz" do DeepSeek caíram de 4 (O) para 1 (A, S18/PT07): a v4 deixou o DeepSeek menos propenso a marcar onde o humano não marca, sem passar a marcar as genéricas.

## Ledgers e custos

| Ledger | Antes | Depois | Delta |
| --- | --- | --- | --- |
| Projeto `data/runtime/budget.sqlite3` | 3826 lançamentos, US$1,41870799, 0 `claude%` | 3898 lançamentos, todos `settled`, US$1,44385467, 0 `claude%`; `.limit` = 2.0 | **+US$0,02514668** (72 lançamentos) |
| ↳ momento 1 `v0100-juiz-deepseek-v4` | | ids 3827 a 3898 | US$0,02514668 |
| Anthropic `data/runtime/anthropic/budget.sqlite3` | 78 lançamentos, US$1,48466 | 153 lançamentos, todos `settled`, US$2,858792; `.limit` = 4.0 (não elevado) | **+US$1,374132** (75 lançamentos) |
| ↳ sonda `v0100-juiz-opus-v4-sonda` | | ids 79 a 81 | US$0,058564 |
| ↳ momento 2 `v0100-juiz-opus-v4` | | ids 82 a 153 | US$1,315568 |
| ↳ momento 3 `eval-calibrate` | | nenhum lançamento nos dois ledgers | US$0 |

- Teto da versão no projeto, US$0,25: foram usados US$0,0251. Folga sob o `BUDGET_LIMIT_USD=1.60` da rodada: US$0,156.
- Cap Anthropic restante: US$4,00 − US$2,858792 = **US$1,141208**.
- Tokens da rodada: DeepSeek 146.433 de entrada (109.056 do cache) e 11.066 de saída; Opus 235.258 de entrada e 21.655 de saída (sonda e rodada), sem cache.
- Falhas: 0. Rejulgamentos: 0.

## Achados e limitações

- **Pendência para o Supervisor, não é defeito:** o CA-57 pede "a decisão do padrão da rubrica registrada". O relatório traz os números e a linha D2, mas não a decisão, que fica com o Supervisor na tarefa 86.
- **Observação:** em `prompts/judge.v3.md`, o arquivo no disco tem CRLF, e o sha256 do disco (`2cab47d1…`) difere do blob (`45d59f0c…`). O conteúdo é idêntico ao do blob (`git diff` vazio; sem `\r`, o hash confere). `judge.v4.md` está com LF. A gravação registra a versão (`judge@3`/`judge@4`), não o hash do arquivo, então nada muda no resultado. Fica o registro para quem conferir hashes no disco.
- **Observação:** com o modelo real, o DeepSeek v4 marcou 0 de 4 genéricas. A sonda programada da revisão (r1, item 4) mostrava 2 de 4 com respostas sintéticas. Não é defeito: aquela sonda testava o relatório, não o modelo.
- **Observação:** os blocos usam a repetição 1 de cada resposta, como na v0.9.0. No DeepSeek v4, S01 depende da repetição (`0,1,1`). O relatório mostra isso na consistência, mas não na tabela das genéricas.
- **Observação:** no `.json` do `eval`, `cost_usd: 0` é o custo das respostas gravadas, não o do juiz. O custo do juiz aparece no `.md` e no ledger, e os dois conferem.
- **Observação:** o HEAD avançou de `5005d81` para `4195468` durante a rodada (só documentação, de outro agente). A superfície da tarefa 83 não mudou.
- **Limitação:** a suíte estrita completa não foi rodada (ver pré-checagens). O subconjunto da tarefa 83 passou.
- **Limitação:** o custo é o do ledger (tokens × `prices.json`). A fatura real só aparece nos consoles dos provedores.
- **Evidência gerada (não commitada):**
  - em `docs/evidence/`: `v0100-juiz-deepseek-v4.json` e `.md`, `v0100-juiz-opus-v4-sonda.json` e `.md`, `v0100-juiz-opus-v4.json` e `.md`, `v0100-juiz-v4.md` e este parecer;
  - os logs em `.pytest_cache/qa-v0100-control/` (`m1.log`, `sonda.log`, `opus-r3.log`, `calibrate.log`).

  `checar-caminhos-pessoais.py` não acha ocorrência nos 7 arquivos gerados, e não há padrão de chave neles. A CLI imprime o caminho absoluto do relatório no terminal, e ele não foi copiado para a evidência.
- **Estado do runtime:** `merchant.sqlite3` terminou com sha256 `4ff00af1…94ba`. Houve só acréscimos: 147 julgamentos (de 625 para 772) e 24 calibrações da campanha `v0100-juiz-v4`. As campanhas `v080-all-r3` e `v090-juiz-opus` ficaram intactas (24 linhas cada, `created_at` anterior). O backup ficou em `.pytest_cache/qa-v0100-backup/`.

## Como terminou

O responsável queria saber se a lacuna da v0.9.0 era mesmo da rubrica. Com a frase nova, o Opus passou a pegar duas das quatro respostas em que ele viu uma generalização sem fonte (PT06 e PT09) e manteve a consistência e a concordância nos outros critérios. Já o DeepSeek, que é o juiz que decide pela regra, não marcou nenhuma delas na repetição que conta. Ele erra menos o veredito (marca menos onde não devia), mas continua sem enxergar a frase genérica. Tudo isso custou US$0,03 no projeto e US$1,37 no ledger Anthropic, sem falha. A decisão sobre o padrão da rubrica fica com o Supervisor, com os números acima.

## Próxima ação e responsável

1. **Supervisor:** aplicar a D2 (pela letra, o DeepSeek v4 não cumpre (ii)) e registrar a decisão na tarefa 86, no relatório e na história ("Resultado da rodada").
2. **Supervisor:** commitar as evidências desta rodada e rodar `tools/scripts/limpar-ambiente.ps1`.
3. **QA:** momentos 4 a 8 quando as tarefas 84 e 85 tiverem candidato fixado.

## Decisão humana pendente

Nenhuma do QA. A escolha do padrão da rubrica pela D2 é do Supervisor, pela regra já escrita.
