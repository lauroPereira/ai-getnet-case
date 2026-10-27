# Tarefa: corrigir os seis achados técnicos da v0.5.0 r1

## Objetivo

Corrigir R1-01 a R1-06 antes de fixar novo candidato para revisão e QA real.

## Especificação relacionada

[Plano aprovado](../specs/base-versionada-v050-plano.md),
[história v1](../historias/base-versionada-v050.md) e
[parecer independente r1](../evidence/v050-reviewer-r1.md).
São correções do escopo aprovado, sem ampliar API, permissões ou orçamento.

## Pré-condições

- Manter as branches `codex/v0.5.0-base-versionada` já derivadas das mains
  atualizadas. Preservar trabalho local e os manifestos/evidências anteriores.
- Developer `gpt-6-luna/high` da r1 substituído, por autorização do responsável
  em 2026-10-27, por novo Developer Claude Sonnet 5.5 (contexto novo); Reviewer
  e QA seguintes também Sonnet 5.5. Um único escritor de produto.
- Nenhuma chamada paga nesta tarefa. QA real aguarda parecer técnico apto.
- Nenhuma alteração em credenciais, arquivos protegidos, dados/ledgers reais,
  coleções existentes, limite nativo ou configuração global. Sem commit/push.

## Arquivos prováveis

`src/merchant_assistant/cli.py`, `config.py`, `orchestration/budget.py`,
`orchestration/graph.py`, `rag/embed.py`, `rag/index.py`, `rag/kb.py` e testes
relacionados. Web somente se correção comprovada exigir, dentro do plano.

## Passos

1. R1-01: fechar os caminhos pagos de embeddings do CLI. Toda chamada recebe
   guarda persistente antes da rede; embedding real sem guarda falha antes
   do provedor. Exercitar `index`, `bootstrap` e `eval-retrieval` com transporte
   falso, incluindo negação e uso desconhecido.
2. R1-02: impedir que CLI/bootstrap apaguem ou reconstruam coleções existentes,
   sobretudo ativa/anterior/referenciadas. Preferir reutilização segura ou
   recusa explícita; coleção nova nunca colide. Preservar bootstrap idempotente
   e não executar remoção fora de Qdrant exclusivamente em memória nos testes.
3. R1-03: conferir integridade da coleção contra o manifesto antes da troca
   do ponteiro (contagem, dimensão/modelo e pontos/digest esperados). Coleção
   vazia ou corrompida não permite ativação nem retorno; o ponteiro fica igual.
   Readiness deve observar a versão ativa atual sem chamada paga.
4. R1-04: tornar liquidação única e consistente. Repetição do mesmo valor pode
   ser idempotente; valor divergente ou liquidação de cancelada não reduz gasto.
   Validar concorrência e falha parcial do guard composto, preservando reserva
   conservadora quando o uso é desconhecido. Rejeitar valores monetários
   inválidos em vez de liberar saldo.
5. R1-05: teste de versão não rebaixa estado publicado. Restringir a candidatas
   ou persistir resultado sem modificar `active`/`retired`; proteger também
   contra corrida entre teste e transição.
6. R1-06: impor teto absoluto finito de US$5 na configuração e guarda, sem
   aumentar limite persistido. Cap adicional continua fixo em até US$0,25;
   limite nativo de US$1 e ledgers reais permanecem intocados.
7. Executar regressões sintéticas significativas e validação estrita backend.
   Usar diretórios novos sob `.pytest_cache`, preservando `_tmp` já existente.
   Registrar passagem r2 com resultados, limites e caminhos alterados.

## Critérios de conclusão

- [x] Os seis casos reproduzidos no parecer têm regressão sintética que falha
  no comportamento anterior e passa após a correção.
- [x] Toda tentativa paga tem reserva anterior; não há SDK retry opaco.
- [x] Coleções publicadas e manifestos permanecem imutáveis; corrupção e corrida
  não produzem transição incoerente.
- [x] Nenhuma repetição/liquidação concorrente reduz custo já conhecido.
- [x] US$5 absoluto e cap persistente fixo não podem ser ampliados por remontagem.
- [x] `python tools/scripts/lint_and_tests.py` passou, com evidência objetiva;
  web foi revalidado se afetado. Nenhuma chamada paga foi executada.
- [x] Passagem entregue ao Supervisor, sem autoaprovação. Novo candidato será
  fixado somente depois e encaminhado ao mesmo Reviewer independente.
  (Passagem r2 entregue; o candidato r2 ainda não foi fixado.)

## Validação

Developer Claude Sonnet 5.5 (contexto novo), 2026-10-27, somente testes
sintéticos e sem rede/provedor. Detalhes, achado a achado, em
[Developer r2](../evidence/v050-developer-r2.md).

- Estrita backend: `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_ADDOPTS="--basetemp
  .pytest_cache/v050-t45-strict"`, `.venv/Scripts/python.exe
  tools/scripts/lint_and_tests.py --strict` → **293 passed** (221 antes),
  Ruff "All checks passed", estrutura e skills válidas e mensagem final
  "Validação estrita concluída sem falhas".
- Regressões dos seis achados: `tests/unit/test_cli_index_guard.py` (novo),
  `tests/integration/test_kb_safety.py` (novo), `tests/unit/test_budget_and_router.py`
  e `tests/unit/rag/test_rag_pipeline.py` (ampliados). Nos quatro arquivos:
  **87 passed** na árvore corrigida e **56 failed / 31 passed** numa cópia
  pré-correção no scratchpad (arquivos originais de produto restaurados e, em
  `budget.py`, a liquidação incondicional e a ausência de teto do r1).
- Contrato: OpenAPI gerado em memória com `demo_mode=True` é igual a
  `ai-getnet-case-web/openapi-v1.json`; o web não foi alterado nem reexecutado.
- Nenhuma chamada paga/rede; `data/runtime/*` e `_tmp/` não foram tocados.

## Status

Concluída — candidato r2 revisado por Reviewer independente Claude Sonnet 5.5:
**apto para QA** ([parecer r2](../evidence/v050-reviewer-r2.md)), sem P1/P2.
R2-06 aceito pelo responsável em 2026-10-27; P3 seguem na
[tarefa46](46-pendencias-revisao-v050-r2.md).
