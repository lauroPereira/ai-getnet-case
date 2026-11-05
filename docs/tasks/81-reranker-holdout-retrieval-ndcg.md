# Tarefa 81 — Reranker, holdout de retrieval e `eval-retrieval` com nDCG

## Objetivo

Medir os modos de retrieval num holdout lacrado, com nDCG@6 além de Recall@6 e MRR, e oferecer um reranker configurável que só fica ligado se melhorar.

## Especificação relacionada

[Juiz Claude e retrieval híbrido v0.9.0](../specs/juiz-retrieval-v090.md): D7, D8, CA-52; especificação 0.2 RF-95 e RF-96.

## Pré-condições

Tarefa 80 commitada na branch. O holdout é escrito **antes** de medir qualquer modo nele e lacrado por hash no mesmo commit em que nasce.

## Arquivos prováveis

`tests/scenarios/retrieval_holdout_v090.jsonl` e `.sha256` (novos), `src/merchant_assistant/rag/rerank.py` (novo), `prompts/rerank.v1.md` (novo), `rag/index.py` (`rerank` após a fusão), `config.py` (`rerank`, só por acréscimo), `cli.py` (`eval-retrieval --mode --split --rerank`), `evaluation/` (nDCG), testes.

## Passos

1. **Holdout.** ≥ 20 perguntas, metade em português, cada uma com o `chunk_id` da passagem correta (e opcionalmente uma segunda relevante com grau 1), cobrindo produtos, taxas, procedimentos e termos exatos; escritas sem consultar os resultados de nenhum modo; `sha256` do arquivo gravado ao lado e conferido por teste, como o `holdout_v080`.
2. **nDCG@6.** Implementação com ganho binário ou graduado conforme o rótulo; teste com números fixos (ranking perfeito = 1,0; invertido conhecido).
3. **Reranker.** `rerank.v1` (prompt versionado): recebe a pergunta e os 12 primeiros da fusão, devolve a ordem dos ids com saída estruturada; modelo do agente (`gpt-6-luna`), `max_output_tokens` pequeno, medido pelo `Meter`; `RERANK=on|off` (padrão `off`); falha do reranker mantém a ordem da fusão e anota no trace.
4. **CLI.** `eval-retrieval --mode dense|hybrid --rerank on|off --split dev|holdout_v090`: tabela com Recall@6, MRR, nDCG@6 e tempo médio por consulta; o holdout exige lacre válido e grava no relatório que foi usado (como o `holdout_v080`, "já visto" depois da primeira execução real).
5. **Decisão.** O relatório gerado inclui a linha "modo padrão sugerido" pela regra D7 (híbrido se melhorar em `dev` e confirmar no holdout; reranker só se melhorar nDCG@6 nos dois); a decisão final é do Supervisor na tarefa 82.

## Critérios de conclusão

- Holdout lacrado, conferido por teste, nunca lido por teste de desenvolvimento do modo.
- nDCG@6 com testes de números fixos; reranker programado testado em sucesso, falha e limite de tokens.
- `eval-retrieval` roda os três modos e dois splits sem rede, com embeddings de hash.
- `lint_and_tests.py --strict` verde.

## Validação

Developer, 2026-11-05, commits `8c1970b` (holdout e lacre, antes de qualquer código que mede), `2856be1` (reranker), `37dfbf6` (`eval-retrieval`) e `4c27e4a` (`.env.example`), na `codex/v0.9.0-juiz-retrieval`. Passagem: [v090-developer.md](../evidence/v090-developer.md), seção "Tarefa 81".

- **Holdout:** `tests/scenarios/retrieval_holdout_v090.jsonl` tem 25 perguntas (13 pt, 12 en) de taxas, produtos, procedimentos e termos exatos. Cada uma tem a passagem correta por `chunk_id` com grau 2 e, em 12, uma segunda com grau 1. O lacre é `d8381ddd7d7f…` (sha256 com LF). O teste confere o lacre, a forma, os `chunk_id` no corpus, ids e perguntas novos e que nenhum outro teste cita o arquivo. Nenhum modo foi medido nele, nem com hash.
- **nDCG@6:** ganho linear e desconto `log2`. No `dev`, rótulo por documento com um alvo só. Testes com números fixos: ideal 1,0, invertido 0,859719, relevante em 6º 0,356207, 7º fora.
- **Reranker:** prompt `rerank.v1`, saída estruturada com a ordem dos rótulos `P1`…`P12`, 150 tokens de saída, modelo do agente e medido pelo `Meter`. Fica em `RERANK=on|off`, padrão `off`, e exige `RETRIEVAL_MODE=hybrid`. Falha, ordem inválida, orçamento, limite da requisição e limite de tokens mantêm a ordem da fusão e ficam anotados no trace. O Knowledge só o usa com `on`.
- **CLI:** `eval-retrieval --mode dense|hybrid --rerank on|off --split dev|holdout_v090 [--out x.md]` mede Recall@6, MRR, nDCG@6 e o tempo médio. O holdout com lacre inválido é recusado antes de qualquer chamada paga. O relatório registra o holdout usado e o sha. `--out` acumula as 6 combinações, marca "holdout já visto" quando uma é repetida e escreve a linha "Modo padrão sugerido" pela regra D7.
- **Testes novos:** 47. Os 3 modos nos 2 splits rodam sem rede pela CLI, e o holdout desse teste é sintético e lacrado num diretório temporário.
- **Referência com hash, só `dev` (19 perguntas):** denso nDCG@6 0,534; híbrido 0,843; híbrido+reranker programado 0,825 (Recall e MRR do denso e do híbrido iguais aos da tarefa 80).
- **`lint_and_tests.py --strict`:** 2096 passed, 1 skipped (o do basetemp), ruff limpo, caminhos limpos (746 arquivos), exit 0.
- Decisões além do texto (regra D7 por nDCG@6 estritamente maior, fusão a 12 com reranker, rótulos curtos, teto de US$0,05 por execução paga do reranker) e o roteiro do QA estão na passagem.

## Status

Aberta pelo Supervisor em 2026-11-05. Rodada 1 implementada pelo Developer em 2026-11-05; aguarda revisão. Critérios da spec não marcados (Supervisor, depois da revisão e do QA).
