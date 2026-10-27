# Passagem do Developer — validação r4 da v0.3.0

- Papel: Developer, correção despachada após o parecer independente [v030-reviewer-r3.md](v030-reviewer-r3.md).
- Resultado: verificações automáticas fortalecidas; imagens e produto r3 podem ser reutilizados, pois não houve mudança em código de runtime, prompts ou insumos de imagem.
- Branch/base: `codex/v0.3.0-jornadas`, base `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`; sem commit.
- Estado: apto para nova revisão independente da validação; QA e revalidação paga permanecem pendentes até parecer apto.

## Arquivos alterados desde r3

- `tests/scenarios/business_journeys.jsonl`: o caso de divergência passa a rejeitar negações explícitas em inglês e português. O caso de evidência insuficiente aceita formulações claras de ausência de evidência e evita que `must_not_include` coincida com a mesma frase negativa. As alternativas e negativas dos outros cenários, rotas, status, ferramentas, valores, fontes e grounding foram preservados; nenhum cenário holdout foi editado.
- `tests/integration/test_evaluation_runner.py`: testes de regressão exercitam os mesmos checks com resposta contraditória, resposta verdadeira acompanhada de ausência de reembolso/correção, insuficiência em inglês/português e alegação positiva de evidência suficiente.
- `docs/evidence/v030-developer-r4.md`: esta passagem.

Não alterei `src/`, `prompts/`, `README.md`, `CHANGELOG.md`, Docker, fixtures ou configurações. Não alterei manifestos nem relatórios de avaliação/revisão. O manifesto r3 lista a alteração do cenário de jornada; o teste de integração foi acrescentado como harness desta correção.

## Validações observadas

- Ruff em `tests/integration/test_evaluation_runner.py`: passou antes dos testes direcionados.
- `git diff --check` nos arquivos alterados: passou; a checagem global também passou.
- Testes direcionados dos checks: **8 passed, 3 deselected**. Casos negativos mantêm rota, status, valores, ferramenta, fonte e grounding corretos e falham na proteção contra contradição; respostas afirmativas verdadeiras de divergência com “no refund/correction” passam; formulações de insuficiência EN/PT passam; afirmações de evidência suficiente continuam reprovadas.
- Avaliação programada offline dos 13 cenários v0.3.0: **13/13 passaram**, com todos os checks automáticos, custo US$ 0. As respostas são da política scripted; esta verificação não substitui modelo real.
- `.venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`, `PYTHONUNBUFFERED=1`, basetemp `.pytest_cache/v030-r4-strict-20261027`: **173 passed em 105,99 s**; Ruff, estrutura e skills passaram.
- Nenhuma chamada paga, acesso a rede externa, runtime ou contêiner foi realizado pelo Developer.

## Passagem

O delta não altera imagens nem fingerprint de runtime do produto; o Supervisor pode reutilizar as imagens r3 para a revalidação futura. Próximo responsável: Reviewer independente para revisar os dois arquivos de validação e estes testes. Somente após revisão apta o Supervisor deve decidir a revalidação real no ledger autorizado e encaminhar a QA. Este resultado local não declara aceite nem liberação.
