# Passagens do Developer — v0.8.0 (Time A)

## Tarefa 68b

- **Papel e responsável:** Developer (Time A), subagente despachado pelo Supervisor.
- **Objetivo e critérios:** [tarefa 68b](../tasks/68b-ticket-id-no-caso.md): depois do primeiro evento aceito do ticketing, `GET /v1/handoffs` e `GET /v1/handoffs/{id}` mostram o `ticket_id` (observação O-8 do QA da v0.7.0).
- **Escopo:** `tests/integration/test_v080_ticket_id.py` (novo), seções Validação e Status da tarefa e esta passagem. Nenhum arquivo de `src/` mudou.
- **Estado:** defeito **não reproduzido**; teste de regressão entregue; aguarda revisão.
- **Branch e base:** `codex/v0.8.0-replan`, base `5134eff`. Identidade conferida antes do commit: `lauroPereira <lauro.s.pereira@gmail.com>`.
- **Independência:** não se aplica (implementação).

### Evidência

- Em processo, com o ticketing real (`AppTransport`): o teste da v0.7.0 `test_case_becomes_a_ticket_worked_on_the_ticketing_and_closed` já exige o `ticket_id` no detalhe depois de `ticket.assigned` e passa na base.
- Com soquetes reais (roteiro exploratório fora do repositório: assistente, ticketing e receptor em três servidores uvicorn em threads, loopback): `POST /tickets/{id}/assign` → `delivered`, `accepted`; `GET /v1/handoffs` → `claimed`, `op_ana`, `ticket_id` igual ao ticket.
- Cópia somente leitura do banco do QA da v0.7.0 (`.pytest_cache/v070-qa-real-runtime/merchant.sqlite3`, copiado para fora do repositório; o diretório original não foi tocado): 5 casos; os 4 que tiveram `ticket.assigned` aceito em `webhook_inbox` têm `ticket_id` (o do momento 9 da história, `hc_154e13748dc742da`, é `tkt_c6d9b62237d4`, o mesmo ticket citado no QA); o único `null`, `hc_bd1b4d4e05924eb9`, não tem evento do ticketing e foi trabalhado direto por `operator:op_ana` (CLI, caso E da O-4). A única amostra com `ticket_id: null` no relato do QA (momento 6) é de antes de qualquer evento.
- Teste novo: 5 passam (`.pytest_cache/t68b-dev-20261104e`). Na cópia da base fora do repositório com o `UPDATE handoff_cases SET ticket_id` removido, os 5 falham. Ruff: `All checks passed`.
- Nenhuma chamada paga, nenhuma rede além de loopback; não li `.env`.

### Decisões tomadas além do texto

1. **Não alterei código de produção.** Sem defeito reproduzível, mudar `integrations.py` seria inventar uma correção. O critério "teste que falhava antes da correção" não se aplica; no lugar dele, a mutação acima prova que o teste detecta a ausência da gravação.
2. **Os testes cobrem os três tipos de primeiro evento** (`assigned`, `action`, `solved`), o ciclo inteiro (o primeiro ticket vence) e as recusas (`unknown_operator`, payload inválido, `claimed_by_other`), que a tarefa pedia.

### Achados e limitações

- **Sugestão ao Supervisor (não implementada):** entre `handoff.created` e o primeiro evento do operador o caso fica com `ticket_id` nulo, embora a resposta do ticketing a `handoff.created` traga o `ticket_id` (`{"status": "received", "ticket_id": ...}`). Quem lê a fila na Recepção vê `null` e pode ter entendido isso como o defeito. Gravar na criação muda o comportamento definido na 66 ("do primeiro evento aceito") e tocaria `api/webhooks.py`; deixo para decisão.
- O QA pode confirmar a leitura repetindo o roteiro do momento 9 e lendo a fila depois do `Assumir`.

### Próxima ação

Supervisor: aceitar o fechamento sem correção (ou pedir a gravação na criação) e revisar o teste.
