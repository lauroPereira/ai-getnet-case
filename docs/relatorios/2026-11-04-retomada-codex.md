# Relatório do Supervisor — retomada da v0.8.0 no Codex em 04/11/2026

Período das 09h09 às 14h43, horário de São Paulo. O desenvolvimento ficou apto para QA. A rodada técnica parou após a amostra por limite de custo.

## Done

- Reconciliação local concluída com o [relatório da manhã](2026-11-04-manha.md). `0c5b13d`, ponto de partida da retomada, acrescenta dois commits documentais ao candidato da T72b r2 (`10171c1`).
- T69 e T70 chegaram aptas para QA. A T71 r2 (`af16869`) também ficou apta após revisão independente. O Reviewer reproduziu 79 testes focados em 73,53 s no worktree `review-a`, com o ambiente Python real do Time B. A suíte estrita de 807 testes consta do relatório anterior.
- A T72b r3 foi fixada em `9b761c2`. O Developer obteve 94 testes focados verdes, Ruff e `git diff --check` sem achados. O Reviewer reproduziu um P2 de status atribuído ao esquema errado e pediu nova rodada. [Parecer T72b](../evidence/v080-reviewer-t72b.md)
- A T72b r4 (`bba6e04`) ficou apta após revisão independente. A sonda de status trocado falha no rótulo, a resposta correta gravada passa e a regressão programada permanece verde. O Reviewer somou 25 testes focados aprovados.
- Integração A+B fixada em `01e56d0`. Cinco conflitos documentais foram reconciliados, com as passagens de ambos os times preservadas. O lacre `91aa5158…4f1bac` foi conferido após normalizar as quebras de linha conforme a regra do teste. A suíte estrita desse SHA teve 1.019 testes aprovados em 17 min 35 s, com Ruff e skills válidas, código 0.
- A implementação da T73 foi fixada em `60ef1eb`. Passaram a unidade do estimador, o pacote focado de guarda, campanha e histórias v0.7/v0.8, Ruff e `docker compose --env-file .env.example config --quiet`. Houve repetição por permissão de hardlink e por uma fixture nova sem o `user_id` obrigatório. A execução final agrupada passou depois de corrigir a fixture.
- A revisão da T73 r1 reproduziu dois P1 e um P2 em `60ef1eb`. O runtime novo redirecionava o ledger e o teto, a projeção omitia quatro conversas de acompanhamento e uma amostra programada podia recomendar teto para QA real. O Reviewer obteve 31 testes focados verdes e pediu correções antes de chamadas pagas. [Parecer T73](../evidence/v080-reviewer-t73.md)
- Correção da T73 r2 fixada em `9deca61`. O pacote focado passou com hardlinks aprovados, além de Ruff e `git diff --check`. O fluxo de avaliação paga usa o ledger persistente, recusa runtime isolado sem caminho de orçamento, exige amostra real completa e estima as quatro conversas e seus dez turnos.
- A revisão r2 confirmou a separação do ledger e a cobertura das conversas por inspeção. Identificou que um JSON com apenas `estimated_cost_usd` ainda liberava o teto excepcional. A correção começou em r3 isolada enquanto a suíte r2 continuou no SHA fixo. [Parecer T73](../evidence/v080-reviewer-t73.md)
- A suíte estrita de `9deca61` terminou em código 1, com 1.027 testes aprovados e quatro falhas. Três testes detectaram que a recusa por configuração de orçamento mascarava o erro existente de juiz inválido ou sem chave. A outra falha foi a expectativa de app `0.7.0` em `/ready`, que retornou `0.8.0` e schema 11. Ruff e skills passaram. O diagnóstico foi encaminhado ao Developer da r3.
- **12h36 a 13h59 — interrupção e retomada.** O Developer atingiu o limite de uso do Luna após salvar a correção r3 e antes do pacote focado. Na retomada solicitada pelo responsável, a branch isolada continuava em `9deca61`, com cinco arquivos modificados. O Supervisor conferiu o diff e iniciou a validação com hashes fixados.
- A validação focada da r3 passou com 49 testes em 117,52 s, Ruff limpo e hashes estáveis. O Supervisor fixou os cinco arquivos em `9057aaa`. O pacote incluiu as três recusas de juiz e a prontidão que falharam na suíte r2.
- Na primeira revisão r3, uma busca ampla exibiu duas linhas do arquivo de holdout da v0.8.0. O Supervisor interrompeu a passagem e descartou-a para aceite. Os conteúdos não foram propagados ao Developer ou usados na correção. A nova revisão recebeu apenas código, testes e fontes normativas de `9057aaa` com hashes, em pacote isolado sem o arquivo de holdout. O incidente fica registrado separadamente da integridade do lacre.
- A revisão nova da T73 r3 deu parecer apto para `9057aaa`. Conferiu os 105 hashes do pacote e validou por inspeção a prova para o teto excepcional e a ordem de recusas. [Parecer T73](../evidence/v080-reviewer-t73.md)
- A suíte estrita de `9057aaa` terminou em código 0, com 1.031 testes aprovados em 16 min 07 s, Ruff e skills válidas. A T73 foi integrada por fast-forward em `codex/v0.8.0-replan`. O manifesto registra 86 hashes, e o lacre foi reconferido. [Candidato v0.8.0-local-r1](../evidence/v080-candidato-r1.json)
- O QA independente conferiu o candidato e executou a preparação e a amostra real. O primeiro bootstrap ficou incompleto sem diagnóstico recuperável. Uma sonda programada passou e um único retry real sob a guarda primária criou o índice com 145 trechos de 40 documentos. A amostra completou cinco casos e cinco juízos independentes. [Parecer do QA](../evidence/v080-qa-r1.md)
- Preflight às 09h09, horário de São Paulo. Disco `C:` com 10,49 GiB livres, RAM física com 0,77 GiB livres, folga virtual de 14,21 GiB incluindo paginação e zero alertas recentes. `checar-memoria.ps1` liberou um agente pesado. A sondagem de hardlink no sandbox padrão retornou `WinError 5`.
- A medição por agente do Codex foi confirmada nos registros locais. O modelo observado nos dois primeiros despachos é `gpt-6-luna/xhigh`, conforme o ensaio autorizado para esta retomada. A sessão principal usa `gpt-6.1-sol/xhigh` e fica separada dos números dos subagentes.

