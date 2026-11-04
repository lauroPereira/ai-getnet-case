# História: o lojista pede um atendente e recebe a resposta humana na mesma conversa

Versão 2, 2026-11-03; roteiro fixado antes de implementar (versão 2: login por JWT e ticketing próprio com tela no projeto web). Spec: [identidade-hitl-v070.md](../specs/identidade-hitl-v070.md).

## Pessoas e objetivo

- **Lojista** (`cliente1988`, usuário e senha fictícios): quer falar com um atendente sobre uma máquina que não conecta e receber a resposta sem abrir outro canal.
- **Operadora** (`op_ana`): trabalha os tickets na tela de ticketing; assume, aprova o rascunho do agente, responde com texto próprio ou rejeita com uma instrução, e resolve.
- **Sistema de ticketing** (serviço `ticketing`): recebe o caso, guarda o ticket e devolve cada ato ao assistente.
- **Outro lojista** (`cliente_demo_002`) e **outro operador** (`op_bruno`): provam que identidade e reivindicação são respeitadas.

## Critérios e candidato

CA-46, CA-47 e CA-48 (spec 0.2), UC-20, UC-21 e UC-22; tarefas 63 a 68 e 66b. O candidato é fixado por hashes dos dois repositórios em `docs/evidence/v070-candidato-rN.json` antes do QA.

## Condições iniciais

Mains com a v0.6.0; candidato v0.7.0 nos dois repositórios. `.env` com os valores fictícios do `.env.example` e a chave de modelo do responsável. QA real sob a campanha `v070-qa` (US$0,20) combinada com o ledger primário. Docker só com o daemon já de pé. Dados sintéticos da seed.

## Momentos da história

| Momento | Ação pela entrada normal | Resultado esperado | Critério | Evidência | Ponto de retorno |
| --- | --- | --- | --- | --- | --- |
| 1. Sem token | `curl POST /messages` sem `Authorization` | `401`; nenhuma chamada a modelo | CA-46, UC-22 | Saída HTTP, ledger sem delta | Não se aplica |
| 2. Login do lojista | `POST /v1/auth/token` com usuário e senha de `cliente1988` | JWT com `sub=merchant:cliente1988`, escopos e validade; o JWKS publicado valida o token | UC-22 | Saída HTTP, claims decodificadas (token mascarado) | `POST /v1/auth/revoke` |
| 3. Token adulterado e revogado | Mudar um caractere do token; depois revogar e reusar | `401` nos dois | CA-46 | Saídas HTTP | Novo login |
| 4. Identidade forjada | `POST /messages` com o token de `cliente1988` e `user_id=cliente_demo_002` | `403 identity_mismatch`; nada de `cliente_demo_002` | CA-46, UC-22 | Saída HTTP | Não se aplica |
| 5. Pergunta normal | Mesmo token, sem `user_id`: "Quando cai meu próximo recebimento?" | Dados de `cliente1988`; auditoria com principal, escopo e resultado em cada tool call | CA-46, UC-22 | `request_id`, linhas de auditoria | Não se aplica |
| 6. Pedido de atendente | "Minha máquina não conecta, quero falar com um atendente" | `status=handoff`, protocolo `HO-…`, sem "simulação"; caso `open` na fila | UC-20, CA-47 | Saída HTTP, `GET /v1/handoffs` com token de operador | O caso fica na fila |
| 7. Recepção no ticketing | `op_ana` entra na interface e abre Ticketing | Ticket `new` com protocolo, resumo, pergunta, rascunho e conversa mascarada; entrega `handoff.created` registrada nos dois lados | CA-47 | Captura, `GET /v1/handoffs/{id}` | Não se aplica |
| 8. Lojista insiste | Nova mensagem do lojista antes da resposta humana | Continuidade da v0.6.0; a interrupção pendente não se perde | CA-48 | Saída HTTP, estado do caso | Não se aplica |
| 9. Atendimento e conflito | `op_ana` assume o ticket; `op_bruno` tenta assumir o mesmo | Ticket `open` com `op_ana`; `op_bruno` vê `409 claimed_by_other` | CA-48 | Capturas | Não se aplica |
| 10. Envio (`reply`) | `op_ana` responde com texto próprio | Grafo retoma; turno `via=operator` com a marca de atendente; ticket `pending` e depois marcado como entregue; webhook ao lojista recebido | UC-20, CA-47 | Captura, `GET /v1/conversations/{id}`, `GET /merchant/events` | Não se aplica |
| 11. Ação repetida | Repetir o envio após falha simulada de transporte (mesma chave); depois uma ação nova no mesmo caso | Mesmo registro; depois `409 already_resumed` | CA-48 | Saídas | Não se aplica |
| 12. Lojista volta | Próxima `POST /messages` do lojista | Rota `human_reply`, `via=operator`, sem chamada a modelo | UC-20, CA-47 | Saída HTTP, ledger sem delta | Não se aplica |
| 13. Finalização | `op_ana` resolve o ticket | Ticket `solved`; caso `closed` no assistente; `handoff.closed` recebido pelo ticketing | CA-47 | Captura, `GET /v1/handoffs/{id}` | Não se aplica |
| 14. Aprovar (`approve`) | Novo encaminhamento; `op_ana` aprova o rascunho (tela ou CLI `operator act`) | Rascunho liberado, marcado como atendente, entregue | UC-20, CA-47 | Saídas | Não se aplica |
| 15. Rejeitar (`reject`) | Novo encaminhamento; `op_ana` rejeita com "verifique o status do dispositivo e responda" | Support reexecuta uma vez com a instrução, sob o principal do operador e o lojista do caso; resposta sem nova intervenção | UC-21, CA-47 | Trace, auditoria, conversa | Não se aplica |
| 16. Reinício | Encaminhar; reiniciar a API; agir no ticketing | Retomada sobre o checkpoint salvo | CA-48 | Saídas antes e depois | Reiniciar de novo |
| 17. Outro lojista | Token de `cliente_demo_002` lê conversa e trace de `cliente1988`; chama `GET /v1/handoffs` e a API do ticketing | `404`/`403`/`401`; nenhum dado de `cliente1988` | CA-46 | Saídas HTTP | Não se aplica |
| 18. Docker | `docker compose up` sem editar o `.env.example`; smoke com token; ciclo do ticket por `curl` | Smoke passa; ticket nasce e volta; checkpoints e bancos nos volumes | CA-47 | Saídas | `docker compose down` |

