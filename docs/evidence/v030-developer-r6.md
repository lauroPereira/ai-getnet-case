# Passagem Developer — candidato local r6

- **Papel:** Developer, continuidade da correção do parecer `v030-reviewer-r5.md`.
- **Objetivo:** rejeitar afirmações positivas contraditórias nas duas jornadas de evidência insuficiente sem classificar incerteza qualificada como afirmação; preservar banimentos literais.
- **Branch/base:** `codex/v0.3.0-jornadas`, HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`; sem commit.
- **Estado:** implementação validada localmente; aguardando nova revisão independente. Não é aceite de QA nem aprovação da conversa real.
- **Delta exato desde r5:**
  - `src/merchant_assistant/evaluation/runner.py`
  - `tests/scenarios/business_journeys.jsonl`
  - `tests/integration/test_evaluation_runner.py`
  - `docs/evidence/v030-developer-r6.md` (esta passagem)
- **Implementação:** `Case.must_not_assert` é uma lista opcional, vazia por padrão, usada para afirmações semânticas que invalidam a resposta. As afirmações apropriadas dos dois cenários insuficientes foram transferidas para essa lista.
- **Semântica limitada:** o avaliador detecta as afirmações configuradas por correspondência textual e permite apenas qualificadores EN/PT pequenos e explícitos de incapacidade ou dúvida. Pontuação, vírgula e contrastes (`but`/`mas`, entre outros) encerram o escopo da qualificação. As regras cobrem os exemplos e regressões descritos nos testes; não são análise linguística universal.
- **Privacidade:** `must_not_include` mantém correspondência literal incondicional. Nenhuma regra de negação ou escopo se aplica a essa lista.
- **Regressões:** contradições reproduzidas EN/PT exigem `content_ok=True` e `forbidden_ok=False`, com os demais checks corretos; frases de incerteza qualificadas passam; a proibição literal continua falhando mesmo dentro de uma frase negada; formulações reais r2 e divergência verdadeira com ausência de reembolso/correção permanecem cobertas.
- **Validações:** Ruff nos arquivos Python alterados: passou; formatação Ruff: passou; `pytest tests/integration/test_evaluation_runner.py --basetemp=.pytest_cache/v030-r6-directed-20261027b`: **29 passed**; `tools/scripts/lint_and_tests.py --strict` com `PYTHONUNBUFFERED=1` e `PYTEST_ADDOPTS=--basetemp=.pytest_cache/v030-r6-strict-20261027`: **191 passed**, estrutura, Ruff e skills válidas; `git -c core.fsmonitor=false diff --check`: passou.
- **Limitações:** nenhuma API paga foi chamada. Sem validação de conversa real r6 nesta etapa. Como `src/merchant_assistant/evaluation/runner.py` mudou, o candidato de runtime precisa de novo build antes de replay/QA.
- **Preservações:** Router v5, critérios de produto, rotas/status/ferramentas/valores/fontes/grounding, holdout e relatórios reais anteriores não foram alterados. A alteração de cenários se limita à lista de afirmações proibidas nas duas linhas dev de evidência insuficiente.
- **Próxima ação:** Reviewer independente revisar a semântica e os testes; Supervisor ajustar a whitelist do replay para aceitar a anotação `must_not_assert` preservando igualdade dos demais checks e de todo holdout.
