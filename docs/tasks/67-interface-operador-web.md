# Tarefa: login por papel e aba Operador no projeto web

## Objetivo

A interface Streamlit aceita sessão de lojista, operador, demo e admin, e ganha a aba "Operador" com fila, detalhe do caso, as três ações e as entregas de webhook.

## Especificação relacionada

[Spec v0.7.0](../specs/identidade-hitl-v070.md) (D9, D10), [spec 0.2](../specs/evolucao-pos-feedback.md) RF-85, [plano](../specs/evolucao-pos-feedback-plano.md) decisão 8. Repositório: `C:\workspace\ai-getnet-case-web`, branch `codex/v0.7.0-identidade-hitl` (Time B; o backend é do Time A).

## Pré-condições

- Tarefa 64 com parecer apto: contrato de `/v1/sessions` (papéis) e `/v1/handoffs` fixado. O OpenAPI vem da branch do backend `codex/v0.7.0-identidade-hitl` no commit que o Supervisor indicar no despacho.
- Não editar o repositório do backend.

## Arquivos prováveis

`app.py`, `src/getnet_web/api.py`, `src/getnet_web/generated_api.py`, `openapi-v1.json`, `src/getnet_web/simulated.py` (modo simulado), `tests/`, `README.md` do web se citar o login.

## Passos

1. Sincronizar `openapi-v1.json` e o cliente gerado com o contrato do backend, pelo processo já usado no projeto (tarefa 34).
2. Login por chave: a interface mostra o papel devolvido pela sessão; áreas visíveis por papel (lojista e demo: Atendimento e Resultados; operador: Operador; admin: Administração e o que já via). O backend continua sendo quem recusa.
3. Aba Operador: lista por estado; detalhe com resumo, pergunta pendente, rascunho, conversa mascarada, eventos e entregas; botões `Aprovar`, `Responder` (texto) e `Rejeitar` (instrução), com confirmação e uma `idempotency_key` gerada por clique e reaproveitada em nova tentativa da mesma ação; `409` vira mensagem com recuperação (atualizar a fila).
4. Atendimento mostra o turno `via=operator` com a marca de atendente e a rota `human_reply`.
5. Navegação, troca de aba e rerun não disparam POST.

## Critérios de conclusão

- [ ] CA-47: `AppTest` com cliente falso cobre lista, detalhe e as três ações, incluindo `409 claimed_by_other` e `already_resumed` com mensagem de recuperação.
- [ ] Repetir o clique após falha de transporte reenvia a mesma `idempotency_key` (teste).
- [ ] Sessão de lojista não vê a aba Operador; sessão de operador não vê Atendimento.
- [ ] Nenhum POST em navegação e rerun (teste).
- [ ] Script estrito do web com código 0.

## Validação

A preencher pelo Developer.

## Status

```text
pendente
```
