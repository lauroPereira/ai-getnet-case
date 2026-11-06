# Evidências

Resultados de validação do projeto, por versão: resultado consolidado, QA final, pareceres finais de revisão, manifestos de candidato (`*-candidato-r*.json`), relatórios das execuções reais, calibração humana do juiz, holdouts e retrieval. Cada relatório diz versão, método, comandos, resultados observados e o nível da verificação (automatizada ou manual). Os dados são sintéticos e não contêm segredos. Novas evidências seguem os modelos em [docs/templates](../templates/candidato.md).

O gasto com APIs pagas e as transições de teto estão em [orcamento.md](orcamento.md). Na tarefa 105 os registros mantidos receberam ajuste de links e de vocabulário, e os registros de processo saíram do repositório; os originais estão nas tags de cada versão.

## v0.1.0 e v0.2.0 (núcleo, conversas e acompanhamento)

| Arquivo | Conteúdo |
| --- | --- |
| [2026-10-26-verificacao-de-fontes.md](2026-10-26-verificacao-de-fontes.md) | Fontes oficiais verificadas e imagem do enunciado |
| [2026-10-26-acesso-e-precos-dos-modelos.md](2026-10-26-acesso-e-precos-dos-modelos.md) | Acesso e preços dos modelos |
| [2026-10-26-pipeline-rag.md](2026-10-26-pipeline-rag.md), [2026-10-26-recuperacao-k6.json](2026-10-26-recuperacao-k6.json) | Ingestão RAG e recuperação com k=6 |
| [2026-10-26-execucao-real-desenvolvimento.md](2026-10-26-execucao-real-desenvolvimento.md) | Primeira execução real dos 10 exemplos |
| [2026-10-26-avaliacao-nucleo.md](2026-10-26-avaliacao-nucleo.md) ([JSON](2026-10-26-avaliacao-nucleo.json)), [2026-10-26-avaliacao-analise.md](2026-10-26-avaliacao-analise.md) | Avaliação do núcleo (27 casos, três rodadas) e análise |
| [2026-10-26-v020-memoria-e-acompanhamento.md](2026-10-26-v020-memoria-e-acompanhamento.md) | Memória, estado do caso e acompanhamento técnico |
| [2026-10-26-regressao-v020.md](2026-10-26-regressao-v020.md) ([JSON](2026-10-26-regressao-v020.json)) | Regressão real da v0.2.0 |

## v0.3.0 (jornadas somente leitura)

| Arquivo | Conteúdo |
| --- | --- |
| [v030-resultado.md](v030-resultado.md) | Resultado consolidado |
| [v030-qa-r6.md](v030-qa-r6.md) | QA final |
| [v030-reviewer-r6.md](v030-reviewer-r6.md) | Parecer final de revisão |
| [v030-release.md](v030-release.md) ([JSON](v030-release.json)), `v030-candidato-r*.json` | Candidato de release e manifestos |
| [v030-real-http-r2.md](v030-real-http-r2.md), [v030-real-http-r2-replay.md](v030-real-http-r2-replay.md), [v030-real-conversations-r3.md](v030-real-conversations-r3.md), [v030-real-budget-r3.json](v030-real-budget-r3.json), [v030-ready-r6.json](v030-ready-r6.json) | Execuções reais pela API, conversas e orçamento |
| [2026-10-27-avaliacao-programada-v030-final.md](2026-10-27-avaliacao-programada-v030-final.md) | Avaliação programada final |

## v0.4.0 (perfis, `/v1` e interface)

| Arquivo | Conteúdo |
| --- | --- |
| [v040-resultado.md](v040-resultado.md) | Resultado consolidado |
| [v040-qa-r6.md](v040-qa-r6.md) | QA final |
| [v040-reviewer-r6.md](v040-reviewer-r6.md) | Parecer final de revisão |
| [v040-catalogo-fontes.md](v040-catalogo-fontes.md), [v040-parametros-modelo-fontes.md](v040-parametros-modelo-fontes.md), [v040-metadados-publicos.json](v040-metadados-publicos.json) | Catálogo de modelos e parâmetros, verificados nas fontes oficiais |
| `v040-candidato-r*.json`, [v040-verificacao-final-r6.json](v040-verificacao-final-r6.json), [v040-docker-r6.json](v040-docker-r6.json) | Manifestos, verificação final e Docker |

## v0.5.0 (base de conhecimento versionada)

| Arquivo | Conteúdo |
| --- | --- |
| [v050-resultado.md](v050-resultado.md) | Resultado consolidado |
| [v050-qa-r3.md](v050-qa-r3.md) | QA final |
| [v050-reviewer-r2.md](v050-reviewer-r2.md), [v050-reviewer-ui-r3.md](v050-reviewer-ui-r3.md) | Pareceres finais de revisão (backend e interface) |
| `v050-candidato-r*.json`, [v050-docker-r7.json](v050-docker-r7.json) | Manifestos e Docker |

## v0.6.0 (atendimento, resultados e administração)

| Arquivo | Conteúdo |
| --- | --- |
| [v060-resultado.md](v060-resultado.md) | Resultado consolidado |
| [v060-qa.md](v060-qa.md) | QA real, com o parecer final da rodada 2 |
| [v060-reviewer.md](v060-reviewer.md) | Revisão independente, até o parecer apto |
| `v060-candidato-r*.json` | Manifestos |

