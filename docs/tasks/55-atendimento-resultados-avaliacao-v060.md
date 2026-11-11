# Tarefa: Atendimento, Resultados e avaliação sob demanda

## Objetivo

Reorganizar a interface em Atendimento, Resultados e Administração, com catálogo de cenários e avaliação sob demanda de execuções persistidas, sem novo agente.

## Especificação relacionada

[Spec v0.6.0, blocos A e B](../specs/fechamento-v060.md), RF-76, RF-77, CA-47, CA-50 e [plano](../specs/fechamento-v060-plano.md) (decisões 1, 2, 3 e 7).

## Pré-condições

Tarefa 54 concluída. Contratos e migração 0008 aprovados. Sem chamada paga.

## Arquivos prováveis

Backend: `data/scenarios/`, `api/v1.py`, `evaluation/runner.py`, `orchestration/graph.py`, `data/migrations.py`, testes. Web: `app.py`, `src/getnet_web/api.py`, cliente gerado, `openapi-v1.json`, fixtures e testes.

## Passos

1. Catálogo curto de cenários rotulados em `data/scenarios/` e `GET /v1/scenarios`; `scenario_id` opcional em `POST /v1/messages`, gravado no snapshot.
2. Migração 0008 (`run_evaluations`, e o que o limite por sessão exigir, se ainda não feito) reversível.
3. `GET /v1/runs/{id}` acrescenta verificações determinísticas aplicáveis e avaliações registradas.
4. `POST /v1/runs/{id}/evaluations/estimate` e `POST /v1/runs/{id}/evaluations` com o avaliador e a rubrica existentes, estimativa confirmada, reserva, custo separado, idempotência e falhas críticas individuais.
5. Interface em três abas; Administração só para `admin`; perfis Referência, Híbrido e Ajustado publicados para a demonstração; mensagens de erro com ação de recuperação; rótulos real, simulado e gravado preservados.
6. Resultados mostram etapas, ferramentas, modelo efetivo por agente, versões, tokens, duração, custo, fontes e trechos recuperados, verificações (com origem) e avaliações ou "não avaliado".
7. Regenerar cliente e snapshot OpenAPI; testes `AppTest` e de API.

## Critérios de conclusão

- [x] Nenhum POST, inferência ou publicação em rerun, troca de aba ou navegação.
- [x] Avaliação de execução persistida não repete o atendimento; custo de avaliação separado; repetição só explícita.
- [x] Demo não vê nem consegue usar Administração (backend `403`).
- [x] Migração 0008 sobe e desce em banco sintético; validação estrita backend e web com código 0.

## Resultado

Interface em Atendimento, Resultados e Administração; catálogo de 8 cenários com `GET /v1/scenarios`; avaliação sob demanda de execuções persistidas com estimativa, reserva, custo separado e repetição só explícita; migração 0008 nos dois sentidos. Suíte estrita: backend 326 testes, web 30. OpenAPI com 31 caminhos e 28 operações. Evidência: [resultado da v0.6.0](../evidence/v060-resultado.md).

## Status

```text
concluída (v0.6.0)
```
