# Projeção de revalidação do QA da v0.8.0

O preflight desta retomada conferiu **US$0,71716239** restantes no cap fixo de US$1,10 e **US$0,75495815** no primário de US$1,70. Ambos sem reservas, com último ID 730 no cap e 2346 no primário.

A [estimativa r3](v080-custo-estimativa-r3.json) reserva US$0,07709880 para as novas avaliações do juiz nos 44 casos pré-holdout e US$0,36062993 para as duas fases do holdout técnico. Isso deixa **US$0,27943366** antes de retestes, smoke e margem. O conjunto lacrado não foi consultado para obter esses valores.

| Recorte hipotético de reteste | Custo observado na r3, com três repetições e quatro conversas | Saldo após as fases reservadas e o reteste |
| --- | ---: | ---: |
| Cinco casos com nó de fallback web e cenário de indisponibilidade | US$0,15421219 | US$0,12522147 |
| Inclui também a rota web direta | US$0,18676818 | US$0,09266548 |
| Inclui também `EX08` e `UC13` | US$0,19653178 | US$0,08290188 |
| Inclui também as 13 jornadas de negócio | US$0,23411308 | US$0,04532058 |
| Repete todos os 44 casos | US$0,38281950 | Déficit de US$0,10338584 |

Os valores são projeções, não autorização de gasto. Usam os custos gravados de agente e juiz por caso e das quatro conversas. O cenário de indisponibilidade rodou com o mock saudável na r3, então seu custo não prova o custo sob falha. O escopo de reteste depende do diff, da revisão de impacto e da saúde do mock. O ledger é a fonte dos gastos realizados.

Uma reavaliação offline de rótulos pode usar respostas arquivadas, com vínculo explícito ao SHA de origem. Uma mudança no comportamento da aplicação exige nova inferência nos fluxos afetados. Um novo bloco pago fica condicionado à margem para terminar a campanha com o cap atual. [Campanha r3](v080-d12-pre-holdout-r3.md) [Tarefa 74](../tasks/74-correcao-qa-pre-holdout-v080.md)