## v0.7.0 (identidade e humano no circuito)

| Arquivo | Conteúdo |
| --- | --- |
| [v070-resultado.md](v070-resultado.md) | Resultado consolidado |
| [v070-qa.md](v070-qa.md), [v070-qa-historia.md](v070-qa-historia.md) | QA final e evidência da história, momento a momento |
| [v070-qa-regressao-real.md](v070-qa-regressao-real.md) ([JSON](v070-qa-regressao-real.json)), [v070-qa-regressao-repeticao.json](v070-qa-regressao-repeticao.json) | Regressão real |
| [v070-reviewer.md](v070-reviewer.md), [v070-reviewer-time-b.md](v070-reviewer-time-b.md), [v070-reviewer-t66-r5.md](v070-reviewer-t66-r5.md), [v070-reviewer-t68.md](v070-reviewer-t68.md) | Pareceres finais de revisão |
| [v070-candidato-r1.json](v070-candidato-r1.json) | Manifesto |

## v0.8.0 (replanejamento, juiz independente e calibração)

| Arquivo | Conteúdo |
| --- | --- |
| [v080-all-r3.md](v080-all-r3.md) ([JSON](v080-all-r3.json)) | Campanha: 44 casos, jornadas e conversas, três execuções |
| [v080-d12-pre-holdout-r6.md](v080-d12-pre-holdout-r6.md) | QA final pré-holdout; dados em [v080-healthy-r6.md](v080-healthy-r6.md), [v080-healthy-r5.md](v080-healthy-r5.md), [v080-healthy-r4.md](v080-healthy-r4.md), [v080-conversations-r4.md](v080-conversations-r4.md), [v080-tool-down-r5.md](v080-tool-down-r5.md) e [v080-smoke-r6.json](v080-smoke-r6.json) |
| [v080-judge-repeat-r6.md](v080-judge-repeat-r6.md) | Variação do juiz |
| [v080-custo-estimativa-r3.json](v080-custo-estimativa-r3.json) | Estimativa revalidada que sustentou o cap da campanha `v080-qa` |
| [v080-holdout-r7.md](v080-holdout-r7.md), [v080-avaliacao-holdout-r7.md](v080-avaliacao-holdout-r7.md), [v080-avaliacao-holdout-judge-repeat-r7.md](v080-avaliacao-holdout-judge-repeat-r7.md), [v080-holdout-derivacao.md](v080-holdout-derivacao.md) | Holdout `holdout_v080`, executado uma vez, e sua derivação |
| [v080-calibracao.md](v080-calibracao.md), [v080-calibracao-amostra.csv](v080-calibracao-amostra.csv), [v080-calibracao-evidencia.md](v080-calibracao-evidencia.md), [v080-calibracao-modelo.md](v080-calibracao-modelo.md) | Calibração humana do juiz (24 respostas) |
| [v080-reviewer.md](v080-reviewer.md), `v080-reviewer-t*.md`, [v080-reviewer-cap-r2.md](v080-reviewer-cap-r2.md) | Pareceres finais de revisão |
| `v080-candidato-r*.json` | Manifestos |

## v0.9.0 (retrieval híbrido e experimento do juiz)

| Arquivo | Conteúdo |
| --- | --- |
| [v090-retrieval.md](v090-retrieval.md) ([JSON](v090-retrieval.json)) | Retrieval por modo no dev e no holdout `retrieval_holdout_v090` |
| [v090-juiz-opus.md](v090-juiz-opus.md), [v090-juiz-opus-r3.md](v090-juiz-opus-r3.md) | Calibração com dois juízes |
| [v090-qa-retrieval-r1.md](v090-qa-retrieval-r1.md), [v090-qa-hybrid-r1.md](v090-qa-hybrid-r1.md), [v090-qa-juiz-r2.md](v090-qa-juiz-r2.md) | QA final |
| [v090-reviewer-t79.md](v090-reviewer-t79.md), [v090-reviewer-t80.md](v090-reviewer-t80.md), [v090-reviewer-t81.md](v090-reviewer-t81.md) | Pareceres finais de revisão |
| `v090-candidato-r*.json` | Manifestos |

## v0.10.0 (rubrica `judge.v4`, comparação retomável e métricas)

| Arquivo | Conteúdo |
| --- | --- |
| [v0100-juiz-v4.md](v0100-juiz-v4.md), [v0100-juiz-deepseek-v4.md](v0100-juiz-deepseek-v4.md), [v0100-juiz-opus-v4.md](v0100-juiz-opus-v4.md) | `judge.v4` contra a calibração humana, com os dois juízes |
| [v0100-qa-juiz-r1.md](v0100-qa-juiz-r1.md), [v0100-qa-ops-r1.md](v0100-qa-ops-r1.md) | QA final (rubrica; comparação interrompida e retomada, `/metrics`, alertas) |
| [v0100-reviewer-t83.md](v0100-reviewer-t83.md), [v0100-reviewer-t84.md](v0100-reviewer-t84.md), [v0100-reviewer-t85.md](v0100-reviewer-t85.md) | Pareceres finais de revisão |
| [v0100-candidato-r1.json](v0100-candidato-r1.json) | Manifesto |
