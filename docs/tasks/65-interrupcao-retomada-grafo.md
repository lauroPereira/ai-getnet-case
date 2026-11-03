# Tarefa: interrupção e retomada do grafo pelo operador

## Objetivo

O encaminhamento interrompe o grafo com estado durável; a ação do operador retoma o mesmo fluxo, passa por Personality e guarda de saída, grava o turno `via=operator` e entrega a resposta ao lojista.

## Especificação relacionada

[Spec v0.7.0](../specs/identidade-hitl-v070.md) (D4, D6, D8, D15, D16), [spec 0.2](../specs/evolucao-pos-feedback.md) RF-82, RF-84, [plano](../specs/evolucao-pos-feedback-plano.md) decisões 4 a 6, [ADR 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).

## Pré-condições

- Tarefa 64 com a costura da ação pronta.
- Primeiro passo é o teste de serialização: se o `GraphState` não serializar no `SqliteSaver`, pare e relate ao Supervisor (plano B na ADR 0018) antes de seguir.

## Arquivos prováveis

`pyproject.toml` (`langgraph-checkpoint-sqlite`), `orchestration/graph.py`, `orchestration/state.py`, `orchestration/run.py`, `agents/escalation.py`, `agents/personality.py`, `agents/support.py` (instrução do operador), `prompts/escalation.v2.md`, `prompts/personality.v4.md`, `conversations.py`, `cases.py`, `api/app.py`, `api/v1.py`, `main.py`, testes.

## Passos

1. Dependência `langgraph-checkpoint-sqlite`; checkpointer em `<runtime>/checkpoints.sqlite3` (configurável), `thread_id` conforme D6. O caminho sem encaminhamento não lê checkpoint.
2. Nó `human_review` depois de `escalation`: `interrupt(payload)` com resumo, pergunta pendente e rascunho (D16, `escalation.v2`). A requisição do lojista termina como hoje (`status=handoff`, protocolo `HO-…`, texto sem "simulação").
3. Retomada pela ação: `Command(resume={action, text, operator_id})` com `RunContext` novo (`request_id` próprio, trace que referencia o original, orçamento normal). `approve`/`reply` → `personality` (`personality.v4`, contribuição `from_operator=True`, evidência válida para a guarda); `reject` → `support` com `operator_instruction`, um ciclo, sob o principal do operador e o lojista do caso (D4), depois `personality`.
4. Turno gravado com `via=operator`, ação e protocolo; estados de fila e caso conforme D15 (a máquina de estados ganha a saída de `handoff` só por ação de operador).
5. Entrega: próxima `POST /messages` (D8, rota `human_reply`, sem modelo); `GET /v1/conversations/{id}` e a rota de demo mostram o turno com a marca de atendente.
6. `GET /ready` ganha `pending_handoffs` e `checkpoints`.

## Critérios de conclusão

- [ ] CA-47: com modelo programado, `approve`, `reply` e `reject` produzem turno `via=operator` com a marca de atendente e o estado de caso de D15; `reject` chama a ferramenta indicada pela instrução uma única vez e não reencaminha.
- [ ] CA-48: retomada após reinício: o teste encaminha num processo, encerra-o e retoma num processo novo sobre o mesmo checkpoint.
- [ ] CA-48: segunda retomada recusada (`409 already_resumed`) sem tocar o grafo.
- [ ] CA-46: na retomada `reject`, a auditoria registra o principal do operador e o lojista do caso; o lojista B não recebe nem vê o turno.
- [ ] Rota `human_reply` não gera chamada a modelo (contagem do modelo programado).
- [ ] Nova mensagem do lojista com o caso aberto não colide com a interrupção pendente.
- [ ] Suíte estrita com código 0; prompts novos como arquivos novos, sem editar versões anteriores.

## Validação

A preencher pelo Developer.

## Status

```text
pendente
```
