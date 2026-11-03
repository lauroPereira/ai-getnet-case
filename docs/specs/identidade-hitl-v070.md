<!-- Papel: especificação complementar curta da v0.7.0 (identidade e HITL real), derivada da evolução pós-feedback. -->

# Especificação: v0.7.0 — identidade e HITL real

Versão 1 — 2026-11-03 — aberta pelo Supervisor sob a "Autorização por versão" do AGENTS.md. Deriva da [especificação 0.2](evolucao-pos-feedback.md) (RF-76 a RF-85, RF-100; CA-46 a CA-48) e do [plano](evolucao-pos-feedback-plano.md) (decisões técnicas 1 a 8, tarefas 63 a 68). História em [identidade-hitl-v070.md](../historias/identidade-hitl-v070.md); decisões em [ADR 0017](../architecture/decisions/0017-identidade-principal-escopos.md) e [ADR 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).

Esta spec não repete a 0.2: fixa o que o plano deixou aberto e diz como cada critério será comprovado.

## Problema

Hoje `POST /messages` aceita qualquer `user_id` do payload, as ferramentas não sabem quem é o principal e o encaminhamento grava um caso `SIM-…` que nenhum humano responde. O avaliador deu 4,0 em HITL e 7,8 em identidade por isso.

## Resultado desejado

1. Toda mensagem chega com uma sessão; o lojista vem do principal; cada tool call verifica escopo e lojista e deixa auditoria com o principal.
2. O encaminhamento interrompe o grafo; um operador autenticado lê o caso, aprova, responde ou rejeita; o mesmo fluxo retoma do ponto salvo e a resposta chega ao lojista na conversa, na consulta e por webhook assinado, com o ticketing da demo recebendo o caso.

## Escopo

| Bloco | Conteúdo | Requisitos | Tarefa |
| --- | --- | --- | --- |
| Identidade | Papéis `merchant` e `operator`, chaves sintéticas, escopos, `identity_mismatch`, auditoria por tool call, rate limit, MCP com chave, rotas de demo com sessão | RF-76 a RF-79 | 63 |
| Fila | Migração 0009, estados, eventos, reivindicação, ações idempotentes, CLI `operator` | RF-80, RF-81, RF-83, RF-85 | 64 |
| Interrupção e retomada | Checkpointer SQLite, nó `human_review`, `Command(resume)`, `approve`/`reply`/`reject`, turno `via=operator`, entrega na próxima mensagem e no GET, retomada após reinício | RF-82, RF-84 | 65 |
| Webhooks | `handoff.created` e `conversation.replied` assinados, tentativas, registro, receptores no `mocks`, compose | RF-100 | 66 |
| Interface | Login por papel e aba Operador no projeto web | RF-85 | 67 |
| Fechamento | Regressão integrada, campanha `v070-qa`, evidência | CA-46 a CA-48 | 68 |

## Fora do escopo

Provedor OIDC real (só o adaptador `resolve_credential`), ticketing comercial, webhook de entrada (o ticketing devolve a ação pela API de operador, autenticado por sessão), replanejamento (v0.8.0), mudança de regras financeiras, de ferramentas de Support ou de snapshots públicos.

## Decisões que o plano não fixou

Todas reversíveis; registradas também no relatório do Supervisor. "Plano" = [evolucao-pos-feedback-plano.md](evolucao-pos-feedback-plano.md).

