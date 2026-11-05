# História: um juiz mais forte é posto à prova contra as notas do responsável, e a busca aprende a achar o termo exato

Versão 1, 2026-11-05; roteiro aprovado com a spec, antes de implementar. Spec: [juiz-retrieval-v090.md](../specs/juiz-retrieval-v090.md).

## Pessoas e objetivo

- **Responsável** (Lauro): já deu 24 notas humanas na v0.8.0 e quer saber se um juiz Claude Opus concorda mais com ele do que o DeepSeek, antes de o juiz decidir conteúdo.
- **Avaliador técnico** (papel vivido pelo QA): quer ver a busca encontrar o que o denso não acha e uma medição num conjunto que ninguém usou para ajustar.
- **Lojista** (`cliente1988`): não percebe nada disto; as respostas continuam iguais.

## Critérios e candidato

CA-56 (experimento do juiz) e CA-52 (retrieval); tarefas 79 a 82. Candidato fixado por hashes em `docs/evidence/v090-candidato-rN.json` antes do QA.

## Condições iniciais

`main` com a v0.8.0 (tag). Runtime de QA `.pytest_cache/qa-v080-r1/runtime` preservado, com as 24 notas humanas e os julgamentos DeepSeek. `.env` com a chave Anthropic. Ledger Anthropic próprio (`BUDGET_RUNTIME_DIR=data/runtime/anthropic`) e campanha `v090-juiz-opus` com o cap aprovado. Seed sintética sem mudança (nenhuma fase depende da data).

## Momentos da história

| Momento | Ação pela entrada normal | Resultado esperado | Critério | Evidência | Ponto de retorno |
| --- | --- | --- | --- | --- | --- |
| 1. Sonda do juiz | QA roda `eval --judge-repeat 1 --answers-from docs/evidence/v080-all-r3.json --only-sample docs/evidence/v080-calibracao-amostra.csv --limit 3 --name v090-juiz-opus-sonda`, com `JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5`, `BUDGET_RUNTIME_DIR=data/runtime/anthropic BUDGET_LIMIT_USD=4.00` e `RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime` | 3 julgamentos válidos, `usage` com pensamento, custo real por julgamento; projeção de 72 contra o cap | CA-56 | Ledger Anthropic, saída da CLI | Não se aplica |
| 2. Julgamentos do Opus | Mesmo comando sobre os 24, sem `--limit`, com `--judge-repeat 3` (ou 1, pela projeção) e `--name v090-juiz-opus-r3` (ou `-r1`) | 72 (ou 24) julgamentos em `run_evaluations` com provedor `anthropic`, campanha `v090-juiz-opus`; consistência entre repetições reportada | CA-56 | `docs/evidence/v090-juiz-opus-*.json` e `.md`, delta do ledger | Não se aplica |
| 3. Concordância com o humano | `eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv --rater lauro --judge anthropic/claude-opus-5-5 --judge-run v090-juiz-opus-r3 --campaign v090-juiz-opus --out docs/evidence/v090-juiz-opus.md` (mesmo `RUNTIME_DIR` e `BUDGET_RUNTIME_DIR`; sem chamada paga) | Relatório com os dois juízes lado a lado contra as mesmas 24 notas; decisão pela regra D2 escrita antes | CA-56 | `docs/evidence/v090-juiz-opus.md` | Não se aplica |
| 4. Termo exato | Avaliador pergunta algo que o denso não acha e o BM25 acha (código, sigla, nome raro do conjunto de retrieval) | `eval-retrieval --mode dense` erra, `--mode hybrid` acerta; o Knowledge responde com a passagem certa no modo híbrido | CA-52 | Saída da CLI, trace | Não se aplica |
| 5. Reranker | `eval-retrieval --mode hybrid --rerank on` em `dev` | nDCG@6 e tempo por modo; `RERANK` só fica `on` se melhorar nos dois splits | CA-52 | Relatório | Não se aplica |
| 6. Holdout de retrieval, por último | Lacre conferido; `eval-retrieval --split holdout_v090` uma vez por modo | Tabela denso × híbrido × híbrido+reranker com Recall@6, MRR, nDCG@6; decisão do modo padrão registrada | CA-52 | Relatório e hash | Não se aplica |
| 7. Regressão | Suíte estrita; `search()` sem `mode` igual ao de hoje; 44 casos e 4 conversas offline | Verde; nenhuma resposta muda com o modo padrão denso | Regressão | Suíte | Não se aplica |

Percorra na ordem. Os momentos 1 a 3 só dependem do juiz e podem rodar antes de 80 e 81 estarem prontas.

## Experiência e exceções

O responsável não dá nota nova: as 24 notas da v0.8.0 são reaproveitadas, e o relatório diz isso. Se o Opus recusar ou estourar tokens num julgamento, aquele julgamento conta como falha e o relatório mostra quantos faltaram; nenhuma nota é inventada. Se a projeção da sonda passar do cap, o QA roda uma repetição e registra o motivo.

## Resultado da rodada

(Preenchido pelo Supervisor após o QA.)

## Como terminou

(Preenchido pelo Supervisor após o QA.)
