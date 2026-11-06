# Registro de gasto com APIs pagas

Teto do projeto: US$5,00. Este registro é manual até a guarda de orçamento da aplicação existir (tarefa 08); depois, o registro da aplicação em `data/runtime/` passa a ser a fonte e este arquivo recebe os totais por rodada.

| Data | Atividade | Reserva | Gasto estimado | Acumulado |
| --- | --- | --- | --- | --- |
| 2026-10-26 | Tarefa 02: chamadas mínimas de verificação | Ingestão e calibração (US$0,25) | US$0,0209 | US$0,0209 |
| 2026-10-26 | Tarefa 07: medição de recuperação com embeddings | Ingestão e calibração (US$0,25) | US$0,0007 | US$0,0216 |
| 2026-10-26 | Tarefas 08-12b: índice real, 10 exemplos, reexecuções e diagnóstico | Desenvolvimento (US$1,25) | US$0,0702 | US$0,0918 |
| 2026-10-26 | Tarefa 13: índice e smoke no Docker em ambiente limpo, encaminhamento | Ensaio e demonstração (US$1,00) | US$0,0262 | US$0,1180 |
| 2026-10-26 | Tarefa 14: três rodadas de avaliação (27 casos) com rubrica por modelo | Avaliação e regressão (US$1,50) | US$0,1620 | US$0,2800 |
| 2026-10-26 | Tarefa 13: smoke final no Docker com o código final | Ensaio e demonstração (US$1,00) | US$0,0250 | US$0,3050 |
| 2026-10-26 | v0.2.0: conversas reais de vários turnos (duas rodadas) | Desenvolvimento (US$1,25) | US$0,0064 | US$0,3114 |
| 2026-10-26 | v0.2.0: duas rodadas de regressão real (27 casos + 4 conversas, com rubrica) | Avaliação e regressão (US$1,50) | US$0,1150 | US$0,4264 |
| 2026-10-26 | v0.2.0: Docker em ambiente limpo (índice) e smoke | Ensaio e demonstração (US$1,00) | US$0,0252 | US$0,4516 |
| 2026-10-27 | v0.3.0: primeira rodada real, 40 casos + 4 conversas, índice e rubrica; relatório original preservado | Validação autorizada, teto adicional persistente US$0,15 | US$0,06747249 | US$0,51907249 |
| 2026-10-27 | v0.3.0: stack Compose e rodada HTTP r2, 40 casos + 4 conversas e rubrica; 35/40 e 3/4 originais preservados | Mesma guarda persistente da validação (US$0,15) | US$0,06837644 | US$0,58744893 |
| 2026-10-27 | v0.3.0: revalidação HTTP das quatro conversas com Router 5, 4/4; replay dos 40 casos sem nova API | Mesmo teto persistente de validação (US$0,15) | US$0,00538690 | US$0,59283583 |

Os custos e latências do relatório de replay são históricos da rodada HTTP r2; o reprocessamento determinístico não fez novas chamadas e não soma gasto ao acumulado. Os JSONs do ledger preservam a precisão; o teto adicional da validação permaneceu em US$0,15.

## Transições de teto da v0.8.0

Consolidação dos dois registros de transição da campanha `v080-qa`. Em ambas, entradas, último ID e SHA-256 lógico das entradas dos ledgers ficaram iguais antes e depois, sem reservas abertas e sem processo do projeto ativo; backups e registros de auditoria ficaram locais.

| Aplicada em | Autorização do responsável | Teto primário persistido | Cap fixo `v080-qa` | Comprometido no primário (antes = depois) | Folga depois |
| --- | --- | ---: | ---: | ---: | --- |
| 2026-11-04 19h26 (São Paulo), candidato `f8daab03` | 2026-11-04: transição local do teto primário para US$1,70 e faixa excepcional de até US$1,10 para `v080-qa` | US$1,00 → US$1,70 | até US$1,10 | US$0,55947501 | primário US$1,14052499 |
| 2026-11-05 03h44 (São Paulo), candidato r7 `658c70ad` | 2026-11-05: contingência de até US$0,30 adicionais para `v080-qa`, debitada da linha "Contingência" da reserva | US$1,70 → US$2,00 | US$1,10 → US$1,40 | US$1,14385079 (campanha US$0,58164655) | primário US$0,85614921, campanha US$0,81835345 |

Na segunda transição, a CLI passou a aceitar `--campaign-cap-usd 1.40` só para continuar a campanha montada, com a estimativa revalidada ([v080-custo-estimativa-r3.json](v080-custo-estimativa-r3.json)); `1.10` passou a ser recusado. A contingência não foi consumida: a campanha fechou em US$0,84 (CHANGELOG 0.8.0).
