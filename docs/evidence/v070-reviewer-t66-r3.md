# Revisão independente da T66 — rodada 3

- **Candidato:** `5ebbfa6aba0dfe3a2238ed55536888697732d09f`, base `b25252333f12d1e4678c9add77254e1458643cf6`, branch `codex/v0.7.0-identidade-hitl`.
- **Independência:** Reviewer em contexto separado; não leu passagem do Developer nem diagnóstico do Supervisor.
- **Parecer:** **bloqueado**. A integração e os critérios CA-47 e CA-48 ainda não foram revalidados nesta rodada.

## Achado

**P2 — reversão da migração 0010 descarta notificações.** O downgrade em `src/merchant_assistant/data/migrations.py:568` executa `DROP TABLE webhook_outbox`, apagando corpo, estado e tentativas de eventos pendentes ou falhos. `webhook_deliveries` não preserva o corpo necessário ao reenvio. Antes de reverter, é necessário um caminho seguro para tratar as intenções pendentes ou documentar e decidir explicitamente sobre essa perda; não executar downgrade em dados existentes por inferência.

## Verificações e limites

- Os **11 testes unitários** de outbox e migração passaram. Cobrem migração sobre dados existentes, mascaramento, ordenação e limite de três tentativas.
- A execução inicial de integração parou na preparação porque `BudgetGuard` recebeu `WinError 5` ao criar um hardlink. Uma execução posterior deixou de progredir e foi interrompida pelo Supervisor; não há resultado válido dessa execução.
- Por inspeção: HMAC sobre corpo bruto, janela de 300 segundos, verificação de principal e escopo, reserva e resposta persistidas para eventos repetidos e inserção transacional de intenções. A spec registra a decisão do responsável de preservar a recusa 4xx na repetição.
- A inspeção e os testes examinados não comprovaram uma disputa real entre dois processos atendendo simultaneamente o mesmo evento.
- O Reviewer não modificou produto nem histórico. O custo dos agentes não foi medido.

## Retomada

Em ambiente com permissão para hardlinks, executar a integração com diretório temporário novo, por exemplo `python -m pytest tests/integration/test_v070_webhooks.py -q -p no:cacheprovider --basetemp .pytest_cache/review-t66-r3-supervisor-20261103`. Conferir memória antes de execução pesada. Tratar o achado P2, completar as evidências independentes necessárias e emitir parecer sobre o candidato aplicável; mudança de código exige novo candidato e revalidação.
