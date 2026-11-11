# Tarefa 91a — Preservar os bytes da amostra selada no checkout

## Objetivo

Garantir que os CSVs de calibração versionados conservem os mesmos bytes registrados em `tests/scenarios/calibration_v0110.sha256` em qualquer checkout.

## Especificação relacionada

[Juiz por afirmação, evidência da web e retrieval — v0.11.0](../specs/juiz-retrieval-v0110.md), D5.

## Comportamento

`.gitattributes` marca como `-text` os dois CSVs de calibração e o selo. O checkout não normaliza finais de linha nem altera o conteúdo selado.

## Critérios de conclusão

- Os hashes dos CSVs após checkout conferem com o selo tanto em checkout com finais LF quanto CRLF.
- O selo e os CSVs permanecem inalterados; a amostra não precisa ser regenerada.
- O teste offline confirma os atributos Git e compara os bytes dos CSVs com os hashes selados.

## Resultado

`.gitattributes` preserva os bytes dos CSVs selados; um teste offline compara os bytes com os hashes do selo.
Evidência: [resultado da v0.11.0](../evidence/v0110-resultado.md).

## Status

```text
concluída (v0.11.0)
```
