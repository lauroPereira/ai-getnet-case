# Tarefa 74 — Correção e revalidação do QA pré-holdout da v0.8.0

## Objetivo

Corrigir falhas de resposta e da medição confirmadas na primeira fase do QA real e verificar o candidato corrigido com o saldo da campanha já montada.

## Especificação relacionada

[Orquestração e avaliação v0.8.0](../specs/orquestracao-avaliacao-v080.md), D7, D12, D16, D17, CA-49, CA-50 e CA-51. [Parecer do QA](../evidence/v080-d12-pre-holdout-r3.md).

## Pré-condições

O candidato `f8daab03` tem 132 respostas gravadas em `v080-all-r3.json`. Os 132 IDs existem no banco local de traces. CA-51 ficou em 9/13, 11/13 e 10/13. O ledger de campanha tem US$0,71716239 restantes e o primário tem US$0,75495815 restantes, com zero reservas. O holdout da v0.8.0 permanece fechado.

## Arquivos prováveis

Prompts, testes focados, rótulos de desenvolvimento em `tests/scenarios/business_journeys.jsonl`, coleta da evidência do juiz e evidência de QA. Mudar somente os arquivos exigidos pela reprodução, sem editar o conjunto lacrado, os casos de holdout legado, os contratos ou a guarda de orçamento.

## Passos

1. Conferir cada divergência de conteúdo com a evidência do caso. Aceitar equivalências semânticas específicas apenas quando preservarem a proposição esperada e as recusas de contradições. Manter controles de valores, fontes, ações, rota, status e afirmações proibidas.
2. Reproduzir as falhas de produto. `REPLAN-WEB` respondeu afirmativamente sobre outros modelos sem confirmar o modelo perguntado. `REPLAN-PROCEDURE` omitiu o procedimento oficial recuperado pelo app. `FU01` resolveu o caso por confirmação do lojista, com rota inicial diferente de `acknowledgement`. Tratar sinais de ausência de evidência e autorização recusada pelo mesmo cotejo, sem editar os rótulos de holdout.
3. Incluir no input do juiz o protocolo verificável que a escalada registrada na trace produziu. Preservar os limites da evidência, a máscara e a rubrica. Reter o julgamento anterior no relatório original.
4. Fixar e revisar o candidato corrigido. Verificar offline os casos corrigidos, os controles negativos e a matriz de regressão. Separar mudanças que exigem nova inferência das respostas arquivadas que podem ser reavaliadas sem custo.
5. Recuperar `detail.plan_hops` e os passos `replan` pelo `request_id` em `traces.sqlite3` do runtime de QA. Executar `REPLAN-TOOL-DOWN` em subprocesso com serviço de preços indisponível e verificar a falha esperada e o protocolo de encaminhamento. Para os demais casos, provar a saúde do mock antes do reteste.
6. Projetar o recorte afetado e as fases remanescentes antes de chamadas pagas. Preservar o ledger de campanha e a evidência do candidato anterior. Para reaproveitar respostas antigas, demonstrar que as mudanças não atingem a execução dos casos respectivos e identificar o SHA de cada resposta.
7. Prosseguir às repetições do juiz e ao smoke somente após o pré-holdout apto. O conjunto lacrado permanece o último passo técnico.

## Critérios de conclusão

- As quatro jornadas de replanejamento demonstram o comportamento previsto, origem da decisão e no máximo três saltos.
- As 13 jornadas de negócio são medidas pela mesma rubrica em três repetições e atingem 12/13 ou mais no critério de aceite.
- O roteiro separa as fases de variação do agente e do juiz e conserva o custo e a evidência de cada tentativa.
- O candidato, os hashes, os casos reutilizados e os reexecutados são rastreáveis. Os dois ledgers batem e o cap continua dentro do limite aprovado.

## Validação

[Triagem do QA](../evidence/v080-qa-triagem-r4.md), [traces recuperadas](../evidence/v080-d12-traces-recuperadas-r3.md). Retestes pagos no Claude Code em 2026-11-05: [r4](../evidence/v080-d12-pre-holdout-r4.md) (reprovado; 8 jornadas inválidas por seed de outro dia; tarefas 75 e 76), [r5](../evidence/v080-d12-pre-holdout-r5.md) (CA-49 apto; CA-51 reprovado só por redação; tarefa 78), [r6](../evidence/v080-d12-pre-holdout-r6.md) (apto para o holdout: CA-51 13/12/12, juiz repetido, smoke Docker), [r7](../evidence/v080-holdout-r7.md) (holdout único e CSV). Candidato final `1baa7b3` ([manifesto r11](../evidence/v080-candidato-r11.json)). Custo da revalidação: US$0,48592451 (ledger US$0,45747628 mais US$0,02844823 do volume Docker). Contingência de US$0,30 aplicada ao cap e não consumida.

## Status

Concluída em 2026-11-05: QA técnico e calibração humana importada ([relatório](../evidence/v080-calibracao.md)). Merge local na `main` feito em 2026-11-05 (d3740d0) com autorização do responsável; push e tag `v0.8.0` são dele.
