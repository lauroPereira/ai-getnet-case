# Relatório do Supervisor — retomada da v0.8.0 no Codex em 04/11/2026

## Done

- Reconciliação local concluída com o [relatório da manhã](2026-11-04-manha.md). `0c5b13d`, ponto de partida da retomada, acrescenta dois commits documentais ao candidato da T72b r2 (`10171c1`).
- T69 e T70 chegaram aptas para QA. A T71 r2 (`af16869`) também ficou apta após revisão independente. O Reviewer reproduziu 79 testes focados em 73,53 s no worktree `review-a`, com o ambiente Python real do Time B. A suíte estrita de 807 testes consta do relatório anterior.
- A T72b r3 foi fixada em `9b761c2`. O Developer obteve 94 testes focados verdes, Ruff e `git diff --check` sem achados. O Reviewer reproduziu um P2 de status atribuído ao esquema errado e pediu nova rodada. [Parecer T72b](../evidence/v080-reviewer-t72b.md)
- Preflight às 09h09, horário de São Paulo. Disco `C:` com 10,49 GiB livres, RAM física com 0,77 GiB livres, folga virtual de 14,21 GiB incluindo paginação e zero alertas recentes. `checar-memoria.ps1` liberou um agente pesado. A sondagem de hardlink no sandbox padrão retornou `WinError 5`.
- A medição por agente do Codex foi confirmada nos registros locais. O modelo observado nos dois primeiros despachos é `gpt-6-luna/xhigh`, conforme o ensaio autorizado para esta retomada. A sessão principal usa `gpt-6.1-sol/xhigh` e fica separada dos números dos subagentes.

## Doing

| Tarefa | Papel | Candidato ou base | Situação |
| --- | --- | --- | --- |
| T72b r4 | Reviewer | `bba6e04` | Correção fixada. Developer obteve 46 testes focados verdes, incluindo a troca de esquema. Revisão independente pendente. |

## To do

1. Fixar e revisar T72b r4. Resolver os achados até obter parecer apto.
2. Integrar o Time B na branch da versão, confirmar o lacre e rodar a suíte estrita integrada.
3. Implementar e revisar T73, fixar o candidato, rodar QA em ambiente novo e gerar o CSV de calibração.
4. Consolidar a comparação somente após o QA finalizar. Contar a implementação, cada revisão, os retornos por falha, as correções e as revalidações, com modelo e esforço por passagem. Usar a comparação histórica de [Sonnet e Opus](2026-11-03-noite-retomada.md) como referência por papel.

## Recursos e medição

| Hora local | Disco `C:` livre | RAM física livre | Observação |
| --- | ---: | ---: | --- |
| 09h09 | 10,49 GiB | 0,77 GiB | Folga virtual de 14,21 GiB com crescimento de paginação. |
| 09h18 | 10,48 GiB | 0,76 GiB | 10,61 GiB de memória virtual livre, sem somar crescimento futuro. |
| 09h27 | 10,42 GiB | 1,33 GiB | Folga virtual de 15,47 GiB com crescimento de paginação e zero alertas recentes. |
| 09h47 | 10,45 GiB | 0,82 GiB | Folga virtual de 15,15 GiB com crescimento de paginação e zero alertas recentes. |

O Supervisor confere os agentes e os recursos no ciclo de 20 minutos e antes de despachar trabalho pesado. Nesta retomada, as primeiras passagens usam testes focados. A estimativa de custo usa entrada sem cache, entrada em cache e saída por subagente, com a tarifa Standard publicada pela OpenAI. Os valores são equivalentes de API. [Tarifas da API](https://developers.openai.com/api/docs/pricing)

| Tarefa | Papel e rodada | Modelo | Minutos registrados | US$ equiv. | Resultado |
| --- | --- | --- | ---: | ---: | --- |
| T72b | Developer r3 | `gpt-6-luna/xhigh` | 19,29 | 0,06831 | 94 testes focados passaram após ajuste e execução com permissão para hardlinks. |
| T71 | Reviewer r2 | `gpt-6-luna/xhigh` | 15,00 | 0,04591 | Apta, 79 testes focados. |
| T72b | Reviewer r3 | `gpt-6-luna/xhigh` | 13,58 | 0,03101 | Um P2 reproduzido. |

O Supervisor iniciou cedo uma rodada exploratória isolada sobre T72b r1 (`c861bee`). Consumiu 8,10 min e US$0,02795 equivalentes. A rodada fica fora da comparação do ciclo e seu custo fica separado. Por orientação do responsável, o benchmark será consolidado após o QA. Até lá, a sessão apenas coleta a telemetria das passagens operacionais.

Campanha real nesta retomada até o momento **US$0,00**. O plano permite US$0,50 ou até US$1,00 em uma única montagem se a estimativa justificar.

## Estado para retomar

| Repositório ou worktree | Branch ou estado | HEAD | Situação no preflight |
| --- | --- | --- | --- |
| Backend principal | `codex/v0.8.0-replan` | `bba6e04` | Candidato T72b r4. `Claude outputs/` e `_tmp/` locais preservados. |
| Backend estável | `main` | `bd0920a` | v0.7.0 integrada localmente. |
| `time-b` | `codex/v0.8.0-avaliacao` | `af16869` | Limpo. |
| `time-b-v070` | `codex/v0.7.0-ticketing` | `2226d4c` | Limpo. |
| `review-a` | Destacado | `af16869` | Limpo. |
| `review-a2` | Destacado | `10171c1` | Limpo. |
| `review-web` | Destacado | `cd7d55d` | Limpo. |
| Web principal | `main` | `0a8e12f` | Limpo. |
| `_tmp/qa-pr7-20261028` | `codex/qa-pr7-20261028` | `16a06f6` | Registro Git órfão preexistente, preservado. |

## Falta

As tarefas e a ordem estão na seção To do.

## Depende de você

- Após o QA técnico, preencher o CSV de calibração antes da integração na `main`.
