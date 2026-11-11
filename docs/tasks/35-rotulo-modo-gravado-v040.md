# Tarefa: alinhar rótulo e snapshot do modo Gravado v0.4.0

## Objetivo

Fazer com que a resposta visível, o indicador da interface e o snapshot de execução identifiquem de forma consistente uma resposta reapresentada em modo Gravado.

## Especificação relacionada

docs/specs/perfis-interface-v040-plano.md; docs/historias/perfis-interface-v040.md; critérios CA-35 e RF-48.

## Pré-condições

Reproduzir a divergência registrada na validação da interface (na tag `v0.4.0`). Preservar a semântica de resposta sintética salva e não usar provedores externos.

## Arquivos prováveis

Código da interface web e testes de apresentação dos modos Simulado/Gravado.

## Passos

1. Reproduzir o caso descrito no relatório de validação, comparando resposta, indicador e snapshot.
2. Corrigir a origem do rótulo exibido para que reflita o modo efetivamente executado.
3. Acrescentar regressão automatizada que falhe na divergência observada e cubra Simulado e Gravado.
4. Validar UI e suíte web completa sem chamadas a provedores.

## Critérios de conclusão

- [x] A resposta no modo Gravado não se identifica como Simulado.
- [x] Indicador da interface e snapshot da execução continuam consistentes.
- [x] O modo Simulado segue identificado corretamente.
- [x] Teste de regressão reproduz a condição anterior e passa após a correção.
- [x] Nenhuma chamada a provedor pago é necessária.

## Resultado

Resposta, indicador da interface e snapshot identificam Gravado e Simulado de forma consistente; `tests/test_interface.py::test_simulated_and_recorded_modes_are_distinct_and_consume_comparison_once` cobre os dois modos. Suíte web: 12 testes, Ruff aprovado, sem chamadas a provedores. Evidência: [resultado da v0.4.0](../evidence/v040-resultado.md).

## Status

```text
concluída (v0.4.0)
```