| ID | Decisão | Motivo | Como reverter |
| --- | --- | --- | --- |
| D1 | **Chaves:** `MERCHANT_ACCESS_KEYS=cliente1988:<chave>,cliente_demo_002:<chave>` e `OPERATOR_ACCESS_KEYS=op_ana:<chave>,op_bruno:<chave>` (o plano previa uma `API_OPERATOR_ACCESS_KEY` única). Cada chave tem ≥ 24 caracteres e é única entre todos os papéis (incluindo `API_DEMO_ACCESS_KEY` e `API_ADMIN_ACCESS_KEY`); a configuração inválida impede a subida. Valores do `.env.example` com prefixo `mk_demo_`/`op_demo_` e sufixo `_fictitious`; a API registra um aviso na subida quando uma chave de exemplo está em uso. Admin e demo continuam sem valor no exemplo | Dois operadores mostram o `409` de reivindicação; `docker compose up` funciona sem edição; admin não ganha chave pública | Voltar a uma variável única |
| D2 | **Principais:** `merchant:<customer_id>`, `operator:<operator_id>`, `demo:default`, `admin:default` | IDs legíveis na auditoria | Renomear na migração |
| D3 | **Escopos:** `support:read` (as nove ferramentas de Support), `handoff:create` (Escalation grava caso), `conversation:read` (conversa própria), `handoff:operate` (fila, reivindicação, ações), `kb:admin`, `profiles:admin`. Papéis: merchant e demo = `support:read`, `handoff:create`, `conversation:read`; operator = `handoff:operate`, `support:read`; admin = `kb:admin`, `profiles:admin`, `support:read`, `handoff:create`, `conversation:read`. As rotas continuam autorizadas por papel como hoje; o escopo é verificado em todo tool call, na gravação do caso e nas rotas de handoff | Menor conjunto que cobre RF-78 | Tabela única em `api/identity.py` |
| D4 | **Operador no caminho `reject`:** o Support roda com o principal do operador e o `customer_id` do caso retomado, lido do caso pelo servidor; o registro exige `support:read` e lojista igual ao do caso | Escopo e lojista verificados também quando quem age é o humano | — |
| D5 | **Rate limit:** janela fixa de 60 s por principal em `rate_limit_hits` (o plano dizia "deslizante"; a tabela do plano já tem formato de balde), `RATE_LIMIT_PER_MINUTE=30`, em `POST /messages`, `POST /v1/messages` e `POST /v1/handoffs/*`; `429 rate_limited` com `Retry-After`, antes de qualquer chamada a modelo. O limite por sessão demo continua | Simples, determinístico, testável com relógio fixo | Trocar o cálculo da janela |
| D6 | **`thread_id` do checkpoint = `request_id` da execução que encaminhou**, gravado em `handoff_cases.thread_id` (o plano dizia `conversation_id`) | Uma nova mensagem do lojista na mesma conversa, com o caso ainda aberto, não pode colidir com a interrupção pendente | Coluna única a trocar |
| D7 | **Protocolo `HO-AAAAMMDD-XXXXXX`**; `simulated` sai do payload e o texto de encaminhamento deixa de dizer "simulação" | Plano, item 7 | — |
| D8 | **Entrega na próxima mensagem:** havendo turno de operador não entregue, `POST /messages` registra a mensagem do lojista, devolve o turno de operador com rota `human_reply` e `via=operator`, sem chamada a modelo, e o marca como entregue | Plano, item 6; resposta humana nunca fica escondida atrás de uma resposta automática | — |
| D9 | **Ação sobre caso `open` reivindica implicitamente** para o operador que age (mesma transação); caso reivindicado por outro → `409 claimed_by_other`; reivindicar de novo o próprio caso é idempotente | Ticketing e CLI agem em uma chamada; conflito continua visível | Exigir `claim` explícito |
| D10 | **`idempotency_key` obrigatória** nas ações (8 a 80 caracteres `[A-Za-z0-9_-]`); mesma chave → `200` com o registro existente e `replayed: true`; outra chave em caso já retomado → `409 already_resumed` | RF-83 | — |
| D11 | **Webhooks nos dois sentidos = ida ao ticketing (`handoff.created`) e volta ao lojista (`conversation.replied`).** Cabeçalhos `X-Webhook-Event`, `X-Webhook-Delivery`, `X-Signature: sha256=<hex do HMAC-SHA256(WEBHOOK_SIGNING_SECRET, corpo)>`; corpo mascarado; três tentativas com esperas de 1 s e 2 s (configuráveis), 3 s de timeout por tentativa; uma linha de `webhook_deliveries` por tentativa. O `mocks` ganha `POST/GET /ticketing/cases` e `POST/GET /merchant/events`, que validam a assinatura (`401 invalid_signature`) e ignoram entrega repetida pelo id | O plano só previa o receptor de ticketing; sem receptor do lojista a "volta" não aparece na demo | Remover a rota do lojista no `mocks` |
| D12 | **`webhook_url` da sessão** só é aceita se o host estiver em `WEBHOOK_ALLOWED_HOSTS` (vazio por padrão; o compose libera `mocks`); senão `422 webhook_host_not_allowed` | Evita que uma sessão faça o servidor chamar qualquer URL | Esvaziar a lista |
| D13 | **MCP:** `--customer` sai; o lojista vem da chave, por `--access-key` ou, preferencialmente, `MERCHANT_ASSISTANT_ACCESS_KEY` (fora da lista de processos); só chaves de lojista | RF-78; chave fora da linha de comando | Reintroduzir `--customer` |
| D14 | **Rotas de demo `GET /traces/{id}` e `GET /conversations/{id}` exigem sessão:** lojista e demo só o que é seu; operador só conversas com caso; admin tudo | Hoje são abertas com `DEMO_MODE=true`, o padrão do compose; CA-46 pede que dado de outro lojista nunca apareça | — |
| D15 | **Estados depois da ação:** `approve`/`reply` → fila `answered`, caso `awaiting_customer`; `reject` → fila `rejected`, caso conforme o Support reexecutado (`awaiting_customer` ou `resolved` com evidência de ferramenta), nunca de volta a `handoff` no mesmo ciclo; fila `closed` quando o caso chega a `resolved`. A máquina de estados ganha a saída de `handoff` só por ação de operador | RF-80, RF-84 | — |
| D16 | **Rascunho do operador** vem do Escalation (`escalation.v2`: resumo, pergunta pendente e rascunho no idioma do lojista); falha do modelo → rascunho determinístico a partir das contribuições, sem bloquear o encaminhamento | Plano, item 4 | — |
| D17 | **Ordem do Time B:** 72a começa já (não depende da 64) e a 67 entra assim que a 64 tiver parecer apto | Evita o Time B parado durante 63 e 64 | — |

