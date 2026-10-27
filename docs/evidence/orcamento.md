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
