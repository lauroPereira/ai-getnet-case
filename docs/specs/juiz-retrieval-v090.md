# Juiz Claude e retrieval híbrido — v0.9.0

Versão 0.2 — 2026-11-05 — escrita pelo Supervisor e **aprovada pelo responsável em 2026-11-05** (escopo, ordem e modelo do juiz; o teto Anthropic está em "Orçamento"). Substitui a proposta 0.1 ("Retrieval híbrido e provedor Anthropic", branch `docs/spec-v090`, não integrada): o provedor Anthropic nos agentes e a comparação pareada saem desta entrega e ficam em "Próximos passos" do README. Deriva da [especificação 0.2](evolucao-pos-feedback.md) (RF-90, RF-91, RF-94 a RF-96, CA-52) e do [plano](evolucao-pos-feedback-plano.md). Vale a "Autorização por versão" do AGENTS.md. Prazo externo: a entrega ao avaliador é em 2026-11-06 às 08h (horário de São Paulo); o README é o que ele lê.

## Problema

1. A calibração humana da v0.8.0 ([relatório](../evidence/v080-calibracao.md)) mostrou um juiz DeepSeek consistente consigo mesmo e mais severo que o humano, mas que nunca marca as mesmas afirmações sem suporte: o humano apontou frases genéricas em quatro respostas de conhecimento; o juiz, três respostas web sem texto gravado e um encaminhamento. O responsável quer saber se um modelo mais forte como juiz concorda mais com ele, antes de o juiz passar a decidir conteúdo nas jornadas (D8 abaixo).
2. O retrieval é só denso, medido numa amostra pequena usada no desenvolvimento, sem holdout, sem BM25, sem fusão e sem reranker (feedback do avaliador; RF-94 a RF-96).

## Resultado desejado

1. Um relatório `docs/evidence/v090-juiz-opus.md` com a concordância humano × juiz da **mesma amostra de 24 respostas**, mesma rubrica `judge.v3` e mesma evidência, para `claude-opus-5-5` e para `deepseek-flash` lado a lado, com a consistência de cada juiz entre repetições, o custo por julgamento e a decisão registrada: qual juiz é o padrão a partir da próxima versão e por quê.
2. `merchant-assistant eval-retrieval --mode --split` mostra denso × híbrido × híbrido+reranker em `dev` e num holdout de retrieval lacrado, com Recall@6, MRR e nDCG@6, e a decisão do modo padrão fica registrada com os números (CA-52).

## Escopo

| Bloco | Conteúdo | Requisitos | Tarefa |
| --- | --- | --- | --- |
| Juiz Anthropic | Adaptador `llm/anthropic.py` (só `parse`), `anthropic` em `JUDGE_PROVIDERS`, preços de `claude-opus-5-5` (e Sonnet/Haiku 5.5 para referência) em `prices.json`, `eval --judge-repeat --only-sample <csv>`, `eval-calibrate --import --judge <provedor>/<modelo>`, provedor programado nos testes | RF-90, RF-91 | 79 |
| Híbrido | BM25 em processo (`rank-bm25`), tokenização sem acentos e stopwords pt/en, persistência por hash do corpus, RRF, `KnowledgeIndex.search(mode)`, `RETRIEVAL_MODE` | RF-94 | 80 |
| Reranker e medição | `rerank.v1` sobre os 12 primeiros no modelo do agente (`gpt-6-luna`), `RERANK=on\|off`, holdout de retrieval lacrado (≥ 20, metade pt), `eval-retrieval --mode --split`, Recall@6, MRR, nDCG@6 | RF-95, RF-96 | 81 |
| Fechamento | Regressão, candidato, revisão, QA real (experimento do juiz e `eval-retrieval`), ADR 0020 (híbrido) e ADR 0021 (juiz), README e CHANGELOG | CA-52, CA-56 | 82 |

Requisito e critério novos para a especificação 0.2 (numerados aqui):

