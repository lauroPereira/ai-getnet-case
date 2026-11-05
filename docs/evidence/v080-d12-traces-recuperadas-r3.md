# Traces recuperadas do QA D12 pré-holdout r3

O relatório de avaliação registra os IDs das respostas. O Supervisor os cruzou com as tabelas `requests` e `steps` em `.pytest_cache/qa-v080-r1/runtime/traces.sqlite3`, em modo somente leitura. Foram encontradas **132 de 132 traces**. Houve 117 respostas com ao menos uma decisão de replanejamento. O maior `plan_hops` foi **2**, dentro do limite de 3.

O [artefato recuperado](v080-d12-traces-recuperadas-r3.json) contém, por ID e repetição, o total de saltos, a sequência das decisões e os respectivos campos `next`, `reason`, `review`, `hops` e `origin`. A última decisão coincide com o total de saltos em cada resposta que replanejou.

O relatório r3 não incluía esses campos no JSON. A evidência existia no banco de traces do runtime, portanto foi recuperada sem custo e sem reexecutar as respostas. As três execuções de `REPLAN-TOOL-DOWN` continuam inválidas para o cenário de indisponibilidade. As falhas de resposta em outros cenários continuam registradas no [parecer de QA](v080-d12-pre-holdout-r3.md).