## Critérios de aceitação e prova

| ID | Critério | Prova determinística (tarefa) | Prova real (QA, campanha `v070-qa`) |
| --- | --- | --- | --- |
| CA-46 | Sem sessão `401`; `user_id` de outro lojista `403 identity_mismatch`; dado de outro lojista nunca aparece; todo tool call com auditoria (principal, escopo, resultado) | Testes de contrato e integração; lojista B não lê fila, conversa, trace nem caso de A; contagem de auditoria = contagem de tool calls (63, 64) | UC-22 por `curl` e na interface; leitura da auditoria |
| CA-47 | Caso na fila e no receptor de ticketing; `approve`, `reply` e `reject` geram turno marcado como atendente e entrega por webhook registrada | Integração com modelo programado nas três ações; receptor do `mocks` em processo (65, 66) | UC-20 e UC-21 na API, na CLI e na aba Operador; receptores no Docker |
| CA-48 | Retomada dupla `409`; mesma chave devolve o registro; retomada após reinício da API | Teste concorrente sob `BEGIN IMMEDIATE`; novo processo sobre o mesmo checkpoint (64, 65) | Reinício do container entre encaminhar e agir |

Regressão: 40 casos (`challenge_examples` 10, `core_cases` 17, `business_journeys` 13) e 4 conversas (`followup`) sem piora em relação à v0.6.0, salvo diferença justificada pelo contrato novo.

## Requisitos não funcionais

- Teto da campanha `v070-qa`: US$0,20, montada uma vez, combinada com o ledger primário (acumulado do projeto antes da versão: US$0,69 de US$5,00).
- Testes sem chamada paga; migração 0009 reversível e testada nos dois sentidos; contrato `/v1` aditivo; a quebra de `POST /messages` vai no CHANGELOG com as duas chamadas do avaliador.
- O caminho sem encaminhamento não lê checkpoint (custo e latência iguais aos da v0.6.0, medidos na suíte).
- Nenhum segredo real; chaves e segredo de webhook do exemplo nomeados como fictícios.

## Riscos

| Risco | Mitigação |
| --- | --- |
| Estado do grafo não serializável pelo `SqliteSaver` | Teste de serialização na 65 antes do resto; plano B (retomada em aplicação) na ADR 0018 |
| Quebra do `curl` do avaliador | README com sessão + mensagem; smoke e `/docs` com sessão; chaves no `.env.example` |
| Escrita concorrente nos dois repositórios ou entre times | Donos de arquivo do plano; Time B em worktree próprio |
