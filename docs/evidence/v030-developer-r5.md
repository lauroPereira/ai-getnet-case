# Passagem do Developer — continuidade e equivalência r5

- Papel: Developer; correção despachada após a rodada real HTTP r2.
- Objetivo: manter o suporte/handoff quando a falha persiste após encaminhamento e alinhar as verificações de conteúdo às cinco formulações corretas observadas, sem alterar critérios nem guardrails.
- Estado: mudanças locais validadas; revisão independente pendente antes do replay real de conversas.
- Branch/base: `codex/v0.3.0-jornadas`, base `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`; sem commit.

## Arquivos alterados desde r4

- `prompts/router.v5.md`: coloca falha persistente após handoff acima da classificação acknowledgement; preserva agradecimento neutro e confirmação explícita de resolução, mantém rota e tópico de suporte e orienta a reutilização do handoff/protocolo existente.
- `tests/scenarios/business_journeys.jsonl`: acrescenta conteúdo alternativo para a diferença entre condições e a divergência EN; reconhece `insufficient evidence` e as formulações condicionais PT sem frases negativas sobrepostas; inclui a variante entre aspas tipográficas do status solicitado. Mantém todos os valores, fontes, ferramentas, rotas, status, conteúdo dos demais cenários e verificações de grounding. Só cinco linhas dev de validação mudaram; nenhum cenário de holdout foi editado.
- `tests/integration/test_evaluation_runner.py`: adiciona regressões para cinco formulações verdadeiras e seus contrapontos contraditórios, preservando checagens financeiras, de rota, status, ferramentas, fonte e grounding; verifica também que o prompt Router 5 contém a regra pós-handoff.
- `docs/evidence/v030-developer-r5.md`: esta passagem.

Não alterei `src/`, o código do avaliador em `src/merchant_assistant/evaluation/runner.py`, dados, prompts anteriores, README, changelog ou `tests/scenarios/followup.jsonl`. O avaliador continua usando correspondência literal; variantes verdadeiras ficam em `must_include_any` e frases contraditórias ficam em `must_not_include`. Os negativos de insuficiência foram escolhidos como afirmações positivas inequívocas para não rejeitar uma frase subordinada como “não foi possível confirmar se a taxa está correta ou incorreta”. As proteções de privacidade, valores e grounding não foram flexibilizadas.

O Dockerfile copia `prompts/` para a imagem; por isso a aplicação efetiva do Router v5 requer rebuild, embora não tenha havido mudança de `src/`, avaliador, fixtures ou configuração.

## Validações observadas

- Ruff do arquivo Python alterado e `git diff --check` dos arquivos alterados passaram antes dos testes.
- Comparação com `.pytest_cache/v030-evaluation-tests-r4.txt` e `.pytest_cache/v030-business-scenarios-r4.jsonl`: delta de validação limitado ao novo prompt Router, cinco linhas dos cenários de tarefa 25 e regressões do harness. Os snapshots r4 foram preservados.
- Testes direcionados de `tests/integration/test_evaluation_runner.py`: **19 passed**. Cobrem as cinco respostas válidas reportadas, contrapontos contraditórios EN/PT, aspas tipográficas, mensagens pós-handoff e o prompt selecionado.
- Avaliação programada offline dos 13 cenários novos: **13/13 passaram** em rota, status, ferramentas, valores, conteúdo, proibições, fontes e grounding; custo US$ 0.
- `python tools/scripts/lint_and_tests.py --strict`, com `PYTHONUNBUFFERED=1` e basetemp `.pytest_cache/v030-r5-strict-20261027`: **181 passed em 91,45 s**; Ruff, estrutura e skills passaram.
- FU02 também permaneceu aprovado no teste offline de conversas da suíte; o cenário reservado não foi editado. Isso não substitui o replay HTTP real.
- Nenhuma chamada paga ou externa foi feita pelo Developer. O ledger compartilhado permanece conforme o Supervisor reportou: US$0,13584893 de US$0,15.

## Próxima ação

Supervisor: fixar hashes e pedir nova revisão independente. Após parecer apto, incorporar `prompts/router.v5.md` à imagem e executar somente a revalidação autorizada das conversas, sem repetir os 40 casos. QA aguarda. Relatórios reais e de revisão anteriores permanecem como evidência histórica e não foram regravados.
