<!-- Papel: especificação complementar da v0.11.0 (juiz por afirmação, evidência web, calibração, retrieval e régua combinada). -->

# Juiz por afirmação, evidência da web e retrieval — v0.11.0

Versão 0.3 — 2026-11-09. Complementa a [especificação do ciclo](roadmap-v0110-v100.md) (RF-109 a RF-115, CA-60 a CA-64) e o [plano técnico](roadmap-v0110-v100-plano.md).

## Problema

1. Um veredito único não identifica quais afirmações da resposta carecem de suporte nem permite comparar diretamente juiz e rotulador.
2. A avaliação de respostas web precisa confrontar as respostas com o texto das páginas citadas, em vez de tratar o resumo do modelo como evidência da página.
3. Retrieval precisa de um controle na mesma profundidade do reranker e de uma forma de avaliar separadamente requisitos determinísticos e conteúdo das jornadas.

## Resultado desejado

1. Respostas web avaliadas contra o texto das páginas citadas, buscado apenas durante a avaliação (CA-60).
2. `judge.v5` lista e julga afirmações individualmente; o código calcula `unsupported_claim` (CA-61).
3. A calibração aceita mais de um rotulador, adjudicação, medidas por afirmação e por resposta, e uma amostra protegida por hash (CA-61, CA-62).
4. `hybrid@36` compara retrieval na mesma profundidade, o piso BM25 é configurável e `RERANK` tem uma opção de controle (CA-63).
5. As jornadas combinam verificações determinísticas e avaliação do conteúdo (CA-64).

## Decisões

| ID | Decisão | Motivo | Como reverter |
| --- | --- | --- | --- |
| D1 | Os passos `knowledge` em modo `web` e `web` gravam `detail.web_summary`, mascarado e limitado a 4 000 caracteres, e `detail.web_urls`. O resumo é identificado como texto gerado, não como conteúdo de uma página. | Preservar contexto da busca sem confundi-lo com evidência de origem. | Ignorar os campos no juiz. |
| D2 | Na avaliação, cada URL citada é buscada por HTTPS, com timeout e limite de bytes; redirecionamento para outro domínio é recusado. O texto é extraído, mascarado, ajustado ao teto de evidências e cacheado em `runtime/web_evidence/<sha256(url)>.json`. Página indisponível usa o resumo com nota explícita. A busca nunca acontece no turno do lojista. | Páginas citadas são evidência verificável; o resumo é apenas fallback. | `WEB_EVIDENCE=off` volta ao formato anterior. |
| D3 | `judge_claims.v1` lista afirmações (`text`, `kind ∈ {fact, value, date, status, promise, guidance, standard}`); `judge.v5` verifica cada afirmação e devolve `verdict ∈ {supported, partial, generic, not_found}` e trecho de suporte, além dos quatro critérios. O código calcula `unsupported_claim` quando uma afirmação que não é `standard` resulta em `generic` ou `not_found`. As saídas são persistidas em `run_evaluations.claims`; v3 e v4 continuam disponíveis. | Permitir análise reproduzível por afirmação e preservar compatibilidade. | Selecionar `--rubric v3` ou `--rubric v4`. |
| D4 | Pacotes de calibração incluem pergunta, resposta, evidências por item e afirmações numeradas. `eval-calibrate --import --rater` aceita CSVs de diferentes rotuladores; `--adjudication` registra o rótulo ouro e o motivo quando há divergência. As métricas incluem concordância e kappa por resposta e por afirmação. | Juiz e rotuladores avaliam a mesma unidade. | O CSV de notas por resposta continua aceito sem CSV de afirmações. |
| D5 | `eval-calibrate --sample` permite exclusões, estratos, rotas enriquecidas e semente explícita. `--seal` grava o SHA-256 da amostra em `tests/scenarios/calibration_v0110.sha256`; importação recusa amostra cujo hash não confere. | Evitar alterações silenciosas na amostra comparada. | Criar uma nova amostra e um novo selo para uma calibração futura. |
| D6 | Um juiz só pode ser promovido se alcançar κ ≥ 0,6 contra rótulos ouro adjudicados no conjunto selado e nenhum critério cair mais de 0,05 no acordo ±1. `judge.v5` foi promovido; `judge.v3` e `judge.v4` permanecem selecionáveis. Os resultados e a decisão estão em [ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md) e na [síntese v0.11.0](../evidence/v0110-resultado.md). | Tornar a escolha verificável e reversível. | Selecionar outra rubrica explicitamente, após nova calibração. |
| D7 | `eval-retrieval --mode hybrid@36` mede a fusão RRF na profundidade usada pelo reranker, sem modelo. `RETRIEVAL_BM25_MIN_SCORE` filtra hits exclusivos de BM25 antes da fusão. `RETRIEVAL_MODE=hybrid` e `RERANK=on` são o padrão; `RERANK=off` preserva a ordem da fusão. A decisão está em [ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md); as [métricas](../evidence/v0110-retrieval.md) comparam desenvolvimento e holdout. | Medir o ganho próprio do reranker contra um controle equivalente. | Definir `RERANK=off` ou mudar `RETRIEVAL_MODE` explicitamente. |
| D8 | O relatório de jornadas separa `deterministic` (rota, status, ferramentas, valores, fontes e frases proibidas) de `content` (juiz padrão: factualidade e relevância ≥ 4, sem afirmação não suportada); `passed = deterministic and content`. `--rubric literal` mantém a comparação com a régua anterior. | Paráfrase correta pode passar, e o conteúdo continua sujeito a critérios semânticos. | Usar `--rubric literal`. |

## Riscos

| Risco | Mitigação |
| --- | --- |
| Página citada indisponível ou sem texto útil | Fallback com o resumo da busca, identificado como tal, e cache das respostas válidas. |
| `judge_claims.v1` omite ou divide mal uma afirmação | Rotuladores podem acrescentar afirmações; a calibração compara resultados por afirmação. |
| A amostra de calibração muda sem ser percebida | Hash selado, conferido na importação e preservado no controle de finais de linha. |
| Reranker falha ou excede o limite de chamadas da requisição | A busca mantém a ordem da fusão; `RERANK=off` continua disponível. |
| O piso BM25 remove evidência útil | O padrão é zero, sem descarte; a métrica pode ser comparada com o controle. |

## Tarefas

87. [Resumo da busca no trace e páginas citadas como evidência](../tasks/87-evidencia-web.md).
88. [`judge_claims.v1` e `judge.v5`: juiz por afirmação](../tasks/88-judge-v5-afirmacoes.md).
89. [Calibração por afirmação a dois rotuladores e amostra selada](../tasks/89-calibracao-dois-rotuladores.md).
90. [Retrieval `hybrid@36`, piso BM25 e régua combinada das jornadas](../tasks/90-retrieval-controle-regua-combinada.md).
91. [Coerência funcional da v0.11.0](../tasks/91-fechamento-v0110.md).
91a. [Preservar os bytes da amostra selada no checkout](../tasks/91a-selo-calibracao-final-de-linha.md).
