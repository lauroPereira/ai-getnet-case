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

Developer, rodada 1 (2026-11-03). Passagem em [v070-developer.md](../evidence/v070-developer.md), seção "Tarefa 65, rodada 1". Os critérios ficam desmarcados até a revisão e o QA.

| Critério | Evidência determinística (`tests/integration/test_v070_resume.py`, salvo indicação) |
| --- | --- |
| Serialização (primeiro passo) | Sonda em dois processos com o `GraphState` completo no `SqliteSaver`, também em `LANGGRAPH_STRICT_MSGPACK=true` com os tipos registrados (`CHECKPOINT_TYPES`): serializa e retoma; plano B não necessário. `test_checkpoint_types_are_registered_for_strict_deserialization` |
| CA-47 | `test_approve_and_reply_write_an_operator_turn` (turno `via=operator`, `operator_action`, `protocol`, caso `awaiting_customer`); `test_reject_reruns_support_once_under_the_operator_and_never_hands_off_again` (uma única `get_device_status`, sem novo caso nem `escalation`) |
| CA-48 (reinício) | `test_resume_after_restart_in_a_new_process`: encaminha num processo, encerra, retoma noutro (`LANGGRAPH_STRICT_MSGPACK=true`) |
| CA-48 (`409 already_resumed` sem tocar o grafo) | `test_second_action_is_refused_without_touching_the_graph` |
| CA-46 | Auditoria do `reject` com `operator:op_ana` e o lojista do caso; `test_another_merchant_never_receives_or_sees_the_operator_turn` |
| `human_reply` sem modelo | `test_next_message_delivers_the_human_reply_without_a_model_call` |
| Nova mensagem com o caso aberto | `test_new_message_with_the_case_open_does_not_collide_with_the_interruption` |
| Caminho sem encaminhamento sem checkpoint | `test_turn_without_handoff_never_touches_checkpoints` (zero chamadas ao `SqliteSaver`, arquivo inexistente) |
| Pedidos do Supervisor | Falha da retomada: `test_failed_resume_is_visible_and_recovers_with_the_same_key`, `test_failure_after_the_graph_finished_writes_the_turn_once_on_retry`, `test_stale_pending_resume_is_retried`. Casos pré-0009: `test_case_from_before_0009_is_refused_clearly`. Texto sem "simulação": `test_handoff_interrupts_with_a_checkpoint_and_no_simulation_text` |
| Suíte estrita | `lint_and_tests.py --strict` → código 0, **437 passed**, Ruff ok, skills ok; prompts `escalation.v2.md` e `personality.v4.md` como arquivos novos |

## Status

```text
pronta para revisão (Developer, rodada 1)
```
