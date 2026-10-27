# Tarefa: Regressão e liberação da v0.2.0

## Objetivo

Comprovar que a v0.2.0 não regrediu o núcleo, registrar o changelog com instruções de retorno e preparar a tag.

## Especificação relacionada

[Complementar](../specs/incrementos-pos-nucleo.md): CA-27, CA-28, CA-29, CA-30.

## Pré-condições

- Tarefas 16 a 19 concluídas.

## Arquivos prováveis

- `CHANGELOG.md`, `README.md`
- `tests/scenarios/` (cenários multi-turno)
- `docs/evidence/` (relatório da regressão)

## Passos

1. Suíte completa sem rede e validação estrita do template.
2. Avaliação real do núcleo (27 casos) e dos cenários novos, com custo registrado no orçamento.
3. Docker em ambiente limpo e smoke dos 10 exemplos.
4. Changelog da v0.2.0: funcionalidades, contratos, dados, validação, limitações e retorno para a v0.1.0.
5. Pedido de autorização para PR, merge e tag `v0.2.0`.

## Critérios de conclusão

- [ ] Núcleo sem regressão nas verificações automáticas.
- [ ] Cenários de memória, acompanhamento e MCP aprovados.
- [ ] Changelog com instruções de retorno.

## Validação

A preencher na execução.

## Status

```text
pendente
```
