# Tarefa 91 — Coerência funcional da v0.11.0

## Objetivo

Consolidar as decisões funcionais da v0.11.0 e manter o produto, as evidências de resultado e a documentação coerentes.

## Especificação relacionada

[Juiz por afirmação, evidência da web e retrieval — v0.11.0](../specs/juiz-retrieval-v0110.md): CA-60 a CA-64 e D6–D8. [Plano do roadmap](../specs/roadmap-v0110-v100-plano.md#decisões-técnicas).

## Critérios de conclusão

- As capacidades CA-60 a CA-64 estão documentadas e cobertas por testes offline.
- `judge.v5` é o padrão; `judge.v3` e `judge.v4` continuam selecionáveis explicitamente.
- Retrieval usa `RETRIEVAL_MODE=hybrid`, `RERANK=on` por padrão e permite `RERANK=off`; `hybrid@36` e o piso BM25 seguem disponíveis como controles.
- [Síntese da v0.11.0](../evidence/v0110-resultado.md), [métricas de retrieval](../evidence/v0110-retrieval.md), [CSV de calibração](../evidence/v0110-calibracao-amostra.csv) e [CSV de afirmações](../evidence/v0110-calibracao-amostra-claims.csv) estão preservados, junto ao [selo](../../tests/scenarios/calibration_v0110.sha256).
- ADR 0023, README, CHANGELOG e versão do produto descrevem os mesmos padrões e capacidades.
