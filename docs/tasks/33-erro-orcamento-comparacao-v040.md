# Tarefa: erro explícito de orçamento na comparação

## Objetivo

Tratar o bloqueio de orçamento como erro operacional estruturado no endpoint
de comparação, preservando integralmente a guarda e a contabilização existente.

## Especificação relacionada

RF-47–49, RF-75, CA-34/CA-37/CA-45; plano v0.4.0 e contratos aprovados.

## Pré-condições

Dentro do plano aprovado, sem chamada paga ou alteração de proteção.

## Arquivos prováveis

Handler `/v1/router/compare`, testes de API/orçamento, documentação do erro.
Não modificar BudgetGuard, limites financeiros ou a regra de reserva.

## Passos

1. Reproduzir bloqueio de reserva antes do primeiro Router e depois do primeiro
   resultado, antes do segundo, usando provedores programados e ledger isolado.
2. Devolver código/status estruturado de orçamento coerente com a API, sem
   fallback, execução de atendimento ou sucesso de comparação incompleta.
3. Preservar custo/reserva já contabilizados; não reiniciar ledger, liberar
   valor consumido ou reduzir proteção para aprovar o teste.
4. Verificar o erro no consumidor HTTP, testes proporcionais e regressão
   necessária; fixar novo candidato para revisão.

## Critérios de conclusão

- [x] Bloqueios por limite da solicitação ou saldo global devolvem erro explícito.
- [x] Provedor não é invocado quando sua reserva foi negada.
- [x] Falha no segundo Router não cria comparação completa/consumível ou atendimento.
- [x] Contabilização anterior permanece intacta, sem ultrapassar limites.
- [x] Revisão e revalidação identificam o novo candidato e a correção real.

## Resultado

Bloqueio de orçamento antes do primeiro ou do segundo Router volta como HTTP 429 com `request_budget_exceeded` ou `installation_budget_exceeded`, sem a chamada seguinte ao modelo nem comparação incompleta; a reserva já liquidada (US$0,03) fica no ledger. 4 testes focados (`-k budget_rejection`) aprovados; OpenAPI declara a resposta 429. Evidência: [resultado da v0.4.0](../evidence/v040-resultado.md).

## Status

```text
concluída (v0.4.0)
```
