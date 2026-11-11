# Tarefa: Ferramentas e comparação de preço

## Objetivo

Responder contestações com quatro resultados comprovados pela comparação determinística entre pricing e cobrança.

## Especificação relacionada

RF-32, RF-46, CA-21, CA-31, UC-23; [plano](../specs/jornadas-v030-plano.md).

## Pré-condições

Tarefa 21; autorização da ampliação de ferramentas e dos dados contratuais.

## Arquivos prováveis

Ferramentas/registro, clientes, comparador de preço, dados contratuais, prompts novos, política programada e testes.

## Passos

1. Implementar `simulate_pricing`, `get_fee_breakdown` e contexto aditivo em `get_contract_snapshot`, sem argumento livre de cliente.
2. Comparar em centavos somente evidências compatíveis, com componentes, parcelas e condições identificadas.
3. Integrar à conversa e ao encaminhamento com fontes e limites claros, sem promessa de correção ou ressarcimento.
4. Demonstrar coerência, condições diferentes, divergência e evidência insuficiente; testar isolamento e falhas.

## Critérios de conclusão

- [x] Quatro resultados distinguíveis, com evidências das duas fontes.
- [x] Nenhum cálculo financeiro delegado ao modelo.
- [x] Recurso de outro cliente bloqueado e auditado.
- [x] Ferramentas equivalentes pela API/domínio e MCP; núcleo preservado.

## Resultado

`simulate_pricing`, `get_fee_breakdown` e contexto contratual, com comparação determinística em centavos e quatro resultados distinguíveis por HTTP e MCP. Suíte estrita: 191 testes; reavaliação das respostas HTTP reais: 40/40; as quatro conversas repetidas com modelo real. Evidência: [resultado da v0.3.0](../evidence/v030-resultado.md).

## Status

```text
concluída (v0.3.0)
```
