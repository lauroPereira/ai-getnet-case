# Tarefa 76 — Pedido de encerramento de contrato recebe pergunta em vez de encaminhamento (v0.8.0)

## Objetivo

Garantir que "I want to close my contract." seja encaminhado a um atendente humano com protocolo, de forma estável nas repetições.

## Especificação relacionada

[Orquestração e avaliação v0.8.0](../specs/orquestracao-avaliacao-v080.md), CA-51 e D16 (rota medida pelo plano inicial). Parecer: [v080-d12-pre-holdout-r4.md](../evidence/v080-d12-pre-holdout-r4.md).

## Pré-condições

Candidato `4c3c8a98ddfc4f7af7bba877177f3479152159b5`, campanha `v080-qa`, ambiente válido: a pergunta não depende de data.

## O que foi feito, o esperado e o observado

- **Feito:** o lojista escreveu "I want to close my contract." (`V030-CONTRACT-TERMINATION`), três vezes.
- **Esperado:** rota inicial `human_handoff`, status `handoff`, resposta com protocolo `HO-` e menção a atendimento humano.
- **Observado:** na repetição 1 (`req_eval35a095aa8794`), a rota inicial foi `clarify`, com status `needs_clarification` e a resposta "Do you want to end your Getnet contract entirely, or cancel a specific service?". Nas repetições 2 e 3 (`req_evalab300e868f6c`, `req_eval80d42c71b9ff`), o caso foi encaminhado corretamente. Na r3, as três execuções seguiram a rota esperada.
- **Critério violado:** CA-51. Essa falha, junto com a da tarefa 75, deixa a repetição 1 em no máximo 11/13.

## Pergunta de produto associada

Se a pergunta de esclarecimento for considerada aceitável para um pedido de encerramento, a decisão é do Supervisor ou do responsável: o rótulo dev aceita hoje só `human_handoff`. O QA não muda o rótulo.

## Decisão do Supervisor (2026-11-05, padrão reversível)

Um pedido explícito de encerramento do contrato, sem menção a um serviço específico ("I want to close my contract.", "quero encerrar meu contrato"), vai para atendente humano com protocolo, como define a jornada da v0.3.0 e o rótulo dev. Pergunta de esclarecimento só é aceitável quando a mensagem é ambígua ou cita um serviço ou produto específico. A decisão fica listada como reversível no relatório da versão; revertê-la significa aceitar `clarify` no rótulo, o que é decisão do responsável.

Orientação de implementação: preferir a menor mudança determinística com regressão programada (por exemplo, regra pós-modelo em `router.enforce` para frases explícitas de encerramento em EN e PT, só em conversa nova e sem `safety`), em vez de nova versão do prompt. Se uma nova versão do prompt for inevitável, ela é `router.v7` (arquivo novo), nunca edição do `router.v6`. Os testes da história da v0.7.0 e de retomada continuam sendo trava.

## Arquivos prováveis

Prompt ou regras do Router (`router.v6`) e regressão programada da jornada.

## Critérios de conclusão

- A jornada segue `human_handoff` em todas as repetições da regressão programada e da campanha real.

## Validação

Developer (2026-11-05), branch `codex/v0.8.0-replan`:

- Regra pós-modelo em `router.enforce` (`src/merchant_assistant/agents/router.py`), sem mudar `router.v6`: em conversa nova, sem `safety`, quando a mensagem inteira é um pedido explícito de encerramento do contrato (EN: close, end, terminate ou cancel + my/the/our [Getnet] contract [with Getnet], com "I want/need/would like to" ou "please" opcionais; PT: encerrar, cancelar, rescindir, fechar, terminar, finalizar e imperativos + [o] [meu/nosso] contrato [com a/da/na Getnet], com "quero/preciso/desejo/gostaria de" ou "por favor" opcionais), a rota vira `human_handoff` com `topic = contract`. Se o modelo já escolheu `human_handoff`, a decisão dele fica como está.
- Fora da regra (seguem com o modelo): mensagem que cita serviço ou produto ("Quero cancelar o serviço X", "contrato da maquininha", "Payment Link contract"), pergunta ("How do I close my contract?", "Quero encerrar meu contrato?"), negação, pedido misto e conversa em andamento.
- `tests/unit/test_t76_contract_termination.py` (74 testes): 17 variantes positivas EN/PT × 3 rotas do modelo, 19 negativas, conversa em andamento e `safety`, decisão do modelo preservada, e a jornada `V030-CONTRACT-TERMINATION` com o Router programado para pedir esclarecimento (a falha da r4): três repetições com rota `human_handoff`, status `handoff`, protocolo `HO-` distinto e todas as checagens do runner; PT encaminha e "Quero cancelar o serviço X." continua em `clarify`.
- Travas de D18: história, webhooks, retomada e encaminhamentos da v0.7.0, jornadas, replanejamento e história da v0.8.0 e testes do Router: 429 passed. Suíte estrita no `HEAD` `94bf7b3`: 1247 passed, ruff e skills ok, exit 0 ([passagem](../evidence/v080-developer.md)).
- Pendente: revisão independente e QA (campanha real).

Developer, rodada 2 (2026-11-05), correção do P2-76 e do P3-76 da [revisão](../evidence/v080-reviewer-t75-77.md):

- Regex em `src/merchant_assistant/agents/router.py`: `fechar`, `finalizar`, `terminar` e os imperativos `feche`, `finalize` e `termine` só contam com `meu` ou `nosso` antes de `contrato`; "close" só conta com `my` ou `our`. `encerrar`, `cancelar`, `rescindir` (e imperativos) e "end/terminate/cancel the contract" continuam aceitos sem possessivo. `terminar` entrou no grupo restrito por decisão do Developer: também significa concluir ("terminar o contrato" = acabar de preenchê-lo).
- Trace: quando a regra troca a rota do modelo por `human_handoff`, o passo `router` registra `rule = "contract_termination"`; sem a regra (modelo já encaminhou ou mensagem fora do padrão), a nota não aparece.
- `tests/unit/test_t76_contract_termination.py`: 93 testes (74 + 19). Novos positivos: "I want to close our contract.", "Quero fechar meu contrato.", "Quero finalizar o nosso contrato com a Getnet.". Novos negativos (mantêm a decisão do modelo): "Quero fechar contrato com a Getnet.", "Gostaria de fechar contrato.", "Quero finalizar o contrato.", "Preciso fechar o contrato da Getnet.", "I want to close the contract.", "Close the contract.", "Feche o contrato.", "Quero terminar o contrato." (todos casavam a regex de `94bf7b3`). Ponta a ponta: a jornada registra a nota no trace; "Quero fechar contrato com a Getnet." com o Router programado em `knowledge` segue `knowledge`, sem protocolo e sem nota; encaminhamento do próprio modelo não ganha nota.
- Travas de D18 (T76, Router e orçamento, todas as integrações v0.7.0 e v0.8.0): ver passagem.

## Status

implementada (rodada 2); aguarda revisão
