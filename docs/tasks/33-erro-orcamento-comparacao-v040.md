# Tarefa: erro explícito de orçamento na comparação

## Objetivo

Tratar o bloqueio de orçamento como erro operacional estruturado no endpoint
de comparação, preservando integralmente a guarda e a contabilização existente.

## Especificação relacionada

RF-47–49, RF-75, CA-34/CA-37/CA-45; plano v0.4.0 e contratos aprovados.
Achado P2 da [revisão r1](../evidence/v040-reviewer-r1.md), candidato r1.

## Pré-condições

Correção dentro do plano aprovado, sem chamada paga ou alteração de proteção.
Manifesto/parecer r1 preservados; QA ainda não iniciado.

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
   necessária; fixar novo candidato e devolver ao mesmo Reviewer.

## Critérios de conclusão

- [ ] Bloqueios por limite da solicitação ou saldo global devolvem erro explícito.
- [ ] Provedor não é invocado quando sua reserva foi negada.
- [ ] Falha no segundo Router não cria comparação completa/consumível ou atendimento.
- [ ] Contabilização anterior permanece intacta, sem ultrapassar limites.
- [ ] Parecer/revalidação identificam o novo candidato e a correção real.

## Validação

`PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -m pytest -q
tests/integration/test_v1_api.py -k budget_rejection
--basetemp=.pytest_cache/v040-budget-r2-target2-20261027`: **4 passaram**.
Os quatro casos usam estimativa/liquidação programadas de US$0,04/US$0,03,
sem provedor ou chamada paga: limite por requisição e saldo global antes do
primeiro Router, e ambos novamente antes do segundo. As respostas são HTTP 429
com `request_budget_exceeded` ou `installation_budget_exceeded`; quando a
primeira reserva foi liquidada, ela permanece em US$0,03 no ledger e a segunda
chamada ao modelo não ocorre. Nenhum registro de comparação incompleta é
criado. OpenAPI declara a resposta 429. A suíte strict r2 e os resultados
completos estão na [passagem Developer r2](../evidence/v040-developer-r2.md).

## Status

Implementação e regressões validadas pelo Developer r2. Aguarda novo parecer
do Reviewer; QA ainda não iniciado. Nenhuma chamada paga, alteração da guarda,
dos limites ou reset do ledger.