## Doing

| Tarefa | Papel | Candidato ou base | Situação |
| --- | --- | --- | --- |
| QA técnico | QA independente | `9057aaa` | **Bloqueado pelo orçamento.** Projeção de US$1,37116382 e saldo primário de US$0,45749509. A campanha continua sem cap montado. |

O responsável aprovou a estratégia de QA e demonstração até a v1.0.0, com reserva de planejamento de US$2,50 e autorização de até US$0,10 adicionais para completar a amostra `dev`. A campanha segue aguardando uma projeção válida dentro dos limites vigentes. [Decisão compartilhada](../specs/evolucao-pos-feedback-plano.md#decisão-aprovada-em-2026-11-04)

## To do

1. Complementar a amostra `dev` dentro dos US$0,10 autorizados e confirmar uma projeção que caiba simultaneamente no teto aprovado e no saldo primário.
2. Concluir a campanha técnica, o smoke Docker e o holdout no último passo técnico. Entregar o CSV de calibração.
3. Consolidar a comparação somente após o QA finalizar. Contar a implementação, cada revisão, os retornos por falha, as correções e as revalidações, com modelo e esforço por passagem. Usar a comparação histórica de [Sonnet e Opus](2026-11-03-noite-retomada.md) como referência por papel.

## Recursos e medição

| Hora local | Disco `C:` livre | RAM física livre | Observação |
| --- | ---: | ---: | --- |
| 09h09 | 10,49 GiB | 0,77 GiB | Folga virtual de 14,21 GiB com crescimento de paginação. |
| 09h18 | 10,48 GiB | 0,76 GiB | 10,61 GiB de memória virtual livre, sem somar crescimento futuro. |
| 09h27 | 10,42 GiB | 1,33 GiB | Folga virtual de 15,47 GiB com crescimento de paginação e zero alertas recentes. |
| 09h47 | 10,45 GiB | 0,82 GiB | Folga virtual de 15,15 GiB com crescimento de paginação e zero alertas recentes. |
| 09h57 | 10,44 GiB | 1,21 GiB | Checagem liberou a suíte integrada. |
| 10h08 | 10,18 GiB | 1,00 GiB | Suíte integrada ativa, sem alertas de memória. |
| 10h15 | 10,07 GiB | — | Suíte integrada encerrada. |
| Após a suíte | 10,43 GiB | — | Removido somente o diretório temporário criado para a suíte integrada, com 365,48 MiB de arquivos. |
| 10h24 | 10,43 GiB | 1,69 GiB | Sem alertas recentes. |
| 10h44 | 10,41 GiB | 1,57 GiB | Sem alertas recentes. |
| 11h01 | 10,36 GiB | 1,45 GiB | Sem alertas recentes. |
| 11h19 | 10,34 GiB | 1,05 GiB | Sem alertas recentes. |
| 11h32 | 10,31 GiB | 0,75 GiB | Folga virtual de 14,58 GiB e zero alertas recentes. |
| 11h46 | 10,30 GiB | 0,70 GiB | No limiar de RAM, sem alertas. |
| 11h56 | 10,30 GiB | 1,48 GiB | Nova checagem liberou o pacote focado da T73 r2. |
| 12h08 | 10,29 GiB | 0,95 GiB | Checagem liberou a suíte estrita da T73 r2. |
| Após a suíte r2 | 10,27 GiB | — | Removido somente o diretório temporário da suíte r2, com 369,68 MiB de arquivos. |
| 12h26 | 10,27 GiB | 1,51 GiB | Sem alertas, preflight liberou os focados da T73 r3. |
| 13h59 | 10,24 GiB | 0,73 GiB | Folga virtual de 11,15 GiB, sem alertas. Um agente pesado liberado na retomada. |
| 14h03 | 9,64 GiB | 0,82 GiB | Folga virtual de 10,93 GiB, sem alertas. Liberada a suíte estrita r3. |
| Fim da suíte r3 | 9,20 GiB | — | 1.031 testes aprovados. |
| Após a suíte r3 | 9,57 GiB | — | Removidos somente os basetemps próprios dos testes focados e da suíte estrita, com 390,54 MiB de arquivos. |
| 14h23 | 9,58 GiB | 0,51 GiB | Adiada a carga pesada do QA pelo limiar de RAM. |
| 14h24 | 9,56 GiB | 1,57 GiB | Nova checagem liberou o QA como única carga pesada. |
| Após a amostra | 9,55 GiB | — | QA parou pelo orçamento. Runtime e evidências preservados. |

O Supervisor confere os agentes e os recursos no ciclo de 20 minutos e antes de despachar trabalho pesado. Nesta retomada, as primeiras passagens usam testes focados. A estimativa de custo usa entrada sem cache, entrada em cache e saída por subagente, com a tarifa Standard publicada pela OpenAI. Os valores são equivalentes de API. [Tarifas da API](https://developers.openai.com/api/docs/pricing)

| Tarefa | Papel e rodada | Modelo | Minutos registrados | US$ equiv. | Resultado |
| --- | --- | --- | ---: | ---: | --- |
| T72b | Developer r3 | `gpt-6-luna/xhigh` | 19,29 | 0,06831 | 94 testes focados passaram após ajuste e execução com permissão para hardlinks. |
| T71 | Reviewer r2 | `gpt-6-luna/xhigh` | 15,00 | 0,04591 | Apta, 79 testes focados. |
| T72b | Reviewer r3 | `gpt-6-luna/xhigh` | 13,58 | 0,03101 | Um P2 reproduzido. |
| T72b | Developer r4 | `gpt-6-luna/xhigh` | 3,77 | 0,02197 | 46 testes focados. |
| T72b | Reviewer r4 | `gpt-6-luna/xhigh` | 5,60 | 0,01849 | Apta, 25 testes focados. |
| T73 | Developer r1 | `gpt-6-luna/xhigh` | 66,99 | 0,24412 | Implementação, preparação e validações focadas com repetições. |
| T73 | Reviewer r1 | `gpt-6-luna/xhigh` | 20,57 | 0,05841 | 31 testes focados e três achados reproduzidos. |
| T73 | Developer r2 | `gpt-6-luna/xhigh` | 38,22 | 0,15836 | Corrigiu os três achados e validou com pacote focado. |
| T73 | Reviewer r2 | `gpt-6-luna/xhigh` | 7,70 | 0,03490 | Correções necessárias na validação do teto excepcional. |
| T73 | Developer r3 | `gpt-6-luna/xhigh` | 22,91 | 0,06621 | Correção em disco. A passagem terminou pelo limite de uso antes dos testes focados. |
| T73 | Reviewer r3, primeira passagem | `gpt-6-luna/xhigh` | 5,30 | 0,02143 | Passagem interrompida por exposição acidental de duas linhas do holdout. |
| T73 | Reviewer r3, novo contexto | `gpt-6-luna/xhigh` | 6,31 | 0,03066 | Apta com pacote verificado, sem acesso ao holdout. |
| QA v0.8.0 | QA, primeira passagem | `gpt-6-luna/xhigh` | 11,82 | 0,06344 | Preflight e bootstrap inicial sem diagnóstico recuperável. |
| QA v0.8.0 | QA, retomada | `gpt-6-luna/xhigh` | 7,09 | 0,02800 | Diagnóstico, retry, amostra e parada por orçamento. |

Subtotal operacional desta retomada de **244,15 minutos de subagente** e **US$0,89122 equivalentes de API**. Inclui a revisão interrompida e as rodadas de correção, além das duas passagens de QA até o bloqueio. Tempo da sessão principal, suíte do Supervisor, campanha e passagem exploratória ficam separados.

O Supervisor iniciou cedo uma rodada exploratória isolada sobre T72b r1 (`c861bee`). Consumiu 8,10 min e US$0,02795 equivalentes. A rodada fica fora da comparação do ciclo e seu custo fica separado. Por orientação do responsável, o benchmark será consolidado após o QA. Até lá, a sessão apenas coleta a telemetria das passagens operacionais.

Inicialmente a T73 ficou limitada à preparação enquanto a suíte integrada rodava no checkout principal. O responsável pediu execução paralela. A T73 passou para worktree próprio a partir do mesmo SHA, mantendo o checkout principal fixo para concluir a suíte. Validações pesadas continuam serializadas.

Preparação e amostra reais desta retomada contabilizaram **US$0,02998644** no ledger primário, incluindo a reserva conservadora do primeiro bootstrap. A campanha `v080-qa` permanece sem montagem. O plano permite US$0,50 ou até US$1,00 em uma única montagem se a estimativa justificar. [Evidência de orçamento](../evidence/v080-qa-r1.md)

## Estado para retomar

| Repositório ou worktree | Branch ou estado | HEAD | Situação no preflight |
| --- | --- | --- | --- |
| Backend principal | `codex/v0.8.0-replan` | Commit deste relatório, após `26c3bd0` | Só documentação desde o início do QA. O produto continua fixado em `9057aaa`. `Claude outputs/` e `_tmp/` preservados. Consulte o plano de orçamento na branch `codex/v0.8.0-replan` também ao retomar de outro worktree. |
| Backend estável | `main` | `bd0920a` | v0.7.0 integrada localmente. |
| `time-b` | `codex/v0.8.0-avaliacao` | `af16869` | Limpo. |
| `time-b-v070` | `codex/v0.7.0-ticketing` | `2226d4c` | Limpo. |
| `review-a` | Destacado | `af16869` | Limpo. |
| `review-a2` | Destacado | `10171c1` | Limpo. |
| `review-web` | Destacado | `cd7d55d` | Limpo. |
| Worktree T73 | `codex/v0.8.0-t73` | `60ef1eb` | Candidato da rodada 1 preservado em `C:\Users\lauro\.codex\visualizations\2026\11\04\01a1a657-5761-7791-b964-8673f2b618b9\v080-t73-worktree`. |
| Worktree T73 r2 | `codex/v0.8.0-t73-r2` | `9deca61` | Candidato e resultado da suíte r2 preservados em `C:\Users\lauro\.codex\visualizations\2026\11\04\01a1a657-5761-7791-b964-8673f2b618b9\v080-t73-r2-worktree`. |
| Worktree T73 r3 | `codex/v0.8.0-t73-r3` | `9057aaa` | Parecer apto e suíte verde. Preservado em `C:\Users\lauro\.codex\visualizations\2026\11\04\01a1a657-5761-7791-b964-8673f2b618b9\v080-t73-r3-worktree`. |
| Web principal | `main` | `0a8e12f` | Limpo. |
| `_tmp/qa-pr7-20261028` | `codex/qa-pr7-20261028` | `16a06f6` | Registro Git órfão preexistente, preservado. |

## Falta

As tarefas e a ordem estão na seção To do.

## Depende de você

- Decidir sobre revisão dos tetos ou recorte apenas se a projeção revisada ultrapassar os limites vigentes.
- Após o QA técnico, preencher o CSV de calibração antes da integração na `main`.
