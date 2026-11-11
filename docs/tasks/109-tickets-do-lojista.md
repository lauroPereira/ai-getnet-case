# Tarefa 109 — Tickets do lojista no Customer Support

## Objetivo

Em qualquer conversa, o lojista pergunta pelos seus tickets de atendimento humano e o assistente responde com protocolo, estado e, quando houver, a resposta da atendente.

## Especificação relacionada

[v1.1.0](../specs/tickets-retomada-v110.md): D1, CA-76, RF-130.

## Pré-condições

Branch `codex/v1.1.0-tickets-retomada` (base `main` em `ed5f02e`). Nenhuma chamada paga: testes com o modelo roteirizado; a conferência com modelo real é do QA.

## Arquivos prováveis

`src/merchant_assistant/tools/domain.py` e `tools/registry.py` (ferramenta e lista do suporte), `prompts/support.v11.md` (e a referência da versão em uso), cenários e testes (`tests/`), contrato da ferramenta na documentação de ferramentas do README, se houver tabela.

## Passos

1. Ferramenta `get_handoff_cases` (escopo `SUPPORT_READ`, especialista do `customer_support`): lê `handoff_cases` do lojista do `ToolEnv`, mais recentes primeiro, no máximo 5; argumento opcional `protocol` (completo ou final com pelo menos 4 caracteres alfanuméricos, sem diferenciar maiúsculas; valor fora disso é erro de argumento). Por caso: `protocol`, `state` (estado da fila), `reason`, `opened_at`, `claimed_at`, `answered_at`, `closed_at` e `operator_reply` (texto da resposta da atendente, quando houver, lido de onde a resposta já é guardada). Sem identificador de operador, sem caso de outro lojista. Resultado com `source` e `observed_at` como as demais.
2. Auditoria e escopo iguais às outras ferramentas de leitura (linha de auditoria por chamada; outro lojista recebe vazio ou `FORBIDDEN_RESOURCE`, sem dado).
3. `prompts/support.v11.md`: quando o lojista pergunta por ticket, protocolo, atendimento humano ou "alguma novidade" sobre um caso, consultar `get_handoff_cases` antes de dizer que não há; relatar estado e resposta da atendente com as palavras dela; não inventar prazo. A versão em uso passa a ser a 11.
4. Router: conferir com o modelo roteirizado e pelos cenários que pedidos de status de ticket ou protocolo vão a `support`. Se o prompt do Router precisar mudar, registre na Validação e crie a versão nova; não mude se não precisar.
5. Os valores relatados vêm do resultado da ferramenta e passam pela guarda de saída como evidência (conferir com um teste).
6. Testes: argumento e filtro por final do protocolo; isolamento entre lojistas; auditoria; caso aberto, assumido, respondido (com `operator_reply`) e encerrado; conversa nova que pergunta pelo ticket aberto em outra conversa (roteirizado, fim a fim pela API).

## Critérios de conclusão

- A ferramenta aparece na lista do suporte, é auditada e nunca devolve caso de outro lojista.
- Um teste fim a fim roteirizado mostra uma conversa nova recebendo protocolo, estado e a resposta da atendente de um caso aberto em outra conversa.
- Suíte estrita verde.

## Validação

Developer, rodada 1 (2026-11-10). Branch `codex/v1.1.0-tickets-retomada`, base `ace786e` (spec e tarefas sobre `main` em `ed5f02e`), commit `1bd2979` (ferramenta, prompt, modelo programado e testes). Sem chamada paga: só o modelo programado.

- **Ferramenta.** `get_handoff_cases` (`tools/domain.py`, `tools/registry.py`): escopo `support:read`, fase `specialist`, na lista do `customer_support`. Lê `handoff_cases` do lojista do `ToolEnv` por `created_at` decrescente, no máximo 5 (`HANDOFF_CASES_LIMIT`). Por caso: `protocol`, `state` (fila: `open`, `claimed`, `answered`, `rejected`, `closed`), `reason`, `opened_at`, `claimed_at`, `answered_at`, `closed_at` e `operator_reply`. O resultado traz ainda `protocol_filter`, `count`, `note`, `source` (`HandoffCases`) e `observed_at`. Não traz identificador de operador, id do caso nem id de conversa. Título de fonte "Human support tickets (your account)" em `orchestration/graph.py`.
- **Resposta da atendente.** `operator_reply` é o último turno `via='operator'` da conversa do caso cujo `meta.case_id` é o caso: o texto que o lojista recebeu (também em `approve` e `rejected`). Nenhuma tabela nova, nenhuma migração.
- **Filtro `protocol`.** Aceita o protocolo completo ou o final, com pelo menos 4 letras ou dígitos, só `[A-Za-z0-9-]` e até 32 caracteres. A comparação ignora maiúsculas e hífens: `1022-CCCC03`, `cccc03` e `CC03` acham `HO-20261022-CCCC03`. Qualquer outro valor dá `INVALID_ARGUMENT`, auditado.
- **Isolamento e auditoria.** A consulta filtra pelo lojista do token: o protocolo de outro lojista devolve lista vazia e não confirma que o caso existe. Escolhi a lista vazia, não `FORBIDDEN_RESOURCE`. Cada chamada deixa uma linha em `audit_events` pelo executor comum. O `resource_id` é o `case_id` quando o filtro acha um único caso; nos demais casos fica nulo.
- **MCP.** A ferramenta entra também na lista do MCP. Não acrescentei código para isso: a regra existente expõe ali todas as leituras do suporte.
- **Prompt.** `prompts/support.v11.md` é a versão em uso (a mais recente; `support@11`). Acrescenta a regra 15 com os seguintes pontos:
  - consultar `get_handoff_cases` antes de dizer que não há ticket;
  - passar o final do protocolo quando o lojista o der;
  - perguntar por ticket não é pedir uma pessoa, então não escalar;
  - significado de cada estado;
  - resposta da atendente com as palavras dela;
  - nenhum prazo que o resultado não mostre.

  As regras 1 a 14 ficam iguais. A frase final passa a admitir protocolos além de valores e datas. `support.v10.md` não foi alterado.
