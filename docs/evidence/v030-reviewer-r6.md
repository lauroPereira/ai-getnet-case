# Revisão independente — v0.3.0 jornadas, rodada 6

## Parecer

**Apto para revalidação real pelo Supervisor e, depois dela, para QA.** O P2 da r5 foi corrigido: afirmações positivas contraditórias falham especificamente em `forbidden_ok`, enquanto formulações qualificadas de dúvida passam. O bloqueio anterior está resolvido nesta rodada.

## Independência e candidato

- Reavaliação independente do Developer, a partir do diff, do código, das respostas HTTP r2 e de reproduções locais próprias.
- Candidato `v0.3.0-local-r6`, branch `codex/v0.3.0-jornadas`, base/HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- Conferi 49/49 hashes de arquivos e o fingerprint de produto `f8efcec3918320c287b3b6c2faef2f38edca4847a02b19bcd781ed7e920a1af9`. Recalculei o fingerprint runtime `e58e5668172b992ebabf9777237686a2e0357cdccd5c7657436acbbc703b1cde`; ambos coincidem. Os hashes dos 31 arquivos de runtime, 126 insumos de build e 9 harnesses também conferem.
- O diff dos manifestos r5/r6 limita-se a `src/merchant_assistant/evaluation/runner.py`, `tests/scenarios/business_journeys.jsonl` e `tests/integration/test_evaluation_runner.py`. Os demais arquivos de produto não mudaram.
- Imagens em execução conferidas por `docker inspect`: API/QA `sha256:f3181423b249dd14368e4b49bb09790c376371097cabc723fbaaba49b41e3699`; mocks `sha256:89364d891ed4a596d6caf72712a00deaec4662359c2dc116fbe9dc6043aea64e`. GET `/ready` confirmou API e QA prontos, Router 5, saldo exibido de US$0,0142 e 145 chunks; GET `/openapi.json` confirmou `/messages`, `/ready` e `/traces/{request_id}`. Nenhum POST foi feito.

## P2 da r5: afirmação qualificada e negação literal

O runner acrescenta `must_not_assert` como verificação separada de `must_not_include`. A segunda permanece uma busca literal e incondicional; a primeira usa `_assertion_is_present`, com um conjunto delimitado de qualificadores EN/PT e fronteiras de oração. Isso evita suprimir uma afirmação posterior só porque a resposta começou com dúvida.

Reproduzi diretamente `_checks` usando respostas em que `content_ok` era verdadeiro:

| Resposta de evidência insuficiente | `content_ok` | `forbidden_ok` | Resultado |
| --- | --- | --- | --- |
| EN: “There is enough evidence to compare the fee. There is no expected pricing fee or recorded charge to compare.” | true | false | reprova |
| EN: “The fee is correct. There is no expected pricing fee or recorded charge to compare.” | true | false | reprova |
| PT: “A taxa está correta. Não há taxa esperada para comparar.” | true | false | reprova |
| EN: “I cannot confirm whether the fee is correct.” | true | true | passa |
| PT: “Não foi possível confirmar se a taxa está correta.” | true | true | passa |

Também testei afirmação depois de qualificador na mesma estrutura de contraste (`..., but the fee is correct` / `..., mas a taxa está correta`) e depois de outra oração. Em ambos os idiomas a afirmação independente fez `forbidden_ok=false`. As frases de incerteza qualificadas, isoladas e correspondentes à falta de evidência, mantiveram todos os checks verdadeiros.

O teste de privacidade injeta o literal `customer ID 123` em `must_not_include` e avalia “Do not disclose customer ID 123.”; `content_ok` permanece verdadeiro e `forbidden_ok` falha. Portanto uma instrução negada não oculta a presença do literal. A implementação combina a rejeição literal e incondicional com as afirmações semânticas; uma não desativa a outra.

## Replay das respostas HTTP r2

Inspecionei o harness atualizado antes de reproduzir sua lógica em memória, sem gravar o relatório produzido pelo script. O dataset de cenários só mudou nos cinco casos dev de condições, divergência, evidência insuficiente EN/PT e cancelamento PT; as alterações ficam limitadas às anotações de conteúdo/negação. Nenhum cenário holdout foi alterado.

Recalculei os 40 casos r2. Os cinco casos afetados agora passam, incluindo as cinco respostas reais anteriores que estavam reprovadas. Permanecem 17/17 casos holdout aprovados. Para todas as 40 respostas, rota, status, idioma, ferramentas, valores, fontes e grounding coincidem com o original; nenhuma divergência em checks fora de conteúdo/negação.

## Verificações

- `python -m pytest tests/integration/test_evaluation_runner.py --basetemp .pytest_cache/v030-review-r6`: **29 passed**. Inclui os positivos e negativos EN/PT, combinações contraditórias, qualificadores em outra oração/contraste e literal de privacidade negado.
- `ruff check src/merchant_assistant/evaluation/runner.py tests/integration/test_evaluation_runner.py`: **All checks passed**.
- GET local de readiness/OpenAPI e inspeção read-only das imagens: concluídos; API e QA usam a imagem r6 fixada.
- Não li `.env`, não fiz POST nem chamadas pagas, não alterei produto/testes/manifestos nem executei ações Git externas. Nenhuma lacuna bloqueia o replay sem custo ou a revalidação real.

## Passagem

O P2 da r5 está encerrado para o escopo coberto. O Supervisor pode executar a revalidação HTTP real, incluindo FU02 no Router 5, sob o saldo compartilhado. Após verificar o resultado real e manter o candidato fixo, encaminhar ao **QA** para a história de uso e demais verificações funcionais.
