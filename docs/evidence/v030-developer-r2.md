# Passagem do Developer — v0.3.0 correção r2

- Papel e responsável: Developer; correção despachada pelo Supervisor após parecer independente.
- Objetivo: corrigir exclusivamente o P2 de isolamento registrado em [v030-reviewer-r1.md](v030-reviewer-r1.md), sem avançar a QA.
- Estado: correção apta à nova revisão; candidato r2 congelado após validações locais.
- Branch: `codex/v0.3.0-jornadas`.
- Base e HEAD: `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`; sem commit. O manifesto r1 e o relatório do Reviewer foram preservados sem alteração. Os hashes do novo candidato devem ser fixados pelo Supervisor.
- Próximo responsável: Supervisor para atualizar o manifesto do candidato; depois Reviewer independente para reavaliar P2. QA só após parecer apto.

## Correção e arquivos alterados desde o candidato r1

O vínculo de cancelamento agora exige que `sale_cancellations.customer_id` e `sales.customer_id` sejam ambos iguais ao cliente confiável da requisição. A regressão insere um cancelamento sintético inconsistente, com `customer_id` do lojista atual e transação de uma venda alheia. A resposta esperada contém exatamente o cancelamento legítimo; nenhuma linha com ID ou status da venda alheia é retornada.

Comparação dos hashes atuais contra os 42 arquivos do manifesto r1 encontrou **exatamente dois arquivos do produto alterados** e nenhum arquivo ausente:

- `src/merchant_assistant/tools/domain.py`
- `tests/unit/tools/test_business_journeys.py`

Este relatório é uma nova evidência e não integra nem modifica o manifesto r1. Nenhum outro arquivo do candidato foi alterado nesta correção.

## Validações

- `.venv/Scripts/python.exe -m pytest tests/unit/tools/test_business_journeys.py`, com `PYTEST_ADDOPTS=--basetemp=.pytest_cache/v030-r2-focused-20261027c`: **7 passed**.
- `.venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`, com `PYTHONUNBUFFERED=1` e `PYTEST_ADDOPTS=--basetemp=.pytest_cache/v030-r2-strict-20261027`: **164 passed em 106,73 s**; Ruff, validação de estrutura e skills passaram.
- `.venv/Scripts/python.exe -m ruff check src/merchant_assistant/tools/domain.py tests/unit/tools/test_business_journeys.py`: passou.
- `git -c core.fsmonitor=false diff --check`: passou.
- Verificação do manifesto r1: exatamente `domain.py` e `test_business_journeys.py` diferem dos hashes r1; 42/42 caminhos existem.

Os testes usam dados sintéticos e basetemp relativo novo sob `.pytest_cache`. Não acessei nem alterei o contêiner/runtimes da rodada real, não fiz chamadas pagas ou externas e não editei o manifesto ou relatório do Reviewer. Nenhum commit, push, merge, tag ou publicação foi feito.

## Passagem

O P2 está corrigido no código e coberto por regressão. A rodada real autorizada em contêiner permanece responsabilidade do Supervisor e não foi interrompida. A revisão r1 é de candidato anterior e não aprova r2. Atualize os hashes para r2 e devolva à revisão independente; QA permanece pendente até novo parecer.