- **RF-108** Experimento de juiz: as mesmas respostas da amostra de calibração podem ser julgadas de novo por outro provedor e modelo, e `eval-calibrate` mede a concordância das notas humanas já gravadas com o juiz escolhido, sem nova avaliação humana.
- **CA-56** O relatório do experimento traz, para cada juiz, concordância exata, ±1, kappa, viés e a matriz de `unsupported_claim` contra as mesmas 24 notas humanas; a consistência de cada juiz entre as repetições; o custo por julgamento; e a decisão do juiz padrão com a regra escrita antes do experimento (D2).

## Fora do escopo

Anthropic como provedor dos agentes e comparação pareada de provedores (proposta 0.1, próximos passos); busca web da Anthropic; embeddings Anthropic (não existem); métricas, comparação retomável e resumo rolante (v0.10.0); novo holdout de respostas; reabrir ou relacrar o `holdout_v080`; mudança de prompts dos agentes; mudança de regras financeiras.

## Decisões

Todas reversíveis; vão também para o relatório do Supervisor.

| ID | Decisão | Motivo | Como reverter |
| --- | --- | --- | --- |
| D1 | **Desenho do experimento.** Os 24 `request_id` do CSV de calibração (`docs/evidence/v080-calibracao-amostra.csv`), o mesmo `judge_input` gravado em `v080-all-r3.json`, o mesmo prompt `judge.v3`, modelo `claude-opus-5-5`, parâmetros padrão do modelo (thinking adaptativo, esforço padrão, `max_tokens` 2000). Primeiro uma sonda de 3 julgamentos para medir custo real; depois 3 repetições sobre os 24 (72 julgamentos) se couber no teto, senão 1 repetição (24) e o relatório diz quantas foram. Os julgamentos são gravados no mesmo banco em que estão as notas humanas (runtime de QA `.pytest_cache/qa-v080-r1/runtime`, que não pode ser apagado), com campanha `v090-juiz-opus` | É a única comparação válida: muda só o modelo do juiz; o Opus é o modelo mais forte disponível, para a variável ficar evidente (decisão do responsável) | Repetir com Sonnet 5.5 pela mesma CLI |
| D2 | **Regra de decisão, escrita antes de rodar.** O Opus vira o juiz padrão das próximas versões se, contra as mesmas 24 notas humanas: (a) a concordância ±1 não piorar em nenhum critério; (b) a concordância do veredito `unsupported_claim` subir acima de 0,667 e pelo menos 2 das 4 respostas com frase genérica (S01, S13, S16, S21) forem marcadas "sim"; (c) a consistência entre repetições (exata) não ficar abaixo de 0,70. Se (b) falhar com (a) e (c) atendidos, a lacuna é da rubrica, não do modelo: o DeepSeek continua e a rubrica ganha a linha sobre afirmação genérica. Em qualquer caso os dois resultados ficam no relatório | Evita escolher o juiz depois de ver o número | Mudar a regra só em nova versão da spec |
| D3 | **Contrato do adaptador.** SDK oficial `anthropic`, `messages.create` com `system` = `instructions`, uma mensagem de usuário = `input`, saída estruturada por `output_config.format` (JSON schema derivado do modelo Pydantic, `strict`), `thinking` omitido (adaptativo), `output_config.effort` omitido (padrão do modelo), `max_tokens` do `CallSpec`, timeout do `Meter` como hoje. `stop_reason` `refusal` ou `max_tokens` vira `LLMError` (julgamento falho, registrado como falha; nunca nota inventada). `usage` com entrada, saída, leitura e criação de cache; a tabela de preços precifica cache lido a US$0,20 por milhão nos modelos 5.5 e cache criado a 1,25× a entrada. `run_tools` e `web_search` levantam `LLMError("not supported for the judge in v0.9.0")`. Preços de lista (US$ por milhão de tokens, consultados em 2026-11-05): Opus 5.5 entrada 4,00 e saída 20,00; Sonnet 5.5 entrada 2,00 e saída 10,00; Haiku 5.5 entrada 0,10 e saída 0,50. Tokens de pensamento são cobrados como saída | É o que a API atual aceita; o juiz só usa `parse` | — |
| D4 | **Independência (D11 da v0.8.0) preservada.** Agente OpenAI, juiz Anthropic: `different_provider`. `JUDGE_PROVIDERS` passa a `("openai", "deepseek", "anthropic")`; `_has_key` cobre `ANTHROPIC_API_KEY`; o padrão continua `deepseek/deepseek-flash` até a decisão D2 | RF-90 | Trocar o padrão em `config.py` depois da decisão |
| D5 | **Ledger Anthropic separado.** O experimento roda com `BUDGET_RUNTIME_DIR=data/runtime/anthropic` (ledger primário próprio, teto US$5,00, o máximo que o código permite) e campanha `v090-juiz-opus` com cap fixo (valor em "Orçamento"). O ledger OpenAI/DeepSeek do projeto (`data/runtime/budget.sqlite3`, teto US$2,00 dentro dos US$5,00) não recebe nenhum lançamento Anthropic. A CLI já grava provedor e modelo em cada julgamento; nenhum campo novo no ledger | Separar créditos Anthropic do saldo do projeto sem mexer no esquema do ledger | Um ledger só, se o responsável preferir |
| D6 | **Régua do CA-51 (pendência da v0.8.0).** Decidido com o responsável em 2026-11-05: a régua literal é o piso determinístico (rota, status, ferramentas, valores, fontes, afirmações proibidas registradas) e o juiz calibrado é a checagem de conteúdo. Nesta versão isso é texto (README, CHANGELOG, ADR 0021); `content_ok` continua reportado como diagnóstico. A troca do critério de aceite no código fica para quando houver nova campanha de jornadas, com o juiz escolhido por D2 | Não há campanha de jornadas nesta versão; mudar critério sem medir seria cosmético | — |
| D7 | **Retrieval.** `RETRIEVAL_MODE` padrão (`dense`, `hybrid`) decidido pela medição em `dev` e confirmado no holdout de retrieval; `RERANK` padrão `off` a menos que melhore nDCG@6 nos dois splits; reranker em `gpt-6-luna` (o modelo do agente), prompt `rerank.v1`; BM25 persistido por hash do corpus ao lado do manifesto do índice; `KnowledgeIndex.search(mode)` sem mudar a assinatura usada pelo Knowledge quando `mode` é omitido | RF-96 pede "ligado por padrão só se melhorar" | — |
| D8 | **Holdout de retrieval.** ≥ 20 perguntas, metade em português, com a passagem correta anotada por `chunk_id`, escritas pelo Developer antes de medir qualquer modo e lacradas por `sha256` (`tests/scenarios/retrieval_holdout_v090.jsonl` + `.sha256`), como o `holdout_v080`; medido uma vez por modo, por último | RF-95 | — |
| D9 | **Nenhum holdout de respostas novo** nesta versão; o `holdout_v080` continua "já visto" e não decide nada | Custo e prazo | Lacrar `holdout_v090` em outra versão |
| D10 | **Dependências.** `anthropic` e `rank-bm25` entram em `pyproject.toml` como dependências normais (o CI instala `.[ingest,dev]`); versões fixadas no mínimo | Simplicidade; os dois são pequenos | Extras opcionais |

