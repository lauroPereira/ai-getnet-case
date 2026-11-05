# Projeção estratificada da campanha v0.8.0 — r3

Registro de 04/11/2026 às 16h08, horário de São Paulo. Candidato de produto `9057aaac36eddbe309393089115175b6fc98b5bd`, checkout de documentação `c6a382407791616a54a4604cbaa2069ad907326f`.

## Decisão

A campanha completa ficou bloqueada pelo saldo primário de **US$ 0,44052499**. A projeção estratificada deu **US$ 0,77451472** no caso-base e **US$ 1,00102584** no cenário de estresse. O QA parou antes de montar `v080-qa` e deixou a repetição dos dois casos de preço para a próxima rodada.

O estimador existente calculou **US$ 1,00929931** sobre o relatório combinado de 11 casos distintos, acima do teto excepcional. Uma checagem offline do Supervisor projetou **US$ 0,63243** com zero casos de busca web no holdout lacrado. Com dois ou cinco casos de busca web, a projeção sobe para **US$ 0,68941** ou **US$ 0,77487**, respectivamente. Todas as estimativas excedem o saldo primário.

## Premissas e composição

O escopo publicado tem 69 casos, distribuídos em 27 de dev, 17 de holdout legado e 25 de `holdout_v080`, além de 10 turnos em quatro conversas. A fórmula aplica três execuções do agente e seis chamadas ao juiz por caso. Os turnos de conversa rodam uma vez, sem juiz.

A mistura ordinária vem somente dos 23 casos dev não classificados como replanejamento: 2 `general_web`, 5 `knowledge`, 3 mistos, 12 de suporte e 1 handoff. Atribuí rotas ambíguas ao estrato medido de maior custo. Para os 42 casos sem amostra, apliquei a frequência observada de replanejamento em dev (4/27), resultando em 10,22 casos esperados de replanejamento no total. O cenário de estresse multiplica por 1,5 o custo variável de tokens e o custo do juiz; a tarifa fixa de web permanece em US$ 0,01 por busca.

| Fase / provedor | Caso-base | Estresse | Observação |
|---|---:|---:|---|
| Agente OpenAI, incluindo busca web | US$ 0,474753 | — | Três execuções por caso |
| Juiz DeepSeek | US$ 0,276815 | US$ 0,415223 | Seis julgamentos por caso |
| Turnos de conversa, agente OpenAI | US$ 0,022935 | incluído na margem variável | Dez turnos, sem juiz |
| Embeddings | US$ 0,000011 | US$ 0,000011 | Projeção pelo custo observado |
| **Total** | **US$ 0,774515** | **US$ 1,001026** | A parcela fixa web de US$ 0,321481 já está incluída nos custos OpenAI acima |

Esses valores extrapolam dados de dev para os dois splits sem medição. A projeção-base ultrapassa o saldo primário em US$ 0,333990. A menor estimativa do Supervisor excede esse saldo em US$ 0,191905.

## Ambiente e achados

O ledger primário `data/runtime/budget.sqlite3` terminou no ID 1605, com gasto de **US$ 0,55947501**, zero reservas abertas e limite persistido de US$ 1,00. A folga fixa restante no teto do processo de amostra (US$ 0,64250491) é **US$ 0,08302990**. Nenhuma chamada foi feita durante esta projeção.

O processo oculto PID 22680 encerrou sem stdout ou stderr, e `GET /openapi.json` falhou. As jornadas `V030-PRICE-DIVERGENCE` e `V030-PT-PRICE-INSUFFICIENT` receberam `UNAVAILABLE` de `simulate_pricing`. O serviço auxiliar indisponível impediu validar esses dois casos. `V030-CONTRACT-TERMINATION` retornou `clarify/needs_clarification` sem erro de dependência em uma única execução. A próxima rodada deve verificar esse resultado com o ambiente preparado.

O holdout segue lacrado. A projeção usou a contagem e o SHA-256 publicados no manifesto. A campanha, o smoke Docker e o CSV de calibração continuam pendentes.

## Evidência detalhada

O JSON ao lado registra as contagens, fórmulas, premissas, valores por fase, estado do ledger, resultado do preflight e decisão sem transcrições ou segredos.
