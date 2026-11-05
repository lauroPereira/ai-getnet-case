# Passagem de papel: QA da v0.9.0, momentos 1 a 3 (experimento do juiz), rodada 2

- **Papel e responsável:** QA nativo, contexto novo; caixa-preta pela CLI (`merchant-assistant eval` e `eval-calibrate`). Sem Docker e sem navegador, como pedido.
- **Objetivo e critérios:** CA-56 pelos momentos 1 a 3 de [juiz-retrieval-v090.md](../historias/juiz-retrieval-v090.md) (versão 1, 2026-11-05), com a spec [juiz-retrieval-v090.md](../specs/juiz-retrieval-v090.md) (D1, D2, D5, "Orçamento") e a regra operacional do P2-4 (complemento de D1; [v090-reviewer-t79.md](v090-reviewer-t79.md), rodada 2).
- **Escopo:** sonda de 3 julgamentos Opus, 72 julgamentos (3 repetições) sobre as 24 respostas da calibração e relatório `eval-calibrate --judge`. Retoma a [rodada 1](v090-qa-juiz-r1.md), que ficou bloqueada por credencial. O responsável trocou a `ANTHROPIC_API_KEY` no `.env`, e o QA não leu o valor.
- **Estado:** **apto** para os momentos 1 a 3. Os três momentos produziram o resultado esperado. Não houve falha, recusa nem corte. O relatório traz tudo o que o CA-56 pede, menos a decisão escrita, que cabe ao Supervisor (ver "Achados"). A regra D2 está verificada abaixo, sem decidir.
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, sem PR. Nada commitado pelo QA.
- **Base e versão final:** candidato [v090-candidato-r1.json](v090-candidato-r1.json) (head do manifesto `80a0853`, fingerprint `e3a8895f…81df`). HEAD durante toda a rodada: `f7ffe2b` (o parecer da rodada 1 sobre `f8f7db4`, só documentação).
- **Independência:** independente (não implementei nem revisei a tarefa 79).

## Pré-checagens (sem custo)

| Verificação | Resultado |
| --- | --- |
| `git rev-parse HEAD` | `f7ffe2b9…`, como pedido |
| sha256 dos 17 arquivos do manifesto (`git show HEAD:<path>`) | 17 de 17 conferem |
| Árvore de trabalho | sem alterações rastreadas; só arquivos não rastreados fora do escopo |
| Suíte estrita | não rodada de novo, a pedido. Outro Reviewer pode estar rodando a suíte da tarefa 80. A pré-condição é a da rodada 1: 2050 passed. Os arquivos do juiz não mudaram desde então (os 17 hashes conferem) |
| Chave Anthropic | presente no `.env` (conferida só a presença, sem ler o valor) |
| Ledger Anthropic `data/runtime/anthropic/budget.sqlite3` antes | 3 lançamentos (máx. id 3), US$0,144128, todos `settled`; `.limit` = 4.0 |
| Ledger do projeto `data/runtime/budget.sqlite3` antes | 3632 lançamentos (máx. id 3632), soma US$1,402518, 0 lançamentos `claude%`; `.limit` = 2.0 |
| Runtime de QA `.pytest_cache/qa-v080-r1/runtime/merchant.sqlite3` | sha256 `1062861e…2e81` antes. Difere do backup `ab3fc701…e3d6`, como esperado: a rodada 1 gravou a sonda e regravou `created_at`. O backup em `.pytest_cache/qa-v090-backup/` está intacto |

Ambiente comum aos comandos (as chaves vêm do `.env`):

```text
JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5 \
BUDGET_RUNTIME_DIR=data/runtime/anthropic BUDGET_LIMIT_USD=4.00 \
RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime
```

## Momento 1, sonda: conforme

```text
merchant-assistant eval --judge-repeat 1 --answers-from docs/evidence/v080-all-r3.json \
  --only-sample docs/evidence/v080-calibracao-amostra.csv --limit 3 --name v090-juiz-opus-sonda2
```