## Pré-condições

- v0.8.0 integrada na `main` (feito: tag `v0.8.0`); branch `codex/v0.9.0-juiz-retrieval` criada da `main` atualizada.
- `.env` com `ANTHROPIC_API_KEY` (presente), nunca lida por Developer ou Reviewer.
- Runtime de QA `.pytest_cache/qa-v080-r1/runtime` preservado: contém as 24 notas humanas em `calibrations` e os julgamentos DeepSeek da campanha `v080-all-r3`.
- Saldo Anthropic conferido pelo responsável antes da primeira chamada paga.

## Critérios de aceitação e prova

| ID | Critério | Prova determinística | Prova real (QA) |
| --- | --- | --- | --- |
| CA-56 | Relatório do experimento com os dois juízes contra as mesmas 24 notas humanas, consistência, custo e decisão por D2 | Adaptador com provedor programado: esquema estruturado, `refusal` → falha, `usage` e preço com cache; `--only-sample` filtra pelos `request_id` do CSV; `--judge` seleciona o julgamento comparado; relatório renderiza os dois juízes | Sonda de 3 julgamentos; 72 (ou 24) julgamentos reais no Opus; `eval-calibrate --import --judge anthropic/claude-opus-5-5` |
| CA-52 | Tabela denso × híbrido × híbrido+reranker em dev e holdout de retrieval (Recall@6, MRR, nDCG@6), decisão registrada | RRF, BM25 por hash e nDCG com números fixos; reranker programado (80, 81); lacre conferido | `eval-retrieval` nos três modos e dois splits com embeddings reais; holdout por último, uma vez por modo |
| Regressão | 44 casos e 4 conversas sem piora; suíte estrita verde; v0.7.0 e v0.8.0 intactas; `search()` sem `mode` dá o mesmo resultado de hoje | Suíte; teste de equivalência do modo denso | Não há campanha de respostas nova nesta versão |

