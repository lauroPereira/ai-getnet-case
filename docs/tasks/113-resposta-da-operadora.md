# Tarefa 113 — Resposta da operadora sem reescrita e ajustes

## Objetivo

A resposta que a operadora escreve chega ao lojista exatamente como ela escreveu; o estado do ticket aparece no idioma do lojista; o log de acesso não guarda a query do login.

## Especificação relacionada

[v1.1.0](../specs/tickets-retomada-v110.md): D4, CA-79; CA-76 (estado do ticket); CA-77 (confirmação de exibição). Emenda a [decisão 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).

## Pré-condições

Tarefas 109 a 112 concluídas nas duas branches da versão. Nenhuma chamada paga.

## Arquivos prováveis

Backend: `orchestration/graph.py` (caminho de retomada), `agents/personality.py` se necessário, `prompts/support.v11.md`, configuração do log de acesso (`docker/entrypoint.sh`, `main.py` ou `observability/logging.py`), ADR 0018 (nota de emenda) e índice das decisões, README, CHANGELOG 1.1.0, testes. Web: `tests/` (teste da confirmação).

## Passos

1. **Responder sem reescrita (D4).** Na retomada com `reply`, o turno `via=operator` leva o texto da operadora sem passar pela Personality nem por outra reescrita; checagens que não alteram o texto podem continuar. `approve` e `reject` ficam como estão. Testes: o texto entregue (resposta da API, conversa por id, `get_handoff_cases`) é idêntico ao enviado, inclusive com valores e datas que não vêm de ferramenta; `approve` continua chamando a Personality.
2. **Estado no idioma do lojista.** `prompts/support.v11.md` (versão ainda não publicada): o estado do ticket é descrito com palavras do idioma do lojista, nunca com o código (`open`, `claimed`, `answered`, `rejected`, `closed`). Teste de presença da regra.
3. **Query do login fora do log de acesso.** O log de acesso da API não registra a query de `/v1/auth/authorize` (traz `state` e `code_challenge`); o caminho continua registrado. Teste.
4. **Teste da confirmação na web.** Histórico com dois turnos de atendente, o primeiro já entregue: o identificador enviado na mensagem seguinte é o do mais recente.
5. ADR 0018 com nota de emenda (D4), README (onde descreve `approve` e `reply` indo à Personality) e CHANGELOG 1.1.0, sem número inventado.

## Critérios de conclusão

- Testes provam o texto idêntico em `reply` e a Personality em `approve`; regra do estado no prompt; log sem a query do authorize; teste da web com dois turnos.
- Suítes estritas dos dois repositórios verdes.

## Validação

Developer, rodada 1 (2026-11-11). Sem chamada paga: modelo programado, embedder de hash, Qdrant em memória e transportes falsos.

- **Commits.** Backend `codex/v1.1.0-tickets-retomada`, base `ae8de56`: `bd9657b` (código, prompt, documentos e testes) e o commit desta seção. Web `codex/v1.1.0-web-retomada`, base `c79d731`: `44408d8` (só o teste do passo 4).
- **Passo 1 (D4).** Grafo de revisão: `human_review` segue para o nó novo `operator_reply` quando a ação é `reply`; o nó usa o texto da operadora (já sem espaços nas pontas, como `handoffs.act` o grava) como `draft_answer` e `answer`, move o caso por `next_state` como qualquer turno de operador (`awaiting_customer`) e termina, sem chamada de modelo e sem guarda de saída. `approve` segue para a Personality e a guarda de saída; `reject`, para Support, Personality e guarda de saída, como antes. `operator_reply` entrou no vocabulário fechado de passos dos spans (`otel.NODE_STEPS`). Um fluxo já parado em `human_review` retoma pelo caminho novo: a rota é decidida depois da retomada.
- **Passo 2.** `prompts/support.v11.md` (ainda não publicado, editado no lugar): na regra 15, "Describe the state in words of $language_name, never with its code (`open`, `claimed`, `answered`, `rejected`, `closed`)."
- **Passo 3.** `observability/logging.py`: `AuthorizeQueryFilter` no logger `uvicorn.access`, instalado uma vez por `configure_logging` (a fábrica roda em cada worker, depois de o uvicorn configurar os logs). Na linha de `/v1/auth/authorize` a query sai e o caminho fica; as demais rotas não mudam.
- **Passo 5.** ADR 0018: nota "Emenda da v1.1.0" e menção no item da retomada; índice das decisões; README (seção "Pause and resume"); CHANGELOG 1.1.0 (resumo, regra do estado no item do `support.v11`, item da resposta da operadora e item do log de acesso), sem número.
- **Decisões além do plano.**
  - `reply` não passa pela guarda de saída: a resposta é só o texto da operadora, que a guarda já aceitava como evidência, e o caminho do `approve` continua com ela. Reversível ligando `operator_reply` a `output_guard` no grafo de revisão.
  - O texto chega como `handoffs.act` o grava (sem espaços nas pontas); nada mais é alterado.
  - O teste de `test_v070_resume.py` que esperava `personality` no `reply` passa a esperar `human_review, operator_reply`; o do `approve` não muda.
