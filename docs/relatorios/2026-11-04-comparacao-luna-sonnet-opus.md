# Comparação de Luna, Sonnet e Opus — 04/11/2026

A comparação usa o trabalho registrado no case Getnet até a meia-noite de 04/11 em São Paulo. A v0.8.0 ainda estava em QA. Os números descrevem as passagens já realizadas, incluindo correções e passagens interrompidas. A sessão principal, o piloto de T72b e as chamadas da aplicação têm registros separados.

## Tempo e custo por papel

| Modelo e recorte | Papel | Passagens | Minutos somados | Minutos por passagem | US$ equivalentes | US$ por passagem |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Luna `gpt-6-luna/xhigh`, retomada v0.8.0 | Developer | 12 | 209,19 | 17,43 | 0,93167 | 0,07764 |
| Luna `gpt-6-luna/xhigh`, retomada v0.8.0 | Reviewer | 13 | 89,58 | 6,89 | 0,31559 | 0,02428 |
| Luna `gpt-6-luna/xhigh`, retomada v0.8.0 | QA | 8 | 157,16 | 19,64 | 0,74310 | 0,09289 |
| Sonnet/xhigh, abertura v0.8.0 | Developer | 8 | 346,4 | 43,30 | 62,51 | 7,81 |
| Sonnet/xhigh, abertura v0.8.0 | Reviewer | 7 | 254,1 | 36,30 | 25,47 | 3,64 |
| Sonnet/xhigh, fechamento v0.7.0 | Developer | 7 | 137,1 | 19,59 | 26,95 | 3,85 |
| Sonnet/xhigh, fechamento v0.7.0 | Reviewer | 8 | 277,6 | 34,70 | 25,40 | 3,18 |
| Sonnet/xhigh, fechamento v0.7.0 | QA | 1 | 54,6 | 54,60 | 17,30 | 17,30 |
| Opus/high, tarde de 03/11 | Developer | 23 | 321 | 13,96 | 91,77 | 3,99 |
| Opus/high, tarde de 03/11 | Reviewer | 19 | 230 | 12,11 | 45,07 | 2,37 |

Os tempos do Luna somam o intervalo entre os eventos de início e fim de cada passagem Codex, incluindo esperas por ferramentas, sem ociosidade entre passagens. Uma passagem de Developer atravessou meia-noite e entra apenas até o corte. As fontes históricas chamam seus intervalos de minutos ativos e contam rodadas conforme o registro Claude. A soma de agentes em paralelo pode exceder o tempo de relógio da sessão. [Retomada Codex](2026-11-04-retomada-codex.md) · [Sonnet v0.8.0](2026-11-04-manha.md) · [Sonnet e Opus v0.7.0](2026-11-03-noite-retomada.md)

## O que os resultados sustentam

- **Desenvolvimento.** O Luna registrou US$0,00445 equivalentes por minuto, ante US$0,18045 do Sonnet na abertura da v0.8.0 e US$0,28589 do Opus na tarde de 03/11. Levou menos tempo por passagem que o Sonnet na abertura. O Opus ficou abaixo do Luna em minutos por rodada no histórico, que pertence a outra versão e inclui rodadas menores. Na T72b, o Luna entrou para corrigir e revisar uma entrega que o Sonnet já havia implementado. A T73 envolveu trabalho novo e várias revalidações.
- **Revisão.** O Luna registrou 6,89 minutos por passagem. Encontrou defeitos de rótulo, prova de orçamento e reabertura da campanha. Houve uma revisão descartada após exposição de duas linhas do holdout e um retorno por limite de uso. O histórico Sonnet v0.7.0 fez sondas executadas em contexto frio e reproduziu P2 em seis de oito revisões. O histórico Opus reutilizou contexto em parte das rodadas.
- **QA.** A primeira fase real da v0.8.0 levou 24 min 25 s e reprovou em CA-51. O Sonnet fechou a rodada de QA da v0.7.0 em 54,6 minutos de subagente. As oito passagens Luna incluem preparação, espera por execuções, diagnóstico, amostragem, reprovação e desenho do reteste. Falta um QA apto da v0.8.0 para comparar tempo e custo até o aceite. [Parecer da campanha v0.8.0](../evidence/v080-d12-pre-holdout-r3.md)

## Como o custo foi medido

O Luna operacional somou **33 passagens, 455,92 minutos e US$1,99036 equivalentes**. A telemetria registrou 4.213.479 tokens de entrada sem cache, 105.994.240 em cache e 1.018.134 de saída. A estimativa aplica a mesma tarifa Standard registrada na retomada, US$0,10 por milhão de tokens sem cache, US$0,01 em cache e US$0,50 de saída. Os valores históricos de Sonnet e Opus vêm do medidor Claude documentado. São conversões de telemetria em equivalente de API, sem conciliação com fatura. [Histórico de medição](2026-11-04-retomada-codex.md) · [Tarifa registrada](https://developers.openai.com/api/docs/pricing)

O piloto Luna em T72b teve 8,10 minutos e US$0,02795 equivalentes e fica fora do total operacional. O Terra, autorizado no fim da rodada, teve duas passagens de Developer com 12,65 minutos e três de Reviewer com 8,78 minutos até meia-noite. Corrigiu o fallback e o procedimento e apontou dois contraexemplos à rubrica em revisões sucessivas. O custo equivalente do Terra ficou sem cálculo para manter a série histórica separada. Nenhuma passagem do Terra entra na coluna Luna. [Revisão T74](../evidence/v080-reviewer-t74-r2.md)

O gasto efetivo da campanha real foi **US$0,38283761**, separado do custo de desenvolvimento, com OpenAI no agente da aplicação e DeepSeek no juiz. As tarefas, os níveis de esforço, as ferramentas, o contexto e os estados de aceite variam entre as coortes. Um ranking de qualidade exigiria a mesma tarefa, as mesmas ferramentas e o mesmo critério de aceite para os três modelos. [Ledger da campanha](../evidence/v080-d12-pre-holdout-r3.md)
