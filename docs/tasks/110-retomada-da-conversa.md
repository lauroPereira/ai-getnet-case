# Tarefa 110 — Lista de conversas e retomada na interface

## Objetivo

Recarregar a página e entrar de novo devolve ao lojista a última conversa, com o histórico e a resposta da atendente; ele pode começar outra.

## Especificação relacionada

[v1.1.0](../specs/tickets-retomada-v110.md): D2, CA-77, RF-131. Contrato em [api-v1.md](../contracts/api-v1.md).

## Pré-condições

Tarefa 109 concluída na branch `codex/v1.1.0-tickets-retomada`. Interface na branch `codex/v1.1.0-web-retomada` do `ai-getnet-case-web` (base `main` em `04ac328`). Nenhuma chamada paga.

## Arquivos prováveis

Backend: `src/merchant_assistant/api/v1.py`, `conversations.py`, `docs/contracts/api-v1.md`, testes. Web: `app.py`, `src/getnet_web/api.py`, `README.md`, testes.

## Passos

1. `GET /v1/conversations` (Bearer, dono): conversas do lojista do token (mesma regra de `acting_merchant` da rota por id), por `updated_at` decrescente; `limit` de 1 a 20, padrão 5 (fora disso, `422`). Por item: `conversation_id`, `state`, `created_at`, `updated_at`, `handoff_protocol` (protocolo do caso da conversa, ou `null`) e `pending_operator_reply` (há turno da atendente ainda não entregue). Sem texto de mensagem. Principal sem lojista vinculado: `403 insufficient_scope`.
2. Contrato `api-v1.md` com a rota nova; OpenAPI com exemplo.
3. Web: cliente `list_conversations`. Depois do login de lojista ou `demo`, sem conversa no estado da sessão, buscar a lista e retomar a mais recente: `GET /v1/conversations/{id}` reconstrói o histórico (lojista, assistente e atendente, esta com a marcação `Atendente humano` que a interface já usa), guarda o `conversation_id` e mostra "Conversa retomada" com a data. Botão **Nova conversa** limpa a conversa da sessão (não apaga nada no backend). Lista vazia: comportamento atual. Falha da lista ou da conversa: aviso curto e conversa nova, sem bloquear o atendimento.
4. A aba Resultados continua listando as execuções da sessão atual.
5. README da web (comportamento ao recarregar) e testes.

## Critérios de conclusão

- Testes da rota: só conversas do dono, ordem, limite, sem texto, `403` para operador e serviço, `422` fora do limite.
- Testes da interface: depois de um novo login, a última conversa volta com o turno da atendente; **Nova conversa** começa outra; a mensagem seguinte usa o `conversation_id` retomado; lista vazia e falha não quebram a tela.
- Suítes estritas do backend e da web verdes.

## Validação

Developer, rodada 1 (2026-11-10). Sem chamada paga: modelo programado, embedder de hash, Qdrant em memória e transportes falsos.

- **Commits.** Backend `codex/v1.1.0-tickets-retomada`, base `30f3718` (tarefa 109): `9d3b25d` (rota, contrato e testes) e o commit desta seção. Web `codex/v1.1.0-web-retomada`, base `main` em `04ac328`: `29c1206` (cliente, retomada, **Nova conversa**, snapshot, README e testes).
- **Rota.** `GET /v1/conversations` (`api/v1.py`, `conversations_list`; consulta em `ConversationStore.recent`). Mesma regra da rota por id: `acting_merchant` e `403 insufficient_scope` para token sem lojista (operador, serviço). Ordem `updated_at` decrescente, desempate pela ordem de criação. `limit` por `Query(ge=1, le=20)`, padrão 5; fora disso, o `422 invalid_request` do tratador comum. Por item: `conversation_id`, `state`, `created_at`, `updated_at`, `handoff_protocol` (caso mais recente da conversa, do mesmo lojista) e `pending_operator_reply` (turno `via='operator'` com `delivered_at` nulo, o mesmo critério da entrega D8). Sem texto. Modelos `ConversationSummary` e `ConversationList` com exemplo no OpenAPI. Sem migração.
- **Contrato.** `docs/contracts/api-v1.md`: linha na tabela de rotas e seção "Acréscimos da v1.1.0: lista de conversas".
- **Web.**
  - `openapi-v1.json` é a exportação do backend em `9d3b25d` (rotas de demonstração desligadas): acrescenta `/v1/conversations` e as rotas já existentes que o snapshot da v0.7.0 não tinha (`/v1/auth/authorize`, retomada de comparação, reenvio de webhook, `/metrics`); nenhuma operação some. `tools/generate_client.py` ganha o alias `list_conversations`; `generated_api.py` regenerado (29 operações).
  - `getnet_web/api.py`: `list_conversations(limit=5)` com parâmetro de consulta; `SimulatedAPI.list_conversations` devolve lista vazia.
  - `app.py`: depois do login de `merchant` ou `demo` (modo Real), sem conversa, sem histórico e sem pergunta pendente na sessão, uma única leitura por login: `list_conversations(limit=1)` e `conversation(id)`. O histórico volta com os turnos do lojista e do assistente, a atendente com a legenda `Atendente humano` de antes; `conversation_id` e contagem de mensagens do backend ficam na sessão; a linha do caso mostra o protocolo do item. Aviso "Conversa retomada · última atividade em dd/mm/aaaa hh:mm" até a mensagem seguinte. **Nova conversa** limpa só a conversa da sessão (histórico, id, caso, pergunta pendente, comparação de Routers) e não procura de novo; Resultados mantém as execuções. Lista vazia: tela como antes. Falha da lista ou da conversa (erro da API, transporte, corpo fora do formato): "Não foi possível retomar a última conversa. Uma conversa nova foi iniciada." uma vez; `401` encerra a sessão como nas demais leituras. Admin, Simulado e Gravado não retomam.
  - README da web: parágrafo "Reloading the page (v1.1.0)" e a linha do snapshot.