Percorra na ordem. Ação do operador é irreversível para aquele caso; cada ação usa um caso novo.

## Experiência e exceções

Mensagens de erro dizem o que aconteceu e como recuperar (entrar de novo, usar a própria conta, atualizar a fila, aguardar o envio pendente). Navegar na tela de ticketing não gera ação nem chamada paga; ações só por clique explícito, protegidas contra duplo clique. A marca de atendente é visível para o lojista.

## Resultado da rodada

QA real, rodada r1, 2026-11-04, candidato `v0.7.0-local-r1` (backend `e97d7f0`, web `932aeb6`, fingerprint `12adae52…ad8f`): **apto, com ressalvas**. Os 18 momentos passaram, na ordem, pelas superfícies que a história nomeia (`curl`, interface Streamlit com três sessões, CLI `operator`, reinício da API e Docker). CA-46, CA-47 e CA-48 comprovados; nenhum defeito aberto. Campanha `v070-qa`: US$0,10140195 de US$0,20 (US$0,07543317 pela guarda composta mais US$0,02596878 do ledger do volume Docker). Regressão real: 33/40 contra 34/40 da v0.6.0 (a diferença é o rótulo `V030-CONTRACT-TERMINATION` desatualizado pelo contrato novo e variação em casos de preço e habilitação), 4/4 conversas. Três atritos (`reject` com "Envio pendente" por causa do timeout de 3 s do ticketing, "sem alterações" do `approve`, texto do `reject`), observações e quatro perguntas ao Supervisor estão em [v070-qa.md](../evidence/v070-qa.md); evidência por momento em [v070-qa-historia.md](../evidence/v070-qa-historia.md).

## Como terminou

A lojista `cliente1988` entrou com usuário e senha, recebeu só os seus dados, pediu um atendente e ganhou um protocolo `HO-…`, sem simulação; ao insistir, o sistema reconheceu o mesmo caso. A operadora `op_ana` recebeu o ticket na recepção, assumiu (o `op_bruno`, ao tentar o mesmo caso, foi barrado com uma mensagem clara), respondeu com texto próprio e resolveu; a lojista viu a resposta marcada como "Atendente humano", sem nova chamada a modelo, e o caso fechou. Em outros casos a operadora aprovou o rascunho (pela tela e pela CLI) e rejeitou com uma instrução, e o assistente refez a resposta sob a identidade dela uma única vez. A API foi derrubada duas vezes e o contêiner reiniciado, e cada caso retomou do ponto salvo; outro lojista não leu nada de `cliente1988`. No Docker, o smoke com token passou e o ticket nasceu, foi respondido e fechou por `curl`.
