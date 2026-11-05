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

Pendente (Developer, revisão e QA).

## Status

pendente
