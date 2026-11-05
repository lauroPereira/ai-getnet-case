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

(Preenchida pelo Developer.)

## Status

Pendente. Aberta pelo Supervisor em 2026-11-05.
