# Tarefa: build/teste de candidata e guarda de embeddings

## Objetivo

Construir/testar coleção própria com estimativa e reserva antes da rede.

## Especificação relacionada

[Plano](../specs/base-versionada-v050-plano.md), RF-64/75 e CA-41/45.

## Pré-condições

Plano aprovado e snapshots/revisões disponíveis; preços conhecidos.

## Arquivos prováveis

`rag/index.py`, `rag/embed.py`, serviço KB, montagem de runtime, API e testes.

## Passos

1. Calcular manifesto/digest e estimativa conservadora sem inferência.
2. Validar confirmação/digest/teto e criar coleção nunca usada, sem rebuild da ativa.
3. Reservar cada lote/consulta antes do provedor; liquidar sem callback duplicado.
4. Testar integridade/recuperação, estados e falhas, bloqueando ativação incompleta.

## Critérios de conclusão

- [x] Negação/custo desconhecido gera zero chamadas; gasto anterior preservado.
- [x] Falha não altera ativa; candidata incompleta não é pronta.
- [x] Manifesto/modelo/dimensão conferidos; fontes tratadas como evidência.

## Resultado

Build cria coleção inédita com estimativa local e reserva por lote antes do provedor; candidata incompleta não ativa. Testes cobrem negação antes da rede, liquidação única, sublimite de campanha persistido e colisão sem substituir coleção. Suíte estrita do backend: 293 testes. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
