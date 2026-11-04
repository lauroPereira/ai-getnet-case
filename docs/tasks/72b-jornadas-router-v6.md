# Tarefa: jornadas de negócio e `router.v6`

## Objetivo

As jornadas de negócio passam de 7/13 para pelo menos 12/13 pela rubrica: as quatro falhas de redação nos casos de preço e a pergunta de condições em inglês que cai em `clarify`.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md) — D15; [spec 0.2](../specs/evolucao-pos-feedback.md) RF-93, CA-51; [plano](../specs/evolucao-pos-feedback-plano.md) decisão técnica 16; limitações em `docs/evidence/v060-resultado.md`.

## Pré-condições

Spec v0.8.0 aprovada; tarefa 69 integrada na branch `codex/v0.8.0-replan` (o replanejamento muda o caminho de alguns casos). Não abrir `tests/scenarios/holdout_v080*`: ajuste de prompt nunca guiado pelo holdout.

## Arquivos prováveis

`prompts/router.v6.md` (novo), `prompts/support.v8.md` (novo, só se a redação vier do Support), `tests/scenarios/business_journeys.jsonl`, `data/scenarios/catalog.json` (rótulos irmãos, mantidos em acordo), `evaluation/scripted_policy.py`, testes.

## Passos

1. Para cada caso que falha, comparar a resposta real gravada na v0.6.0 com o rótulo e classificar: resposta correta com rótulo literal demais → ajustar o rótulo, com justificativa por caso na passagem; resposta errada → ajustar prompt.
2. `router.v6` com a forma interrogativa em inglês da pergunta de condições; regressão programada com a frase e variações.
3. Manter catálogo e JSONL em acordo nos rótulos dos casos irmãos (teste que compara os dois).

## Critérios de conclusão

- [ ] Cada rótulo alterado tem justificativa por caso; nenhum check afrouxado sem motivo.
- [ ] Regressão programada do Router com a pergunta em inglês e variações.
- [ ] 40 casos e 4 conversas sem piora no eval programado.
- [ ] Suíte estrita com código 0; nenhuma chamada paga.

## Validação

Passagem, com a tabela caso a caso (rótulo ou prompt, antes e depois, justificativa), em [v080-developer.md](../evidence/v080-developer.md), seção "Tarefa 72b". Candidato: `046cb73` (commits `b1b4951`, `46e5600`, `046cb73`), base `5da3de5`.

- **Re-pontuação das respostas reais gravadas** (v0.7.0, sem modelo): 6/13 com os rótulos de antes, **10/13** com os de agora; os três que faltam são os que só prompt resolve e que só a campanha real mede (`V030-PRICE-CONDITIONS`, `V030-PT-PRICE-CONDITIONS` na primeira execução, `V030-CONTRACT-TERMINATION`). A repetição real do `V030-PT-PRICE-CONDITIONS` (resposta de Support, redigida "condições distintas") passa no rótulo novo. Com o `router.v6` resolvendo as duas perguntas de condições, 12/13; com o `personality.v5` dizendo "human agent", 13/13.
- **Rótulos alterados (5), prompts novos (3):** `router.v6`, `personality.v5` e `replan.v2` (arquivos anteriores intactos). Valores, ferramentas, status, rota e fontes dos rótulos não mudaram; cada grupo de redação ampliado ganhou frases-guarda do sentido oposto.
- **Acréscimo do Supervisor (P3 da revisão da 69):** rótulo `REPLAN-WEB` (jsonl e catálogo em acordo), testes dos mutantes A08 e A09, e a lacuna declarada chegando ao texto (`personality.v5` e texto de reserva).
- **Testes** (um pytest por vez, basetemp novo `.pytest_cache/t72b-dev-*`, `-p no:cacheprovider`): novos e afetados **256 passed** (`test_v080_journeys` 41, `test_v080_replan` 63, runner, use_cases, v060_api, closing, ticket_id, unit do replanner, jornadas de ferramentas); trava da v0.7.0 **94 passed**, arquivos sem alteração; `tests/unit` **279 passed**; os outros 14 arquivos de integração **199 passed**. `ruff check src tests`: ok.
- **Regressão programada** (40 casos e 4 conversas, `main` por `git archive` contra a árvore): idênticas campo a campo (25/40 e 4/4, 123 chamadas), inclusive resposta, `agents`, ferramentas e os nove checks por caso.
- Mutações (cópia fora do repositório): 9 sondas, 8 mortas; a que sobrou remove uma frase de prompt sem efeito sobre o que o teste afirma (equivalente).
- Não rodei a suíte estrita, nenhuma chamada paga, nenhuma rede, `.env` não lido, `holdout_v080*` não aberto.

## Status

```text
implementada em 2026-11-04 na branch codex/v0.8.0-replan (candidato 046cb73); aguarda revisão e a campanha real do QA, que mede o efeito dos prompts (critérios de conclusão ainda não marcados)
```