- **Decisões além do plano.**
  - Resposta de atendente ainda não entregue: aparece no histórico retomado e, pela regra D8 do backend, volta como resposta da mensagem seguinte. A interface avisa isso numa legenda quando `pending_operator_reply` é verdadeiro, em vez de esconder o turno ou omitir a repetição. Reversível só na interface.
  - A interface pede `limit=1`: só usa a mais recente.
  - O snapshot OpenAPI foi exportado inteiro, como na v0.7.0, em vez de acrescentar só o caminho novo; a tarefa 111 muda `GET /v1/profiles` e pede nova exportação.
- **Testes.**
  - Backend, novo `tests/integration/test_v110_conversations.py` (12): só as conversas do dono, ordem, item sem texto (o texto de uma mensagem e o outro lojista não aparecem na resposta); `limit` padrão 5, 1 e 20; `422` para `0`, `21`, `-1` e `abc`; `403 insufficient_scope` com desafio para operador e serviço; `401` sem token; demo e admin no lojista da demonstração; protocolo e `pending_operator_reply` pelo fluxo real (handoff, resposta da operadora, entrega na mensagem seguinte); OpenAPI com limites e exemplo.
  - Web, novo `tests/test_v110_resume.py` (16): retomada com o turno da atendente e a legenda, só GET, rerun sem nova leitura, mensagem seguinte com o `conversation_id` retomado; página recarregada (nova sessão do Streamlit) traz a resposta escrita no intervalo; **Nova conversa** começa outra, mantém as execuções e não retoma de novo; lista vazia; quatro falhas (lista e conversa, API e transporte) com aviso único; `401` na lista encerra a sessão; admin não retoma e demo retoma; logout e outro lojista; Simulado sem conversa anterior; cliente HTTP (rota, `limit`, Bearer, recusa estruturada) e snapshot. `tests/test_interface.py` passa a esperar 29 operações.
  - Entre repositórios, novo `tests/test_v110_backend_integration.py` (1, ignorado sem o backend no caminho): login pela página do emissor, handoff, resposta da operadora; o cliente da web lista a conversa com protocolo e resposta pendente, lê o turno da atendente pela rota por id, recebe `422` com `limit=21` e `403` com token de operador.
