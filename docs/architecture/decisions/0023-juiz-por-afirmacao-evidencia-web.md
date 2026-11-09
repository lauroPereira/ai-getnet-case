# 0023. Promover `judge.v5` e `RERANK` após medir o controle de profundidade

## Título

Tornar o juiz por afirmação padrão e habilitar o reranker após comparar com `hybrid@36`.

## Status

```text
aceita (v0.11.0, 2026-11-09)
```

## Contexto

1. A v0.10.0 manteve `judge.v3` como padrão. A v0.11.0 introduziu `judge.v5`, que enumera as afirmações, avalia cada uma contra a evidência e calcula `unsupported_claim` em código. D6(g) definiu antes da medição que um candidato só seria promovido com κ ≥ 0,6 no veredito das 36 respostas seladas e sem queda superior a 0,05 no acordo ±1 de qualquer critério.
2. A calibração usou as notas do responsável nas 36 respostas seladas e um painel de modelos declarado como segundo rotulador. O lote de 130 propostas de adjudicação foi gerado por `gpt-6.1-sol` ultra e aceito pelo responsável; não é descrito como escrito nem revisado individualmente por uma pessoa.
3. A ADR 0020 manteve `RERANK=off` porque a comparação original confundia o efeito do modelo com a profundidade da fusão. A tarefa 90 acrescentou `hybrid@36`, o controle sem modelo na mesma profundidade, e D7 definiu a decisão pelo ganho de nDCG@6 nos dois splits.

## Decisão

- `judge.v5` passa a ser o padrão de `eval`, `eval --judge-repeat` e das resoluções que usam a rubrica configurada. `judge.v3` e `judge.v4` continuam disponíveis por `--rubric v3` e `--rubric v4`. Os arquivos congelados `prompts/judge.v5.md` e `prompts/judge_claims.v1.md` não mudam.
- D6(g), nas 36 respostas seladas com rótulo ouro e avaliação humana:

  | Candidato | κ do veredito (IC 95%) | ±1: groundedness / factual correctness / relevance / usefulness | Custo por julgamento |
  | --- | ---: | --- | ---: |
  | `judge.v3` (base) | 0,538 (−0,04 a 0,89) | 0,944 / 0,917 / 0,972 / 0,917 | US$ 0,000398 |
  | `judge.v5` | **0,647** (0,28 a 0,92) | **0,972 / 0,972 / 1,000 / 1,000** | US$ 0,000945 |

  `judge.v5` supera o piso de κ e não reduz o acordo ±1 de nenhum critério em mais de 0,05. A diferença maior, +0,083 em usefulness, é uma melhora; nenhum critério foi piorado. A amostra é pequena e o intervalo de κ é amplo.
- `RERANK=on` passa a ser o padrão, com `RETRIEVAL_MODE=hybrid` mantido. O reranker vence `hybrid@36` em nDCG@6 no dev (0,981 contra 0,974) e no holdout (0,972 contra 0,907). `RERANK=off` continua sendo a opção explícita para quem preferir a ordem RRF sem a chamada adicional. A medição completa está em [v0.11.0 retrieval](../../evidence/v0110-retrieval.md).

## Alternativas consideradas

- **Manter `judge.v3` como padrão:** não atende ao piso κ ≥ 0,6 definido em D6(g); permanece disponível para execução explícita.
- **Promover `judge.v4`:** não foi candidato na comparação D6(g) da v0.11.0; permanece disponível sem substituir a decisão medida.
- **Manter `RERANK=off`:** evita uma chamada de modelo em buscas de Knowledge, mas ignora o ganho que o controle de mesma profundidade confirmou nos dois splits.
- **Comparar o reranker apenas com `hybrid`:** mantém a confusão entre a reordenação do modelo e a profundidade 36; `hybrid@36` é a referência adequada.

## Consequências

- As avaliações de campanha passam a verificar cada afirmação contra a evidência, incluindo o texto das páginas citadas em respostas web. `unsupported_claim` é derivado dos vereditos por afirmação.
- O julgamento padrão faz duas chamadas e custa aproximadamente 2,4 vezes o `judge.v3` por resposta na amostra medida. O modelo permanece configurável e a rubrica antiga segue explícita.
- O reranker acrescenta uma chamada de modelo por busca de Knowledge; `RERANK=off` permite desativá-la por configuração. Falhas continuam retornando a ordem sem reranking.
- As medições de retrieval sustentam a configuração padrão, mas representam 19 perguntas de dev e 25 de holdout. Os resultados e a decisão são reversíveis por configuração.

## Data

2026-11-09.
