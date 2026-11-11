# Tarefa 113 — Resposta da operadora sem reescrita, estado do ticket e log de acesso

## Objetivo

A resposta que a operadora escreve chega ao lojista exatamente como ela escreveu; o estado do ticket aparece no idioma do lojista; o log de acesso não guarda a query do login.

## Especificação relacionada

[v1.1.0](../specs/tickets-retomada-v110.md): D4, CA-79; CA-76 (estado do ticket); CA-77 (confirmação de exibição). Emenda a [decisão 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).

## Pré-condições

Tarefas 109 a 112 concluídas no backend e na interface. Nenhuma chamada paga.

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

## Resultado

`reply` entrega o texto da operadora sem chamada de modelo (nó `operator_reply`); `approve` segue pela Personality e pela guarda de saída; `support.v11` descreve o estado no idioma do lojista e traz a resposta da atendente em cada ticket listado; o log de acesso registra o caminho do authorize sem a query; ADR 0018 emendada.
`test_v110_operator_reply.py` com 7 testes; suítes estritas com 3.059 aprovados no backend e 203 na interface.
Com modelo real: texto idêntico na interface, em `GET /v1/conversations/{id}` e na ferramenta; linha do login sem a query. Evidência: [resultado da v1.1.0](../evidence/v110-resultado.md).

## Status

```text
concluída (v1.1.0)
```