- **Comandos e números.** Backend: `.venv` do repositório principal com `PYTHONPATH=src` deste worktree. Web: `.venv-v040` do checkout da web com `PYTHONPATH=src` do worktree da web. Sempre `-p no:cacheprovider` e `--basetemp` novo em `<scratchpad da sessão>` (na web, por `PYTEST_ADDOPTS`, porque o script não repassa argumentos).

  | Comando | Resultado |
  | --- | --- |
  | backend `pytest tests/integration/test_v110_conversations.py` | **12 passed** |
  | web `pytest tests/test_v110_resume.py tests/test_interface.py` | **36 passed** |
  | entre repositórios, `.venv` do backend com os dois `src`: `pytest tests/test_v110_backend_integration.py tests/test_oauth_backend_integration.py` (web) | **5 passed** |
  | web `python tools/scripts/lint_and_tests.py --strict` | **184 passed, 2 skipped** (os dois módulos entre repositórios, sem o backend no caminho) em 3 min 58 s, `ruff` "All checks passed!", exit 0 |
  | backend `python tools/scripts/lint_and_tests.py --strict` | **3027 passed, 1 skipped**, 0 falhas (contagem pela barra de progresso: com `-q` a linha final de totais não sai), `ruff` "All checks passed!", links e caminhos pessoais sem ocorrência, exit 0. O skip é `test_v0130_otel.py:436` (o venv não tem o extra `otel`) |
  | `checar-caminhos-pessoais.py` (backend inteiro e os arquivos alterados da web) | nenhuma ocorrência |

- **Roteiro do QA** (momentos 4, 5 e 10 da [história](../historias/tickets-retomada-v110.md)):
  1. Depois do handoff e da resposta da operadora (momentos 2 e 3), recarregar a página do lojista e entrar de novo. Esperado: "Conversa retomada · última atividade em …", histórico com a pergunta, a mensagem do protocolo e a resposta da atendente com a legenda `Atendente humano · … · protocolo HO-…`; linha do caso com o protocolo; a legenda de resposta ainda não entregue, se o lojista não tinha enviado nada depois da resposta.
  2. Enviar "Obrigado". Esperado: mesmo `conversation_id` (Resultados ou `GET /v1/conversations`). Se havia resposta não entregue, ela volta como resposta desta mensagem (regra D8), como diz a legenda.
  3. **Nova conversa**: tela de conversa vazia, Resultados com as execuções da sessão; a mensagem seguinte abre outra `conversation_id`; recarregar depois disso retoma a conversa nova, que passou a ser a mais recente.
  4. `GET /v1/conversations` com o token do lojista: itens sem texto, o mais recente primeiro; com o token da operadora, `403 insufficient_scope`; com `limit=50`, `422 invalid_request`.

Developer, rodada 2 (2026-11-10), correções da revisão sobre a spec 0.2 (D2 com a confirmação de exibição). Sem chamada paga.

- **Commits.** Backend: `213978c` (confirmação, `message_id`, contrato, CHANGELOG, README e testes) e o commit desta seção. Web: `c79d731` em `codex/v1.1.0-web-retomada`, sobre `a241175`.
- **P2-1, confirmação de exibição.**
  - Backend: `GET /v1/conversations/{id}` (e a rota de demonstração `/conversations/{id}`) traz `message_id` em cada turno, o `id` da tabela `messages`, aditivo. `POST /v1/messages` aceita `displayed_operator_message_id` (inteiro ≥ 1, opcional; fora disso `422 invalid_request`). `Orchestrator.handle` chama `ConversationStore.confirm_displayed` logo depois de abrir a conversa (dono já conferido por `open`) e antes da regra D8: se o id é de turno `via='operator'` desta conversa com `delivered_at` nulo, marca esse turno e os turnos de atendente anteriores ainda não entregues da mesma conversa; qualquer outro id não muda nada. A mensagem segue para Router e agentes; uma resposta mais nova que a exibida continua pendente e é entregue pela D8. A rota legada `POST /messages` não ganhou o campo.
  - Web: `resume_last_conversation` guarda em `resumed` o `message_id` do último turno de atendente do histórico quando o item da lista vem com `pending_operator_reply`; `send_chat_message` o envia na primeira mensagem seguinte da mesma conversa (o `resumed` é limpo depois dela). A legenda sobre a repetição saiu. Snapshot `openapi-v1.json` reexportado de `213978c` com as rotas de demonstração desligadas: diferença só em `info.version` (1.1.0) e no campo novo de `V1MessageRequest`; `generated_api.py` regenerado sem mudança (29 operações). README da web atualizado.
- **P3-1.** `test_each_case_of_one_conversation_gets_only_its_own_reply`: dois casos na mesma conversa, só o primeiro respondido; o segundo sai com `operator_reply` nulo.
- **P3-2.** Web: `404` ou `405` na lista (backend anterior à v1.1.0) é tratado como "nada a retomar", sem aviso; `404` na leitura da conversa continua avisando.
- **P3-3.** Coberto pela reexportação acima (`info.version` 1.1.0, com teste).
- **P3-6.** A docstring de `get_handoff_cases` diz que a resposta é o turno de atendente mais recente do caso, entregue ou não.
- **Decisões além do plano.**
  - Confirmar um turno também marca os turnos de atendente anteriores ainda não entregues da mesma conversa: estão acima dele no mesmo histórico exibido, e marcar só o turno informado deixaria o mais antigo para a D8 repetir. Reversível em `confirm_displayed` (trocar `id <= ?` por `id = ?`).
  - O campo novo é passado ao orquestrador como argumento de `handle`, não pelo esquema público `MessageRequest`, para não abrir o campo na rota legada.
  - Nenhum evento de trace novo para a confirmação.
