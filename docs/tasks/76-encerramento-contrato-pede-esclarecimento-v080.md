# Tarefa 76 — Encaminhamento estável do pedido de encerramento de contrato (v0.8.0)

## Objetivo

Garantir que "I want to close my contract." seja encaminhado a um atendente humano com protocolo, de forma estável nas repetições.

## Especificação relacionada

[Orquestração e avaliação v0.8.0](../specs/orquestracao-avaliacao-v080.md), CA-51 e D16 (rota medida pelo plano inicial).

## Pré-condições

Campanha `v080-qa`, ambiente válido: a pergunta não depende de data.

## Contexto

- **Feito:** o lojista escreveu "I want to close my contract." (`V030-CONTRACT-TERMINATION`), três vezes.
- **Esperado:** rota inicial `human_handoff`, status `handoff`, resposta com protocolo `HO-` e menção a atendimento humano.
- **Observado:** na repetição 1 (`req_eval35a095aa8794`), a rota inicial foi `clarify`, com status `needs_clarification` e a resposta "Do you want to end your Getnet contract entirely, or cancel a specific service?". Nas repetições 2 e 3 (`req_evalab300e868f6c`, `req_eval80d42c71b9ff`), o caso foi encaminhado corretamente. Na r3, as três execuções seguiram a rota esperada.

## Decisão (2026-11-05, reversível)

Um pedido explícito de encerramento do contrato, sem menção a um serviço específico ("I want to close my contract.", "quero encerrar meu contrato"), vai para atendente humano com protocolo, como define a jornada da v0.3.0 e o rótulo dev. Pergunta de esclarecimento só é aceitável quando a mensagem é ambígua ou cita um serviço ou produto específico. Revertê-la significa aceitar `clarify` no rótulo, decisão do responsável.

Orientação de implementação: preferir a menor mudança determinística com regressão programada (por exemplo, regra pós-modelo em `router.enforce` para frases explícitas de encerramento em EN e PT, só em conversa nova e sem `safety`), em vez de nova versão do prompt. Se uma nova versão do prompt for inevitável, ela é `router.v7` (arquivo novo), nunca edição do `router.v6`. Os testes da história da v0.7.0 e de retomada continuam sendo trava.

## Arquivos prováveis

Prompt ou regras do Router (`router.v6`) e regressão programada da jornada.

## Critérios de conclusão

- A jornada segue `human_handoff` em todas as repetições da regressão programada e da campanha real.

## Resultado

Regra pós-modelo em `router.enforce`, sem mudar `router.v6`: o pedido explícito de encerramento em conversa nova vai para `human_handoff` e registra `rule = "contract_termination"` no trace; menção a serviço, pergunta, negação e conversa em andamento seguem com o modelo. `tests/unit/test_t76_contract_termination.py`: 93 testes. Evidência: [validação pré-holdout](../evidence/v080-d12-pre-holdout-r6.md).

## Status

```text
concluída (v0.8.0)
```
