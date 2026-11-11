# Evidências

Registros de validação do projeto, da v0.1.0 à v1.1.0. Da v0.3.0 em diante, cada versão tem um resultado consolidado (`vXYZ-resultado.md`) com as capacidades entregues e a validação. Ao lado ficam as revisões independentes, as validações com modelos reais, os manifestos de candidato (`*-candidato-r*.json`), os relatórios das execuções reais, a calibração do juiz, os holdouts e o retrieval. Os dados são sintéticos e não contêm segredos; novas evidências seguem os modelos em [docs/templates](../templates/candidato.md).

Um relatório `.md` pode vir com um `.json` de mesmo nome, com os dados da execução. A tabela antes × depois por área, com o número da v0.10.0 e o atual, está no [README](../../README.md#what-changed-since-v0100). O gasto com APIs pagas, por versão, está em [orcamento.md](orcamento.md).

Cada parecer de revisão ou de validação abre com o parecer final e o candidato, seguido do registro completo da verificação. Os links apontam para os caminhos atuais do repositório; o texto de cada registro como foi gravado está na tag da sua versão (`v0.3.0` a `v0.10.0`).

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
| [v030-qa-r6.md](v030-qa-r6.md) | Validação independente |
| [v030-reviewer-r6.md](v030-reviewer-r6.md) | Revisão independente |
| [v030-release.md](v030-release.md) ([JSON](v030-release.json)), `v030-candidato-r*.json` | Candidato de release e manifestos |
| [v030-real-http-r2.md](v030-real-http-r2.md), [v030-real-http-r2-replay.md](v030-real-http-r2-replay.md), [v030-real-conversations-r3.md](v030-real-conversations-r3.md), [v030-real-budget-r3.json](v030-real-budget-r3.json), [v030-ready-r6.json](v030-ready-r6.json) | Execuções reais pela API, conversas e orçamento |
| [2026-10-27-avaliacao-programada-v030-final.md](2026-10-27-avaliacao-programada-v030-final.md) | Avaliação programada final |

## v0.4.0 (perfis, `/v1` e interface)

| Arquivo | Conteúdo |
| --- | --- |
| [v040-resultado.md](v040-resultado.md) | Resultado consolidado |
| [v040-qa-r6.md](v040-qa-r6.md) | Validação independente |
| [v040-reviewer-r6.md](v040-reviewer-r6.md) | Revisão independente |
| [v040-catalogo-fontes.md](v040-catalogo-fontes.md), [v040-parametros-modelo-fontes.md](v040-parametros-modelo-fontes.md), [v040-metadados-publicos.json](v040-metadados-publicos.json) | Catálogo de modelos e parâmetros, verificados nas fontes oficiais |
| `v040-candidato-r*.json`, [v040-verificacao-final-r6.json](v040-verificacao-final-r6.json), [v040-docker-r6.json](v040-docker-r6.json) | Manifestos, verificação final e Docker |

## v0.5.0 (base de conhecimento versionada)

| Arquivo | Conteúdo |
| --- | --- |
| [v050-resultado.md](v050-resultado.md) | Resultado consolidado |
| [v050-qa-r3.md](v050-qa-r3.md) | Validação com modelos reais |
| [v050-reviewer-r2.md](v050-reviewer-r2.md), [v050-reviewer-ui-r3.md](v050-reviewer-ui-r3.md) | Revisões independentes (backend e interface) |
| `v050-candidato-r*.json`, [v050-docker-r7.json](v050-docker-r7.json) | Manifestos e Docker |

## v0.6.0 (atendimento, resultados e administração)

| Arquivo | Conteúdo |
| --- | --- |
| [v060-resultado.md](v060-resultado.md) | Resultado consolidado |
| [v060-qa.md](v060-qa.md) | Validação com modelos reais |
| [v060-reviewer.md](v060-reviewer.md) | Revisão independente |
| `v060-candidato-r*.json` | Manifestos |

## v0.7.0 (identidade e humano no circuito)

| Arquivo | Conteúdo |
| --- | --- |
| [v070-resultado.md](v070-resultado.md) | Resultado consolidado |
| [v070-qa.md](v070-qa.md), [v070-qa-historia.md](v070-qa-historia.md) | Validação com modelos reais e evidência da história, momento a momento |
| [v070-qa-regressao-real.md](v070-qa-regressao-real.md) ([JSON](v070-qa-regressao-real.json)), [v070-qa-regressao-repeticao.json](v070-qa-regressao-repeticao.json) | Regressão real |
| [v070-reviewer.md](v070-reviewer.md), [v070-reviewer-time-b.md](v070-reviewer-time-b.md), [v070-reviewer-t66-r5.md](v070-reviewer-t66-r5.md), [v070-reviewer-t68.md](v070-reviewer-t68.md) | Revisões independentes |
| [v070-candidato-r1.json](v070-candidato-r1.json) | Manifesto |

## v0.8.0 (replanejamento, juiz independente e calibração)

| Arquivo | Conteúdo |
| --- | --- |
| [v080-resultado.md](v080-resultado.md) | Resultado consolidado |
| [v080-all-r3.md](v080-all-r3.md) ([JSON](v080-all-r3.json)) | Campanha: 44 casos, jornadas e conversas, três execuções |
| [v080-d12-pre-holdout-r6.md](v080-d12-pre-holdout-r6.md) | Validação pré-holdout com modelos reais; dados em [v080-healthy-r6.md](v080-healthy-r6.md) (traces em [v080-healthy-traces-r6.json](v080-healthy-traces-r6.json)), [v080-healthy-r5.md](v080-healthy-r5.md), [v080-healthy-r4.md](v080-healthy-r4.md), [v080-conversations-r4.md](v080-conversations-r4.md), [v080-tool-down-r5.md](v080-tool-down-r5.md) e [v080-smoke-r6.json](v080-smoke-r6.json) |
| [v080-judge-repeat-r6.md](v080-judge-repeat-r6.md) | Variação do juiz |
| [v080-custo-estimativa-r3.json](v080-custo-estimativa-r3.json) | Estimativa revalidada que sustentou o cap da campanha `v080-qa` |
| [v080-holdout-r7.md](v080-holdout-r7.md) (traces em [v080-holdout-traces-r7.json](v080-holdout-traces-r7.json)), [v080-avaliacao-holdout-r7.md](v080-avaliacao-holdout-r7.md), [v080-avaliacao-holdout-judge-repeat-r7.md](v080-avaliacao-holdout-judge-repeat-r7.md), [v080-holdout-derivacao.md](v080-holdout-derivacao.md) | Holdout `holdout_v080`, executado uma vez, e sua derivação |
| [v080-calibracao.md](v080-calibracao.md), [v080-calibracao-amostra.csv](v080-calibracao-amostra.csv), [v080-calibracao-evidencia.md](v080-calibracao-evidencia.md), [v080-calibracao-modelo.md](v080-calibracao-modelo.md) | Calibração humana do juiz (24 respostas) |
| [v080-reviewer.md](v080-reviewer.md), `v080-reviewer-t*.md`, [v080-reviewer-cap-r2.md](v080-reviewer-cap-r2.md) | Revisões independentes |
| `v080-candidato-r*.json` | Manifestos |

## v0.9.0 (retrieval híbrido e experimento do juiz)

| Arquivo | Conteúdo |
| --- | --- |
| [v090-resultado.md](v090-resultado.md) | Resultado consolidado |
| [v090-retrieval.md](v090-retrieval.md) ([JSON](v090-retrieval.json)) | Retrieval por modo no dev e no holdout `retrieval_holdout_v090` |
| [v090-juiz-opus.md](v090-juiz-opus.md), [v090-juiz-opus-r3.md](v090-juiz-opus-r3.md) | Calibração com dois juízes |
| [v090-qa-retrieval-r1.md](v090-qa-retrieval-r1.md), [v090-qa-hybrid-r1.md](v090-qa-hybrid-r1.md), [v090-qa-juiz-r2.md](v090-qa-juiz-r2.md) | Validação com modelos reais |
| [v090-reviewer-t79.md](v090-reviewer-t79.md), [v090-reviewer-t80.md](v090-reviewer-t80.md), [v090-reviewer-t81.md](v090-reviewer-t81.md) | Revisões independentes |
| `v090-candidato-r*.json` | Manifestos |

## v0.10.0 (rubrica `judge.v4`, comparação retomável e métricas)

| Arquivo | Conteúdo |
| --- | --- |
| [v0100-resultado.md](v0100-resultado.md) | Resultado consolidado |
| [v0100-juiz-v4.md](v0100-juiz-v4.md), [v0100-juiz-deepseek-v4.md](v0100-juiz-deepseek-v4.md), [v0100-juiz-opus-v4.md](v0100-juiz-opus-v4.md) | `judge.v4` contra a calibração humana, com os dois juízes |
| [v0100-qa-juiz-r1.md](v0100-qa-juiz-r1.md), [v0100-qa-ops-r1.md](v0100-qa-ops-r1.md) | Validação com modelos reais (rubrica; comparação interrompida e retomada, `/metrics`, alertas) |
| [v0100-reviewer-t83.md](v0100-reviewer-t83.md), [v0100-reviewer-t84.md](v0100-reviewer-t84.md), [v0100-reviewer-t85.md](v0100-reviewer-t85.md) | Revisões independentes |
| [v0100-candidato-r1.json](v0100-candidato-r1.json) | Manifesto |

## v0.11.0 (juiz por afirmação e evidência web)

| Arquivo | Conteúdo |
| --- | --- |
| [v0110-resultado.md](v0110-resultado.md) | Resultado consolidado do juiz por afirmação e da configuração de retrieval |
| [v0110-calibracao.md](v0110-calibracao.md) | Calibração do juiz contra rótulos de referência: κ 0,647 do `judge.v5` nas 36 respostas seladas, recalculável sem chamada a modelo, com o comando |
| `v0110-calibracao-responsavel-*.csv`, `v0110-calibracao-modelo-a-*.csv`, `v0110-calibracao-modelo-b-*.csv`, `v0110-calibracao-painel-*.csv`, [v0110-calibracao-adjudicacao.csv](v0110-calibracao-adjudicacao.csv), [v0110-calibracao-rotulos-referencia.csv](v0110-calibracao-rotulos-referencia.csv) | Notas do responsável, de cada modelo do painel e do painel; adjudicação aprovada pelo responsável; rótulos de referência |
| `v0110-calibracao-juiz/` | Julgamentos do `judge.v5` nas 60 respostas (29 relatórios JSON) |
| [v0110-v5-ajuste.md](v0110-v5-ajuste.md) | Ajuste do `judge.v5` no conjunto de ajuste (24 respostas da v0.8.0): 4 de 4 frases genéricas marcadas |
| [v0110-qa.md](v0110-qa.md) ([JSON](v0110-qa.json)), [v0110-qa-holdout-v080.md](v0110-qa-holdout-v080.md) ([JSON](v0110-qa-holdout-v080.json)) | Campanha com modelos reais: desenvolvimento (44 casos, jornadas e conversas, três execuções) e holdout da v0.8.0. Nos JSON, o texto de páginas de terceiros foi omitido; ficam a URL, o tamanho e o hash |
| [v0110-reviewer-v5i3b.md](v0110-reviewer-v5i3b.md) | Revisão independente |
| [v0110-candidato-r3.json](v0110-candidato-r3.json) | Manifesto do candidato |
| [v0110-retrieval.md](v0110-retrieval.md) ([JSON](v0110-retrieval.json)) | Métricas de retrieval em dev e no holdout, incluindo o controle `hybrid@36` |
| [v0110-calibracao-amostra.csv](v0110-calibracao-amostra.csv), [v0110-calibracao-amostra-claims.csv](v0110-calibracao-amostra-claims.csv), [selo](../../tests/scenarios/calibration_v0110.sha256) | Amostra selada de calibração e afirmações |

## v0.12.0 (memória, replanejamento medido e cancelamento com confirmação)

| Arquivo | Conteúdo |
| --- | --- |
| [v0120-resultado.md](v0120-resultado.md) | Resultado consolidado: resumo rolante e registro de fatos, conversa longa, replanejamento com e sem, cancelamento com confirmação explícita, suíte estrita e gasto da campanha |
| [v0120-validacao.md](v0120-validacao.md) | Validação momento a momento (candidato integrado e modelo real, com a ablação do replanejamento) e revisão independente: re-derivações, testes e mutações |
| [v0120-comparacao.md](v0120-comparacao.md), [v0120-comparacao-holdout.md](v0120-comparacao-holdout.md) | Replanejamento com × sem, pareado por caso, critério e rota, com intervalo por bootstrap e decisões por origem |

## v0.13.0 (identidade e operação)

| Arquivo | Conteúdo |
| --- | --- |
| [v0130-resultado.md](v0130-resultado.md) | Resultado consolidado: login por redirecionamento, emissores OIDC, dois workers, reenvio de webhooks, operador no Telegram, OTLP e painel, migrações, suíte estrita e gasto da campanha |
| [v0130-validacao.md](v0130-validacao.md) | Validação momento a momento (emissor externo, dois workers, reenvio, OTLP, Telegram, login pela interface) e revisão independente |

## v1.0.0 (imagem publicada, dependências fixadas e túnel de demonstração)

| Arquivo | Conteúdo |
| --- | --- |
| [v100-resultado.md](v100-resultado.md) | Resultado consolidado: imagem por tag com `uv.lock`, suíte estrita dentro da imagem sem rede, compose sem imagem publicada, trilha de 10 minutos com modelo real, proxy do túnel, trava de credenciais de exemplo, acesso por outra rede e gasto |
| [v100-validacao.md](v100-validacao.md) | Validação momento a momento (imagem, trilha de 10 minutos, proxy do túnel, credenciais, acesso por outra rede) e revisão independente |

## v1.1.0 (tickets do lojista, retomada da conversa e resposta da atendente)

| Arquivo | Conteúdo |
| --- | --- |
| [v110-resultado.md](v110-resultado.md) | Resultado consolidado: tickets do lojista em qualquer conversa, retomada da última conversa, resposta da atendente com as palavras dela, perfis disponíveis, isolamento entre lojistas, suíte estrita e gasto das campanhas |
| [v110-validacao.md](v110-validacao.md) | Validação momento a momento (tickets, retomada, resposta da atendente, disponibilidade) e revisão independente |
| [v110-cobertura.md](v110-cobertura.md) | Cobertura dos testes automatizados: 93,8% das instruções e 88,0% dos ramos, com a tabela por pacote e o comando da medição |
