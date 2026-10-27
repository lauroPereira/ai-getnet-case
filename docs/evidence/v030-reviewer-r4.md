# Revisão independente — v0.3.0 jornadas, rodada 4

## Parecer

**Apto para QA.** Os dois achados P2 da r3 foram corrigidos no escopo r4: as verificações rejeitam negações da divergência em inglês e português, e aceitam formulações claras de evidência insuficiente nas duas línguas sem aceitar a afirmação de que a evidência é suficiente.

## Independência e candidato

- Revisão em contexto independente do implementador: **independente**.
- Candidato: `v0.3.0-local-r4`, branch `codex/v0.3.0-jornadas`, base e HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- Manifesto `docs/evidence/v030-candidato-r4.json`: conferi 46/46 hashes de produto, 29/29 hashes de runtime, 125/125 insumos de build e 5/5 harnesses. Recalculei o fingerprint de produto (`d626b894b143a496a8f9d67db7d50f5088d4fc84d10e39b51fbd958d90cfef94`) e o de runtime (`f0c8d937187e8929a214634cafd3416a8f912314ada5c462be5184c77d983d12`); ambos coincidem.
- Comparação dos mapas r3/r4 confirma somente o delta declarado: `tests/scenarios/business_journeys.jsonl` e `tests/integration/test_evaluation_runner.py`. Código de produto, dados, prompts e runtime não mudaram desde r3.

## Reproduções próprias dos achados r3

Executei `_checks` diretamente para os oito casos abaixo. Usei rotas, status, ferramentas, fontes e traces corretos; respostas de divergência incluíram o valor de R$ 0,75.

| Caso | Resposta | Resultado independente |
| --- | --- | --- |
| Divergência EN | “No divergence was found. The difference is R$ 0.75 and I am handing the case to a human.” | `content_ok=true`, `amounts_ok=true`, `forbidden_ok=false`; o caso não passa |
| Divergência EN | “A divergence of R$ 0.75 was found. No refund or correction is being made; I referred it for review.” | Todos os checks passam |
| Divergência PT | “Não há divergência. A diferença é R$ 0,75 e encaminhei para análise de um atendente.” | `content_ok=true`, `amounts_ok=true`, `forbidden_ok=false`; o caso não passa |
| Divergência PT | “Foi encontrada uma divergência de R$ 0,75. Não haverá reembolso nem correção; encaminhei para revisão.” | Todos os checks passam |
| Evidência insuficiente EN | “There is not enough evidence to compare the fee.” | Conteúdo e negativos passam; todos os checks passam |
| Evidência insuficiente EN | “There is enough evidence to compare the fee.” | Conteúdo e/ou negativos reprovam; o caso não passa |
| Evidência insuficiente PT | “Não há evidência suficiente para comparar a taxa desta venda.” | Conteúdo e negativos passam; todos os checks passam |
| Evidência insuficiente PT | “A evidência é suficiente para comparar a taxa.” | Conteúdo e/ou negativos reprovam; o caso não passa |

As strings negativas foram adicionadas aos quatro casos em `tests/scenarios/business_journeys.jsonl:3-4,10-11`; as reproduções foram incorporadas em testes de contrato em `tests/integration/test_evaluation_runner.py:67-119`. As verificações continuam exigindo rota, status, ferramenta, valor de 75 centavos, fontes e ausência de violação, conforme aplicável; nenhuma exigência de produto foi removida.

## Verificações executadas

- `.\.venv\Scripts\python.exe -m pytest tests/integration/test_evaluation_runner.py --basetemp .pytest_cache/v030-review-r4`: **11 passed**.
- `.\.venv\Scripts\python.exe -m ruff check tests/integration/test_evaluation_runner.py`: **All checks passed**.
- GET local a `http://127.0.0.1:18030/ready`: `ready=true`, app `0.3.0`, esquema 5, índice com 145 chunks, prompts Router 4 e Support 7.
- GET local a `/openapi.json`: rotas esperadas presentes, incluindo `/messages`, `/ready` e `/traces/{request_id}`.
- Nenhum POST de mensagem, chamada paga, acesso a `.env` ou runtime anterior foi feito. As chamadas pagas da revalidação permanecem sob responsabilidade do Supervisor e do ledger compartilhado.

## Limites e passagem

Esta revisão aprova o delta de validação r4 para QA; não substitui a rodada real de regressão que o Supervisor ainda fará, nem a história funcional de QA. A avaliação por frases continua sendo uma lista de padrões, então não cobre todas as paráfrases naturais possíveis; os positivos e negativos da tarefa 25 e as duas reproduções que bloquearam r3 agora estão cobertos sem mascarar os checks centrais.

Próximo responsável: **QA**, pela história v0.3.0 no candidato fixado r4, após o Supervisor concluir as validações reais pendentes sem alterar o produto ou o candidato.
