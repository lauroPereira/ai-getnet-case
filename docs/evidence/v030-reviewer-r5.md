# Revisão independente — v0.3.0 jornadas, rodada 5

## Parecer

**Correções necessárias (P2).** A correção de continuidade após handoff está alinhada ao contrato já implementado, e as respostas reais r2 agora passam pelos critérios de conteúdo ampliados. Porém, os critérios novos para evidência insuficiente aceitam respostas contraditórias em inglês e português como totalmente aprovadas. Isso enfraquece a regressão semântica de RF-32/RF-46 e CA-21/CA-28/CA-31.

## Independência e candidato

- Revisão independente do Developer; rederivei os resultados a partir dos arquivos, das respostas brutas r2 e da execução local.
- Candidato: `v0.3.0-local-r5`; branch `codex/v0.3.0-jornadas`; base e HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- Conferi 48/48 hashes de arquivos e recalculei o fingerprint `8b15414ab90acfc576404ef45c23a71526eea333d0c4cdcf8d46d4f3e4741f97`; coincide com o manifesto. O fingerprint de runtime `643609655b811641b497b96d5d4555b1dc6f2387016ac5e591ab79914622ab78` também coincide. Os 30 hashes de runtime, insumos de build e harnesses listados conferem.
- A comparação com r4 identifica somente quatro alterações: `prompts/router.v5.md`, `tests/scenarios/business_journeys.jsonl`, `tests/integration/test_evaluation_runner.py` e `docs/tasks/26-continuidade-apos-handoff.md`. Os arquivos de produto restantes, os dados e os critérios não mudaram.
- Containers em execução: API `sha256:71e97b5928e10bc5d3ba8cafedf95439295492c606b2a7ed139a9d90b9d61f1c`; mocks `sha256:785653851bba24428b90552513bc0d6cc0947f64753071d44067eccd208a1cad`; QA usa a mesma imagem da API. GET `/ready` confirmou API e QA prontas e Router 5. GET `/openapi.json` confirmou `/messages`, `/ready` e `/traces/{request_id}`.

## Continuidade após handoff

Os dados brutos de `v030-real-http-r2.json` mostram FU02: os dois primeiros turnos passam; no terceiro, “Still the same, nothing works.” foi classificado como `acknowledgement`/`answered`, enquanto o caso e o protocolo permaneceram em `handoff`. Esse é o defeito reproduzível que a tarefa 26 aborda.

O prompt r5 separa agradecimento de falha persistente, conserva tópico/rota de suporte e pede `still_failing`, inclusive após encaminhamento. Isso é consistente com RF-28–RF-30, CA-18/CA-19 e CA-28. A implementação sem alteração já trata esse caminho: `support.py` marca `already_handed_off`; `escalation.py` reutiliza o caso/protocolo existente; `cases.py` mantém `handoff` e a evidência anterior. O teste local `test_case_already_with_human_reuses_the_protocol` passou. A conversa real FU02 r3 ainda deve confirmar que o Router real segue a nova orientação, que o status final é handoff e que o protocolo é o mesmo; não enviei POST nem chamadas pagas.

## Reproduções da avaliação e achado

Recalculei offline os 40 casos originais HTTP r2 com os critérios atuais, sem gerar arquivo de evidência. Cinco resultados dev mudaram de reprovados para aprovados: `V030-PRICE-CONDITIONS`, `V030-PRICE-DIVERGENCE`, `V030-PRICE-INSUFFICIENT`, `V030-PT-PRICE-INSUFFICIENT` e `V030-PT-SALE-CANCELLATION`. Em todos, somente `content_ok` e/ou `forbidden_ok` mudaram. As 17 linhas holdout permanecem aprovadas, sem mudanças, e rota, status, idioma, ferramentas, valores, fontes, grounding e violações coincidem com os resultados r2 em todos os 40 casos. O dataset holdout e os outros campos de cada cenário estão byte a byte preservados.

Os positivos e contrapontos existentes para divergência em EN/PT continuam adequados: a frase verdadeira com R$ 0,75 passa, e “No divergence…” / “Não há divergência…” falham em `forbidden_ok` mesmo quando os demais critérios sintéticos estão corretos. Condições e cancelamento também conservam contraprovas.

**[P2] Respostas contraditórias passam no cenário de evidência insuficiente.** Ao substituir os negativos amplos por frases específicas de confirmação, os critérios deixaram de rejeitar afirmações positivas que coexistam com uma frase exigida de falta de dados. Reprodução direta de `_checks` para ambos os cenários insuficientes:

| Resposta | Resultado dos checks |
| --- | --- |
| EN: “There is enough evidence to compare the fee. There is no expected pricing fee or recorded charge to compare.” | Todos os checks `true` |
| EN: “The fee is correct. There is no expected pricing fee or recorded charge to compare.” | Todos os checks `true` |
| PT: “A taxa está correta. Não há taxa esperada para comparar.” | Todos os checks `true` |

Condição: uma resposta ao cenário que pergunta se há evidência insuficiente inclui a alternativa permitida “no expected pricing fee…”/“não há taxa esperada…”, mas também afirma que a evidência é suficiente ou que a taxa está correta. Impacto: o avaliador marca como correta uma resposta financeiramente contraditória, contrariando RF-08/RF-32/RF-46 e CA-21/CA-28/CA-31. Arquivos/linhas: `tests/scenarios/business_journeys.jsonl:4,11` e `tests/integration/test_evaluation_runner.py:114-123,143-152`. Verificação própria: chamadas diretas a `_checks` retornaram todos os `CHECK_KEYS` verdadeiros nos exemplos EN e PT acima.

O teste `test_insufficient_evidence_checks_still_reject_positive_sufficiency_claim` só exige que `content_ok` ou `forbidden_ok` seja falso. A resposta positiva isolada reprova por não incluir o conteúdo exigido, então o teste não demonstra que a afirmação proibida seja detectada; uma resposta contraditória combinada com a frase permitida passa. Corrigir preservando as formulações legítimas de incerteza — por exemplo, exigindo teste de combinação contraditória e verificando especificamente que ela não pode passar — sem reintroduzir falsos positivos em “não foi possível confirmar se a taxa está correta ou incorreta”.

## Verificações executadas

- `python -m pytest tests/integration/test_evaluation_runner.py --basetemp .pytest_cache/v030-review-r5`: **19 passed**.
- `python -m ruff check tests/integration/test_evaluation_runner.py`: **All checks passed**.
- `python -m pytest tests/integration/test_conversations.py::test_case_already_with_human_reuses_the_protocol --basetemp .pytest_cache/v030-review-r5-handoff` (execução local autorizada): **1 passed**.
- GET de readiness/OpenAPI da API e GET `/ready` do QA: prontos, sem chamada de mensagem.
- Nenhum acesso a `.env`, POST, chamada paga, modificação de produto/teste/critério, alteração Git externa ou arquivo de replay foi feito. O replay foi refeito em memória.

## Lacunas e passagem

A avaliação sem custo confirma que os critérios aceitam as paráfrases naturais da execução r2 e preservam os checks financeiros e o holdout. Ela também expõe o P2 acima, que bloqueia o aceite de CA-28 para a negação de evidência insuficiente. A conversa real FU02 deve permanecer para a revalidação do Supervisor no teto compartilhado; depois de corrigir o P2 e fixar novo candidato, encaminhar a nova revisão independente antes de QA.

**Próximo responsável: Developer**, para corrigir somente a detecção de afirmações contraditórias no cenário de evidência insuficiente e acrescentar uma contraprova combinada EN/PT. Não reduzir os outros checks nem alterar o holdout.
