# Relatório de avaliação: v030-real-http-r2-replay

Gerado em 2026-10-27T06:14:53+00:00. Configuração: `{"mode": "deterministic_replay", "candidate": "v0.3.0-local-r6", "source_fingerprint_sha256": "f8efcec3918320c287b3b6c2faef2f38edca4847a02b19bcd781ed7e920a1af9", "original_report": "v030-real-http-r2.json", "original_report_sha256": "5b9a0f77183d6a8376263c06324c0480eb6189893fe18129055a2a1d76e3a793", "new_api_calls": 0, "new_api_cost_usd": 0, "original_case_dataset_sha256": "eb4674308a1657778f5c9ef15686bf408e5af2908a2e4487f34fcfbfe743601f", "current_case_dataset_sha256": "a32e468a065173eb8aca354f0f9cb118e2dc6003d7dbe90c2b2f985bb2859b62", "scoring_code_sha256": "b17952c593fc610402d9e2727f9325f8bcc4d72c0e5d64d149b2ef38f2c673ab", "historical_latency_cost_and_judge_preserved": true, "changed_outcomes": [{"id": "V030-PRICE-CONDITIONS", "before": false, "after": true, "checks_changed": ["content_ok"]}, {"id": "V030-PRICE-DIVERGENCE", "before": false, "after": true, "checks_changed": ["content_ok"]}, {"id": "V030-PRICE-INSUFFICIENT", "before": false, "after": true, "checks_changed": ["content_ok"]}, {"id": "V030-PT-PRICE-INSUFFICIENT", "before": false, "after": true, "checks_changed": ["content_ok", "forbidden_ok"]}, {"id": "V030-PT-SALE-CANCELLATION", "before": false, "after": true, "checks_changed": ["content_ok"]}]}`.

## Resumo

| Recorte | n | Aprovados | Rota | Status | Ferramentas | Valores | Conteúdo | Fontes | Sem violação | p50 (ms) | p95 (ms) | Custo (US$) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geral | 40 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 7530 | 14899 | 0.05995 |
| split dev | 23 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 7785 | 12452 | 0.03157 |
| split holdout | 17 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 6407 | 14899 | 0.02838 |
| idioma en | 21 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 7785 | 12452 | 0.03011 |
| idioma pt | 19 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 6934 | 14899 | 0.02983 |

Rubrica por modelo (média 1-5, não é revisão humana): responde à pergunta 4.38, clareza e tom 4.67, honestidade 4.5.

## Casos

| Caso | Split | Rota | Status | Aprovado | Falhas | ms | US$ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EX01 | dev | knowledge | answered | sim | - | 11960 | 0.000758 |
| EX02 | dev | general_web | answered | sim | - | 6498 | 0.01071871 |
| EX03 | dev | support | answered | sim | - | 10555 | 0.00066013 |
| EX04 | dev | knowledge | answered | sim | - | 8225 | 0.00041961 |
| EX05 | dev | knowledge_and_support | answered | sim | - | 12452 | 0.0008159 |
| EX06 | dev | knowledge | answered | sim | - | 7890 | 0.00049411 |
| EX07 | dev | general_web | answered | sim | - | 7579 | 0.01063984 |
| EX08 | dev | knowledge_and_support | answered | sim | - | 16871 | 0.00100212 |
| EX09 | dev | knowledge | answered | sim | - | 6520 | 0.00037381 |
| EX10 | dev | knowledge | answered | sim | - | 4767 | 0.00037341 |
| PT01 | holdout | knowledge | answered | sim | - | 6934 | 0.00054951 |
| PT02 | holdout | general_web | answered | sim | - | 5756 | 0.01073471 |
| PT03 | holdout | support | answered | sim | - | 8944 | 0.00066953 |
| PT04 | holdout | knowledge | answered | sim | - | 6407 | 0.00042281 |
| PT05 | holdout | knowledge_and_support | answered | sim | - | 14899 | 0.00099448 |
| PT06 | holdout | knowledge | answered | sim | - | 8195 | 0.00053911 |
| PT07 | holdout | general_web | answered | sim | - | 6560 | 0.01066465 |
| PT08 | holdout | knowledge_and_support | answered | sim | - | 18146 | 0.00106236 |
| PT09 | holdout | knowledge | answered | sim | - | 4754 | 0.00038031 |
| PT10 | holdout | knowledge | answered | sim | - | 5643 | 0.00038791 |
| UC12 | holdout | out_of_scope | refused | sim | - | 2766 | 0.00012271 |
| UC13 | holdout | support | answered | sim | - | 11012 | 0.00074762 |
| UC14 | holdout | human_handoff | handoff | sim | - | 7057 | 0.00030601 |
| UC16 | holdout | out_of_scope | refused | sim | - | 1271 | 7.93e-05 |
| UC17 | holdout | support | answered | sim | - | 2862 | 0.00013175 |
| UC18 | holdout | clarify | needs_clarification | sim | - | 2812 | 0.00011061 |
| NOEV | holdout | knowledge | answered | sim | - | 6054 | 0.00047551 |
| V030-PRICE-CONSISTENT | dev | support | answered | sim | - | 7785 | 0.00054158 |
| V030-PRICE-CONDITIONS | dev | support | answered | sim | - | 7948 | 0.00036825 |
| V030-PRICE-DIVERGENCE | dev | support | handoff | sim | - | 11365 | 0.00057725 |
| V030-PRICE-INSUFFICIENT | dev | support | answered | sim | - | 9084 | 0.00030168 |
| V030-ENABLEMENT-PENDING | dev | support | answered | sim | - | 7641 | 0.0004485 |
| V030-SALE-CANCELLATION | dev | support | answered | sim | - | 7075 | 0.00024146 |
| V030-CONTRACT-TERMINATION | dev | human_handoff | handoff | sim | - | 6165 | 0.00029821 |
| V030-PT-PRICE-CONSISTENT | dev | support | answered | sim | - | 7481 | 0.00053512 |
| V030-PT-PRICE-CONDITIONS | dev | support | answered | sim | - | 8825 | 0.00043859 |
| V030-PT-PRICE-DIVERGENCE | dev | support | handoff | sim | - | 11454 | 0.00057657 |
| V030-PT-PRICE-INSUFFICIENT | dev | support | answered | sim | - | 7710 | 0.00051114 |
| V030-PT-ENABLEMENT-PENDING | dev | support | answered | sim | - | 6811 | 0.00025068 |
| V030-PT-SALE-CANCELLATION | dev | support | answered | sim | - | 6877 | 0.00022528 |

## Proveniência

Reprocessamento determinístico das respostas HTTP originais, sem novas chamadas ou gasto de API. Valores, rotas, status, fontes e violações foram preservados e reconferidos. Somente equivalência de conteúdo e afirmações proibidas dos cenários dev foram reavaliadas. Custos, latências e notas do juiz pertencem à execução original. A continuidade das conversas é revalidada em relatório separado.