## Requisitos não funcionais e orçamento

- Testes sem chamada paga e sem rede: provedor programado para `anthropic` (mesma política do `scripted`), `rank-bm25` em processo, embeddings de hash.
- **Orçamento Anthropic (decisão do responsável, a confirmar antes da sonda):** proposta de cap fixo de **US$4,00** na campanha `v090-juiz-opus`, em créditos Anthropic, fora do teto de US$5,00 do projeto. Estimativa antes da sonda: cerca de 3.500 tokens de entrada e 300 a 1.500 de saída (com pensamento) por julgamento no Opus 5.5, entre US$0,02 e US$0,05 cada; 72 julgamentos entre US$1,50 e US$3,60. A sonda de 3 julgamentos fixa o número; se a projeção de 72 passar do cap, o QA roda 1 repetição.
- **Orçamento OpenAI (dentro do plano):** `eval-retrieval` real gasta embeddings das perguntas (centavos) e, com `RERANK=on`, chamadas `gpt-6-luna` curtas; cabe nos US$0,10 de QA reservados no plano para a v0.9.0, com US$0,35 de correções.
- Latência: nenhum limite novo; o relatório de retrieval traz o tempo por modo.
- Nenhum dado real; snapshots públicos e seed sintética inalterados. Nenhum caminho pessoal em evidência (AGENTS.md, "Caminhos pessoais").

## Riscos

| Risco | Mitigação |
| --- | --- |
| Opus recusa ou estoura `max_tokens` por causa do pensamento | `refusal`/`max_tokens` vira falha registrada; sonda antes; `max_tokens` 2000 |
| Custo acima do estimado | Sonda de 3; cap fixo; 1 repetição como alternativa declarada |
| Esquema JSON do `JudgeScoreV3` não aceito como `strict` | Teste de contrato do esquema; ajuste só no adaptador, nunca no modelo Pydantic |
| Comparação viciada por ordem ou cache | Mesmo `judge_input` serializado dos dois lados; cache lido reportado à parte |
| Reranker piora latência sem melhorar nDCG | `RERANK=off` por padrão até a medição mostrar ganho nos dois splits |
| Prazo das 08h | Ordem fixa: 79 → QA do juiz → 80 → 81 → 82; se 81 não couber, 80 fecha sozinho com `eval-retrieval` em `dev` e o holdout fica declarado como não medido |

## Tarefas

As tarefas 74 a 78 foram usadas pelas correções da v0.8.0. Nesta versão: 79 a 82; v0.10.0 passa a 83 a 85; v1.0.0 a 86 a 88. Um time só, em série.

79. [Juiz Anthropic e experimento de calibração](../tasks/79-juiz-anthropic-opus-calibracao.md).
80. [Retrieval híbrido BM25 + RRF](../tasks/80-retrieval-hibrido-bm25-rrf.md).
81. [Reranker, holdout de retrieval e `eval-retrieval` com nDCG](../tasks/81-reranker-holdout-retrieval-ndcg.md).
82. [Fechamento da v0.9.0](../tasks/82-fechamento-v090.md).

História de uso: [juiz-retrieval-v090.md](../historias/juiz-retrieval-v090.md).