Início 2026-11-05T21:05:44Z, 41 s, rc 0. Saída: "grading 3 of 44 recorded answers (24 request ids in v080-calibracao-amostra.csv), --limit 3", `judge_failed: 0`, "judgements stored in run_evaluations: 3 (execution v090-juiz-opus-sonda2)". Nome novo, como pedido; a execução `v090-juiz-opus-sonda` da rodada 1 ficou intacta.

| Julgamento | Caso | `request_id` | Estado | Entrada | Cache lido / criado | Saída (com pensamento) | Custo no ledger (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `eval_cc15a9756b264d258696` | PT06 (S01) | `req_eval0c6f7493f669` | completed | 3793 | 0 / 0 | 531 | 0,025792 |
| `eval_b12734b8161540409c75` | V030-ENABLEMENT-PENDING | `req_evalda08fa632aaf` | completed | 2530 | 0 / 0 | 205 | 0,014220 |
| `eval_b9304ac2e9c54b3ea7e6` | REPLAN-ACCOUNT | `req_eval4e3529ab6de2` | completed | 2855 | 0 / 0 | 244 | 0,016300 |

- Total da sonda: 9178 tokens de entrada e 980 de saída, sem cache. Custo pelo ledger: US$0,056312 (lançamentos 4 a 6, `settled`; reserva de US$0,047 a US$0,050 por chamada, ajustada ao custo real). O relatório também diz US$0,05631.
- Preço aplicado (`prices.json`): US$4/MTok de entrada e US$20/MTok de saída. Confere com os tokens (por exemplo, 3793 × 4 + 531 × 20 = US$0,025792).
- Projeção para 72: média de US$0,018771 × 72 = **US$1,35**. No pior caso, com o maior custo da sonda × 72, dá US$1,86. Os dois cabem em US$3,50 (cap restante de US$3,79956 menos a margem), então o momento 2 roda com 3 repetições.

## Momento 2, 72 julgamentos: conforme

```text
merchant-assistant eval --judge-repeat 3 --answers-from docs/evidence/v080-all-r3.json \
  --only-sample docs/evidence/v080-calibracao-amostra.csv --name v090-juiz-opus-r3
```

Das 21:07:16Z às 21:11:54Z, rc 0. Saída: "grading 24 of 44 recorded answers", `judge_failed: 0`, "judgements stored in run_evaluations: 72 (execution v090-juiz-opus-r3)".

- No banco, 72 julgamentos com provedor `anthropic`, modelo `claude-opus-5-5`, execução `v090-juiz-opus-r3` e estado `completed` (72 de 72), somando US$1,284220. Os julgamentos Anthropic no runtime ficam assim: `v090-juiz-opus-sonda` 3 (falhos, da rodada 1), `v090-juiz-opus-sonda2` 3 e `v090-juiz-opus-r3` 72.
- Tokens: 222.255 de entrada (média de 3086,9), 19.760 de saída (média de 274,4) e cache 0 / 0.
- Custo por julgamento: média de US$0,017836, mínimo de US$0,011544 e máximo de US$0,033072. Os 72 lançamentos ficaram `settled` (ids 7 a 78).
- Recusas, cortes por `max_tokens` e erros: nenhum. **Nenhum rejulgamento**, então a regra do P2-4 (cópia para `-original` e `--only-sample` filtrado) não precisou ser usada. Nenhuma rodada repetiu um nome.
- No relatório, as médias são groundedness 4,64, factual 4,58, relevance 4,81 e usefulness 4,35; a taxa de `unsupported_claim` é de 0,042 (só PT06, marcada nas 3 de 3 repetições).

## Momento 3, concordância com o humano: conforme

```text
RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime BUDGET_RUNTIME_DIR=data/runtime/anthropic BUDGET_LIMIT_USD=4.00 \
merchant-assistant eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv --rater lauro \
  --judge anthropic/claude-opus-5-5 --judge-run v090-juiz-opus-r3 --campaign v090-juiz-opus \
  --out docs/evidence/v090-juiz-opus.md
```

O comando terminou com rc 0 e sem chamada paga (o ledger Anthropic continuou com 78 lançamentos). Saída:

- "calibrations: 24 stored, 0 updated, 0 skipped (campaign v090-juiz-opus, rater lauro)";
- "judges: anthropic/claude-opus-5-5 (campaign v090-juiz-opus, execution v090-juiz-opus-r3) beside deepseek/deepseek-flash (campaign v080-all-r3, execution legado), 24 human ratings".

O relatório [v090-juiz-opus.md](v090-juiz-opus.md) traz, para os dois juízes contra as mesmas 24 notas humanas:

- exata, ±1, kappa e viés por critério;
- a matriz de `unsupported_claim` e a lista por amostra;
- as execuções consideradas (A com 24, 72 e 72; a sonda fica fora);
- a consistência entre repetições;
- o custo por julgamento e os tokens.

O relatório também diz que não houve avaliação humana nova.

## Regra D2, verificada literalmente (sem decidir)

| Condição | Números (A = Opus, B = DeepSeek) | Resultado |
| --- | --- | --- |
| (a) ±1 por critério não piora em nenhum dos quatro | groundedness 0,958 contra 0,833; factual_correctness 0,958 contra 0,833; relevance 1,000 contra 1,000; usefulness 0,958 contra 0,917 | **atendida**: subiu em três e empatou em relevance |
| (b1) concordância do veredito `unsupported_claim` > 0,667 | 0,875 contra 0,667. Matriz A: ambos sim 1, só humano 3, só juiz 0, nenhum 20. Kappa 0,357 contra −0,200 | atendida |
| (b2) ≥ 2 de S01, S13, S16, S21 marcadas "sim" pelo Opus | S01 (PT06) sim; S13 (PT05) não; S16 (EX01) não; S21 (PT09) não. Na repetição 1 só S01 foi marcada, e a consistência do veredito é de 1,0, então as 3 repetições coincidem | **não atendida** (1 de 4) |
| (b) como um todo | b1 sim, b2 não | **não atendida** |
| (c) consistência exata entre repetições ≥ 0,70 | groundedness 0,972; factual_correctness 1,0; relevance 0,889; usefulness 0,806; `unsupported_claim` 1,0 (72 julgamentos, 72 pares, 0 falhos) | **atendida** |

Resultado: (a) e (c) foram atendidas e (b) não, pela parte das quatro respostas com frase genérica. É o caso que D2 descreve como "lacuna da rubrica, não do modelo". A decisão cabe ao Supervisor e ao responsável.

Dado lateral, fora de D2: a concordância exata de usefulness caiu de 0,583 para 0,417, com viés de −0,46 contra −0,17 (o Opus é mais severo em utilidade). Nas outras três, a exata subiu ou empatou.

## Ledgers e custos

| Ledger | Antes | Depois | Delta |
| --- | --- | --- | --- |
| Anthropic `data/runtime/anthropic/budget.sqlite3` | 3 lançamentos, US$0,144128 | 78 lançamentos, todos `settled`, US$1,484660; `.limit` = 4.0 (não elevado) | **+US$1,340532** em 75 lançamentos |
| ↳ sonda `v090-juiz-opus-sonda2` | | ids 4 a 6 | US$0,056312 |
| ↳ `v090-juiz-opus-r3` | | ids 7 a 78 | US$1,284220 |
| ↳ `eval-calibrate` | | nenhum lançamento | US$0 |
| Projeto `data/runtime/budget.sqlite3` | 3632 lançamentos, US$1,402518, 0 `claude%` | idem | **0** |

- Cap restante no ledger Anthropic: US$4,00 − US$1,484660 = **US$2,515340**.
- Tokens da rodada: 231.433 de entrada e 20.740 de saída (com o pensamento), sem cache.
- Falhas: 0. Rejulgamentos: 0.
- Os US$0,144128 da rodada 1 são reservas de requisições recusadas (HTTP 400). Continuam no ledger e contam no cap.

## Achados e limitações

- **Pendência para o Supervisor, não é defeito:** o CA-56 pede o relatório com "a decisão do juiz padrão com a regra escrita antes (D2)". O relatório gerado traz todos os números da regra, mas não tem uma seção de decisão. O QA não decide (a decisão é do Supervisor e do responsável). Um parágrafo escrito à mão, como o de disclosure da v0.8.0, fecharia o critério.
- **Observação, já registrada pelo Reviewer (rodada 2 da tarefa 79):** na tabela de consistência, B (`legado`) soma a campanha original e uma rodada DeepSeek posterior. São 72 julgamentos e 96 pares (16 respostas com 4 julgamentos e 8 com 1), e o relatório explica isso. Por isso a consistência de B não é estritamente comparável à de A. D2(c) só usa a de A.
- **Observação:** no `.json` e no resumo da CLI, `cost_usd: 0` é o custo das respostas gravadas, não o do juiz. O custo do juiz aparece no `.md` ("Custo do juiz: US$ 1.28422") e no ledger, e os dois conferem.
- **Observação:** o pensamento adaptativo produziu saídas curtas (média de 274 tokens, incluindo o pensamento). O `usage` não separa o pensamento da saída, e os relatórios dizem isso ("saída inclui o pensamento").
- **Observação:** a campanha `v090-juiz-opus` fica gravada em `calibrations` pelo `eval-calibrate`. No `eval`, `campaign` sai `null`, como prevê o complemento de D5 (não há `FixedBudgetGuard` nomeada). A execução é identificada por `--name`.
- **Limitação:** a suíte estrita não foi rodada nesta rodada (pedido do Supervisor). A pré-condição vem da rodada 1, e os 17 hashes conferem.
- **Limitação:** o custo é o do ledger (tokens × `prices.json`). A fatura real da Anthropic só aparece no console.
- **Evidência gerada (não commitada):** `docs/evidence/v090-juiz-opus-sonda2.json` e `.md`, `docs/evidence/v090-juiz-opus-r3.json` e `.md` e `docs/evidence/v090-juiz-opus.md`. Os logs ficam em `.pytest_cache/qa-v090-control/` (`sonda2.log`, `r3.log`, `calibrate.log`). Nenhum dos arquivos gerados tem caminho pessoal ou padrão de chave. A CLI imprime o caminho absoluto do relatório no terminal, mas ele não foi copiado para a evidência.
- **Estado do runtime:** `.pytest_cache/qa-v080-r1/runtime/merchant.sqlite3` terminou com sha256 `18968e43…1c87` (acréscimos: 75 julgamentos e 24 calibrações da campanha `v090-juiz-opus`). Nada foi apagado. As 24 notas da `v080-all-r3` não foram tocadas por este import, que gravou outra campanha.

## Como terminou

O responsável queria saber se um juiz Claude Opus concorda mais com ele do que o DeepSeek. Desta vez a chave funcionou. O Opus julgou as mesmas 24 respostas três vezes sem uma falha, por US$1,34 no total, e quase sempre repetiu a própria nota. Contra as 24 notas humanas, ele erra por mais de um ponto menos que o DeepSeek e acerta o veredito de afirmação sem suporte em 21 de 24 respostas. Ainda assim, das quatro respostas em que o responsável viu uma frase genérica sem fonte, o Opus só pegou uma (PT06). Os números para aplicar a regra escrita antes estão no relatório, e a decisão fica com o responsável.

## Próxima ação e responsável

1. **Supervisor:** aplicar D2 com os números acima e registrar a decisão no relatório do experimento e na história ("Resultado da rodada"). Pela letra de D2, com (a) e (c) atendidas e (b) não, o DeepSeek continua e a rubrica ganha a linha sobre afirmação genérica.
2. **Supervisor:** commitar as evidências desta rodada.
3. **QA:** momentos 4 a 7 (retrieval) quando as tarefas 80 e 81 tiverem candidato fixado.

## Decisão humana pendente

Nenhuma do QA. A escolha do juiz padrão por D2 é do Supervisor e do responsável, pela regra já escrita.