- **Testes novos.**
  - Backend, `test_v110_conversations.py` (+12): fluxo real (handoff, resposta da operadora, `message_id` estável e crescente, mensagem com a confirmação respondida por agente, resposta uma vez no histórico, pendência zerada); sem o campo, D8 como antes; corrida com resposta mais nova (entregue pela D8; reenviar o id já entregue não muda nada); turnos anteriores também confirmados sem tocar outra conversa; id de turno do lojista, de outra conversa, de outro lojista, já entregue ou inexistente não muda nada (5); `0`, `-1` e `abc` dão `422` (3); OpenAPI com o campo opcional. `test_v110_tickets.py` (+1, P3-1). Mutação manual de `confirm_displayed` (filtro de conversa no SELECT e no UPDATE, filtro de entrega, filtro de `via`, `id <= ?` trocado por `id = ?`): as cinco mortas por asserção.
  - Web, `test_v110_resume.py`: o falso do assistente passa a entregar como o backend (D8 e confirmação, `message_id` pela posição). Novos: a mensagem seguinte recebe a própria resposta, a da atendente aparece uma vez e a tela bate com o histórico gravado; só a primeira mensagem leva o campo; resposta já entregue não é confirmada; corrida com resposta escrita depois da retomada (aparece uma vez); `404` e `405` na lista sem aviso (2); snapshot com o campo e com `info.version` 1.1.0; cliente HTTP envia o campo no corpo. O teste principal agora confere o campo e a ausência da legenda.
  - Entre repositórios, `test_v110_backend_integration.py`: depois da resposta da operadora, o cliente da web envia a mensagem com o `message_id` lido pela rota por id e recebe resposta de agente; a lista deixa de ter pendência e o histórico tem a resposta uma vez.
- **Comandos e números.** Mesmos ambientes da rodada 1, `-p no:cacheprovider` e `--basetemp` novo em `<scratchpad da sessão>`.

  | Comando | Resultado |
  | --- | --- |
  | backend `pytest tests/integration/test_v110_conversations.py` | **24 passed** |
  | web `pytest tests/test_v110_resume.py tests/test_interface.py` | **43 passed** |
  | entre repositórios, `.venv` do backend com os dois `src`: `pytest tests/test_v110_backend_integration.py tests/test_v111_backend_integration.py tests/test_oauth_backend_integration.py` (web) | **6 passed** |
  | backend `python tools/scripts/lint_and_tests.py --strict` | **3052 passed, 1 skipped**, 0 falhas (contagem pela barra de progresso), `ruff` "All checks passed!", skills válidas, caminhos pessoais sem ocorrência em 741 arquivos, links sem alvo ausente em 374, exit 0. O skip é o de `test_v0130_otel.py` (extra `otel` ausente) |
  | web `python tools/scripts/lint_and_tests.py --strict` | **202 passed, 3 skipped** (os três módulos entre repositórios, sem o backend no caminho) em 3 min 45 s, `ruff` "All checks passed!", exit 0 |
  | `checar-caminhos-pessoais.py` (arquivos alterados da web) | nenhuma ocorrência em 5 arquivos |

- **Roteiro do QA** (substitui os passos 1 e 2 da rodada 1):
  1. Depois do handoff e da resposta da operadora, recarregar a página do lojista e entrar de novo, sem enviar nada antes. Esperado: "Conversa retomada · última atividade em …", histórico com a resposta da atendente e a legenda `Atendente humano · … · protocolo HO-…`; nenhuma legenda sobre repetição.
  2. Enviar "E quando cai na conta?". Esperado: mesmo `conversation_id`; resposta do assistente à pergunta, sem repetir a da atendente; `GET /v1/conversations` sem pendência; `GET /v1/conversations/{id}` com a resposta da atendente uma vez, seguida da pergunta e da resposta do assistente.

## Status

```text
pronta para revisão (rodada 2); navegação pela interface com modelo real no QA
```
