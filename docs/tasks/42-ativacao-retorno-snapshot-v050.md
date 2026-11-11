# Tarefa: ativação, retorno e base capturada por execução

## Objetivo

Trocar a base atomicamente sem alterar o atendimento em curso.

## Especificação relacionada

RF-64–65, CA-41 e [ADR 0014](../architecture/decisions/0014-ciclo-kb-v050.md).

## Pré-condições

Plano aprovado; candidata íntegra/pronta e anterior preservada.

## Arquivos prováveis

Registro/serviço KB, grafo/RunContext, trace/snapshot e API.

## Passos

1. Ativar com ativa esperada e confirmação; registrar ator/evento.
2. Resolver/capturar índice e versão no início de cada atendimento.
3. Retornar explicitamente à anterior íntegra, sem apagar coleções.
4. Testar corrida de ativação e execução presa à versão inicial.

## Critérios de conclusão

- [x] Conflito 409; demo não ativa; estado inválido não muda ponteiro.
- [x] Uma versão por run, registrada; nova execução vê a nova ativa.
- [x] Rollback e legado/MCP preservados, sem remoção de dados.

## Resultado

Ativação e retorno por troca condicional (CAS) com ator e evento; o índice antigo segue utilizável após a ativação, e o trace registra a versão capturada no início do atendimento; conflito obsoleto retorna `409`. Suíte estrita do backend: 293 testes. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