- **Router.** `router.v7` não mudou: nada indicou falha com o modelo programado. A conferência com modelo real é do QA. O modelo programado (`evaluation/scripted_policy.py`) ganhou dois comportamentos:
  - uma regra `TICKET_QUESTION` (`ticket`, `chamado` ou um protocolo `HO-…` completo) que manda a mensagem a `support`/`general`, antes da regra de atendente;
  - um plano de Support que chama `get_handoff_cases` com o final do protocolo citado.

  Mantêm a rota: "Já pedi habilitação Visa, qual é o protocolo?" (enablement), "Quero falar com um atendente" (handoff) e "Quero encerrar meu contrato". Risco para o QA: no modelo real, "ticket de atendimento humano" pode cair em `human_handoff`, cuja regra é "explicitly asks for a human".
- **Guarda de saída.** Os valores relatados vêm do resultado da ferramenta, que entra na evidência como as demais. Um teste mostra que a resposta com o valor e a data da atendente não tem violação com o resultado como evidência e tem violação de valor e data sem ele. No fluxo pela API, `output_violations == []`.
- **Testes.** Novo `tests/integration/test_v110_tickets.py` com 34 testes:
  - catálogo e esquema (só `protocol`, sem campo de cliente) e presença no MCP;
  - estados aberto, assumido, respondido (com `operator_reply`) e encerrado;
  - ordem e limite de 5;
  - filtro completo, final e maiúsculas, e 8 argumentos inválidos;
  - isolamento entre lojistas e linhas de auditoria;
  - sessão sem escopo (`FORBIDDEN_SCOPE`, auditada);
  - guarda de saída;
  - `support.v11` em uso, com as regras de v10 preservadas;
  - rotas do modelo programado;
  - fim a fim pela API: quatro casos abertos em quatro conversas. Assumido pela rota de claim, respondido pela rota de ações, encerrado por `handoffs.close`. Numa conversa nova chegam protocolo, estado e resposta da atendente de cada um; "Qual o status do ticket que termina em <final>?" devolve só aquele caso; outro lojista recebe "Não encontrei ticket"; três linhas de auditoria, com principal e escopo.

  `tests/integration/test_v0120_memory.py` passa a esperar `support@11` (consequência da versão nova, com comentário).
- **Comandos e números.** Ambiente: `.venv` do repositório principal com `PYTHONPATH=src` deste worktree, `-p no:cacheprovider` e `--basetemp` novo em `<scratchpad da sessão>`.

  | Comando | Resultado |
  | --- | --- |
  | `pytest tests/integration/test_v110_tickets.py` | **34 passed** |
  | `tests/unit/tools`, `test_mcp`, `test_v0120_memory`, `test_v0120_cancellation`, `test_use_cases`, `test_v080_journeys`, `test_conversations` | **313 passed** |
  | `python tools/scripts/lint_and_tests.py --strict` | **3015 passed, 1 skipped** em 24 min 24 s, `ruff` "All checks passed!", exit 0 |
  | `checar-caminhos-pessoais.py` | nenhuma ocorrência em 739 arquivos |

  O skip da suíte estrita é `test_v0130_otel.py:436`: o venv não tem o extra `otel`.
- **Fora desta tarefa.** A tabela de ferramentas do README (a frase "ten tools" vira onze) e o CHANGELOG ficam para a tarefa 112. Não acrescentei cenário de avaliação: os dados semeados não têm caso de encaminhamento, e a pergunta só faz sentido depois de um handoff na mesma execução.
- **Roteiro do QA** (momentos 6 a 8 da [história](../historias/tickets-retomada-v110.md), modelo real):
  1. Depois do handoff e da resposta da operadora, numa **Nova conversa**, enviar "Tenho algum ticket aberto?". Esperado: protocolo `HO-…`, estado e resposta da atendente. No trace, `tool:get_handoff_cases` e o prompt `support@11`; em Resultados, a fonte "Human support tickets (your account)". Rota `support`, não `human_handoff` (se for `human_handoff`, registrar: é a condição de D1 para mudar o Router).
  2. Nova conversa, "Qual o status do ticket que termina em <6 últimos caracteres>?". Esperado: o argumento `protocol` com o final e só aquele caso.
  3. Com `cliente_demo_002`, o mesmo final de protocolo. Esperado: nenhum dado do caso.
  4. Conferir a auditoria: `SELECT customer_id, principal_id, scope, outcome, resource_id FROM audit_events WHERE tool='get_handoff_cases'` mostra uma linha por chamada, cada uma com o próprio lojista.
  5. Conferir que a resposta não inventa prazo e repete os valores e datas da atendente sem mudança.

## Status

```text
pronta para revisão (rodada 1); conferência com modelo real no QA
```
