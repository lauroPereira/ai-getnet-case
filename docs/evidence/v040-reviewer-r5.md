# Parecer do Reviewer independente — v0.4.0 local r5

**Parecer: apto para seguir à etapa de QA da história.** Este parecer é técnico e não declara QA, integração ou release concluídos.

## Candidato e independência

- Candidato: `v0.4.0-local-r5`, branch `codex/v0.4.0-perfis-interface`.
- Base e HEAD: `bd549cc921ccffb37bd304a0959b8a4b690d6421`.
- Fingerprint combinado: `a65496ada0c9757e11a581fb61a6236a6606f0fd5a5ed02c31f44ce407999d34`.
- Fingerprint runtime: `b8d3a1845ac4ea16c50272bb800248bc7c4df4dbd172e40c47ae220fb063c4a5`.
- Fingerprint dos insumos de build: `ed67d7ff81f6ed49042e9f3aa332ac145fdd004fa38d6b99e7a05072155d816d`.
- Independência: não consultei relato nem conclusão do Developer. Sou o mesmo Reviewer das rodadas anteriores; o parecer é independente da implementação, mas não constitui um novo contexto de revisão.
- Antes da revisão, conferi 50/50 arquivos backend, 84/84 frontend, 127/127 runtime e 128/128 build, sem arquivos ausentes ou hashes divergentes. Os fingerprints combinado, runtime e build conferiram com o manifesto r5.

## Revisão do delta r4 → r5

A alteração separa os dados de custo/reserva dos parâmetros enviados pelo adaptador. `RunContext.reserve()` continua estimando o custo com `max_output_tokens`, mas somente escreve `effective_parameters_by_agent` quando o adaptador informa explicitamente `effective_parameters`. O adaptador TypeSafe segue reservando com limite interno de 80 e não marca esse limite como efetivo. OpenAI/DeepSeek informam o limite aplicado no adaptador, que é o valor limitado no `CallSpec` e enviado no payload.

Em `/v1/router/compare`, `_decision()` deriva os parâmetros efetivos do wrapper usado ou, no caso do JEV, retorna mapa vazio. A decisão JEV serializada não depende do mapa de metering que também registra o custo LLM da comparação. Em `/v1/messages`, a comparação consumida fornece a decisão sem nova chamada ao Router; o snapshot mescla o mapa da decisão selecionada. O caso JEV mantém mapa vazio, e o caso LLM mantém seu valor efetivo.

Não identifiquei alteração de schema no delta: o OpenAPI produzido por `create_app(...).openapi()` coincide integralmente com `openapi-v1.json` do workspace web: 13 paths idênticos, objetos por path idênticos e 18 schemas idênticos. O manifesto confirma que o workspace web não mudou byte a byte desde r4. Não há mudança na migração nem no contrato de `POST /messages` legado no delta revisado.

## Evidência própria

- Regressões afetadas: `PYTHONDONTWRITEBYTECODE=1 .venv\Scripts\python.exe -m pytest -q tests/unit/test_jev_adapter.py tests/unit/test_profile_output_parameters.py tests/integration/test_v1_api.py -k "jev_reservation_limit_is_internal_and_not_an_effective_provider_parameter or comparison_and_reused_run_report_only_provider_applied_router_parameters or profile_output_cap_reaches_provider or router_comparison_budget_rejection_is_explicit_and_preserves_prior_cost" --basetemp=.pytest_cache\v040-review-r5-focused` — **7 passaram**. Inclui as quatro combinações de limite de orçamento parametrizadas.
- Reuso/consumo único: `PYTHONDONTWRITEBYTECODE=1 .venv\Scripts\python.exe -m pytest -q tests/integration/test_v1_api.py::test_router_comparison_is_router_only_and_consumed_once --basetemp=.pytest_cache\v040-review-r5-consume` — **1 passou**.
- Reproduzi também o fluxo dos adaptadores sem rede. JEV: reserva estimada com limite 80, payload com `model/questions/state`, mapa efetivo vazio e uma liquidação. LLM OpenAI fake com cap de perfil 128: estimativa de saída 128, parâmetro na reserva 128, payload 128 e mapa efetivo `{'personality': {'max_output_tokens': 128}}`.
- O teste integrado do candidato executa dois pares de comparação com transportes fake, confere JEV vazio e LLM em 300, reusa a decisão escolhida em atendimento e confirma ausência de segunda chamada Router. O teste de orçamento mantém rejeição explícita e contabilização do custo anterior.
- A inspeção do adaptador confirma que `parse`, `run_tools` e `web_search` passam parâmetros efetivos OpenAI/DeepSeek ao medidor; TypeSafe mantém contrato restrito ao Router e não anuncia limite de saída.

## Achados e limites

- Não encontrei achado técnico no delta r4 → r5: o P2 do parecer r4 foi corrigido sem mudar a estimativa JEV de 80, a liquidação, a guarda de orçamento, o uso único da comparação ou o limite real enviado por LLM.
- Não rodei a suíte completa nem a história ponta a ponta. Provedores reais, embeddings, judge e consulta autenticada de metadados não foram executados. CA-32 real permanece explicitamente pendente; os fakes demonstram apenas contrato e fluxo local, não disponibilidade, resposta ou custo efetivos do provedor.
- A construção disponibilizada pelo Supervisor é incremental sobre a imagem r2, sem rede e sem rebuild independente da receita Docker canônica. Não usei o endpoint pago legado.

## Próximo responsável

QA pode executar a história v1 no candidato r5 e registrar resultados e limitações, mantendo CA-32 real pendente enquanto não houver autorização e evidência de provedor real. Este parecer não substitui essa validação.
