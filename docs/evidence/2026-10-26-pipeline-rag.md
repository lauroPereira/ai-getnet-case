# Evidência: pipeline de ingestão RAG

Tarefa: [07](../tasks/07-pipeline-ingestao-rag.md). Data: 2026-10-26. Verificação automatizada.

## Ingestão

- `merchant-assistant ingest` coletou as 32 fontes de [data/sources/public-sources.json](../../data/sources/public-sources.json) (30 por HTTP com `robots.txt` respeitado e 1 s entre requisições; 2 a partir da captura renderizada). Nenhuma falha. Cópias em `data/snapshots/public/pages/`, cada uma com URL, título, data de coleta, forma de captura e hash do conteúdo.
- Base fictícia promovida para `data/knowledge-demo/` (8 procedimentos). Ajustes: nome da ferramenta de autorizações, tabela de códigos de negativa sintéticos e aviso de disponibilidade nos procedimentos de preço, habilitação e cancelamento (consultas previstas para a fatia 3).
- Corpus: 40 documentos, 145 fragmentos, média de 907 caracteres.

## Recuperação

Conjunto de desenvolvimento [tests/scenarios/retrieval.jsonl](../../tests/scenarios/retrieval.jsonl): 14 perguntas (7 exemplos do enunciado em inglês e suas versões em português). Acerto = pelo menos um documento esperado entre os k primeiros.

| Embedder | k | Recall@k geral | Inglês | Português | MRR |
| --- | --- | --- | --- | --- | --- |
| `text-embedding-3-small` | 6 | 1,00 | 1,00 | 1,00 | 1,00 |
| Hash lexical (testes offline) | 6 | 0,86 | — | — | 0,68 |

Maior similaridade do primeiro resultado: 0,43 a 0,60 em inglês e 0,54 a 0,72 em português. Resultado completo por pergunta em [2026-10-26-recuperacao-k6.json](2026-10-26-recuperacao-k6.json).

Custo: 37.351 tokens de embedding, US$0,0007.

## Decisões

- A pergunta em inglês recupera o conteúdo em português sem reescrita: a reescrita prevista na tarefa 10 não será ativada.
- O limiar mínimo de similaridade (0,30) fica abaixo dos menores valores relevantes observados; será recalibrado com perguntas fora do domínio na tarefa 14.

## Limitações

- Amostra pequena e usada no desenvolvimento; não é um conjunto reservado.
- Testes automatizados usam o embedder lexical, que mede o encadeamento do pipeline e não a qualidade semântica.
