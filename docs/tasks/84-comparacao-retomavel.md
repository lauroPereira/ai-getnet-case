# Tarefa 84 — Comparação retomável após reinício

## Objetivo

Uma comparação de perfis interrompida por reinício da API não vira `failed`: fica `interrupted`, preserva as células concluídas e pode ser retomada pela API, executando só o que falta e sem pagar duas vezes.

## Especificação relacionada

[Rubrica `judge.v4` e operação v0.10.0](../specs/rubrica-operacao-v0100.md): D3, D6, CA-58; especificação 0.2 RF-104. Código: `src/merchant_assistant/comparisons.py` (`start`, `_run`, `_save`, `_alive`, `read`), tabela `comparisons` (`data/migrations.py`, `CHECK` do `state`), `api/v1.py` (rotas de comparação), `api/app.py` (`lifespan`).

## Pré-condições

Tarefa 83 commitada (não precisa estar revisada). Nenhuma chamada paga: testes com modelo programado.

## Arquivos prováveis

`comparisons.py`, `api/v1.py` (rota nova `POST /v1/comparisons/{id}/resume`, só por acréscimo), `api/app.py` (`lifespan`: marcar `interrupted`), `data/migrations.py` (migração 0012 reversível só se o `CHECK` impedir o estado novo), `docs/contracts/` se houver contrato de comparação, testes de integração com reinício simulado (novo `TestClient` sobre o mesmo runtime).

## Passos

1. **Estado `interrupted`.** Se o `CHECK` da coluna `state` não aceitar, migração 0012 reversível que amplia o `CHECK` (recriação da tabela), testada nos dois sentidos; `read()` deixa de marcar `failed` uma comparação `running` sem thread viva: marca `interrupted` e preserva `cells`.
2. **Startup.** No `lifespan`, toda comparação `running` vira `interrupted` (nenhuma thread sobrevive ao processo); log estruturado com o id.
3. **Retomada.** `POST /v1/comparisons/{id}/resume` (mesmas regras de principal da leitura; idempotente: `resume` de uma `running` ou `completed` devolve `409` com código claro): relê `config` e `cells`, pula células com `request_id` (resultado gravado), reserva orçamento só para as restantes com o mesmo `estimate` por célula, roda na thread como `start`, e no fim calcula `completed`/`partial`/`failed` como hoje. Uma célula que já tinha falhado (`status=failed`) é reexecutada só se `?retry_failed=true`.
4. **Custo.** O `cost_usd` acumula; nenhuma célula com `request_id` gera nova chamada (teste com contador de chamadas do modelo programado).
5. **Contrato.** `GET /v1/comparisons/{id}` passa a poder devolver `interrupted`; OpenAPI e `docs/contracts/` atualizados por acréscimo; a interface web (projeto irmão) não muda nesta versão: `interrupted` é exibido como está.
6. **Testes:** interrupção simulada (marcar `running` e abrir novo app sobre o runtime → `interrupted`), retomada completa, retomada idempotente, `retry_failed`, célula concluída não reexecutada (contador), migração 0012 ida e volta se existir.

## Critérios de conclusão

- Comparação `running` sem processo vivo aparece `interrupted` com as células preservadas.
- `resume` termina `completed` sem reexecutar células com resultado; ledger coerente.
- Suíte estrita verde; `checar-caminhos-pessoais.py` limpo.

## Validação

(Preenchida pelo Developer.)

## Status

Pendente. Aberta pelo Supervisor em 2026-11-05.