- **Testes.**
  - Backend, novo `tests/integration/test_v110_operator_reply.py` (4). Com uma Personality programada para acrescentar "Os créditos ainda não estão confirmados." ao texto humano: em `reply` com valores, porcentagem e datas que nenhuma ferramenta devolveu, nenhuma chamada de modelo na retomada, passos `human_review, operator_reply`, e o texto idêntico em `GET /v1/conversations/{id}`, na resposta de `POST /v1/messages` à mensagem seguinte e em `get_handoff_cases`; em `approve`, uma chamada à Personality e o texto com a frase acrescentada. Regra do estado no `support.v11`. Log de acesso: linha escrita como o uvicorn escreve (`get_path_with_query_string` no logger `uvicorn.access`) sem `state` nem `code_challenge`, com o caminho; outra rota mantém a query; `configure_logging` duas vezes instala um filtro só.
  - Web, `tests/test_v110_resume.py` (+1): histórico com dois turnos de atendente, o primeiro já entregue; a mensagem seguinte leva `displayed_operator_message_id` 5 (o mais recente, não o 3), recebe resposta própria e cada turno de atendente aparece uma vez.
- **Comandos e números.** Backend: `.venv` do repositório principal com `PYTHONPATH=src` deste worktree. Web: `.venv-v040` do checkout da web com `PYTHONPATH=src` do worktree da web, em formato Windows. Sempre `-p no:cacheprovider` e `--basetemp` novo em `<scratchpad da sessão>` (na web, por `PYTEST_ADDOPTS`).

  | Comando | Resultado |
  | --- | --- |
  | backend `pytest` em `test_v110_operator_reply.py`, `test_v070_resume.py`, `test_v110_tickets.py`, `test_v0130_otel.py`, `test_v080_replan.py`, `test_v110_conversations.py` | todos passaram, 1 skip (otel) |
  | web `pytest tests/test_v110_resume.py` | **24 passed** |
  | backend `python tools/scripts/lint_and_tests.py --strict`, primeira execução | testes sem falha; `ruff` com 3 linhas longas (docstring de `graph.py` e duas linhas do teste novo), exit 1; corrigidas |
  | backend `python tools/scripts/lint_and_tests.py --strict`, depois da correção | **3056 passed, 1 skipped**, 0 falhas (contagem pela barra de progresso), `ruff` "All checks passed!", caminhos pessoais e links sem ocorrência, exit 0, 17 min 40 s. O skip é o de `test_v0130_otel.py` (venv sem o extra `otel`) |
  | web `python tools/scripts/lint_and_tests.py --strict` | **203 passed, 3 skipped** (módulos entre repositórios, sem o backend no caminho) em 3 min 46 s, `ruff` "All checks passed!", exit 0 |

