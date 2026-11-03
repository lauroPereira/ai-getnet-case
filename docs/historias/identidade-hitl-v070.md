# História: o lojista pede um atendente e recebe a resposta humana na mesma conversa

Versão 1, 2026-11-03; roteiro fixado antes de implementar. Spec: [identidade-hitl-v070.md](../specs/identidade-hitl-v070.md).

## Pessoas e objetivo

- **Lojista** (`cliente1988`, chave sintética própria): quer falar com um atendente sobre uma máquina que não conecta e receber a resposta sem abrir outro canal.
- **Operadora** (`op_ana`, chave sintética de operador): atende a fila; aprova o rascunho do agente, responde com texto próprio ou rejeita o rascunho com uma instrução.
- **Ticketing da demo** (receptor no serviço `mocks`): recebe o caso assinado quando ele nasce; a resposta volta ao lojista pelo webhook da conversa.
- **Outro lojista** (`cliente_demo_002`) e um segundo operador (`op_bruno`): existem para provar que identidade e reivindicação são respeitadas.

## Critérios e candidato

CA-46, CA-47 e CA-48 (spec 0.2), UC-20, UC-21 e UC-22; tarefas 63 a 68. O candidato é fixado por hashes dos dois repositórios em `docs/evidence/v070-candidato-rN.json` antes do QA.

## Condições iniciais

Mains com a v0.6.0; candidato v0.7.0 nos dois repositórios. `.env` com as chaves do `.env.example` (fictícias) e a chave de modelo do responsável. QA real sob a campanha `v070-qa` (US$0,20) combinada com o ledger primário. Docker só para o smoke final, com o daemon já de pé. Dados sintéticos da seed.

## Momentos da história

| Momento | Ação pela entrada normal | Resultado esperado | Critério | Evidência | Ponto de retorno |
| --- | --- | --- | --- | --- | --- |
| 1. Sem sessão | `curl POST /messages` sem `Authorization` | `401 session_required`; nenhuma chamada a modelo | CA-46, UC-22 | Saída HTTP, ledger sem delta | Não se aplica |
| 2. Sessão do lojista | `POST /v1/sessions` com a chave de `cliente1988` | `201` com `role=merchant`, `customer_id=cliente1988` e escopos | UC-22 | Saída HTTP (token mascarado) | `DELETE /v1/sessions/current` |
| 3. Identidade forjada | `POST /messages` com a sessão de `cliente1988` e `user_id=cliente_demo_002` | `403 identity_mismatch`; nada de `cliente_demo_002` na resposta | CA-46, UC-22 | Saída HTTP | Não se aplica |
| 4. Pergunta normal | Mesma sessão, sem `user_id`: "Quando cai meu próximo recebimento?" | Resposta com dados de `cliente1988`; auditoria com `merchant:cliente1988`, escopo e resultado em cada tool call | CA-46, UC-22 | `request_id`, linhas de auditoria | Não se aplica |
| 5. Pedido de atendente | "Minha máquina não conecta, quero falar com um atendente" | `status=handoff`, protocolo `HO-…`, sem "simulação"; caso `open` na fila | UC-20, CA-47 | Saída HTTP, `GET /v1/handoffs` | O caso fica na fila |
| 6. Ticketing recebe | Ler `GET /ticketing/cases` no `mocks` | Caso com o protocolo, assinatura válida, corpo mascarado; entrega `handoff.created` registrada no caso | CA-47 | Saída do receptor, `GET /v1/handoffs/{id}` | Não se aplica |
| 7. Lojista insiste | Nova mensagem na mesma conversa antes da resposta humana | Atendimento segue o comportamento de continuidade da v0.6.0; o caso pendente não é retomado nem perdido | CA-48 | Saída HTTP, estado do caso | Não se aplica |
| 8. Fila do operador | Login como `op_ana` na aba Operador; abrir o caso | Resumo, pergunta pendente, rascunho do agente, conversa mascarada, eventos e entregas | CA-47 | Captura da interface | Não se aplica |
| 9. Conflito de reivindicação | `op_ana` reivindica; `op_bruno` tenta reivindicar ou agir | `409 claimed_by_other` para `op_bruno` | CA-48 | Saída HTTP | Não se aplica |
| 10. Responder (`reply`) | `op_ana` responde com texto próprio | Grafo retoma; turno `via=operator` com a marca de atendente; caso `answered`; webhook `conversation.replied` entregue | UC-20, CA-47 | Captura, `GET /v1/conversations/{id}`, `GET /merchant/events` | Não se aplica |
| 11. Ação repetida | Mesma ação com a mesma `idempotency_key`; depois, outra chave | `200` com o mesmo registro (`replayed`); depois `409 already_resumed` | CA-48 | Saídas HTTP | Não se aplica |
| 12. Lojista volta | Próxima `POST /messages` do lojista | Rota `human_reply`, `via=operator`, sem chamada a modelo | UC-20, CA-47 | Saída HTTP, ledger sem delta | Não se aplica |
| 13. Aprovar (`approve`) | Novo encaminhamento; `op_ana` aprova o rascunho pela CLI `operator act` | Rascunho liberado, marcado como atendente, entregue por webhook | UC-20, CA-47 | Saída da CLI e do receptor | Não se aplica |
| 14. Rejeitar (`reject`) | Novo encaminhamento; `op_ana` rejeita com "verifique o status do dispositivo e responda" | Support reexecuta uma vez com a instrução (ferramenta de dispositivo chamada sob o principal do operador e o lojista do caso); resposta ao lojista sem nova intervenção | UC-21, CA-47 | Trace, auditoria, conversa | Não se aplica |
| 15. Reinício | Encaminhar; reiniciar a API (processo ou container); agir | Retomada funciona sobre o checkpoint salvo | CA-48 | Saídas antes e depois do reinício | Reiniciar de novo |
| 16. Outro lojista | Sessão de `cliente_demo_002` lê a conversa e o trace de `cliente1988`; tenta `GET /v1/handoffs` | `404`/`403`; nenhum dado de `cliente1988` | CA-46 | Saídas HTTP | Não se aplica |
| 17. Docker | `docker compose up` sem editar `.env.example`; smoke com sessão | Smoke passa; receptores do `mocks` recebem; checkpoints no volume | CA-47 | Saída do smoke e dos receptores | `docker compose down` |

Percorra na ordem. Ação do operador é irreversível para aquele caso; cada ação usa um caso novo.

## Experiência e exceções

Mensagens de erro dizem o que aconteceu e como recuperar (criar sessão, usar a própria conta, reivindicar outro caso). Navegar na aba Operador não gera ação nem chamada paga; ações só por clique explícito, protegidas contra duplo clique. A marca de atendente é visível para o lojista na conversa e na interface.

## Resultado da rodada

A preencher pelo QA.

## Como terminou

A preencher pelo QA.
