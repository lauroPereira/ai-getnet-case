# Revisão independente — v0.3.0 jornadas, rodada 3

## Parecer

**Correções necessárias.** A correção de isolamento de r1 passou; a validação automática ampliada pela tarefa 25 ainda pode aprovar uma afirmação que contradiz a divergência e rejeitar uma resposta verdadeira de evidência insuficiente. Como esse gate cobre o comportamento central de preço da CA-21/CA-31, o candidato não deve avançar para QA até corrigir as duas verificações.

## Independência e candidato

- Contexto independente do implementador, com critérios e comportamento rederivados: **independente**.
- Branch `codex/v0.3.0-jornadas`; base e HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- Candidato `v0.3.0-local-r3`, manifesto `docs/evidence/v030-candidato-r3.json`.
- Conferência própria: 45/45 hashes de produto, 29/29 hashes de runtime, 125/125 insumos de build e 3/3 hashes de harness conferem. Recalculei ambos os fingerprints com o algoritmo documentado: produto `052bc6ca8e10f053cf9f2612e27563e3367bef34e8adb493657869598f2bc660`; runtime `f0c8d937187e8929a214634cafd3416a8f912314ada5c462be5184c77d983d12`.
- O delta declarado desde r1 contém oito arquivos, e a comparação própria dos mapas de hash confirmou esses oito caminhos.
- Imagens confirmadas: API `sha256:af1334f5eb9a1e935747411f1e4696b26c5a9d11a13bb0f237ba67870e1e633c`; mocks `sha256:025584d7927b745f645b15a67e1ec79c581fe7bbd932cd305dc0c60cb6005002`.

## Achados

### P2 — verificação de conteúdo aprova resposta que nega uma divergência

- **Condição:** a resposta contém a palavra `divergence` e R$ 0,75, mas afirma que não há divergência. O cenário exige apenas a inclusão da substring `divergence`, valor de 75 centavos, encaminhamento, fonte e demais campos; não possui `must_not_include` para a negação.
- **Impacto:** o gate pode marcar como aprovada uma resposta factualmente oposta ao resultado determinístico `divergence`, enfraquecendo a evidência de CA-21 e CA-31. O encaminhamento, sozinho, não corrige a afirmação contraditória.
- **Local:** `tests/scenarios/business_journeys.jsonl`, caso `V030-PRICE-DIVERGENCE`; verificador substring-only em `src/merchant_assistant/evaluation/runner.py:81-84`.
- **Reprodução própria:** carreguei o caso e executei `_checks` com rota `support`, status `handoff`, ferramenta `simulate_pricing`, fonte sintética e resposta `No divergence was found. The difference is R$ 0,75 and I am handing the case to a human.`. Resultado: todos os checks, inclusive `content_ok`, `amounts_ok` e `forbidden_ok`, retornam `true`.
- **Correção sugerida:** incluir verificações negativas pertinentes para negação/ausência de divergência ou usar validação que distinga afirmação de negação. Acrescentar teste negativo com a reprodução acima.

### P2 — verificação de insuficiência rejeita formulação correta por substring

- **Condição:** a frase verdadeira `There is not enough evidence to compare the fee.` contém a substring configurada em `must_not_include` (`enough evidence to compare`) e não coincide com nenhuma alternativa positiva atual do caso inglês.
- **Impacto:** uma resposta correta e compatível com `insufficient_evidence` é reprovada como conteúdo e violação. Isso mantém um falso negativo precisamente no caso em que a tarefa 25 pede equivalência semântica.
- **Local:** `tests/scenarios/business_journeys.jsonl`, caso `V030-PRICE-INSUFFICIENT`; correspondência literal em `src/merchant_assistant/evaluation/runner.py:82-83`.
- **Reprodução própria:** `_checks` retorna `content_ok=false` e `forbidden_ok=false` para `There is not enough evidence to compare the fee.`; rota, status, ferramenta, fonte e grounding permanecem verdadeiros. O mesmo ocorre com `Não há evidência suficiente para comparar a taxa desta venda.` no caso português, que a lista atual não cobre.
- **Correção sugerida:** retirar a frase positiva da lista de negativos ou torná-la sensível à negação, e acrescentar formulações corretas sem alterar as restrições contra declarar evidência suficiente.

## Reavaliação dos critérios e correção r1

- **RF-08:** `financial_evidence` normaliza valores de pricing/cobrança em BRL com o helper `money`; apenas inclui valores das fontes quando a comparação não é `insufficient_evidence`. O guardrail de resposta permanece inalterado. O teste verifica que R$ 80,00/R$ 79,25 são aceitos, R$ 99,99 é rejeitado e R$ 79,25 não pode ser citado quando a evidência de pricing/cobrança é insuficiente.
- **RF-15:** a consulta de cancelamento agora exige `c.customer_id` e `s.customer_id` iguais ao cliente confiável da requisição. O teste r3 insere vínculo cruzado sintético e confirma que ID e status da venda alheia não aparecem. A falha de isolamento P2 da r1 foi corrigida.
- **RF-16:** a função de eventos conserva seleção por período; o novo teste comprova que a busca padrão recente encontra o evento de ontem e que os períodos explícitos `today` e `yesterday` mantêm seus limites.
- **RF-32/RF-46:** a comparação segue em inteiros de centavos, nas quatro categorias, e usa as duas fontes independentes. A normalização apresentada ao modelo deriva desses campos de origem e não desloca a aritmética para o modelo.
- **Cenários:** revisei as alternativas e negativas alteradas. A intenção é compatível com as respostas observadas na avaliação r1, mas o verificador literal causa os dois problemas acima; logo, equivalência e proteção contra contradição ainda não estão demonstradas.

## Evidência executada e limites

- `.\.venv\Scripts\python.exe -m pytest --basetemp .pytest_cache/v030-review-r3`: **165 passed** em 90,07 s.
- `.\.venv\Scripts\python.exe -m ruff check src tests`: **All checks passed**.
- Smoke próprio com as imagens r3 pela rede interna: `MockServiceClient` obteve 194 centavos no pricing e 194 centavos na cobrança para a venda sintética; o cliente incorreto recebeu `FORBIDDEN_RESOURCE`.
- Não iniciei o stack completo da API nem fiz nova revalidação real ou chamada paga; o Supervisor estava preparando esses passos. Não li `.env` nem runtime anterior, e não alterei produto, testes, critérios, história ou manifesto.

## Passagem

Próximo responsável: **Developer**, para fortalecer os checks de negação e equivalência com casos positivos/negativos reproduzíveis, sem reduzir valores, rota, status, ferramentas, fontes ou guardrail. Depois, fixar um novo manifesto e devolver à revisão. QA aguarda parecer apto.
