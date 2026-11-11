# Tarefa: jornadas de negócio e `router.v6`

## Objetivo

As jornadas de negócio passam de 7/13 para pelo menos 12/13 pela rubrica: as quatro falhas de redação nos casos de preço e a pergunta de condições em inglês que cai em `clarify`.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md) — D15; [spec 0.2](../specs/evolucao-producao-v070-v0100.md) RF-93, CA-51; [plano](../specs/evolucao-producao-v070-v0100-plano.md) decisão técnica 16; limitações em `docs/evidence/v060-resultado.md`.

## Pré-condições

Spec v0.8.0 aprovada; tarefa 69 integrada (o replanejamento muda o caminho de alguns casos). Não abrir `tests/scenarios/holdout_v080*`: ajuste de prompt nunca guiado pelo holdout.

## Arquivos prováveis

`prompts/router.v6.md` (novo), `prompts/support.v8.md` (novo, só se a redação vier do Support), `tests/scenarios/business_journeys.jsonl`, `data/scenarios/catalog.json` (rótulos irmãos, mantidos em acordo), `evaluation/scripted_policy.py`, testes.

## Passos

1. Para cada caso que falha, comparar a resposta real gravada na v0.6.0 com o rótulo e classificar: resposta correta com rótulo literal demais → ajustar o rótulo, com justificativa por caso; resposta errada → ajustar prompt.
2. `router.v6` com a forma interrogativa em inglês da pergunta de condições; regressão programada com a frase e variações.
3. Manter catálogo e JSONL em acordo nos rótulos dos casos irmãos (teste que compara os dois).

## Critérios de conclusão

- [x] Cada rótulo alterado tem justificativa por caso; nenhum check afrouxado sem motivo.
- [x] Regressão programada do Router com a pergunta em inglês e variações.
- [x] 40 casos e 4 conversas sem piora no eval programado.
- [x] Suíte estrita com código 0; nenhuma chamada paga.

## Resultado

Cinco rótulos ampliados com frases-guarda do sentido oposto e três prompts novos (`router.v6`, `personality.v5`, `replan.v2`). Re-pontuação das respostas reais gravadas: 6/13 → 10/13 pelos rótulos; os três casos restantes dependiam de prompt e foram medidos na campanha real. Regressão programada idêntica (25/40, 4/4, 123 chamadas); 19 mutantes novos mortos. Evidência: [validação pré-holdout](../evidence/v080-d12-pre-holdout-r6.md).

## Status

```text
concluída (v0.8.0)
```
