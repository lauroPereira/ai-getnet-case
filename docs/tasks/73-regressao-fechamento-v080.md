# Tarefa: regressão integrada e preparação do QA da v0.8.0

## Objetivo

Provar a história da v0.8.0 com modelo programado sobre as tarefas 69, 70, 71 e 72b integradas e deixar a campanha `v080-qa` pronta e estimada.

## Especificação relacionada

[Spec v0.8.0](../specs/orquestracao-avaliacao-v080.md), critérios e requisitos não funcionais; [história](../historias/orquestracao-avaliacao-v080.md); [plano](../specs/evolucao-pos-feedback-plano.md) tarefa 73 e "Estratégia de testes".

## Pré-condições

Tarefas 69, 70, 71 e 72b com parecer apto; branch do Time B integrada pelo Supervisor na branch da versão. Fechamento do Supervisor (evidência, README, CHANGELOG, ADR 0019 aceita, merge) fica fora desta tarefa.

## Arquivos prováveis

`tests/integration/` (história programada), `evaluation/` só se a campanha não montar, `pyproject.toml` e `__init__.py` (versão `0.8.0`), testes.

## Passos

1. Teste de integração programado dos momentos 1 a 8 da história: quatro cenários de replanejamento, laço evitado, pergunta simples sem chamada a mais, `eval --judge --repeat 3` e `--judge-repeat 3` com juiz programado de "outro provedor" e jornadas. O relatório separado por split é provado com um split sintético do teste; o `holdout_v080` real nunca roda fora do QA (D17).
2. Campanha `v080-qa` montável com teto de US$0,50 uma única vez, combinada com o ledger primário (teste sem rede).
3. Estimador de custo da campanha a partir de N casos medidos (usado pelo QA antes de montar), com as duas etapas da D12 (agente 3 vezes; juiz 3 vezes sobre a primeira execução).
4. Roteiro do QA com o holdout como último passo técnico (D17).
5. Versão `0.8.0`; `docker compose config` válido.

## Critérios de conclusão

- [ ] CA-49, CA-50 (parte determinística) e CA-51 (parte programada) cobertos pelo teste da história.
- [ ] Suíte estrita com código 0; nenhuma chamada paga.
- [ ] Campanha `v080-qa` montável com US$0,50 e estimativa reproduzível (teste).

## Roteiro do QA (D17)

1. Antes da amostra paga, confirme que `BUDGET_RUNTIME_DIR` aponta para o diretório persistente de orçamento do projeto; a imagem Docker mantém `/app/runtime` nesse papel mesmo quando `RUNTIME_DIR` é isolado para o QA. Fora desse padrão, configure o caminho persistente explicitamente: a CLI recusa antes de chamar o provedor se `RUNTIME_DIR` for novo e `BUDGET_RUNTIME_DIR` estiver ausente. Com as validações determinísticas, o smoke Docker e os demais momentos aptos, meça cinco casos de `dev` com `eval --judge --include-replan --split dev --limit 5 --no-conversations --name v080-custo-amostra`.
2. Gere a estimativa sem nova chamada de modelo: `merchant-assistant eval-estimate --from docs/evidence/v080-custo-amostra.json --out docs/evidence/v080-custo-estimativa.json`. Mantenha o relatório e a estimativa no mesmo diretório: o artefato referencia a amostra e a CLI revalida a origem e recalcula toda a projeção antes de aceitar o teto de US$1,00. A CLI só aceita relatório `mode=real`, com pelo menos cinco casos distintos, custo positivo de agente e juiz e todos os juízos completos e consistentes com o modelo independente configurado; amostra scripted, custo zero ou juiz incompleto não podem recomendar um teto pago. A projeção inclui os splits `dev`, `holdout` e `holdout_v080` (25 casos conforme a tarefa 72a), sem abrir o JSONL lacrado; separa as três execuções do agente e as três avaliações do juiz sobre cada primeira resposta; usa a média global quando o sample não contém um split; e acrescenta as quatro conversas de acompanhamento, somando os turnos de `followup.jsonl` uma vez cada ao custo médio medido do agente por resposta, sem chamadas de juiz.
3. Monte `v080-qa` uma vez com o teto recomendado no JSON. Até US$0,50, use `--campaign v080-qa`. Acima de US$0,50 e até US$1,00, use `--campaign v080-qa --campaign-cap-usd 1.00 --campaign-estimate docs/evidence/v080-custo-estimativa.json` em cada fase. A CLI só cria a guarda do cap depois de verificar a amostra referenciada e confirmar que o artefato inteiro corresponde à projeção recalculada. Acima de US$1,00, pare e peça decisão ao responsável. O mesmo ledger fixo e o ledger primário guardam agente, ferramentas pagas e juiz.
4. Rode os splits de desenvolvimento e o holdout legado com `eval --campaign v080-qa --include-replan --judge --repeat 3 --split all --name v080-all`; depois `eval --campaign v080-qa --judge-repeat 3 --answers-from docs/evidence/v080-all.json --name v080-all-judge`. O `all` contém os 40 casos, os quatro cenários de replanejamento e as quatro conversas de acompanhamento.
5. Antes do holdout, conclua correções, revisão, sorteio da amostra de calibração a partir dos relatórios de desenvolvimento e o smoke final. Só então rode `eval --campaign v080-qa --judge --repeat 3 --split holdout_v080 --name v080-holdout-v080`, seguido de `eval --campaign v080-qa --judge-repeat 3 --answers-from docs/evidence/v080-holdout-v080.json --name v080-holdout-v080-judge`. Esse par fecha a rodada técnica; não ajuste prompts ou código com base no resultado. Uma nova rodada deve marcar o holdout como já visto.
6. O responsável preenche e importa a calibração depois do bloco técnico final; ela não autoriza nova correção baseada no holdout.

## Validação

A preencher pelo Developer.

## Status

```text
pendente (spec aprovada; começa depois do merge da v0.7.0)
```
