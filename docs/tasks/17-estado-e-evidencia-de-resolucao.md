# Tarefa: Estado do atendimento e evidência de resolução

## Objetivo

Controlar o estado do caso (`in_progress`, `awaiting_customer`, `resolved`, `handoff`) e só marcar resolução com evidência identificada.

## Especificação relacionada

[Especificação principal](../specs/assistente-multiagente-lojista.md): RF-29, CA-19. [Complementar](../specs/incrementos-pos-nucleo.md): RF-44, UC-20.

## Pré-condições

- Tarefa 16 concluída.

## Arquivos prováveis

- `src/merchant_assistant/cases.py` (novo; máquina de estados)
- `src/merchant_assistant/data/migrations/0003_case_attempts.py`
- `src/merchant_assistant/agents/router.py`, `support.py`, `prompts/router.v2.md`
- `tests/unit/test_case_states.py`, `tests/integration/test_resolution.py`

## Passos

1. Máquina de estados com transições permitidas e testadas.
2. Evidências: `tool_verified` (ferramenta confirma o fato), `customer_confirmed` (lojista confirma explicitamente o problema correto) e `informational` (critério do cenário para dúvidas).
3. O Router reconhece confirmação, agradecimento e persistência do problema; agradecimento ou silêncio não resolvem.
4. Registro de orientações, tentativas, resultados e pendências (`case_attempts`).
5. `resolution` na resposta traz estado e evidência; a resposta ao lojista não diz "resolvido" sem evidência.

## Critérios de conclusão

- [x] "Voltou a funcionar" resolve com `customer_confirmed`; "obrigado" não resolve.
- [x] Transições inválidas são recusadas.
- [x] Tentativas e resultados ficam registrados por caso.

## Validação

2026-10-26: máquina de estados em `cases.py` (testes em `tests/unit/test_case_states.py`), sinal do caso no Router v2, rota `acknowledgement`, `customer_confirmed` e `tool_verified`, tentativas em `case_attempts` (migração 0003). Verificado com modelo programado e real. Desvio consciente do passo 2: não há evidência `informational` automática; respostas informativas ficam `awaiting_customer` até o lojista confirmar, critério mais estrito que o previsto. Ver [evidência](../evidence/2026-10-26-v020-memoria-e-acompanhamento.md). Revisão não independente.

## Status

```text
concluída
```
