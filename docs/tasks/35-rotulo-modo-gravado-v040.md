# Tarefa: alinhar rótulo e snapshot do modo Gravado v0.4.0

## Objetivo

Fazer com que a resposta visível, o indicador da interface e o snapshot de execução identifiquem de forma consistente uma resposta reapresentada em modo Gravado.

## Especificação relacionada

docs/specs/perfis-interface-v040-plano.md; docs/historias/perfis-interface-v040.md; critérios CA-35 e RF-48.

## Pré-condições

Reproduzir a evidência em docs/evidence/v040-qa-r3.md. Preservar a semântica de resposta sintética salva e não usar provedores externos.

## Arquivos prováveis

Código da interface web e testes de apresentação dos modos Simulado/Gravado.

## Passos

1. Reproduzir o caso descrito no relatório de QA, comparando resposta, indicador e snapshot.
2. Corrigir a origem do rótulo exibido para que reflita o modo efetivamente executado.
3. Acrescentar regressão automatizada que falhe na divergência observada e cubra Simulado e Gravado.
4. Validar UI e suíte web completa sem chamadas a provedores.

## Critérios de conclusão

- [x] A resposta no modo Gravado não se identifica como Simulado.
- [x] Indicador da interface e snapshot da execução continuam consistentes.
- [x] O modo Simulado segue identificado corretamente.
- [x] Teste de regressão reproduz a condição anterior e passa após a correção.
- [x] Nenhuma chamada a provedor pago é necessária.

## Validação

`ai-getnet-case-web/tests/test_interface.py::test_simulated_and_recorded_modes_are_distinct_and_consume_comparison_once` valida a resposta visível e os snapshots nos dois modos. Suíte web r4: 12 testes passaram; Ruff check e format passaram. Sem chamadas a provedores. Detalhes em `docs/evidence/v040-developer-r4.md`.

## Status

Concluída no escopo sem custo: implementação r4, revisão e confirmação pela
UI no [QA r5](../evidence/v040-qa-r5.md); modo Gravado e snapshot coerentes.