- **Roteiro do QA** (modelo real e Docker):
  1. Lojista pede atendente; operadora assume e usa **Responder** com um texto que traga valor e data que não vêm de ferramenta (por exemplo, "Seu estorno de R$ 150,00 cai na conta em 12/11."). Esperado: na conversa do lojista (interface, `Atendente humano`), em `GET /v1/conversations/{id}` e na mensagem seguinte, exatamente esse texto, sem frase a mais; o trace da retomada tem `human_review` e `operator_reply`, sem `personality`.
  2. Outro caso, **Aprovar o rascunho**: o trace da retomada tem `personality` e `output_guard`.
  3. Em conversa nova, "Tenho algum ticket aberto?": o estado de cada ticket vem em português (sem `open`, `claimed`, `answered`, `rejected`, `closed`) e a resposta da atendente do passo 1 com as palavras dela.
  4. Login pela página (`/v1/auth/authorize`) com a API no compose; `docker compose logs api`: a linha de acesso mostra `GET /v1/auth/authorize` sem `?` nem `state`/`code_challenge`.
  5. Recarregar a página com duas respostas de atendente na conversa, a primeira já entregue e a segunda não: a mensagem seguinte recebe resposta própria e a segunda resposta aparece uma vez.

Developer, rodada 2 (2026-11-11): ajustes finais antes do merge, pedidos pela reconferência da tarefa 113 (P3-8 e P3-9) e pelo QA com modelo real (CA-76 numa lista mista). Sem chamada paga. Só o backend; a web continua em `44408d8`.

- **Commit.** Backend `codex/v1.1.0-tickets-retomada`, base `95dd9bd`: um commit com prompt, documentos, spec, teste e esta seção.
- **CA-76 numa lista mista.** `prompts/support.v11.md` (ainda não publicado, editado no lugar), regra 15: "When you list tickets, every ticket with `operator_reply` comes with that reply in the attendant's own words, never only its protocol; this holds also when the merchant asked only about open tickets." O item do `support.v11` no CHANGELOG diz o mesmo.
- **Webhook do lojista (P3-8).** Nenhuma mudança de código nem da regex da guarda de entrada. README ("Pause and resume") e CHANGELOG 1.1.0 dizem que a cópia em `conversation.replied` passa pelo mesmo mascaramento de dados sensíveis de todo evento de saída; o README nomeia o que é mascarado (e-mail, CPF ou CNPJ, cartão, credencial).
- **README linha 8 (P3-9).** A Personality escreve toda resposta do assistente; a resposta escrita pela operadora chega com as palavras dela.
- **Spec, D2.** A confirmação de exibição marca o turno informado e os turnos de atendente anteriores ainda não entregues da mesma conversa, como o contrato já diz. A versão da spec continua 0.3.
- **Decisão além do pedido.** Além do teste com texto comum, um teste fixa o mascaramento que o README agora afirma: com um e-mail na resposta, o webhook leva `[e-mail removed]` e a conversa guarda o texto inteiro.
- **Testes.** `tests/integration/test_v110_operator_reply.py` (+3, agora 7): presença da regra da lista mista; `reply` com texto comum, webhook do lojista num receptor falso (`httpx.MockTransport`) com `reply_text` igual ao texto da operadora, sem `operator_id`; `reply` com e-mail, webhook mascarado e conversa com o texto inteiro.
- **Comandos e números.** `.venv` do repositório principal com `PYTHONPATH=src` deste worktree em formato Windows, `-p no:cacheprovider` e `--basetemp` novo em `<scratchpad da sessão>`.

  | Comando | Resultado |
  | --- | --- |
  | `pytest` em `test_v110_operator_reply.py`, `test_v110_tickets.py`, `test_v0120_memory.py`, `test_v070_webhooks.py`; `ruff check` no teste | **144 passed**; "All checks passed!" |
  | `python tools/scripts/lint_and_tests.py --strict` | **3059 passed, 1 skipped**, 0 falhas (contagem pela barra de progresso; +3 sobre a rodada 1), `ruff` "All checks passed!", caminhos pessoais e links sem ocorrência, skills válidas, exit 0. O skip é o de `test_v0130_otel.py` (venv sem o extra `otel`) |

- **Roteiro do QA**, além do da rodada 1: com um ticket aberto e outro respondido, "Tenho algum ticket aberto?" traz o estado de cada um em português e, no respondido, a resposta da atendente com as palavras dela, não só o protocolo.

## Status

```text
pronta para revisão (rodada 2); conferência com modelo real no QA
```
