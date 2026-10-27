# Parecer do Reviewer independente — v0.4.0 local r4

**Parecer: correções necessárias.**

## Candidato e independência

- Candidato: `v0.4.0-local-r4`, branch `codex/v0.4.0-perfis-interface`.
- Base e HEAD: `bd549cc921ccffb37bd304a0959b8a4b690d6421`.
- Fingerprint combinado: `e785167251c25158cc1d5e82c1cd487785d0132244c3aa890dadf0e4d5caf5ef`.
- Fingerprint runtime: `12582cbe7a91b8db62818bc0b1abe6cc73731f5d680bc5adc361023b47422eeb`.
- Fingerprint dos insumos de build: `8c13c0229e66f449c3f5bb81aa4d47805635ef5d27d0398234a380f585df8b7d`.
- Independência: revisão feita sem ler relato ou conclusão do Developer. Sou o mesmo Reviewer das rodadas anteriores; portanto, a separação é em relação à implementação, não uma segunda revisão-contexto novo.
- Os mapas do manifesto foram recalculados antes da revisão: 48/48 arquivos backend, 84/84 frontend, 127/127 runtime e 128/128 build, sem ausências ou divergências. O fingerprint combinado bate com o candidato. Os mesmos mapas serão conferidos novamente após o relatório.

## Achado

### P2 — limite usado só para estimar custo aparece como parâmetro efetivo do JEV

**Condição:** quando uma comparação escolhe JEV como Router. `JevRouter.parse()` reserva custo com `max_output_tokens=80`, mas o corpo enviado ao System One contém apenas `model`, `state` e `questions`; não há limite de saída configurável nesse contrato. `RunContext.reserve()` grava todo valor recebido pelo meter em `effective_parameters_by_agent`. A rota de comparação devolve esse mapa como configuração efetiva e `/v1/messages` o incorpora no trace/snapshot da decisão selecionada.

**Impacto:** a comparação e o snapshot afirmam que JEV executou com `max_output_tokens: 80`, embora esse número seja apenas parâmetro interno da estimativa e não tenha sido aplicado ao provedor. Isso contradiz a semântica de configuração efetiva/snapshot de RF-51 e a regra da implementação de que JEV/TypeSafe não oferece esse parâmetro. Um consumidor do trace pode interpretar incorretamente a configuração comparada.

**Localização:** [run.py](../../src/merchant_assistant/orchestration/run.py#L82) grava o campo; [jev.py](../../src/merchant_assistant/llm/jev.py#L95) fornece o valor somente à reserva e [jev.py](../../src/merchant_assistant/llm/jev.py#L103) monta o payload sem esse campo; [v1.py](../../src/merchant_assistant/api/v1.py#L454) expõe o mapa da comparação e [v1.py](../../src/merchant_assistant/api/v1.py#L650) o copia para o snapshot.

**Reprodução própria, sem rede/provedor:** executei `JevRouter.parse()` com `RunContext` e transporte fake. Saída observada: `provider_payload_keys=['model', 'questions', 'state']`, `trace_effective_parameters={'max_output_tokens': 80}`, `calls=1`. A decisão tipada sintética foi aceita. A correção deve distinguir limite interno de reserva de parâmetro efetivamente enviado; JEV deve deixar o mapa de parâmetros efetivos vazio.

## Evidência favorável observada

- Backend: `PYTHONDONTWRITEBYTECODE=1 .venv\Scripts\python.exe -m pytest -q tests/integration/test_v1_api.py tests/unit/test_profile_output_parameters.py -k "output_token_parameter or rejects_unknown_or_unsafe_output_token_parameters or catalog_publishes_only_documented_output_parameter_compatibility or profile_output_cap_reaches_provider" --basetemp=.pytest_cache/v040-review-r4-independent` — **8 passaram**. Cobre publicação/snapshot do parâmetro compatível, rejeições e reserva/payload do adaptador OpenAI fake.
- Interface: `PYTHONDONTWRITEBYTECODE=1 .venv-v040\Scripts\python.exe -m pytest -q tests\test_interface.py -k "simulated_and_recorded_modes or simulated_model_catalog or admin_ui_offers_documented_output_token_limit" --basetemp=.pytest_cache\v040-review-r4-independent-web` — **3 passaram, 9 não selecionados**. Cobre o rótulo Gravado, catálogo simulado e controle administrativo do limite.
- Contrato/cliente: `... pytest -q tests\test_interface.py -k "generated_client_operations_match_openapi_v1_contract or openapi_documents_session_bearer_for_protected_operations or openapi_documents_router_budget_error_body" --basetemp=.pytest_cache\v040-review-r4-contract` — **3 passaram, 9 não selecionados**.
- Consultei somente `GET http://127.0.0.1:18841/openapi.json` no serviço sintético instalado para a revisão: 13 caminhos; o conjunto coincide com `openapi-v1.json`, incluindo `/v1/router/compare` e `/v1/catalog/models`.
- A inspeção da validação do perfil confirma que combinações fora do catálogo, parâmetros desconhecidos, booleanos, limites fora da faixa, Evaluation e TypeSafe no perfil Router são recusados; a configuração de `max_output_tokens` é limitada ao menor entre o perfil e a chamada. A UI oferece a opção por compatibilidade do modelo/agente e mantém o modo Gravado distinto do Simulado nos testes focados.

## Lacunas e limites

- Não executei inferência real, embeddings, judge, nem chamadas autenticadas de metadados. `docs/evidence/v040-metadados-publicos.json` registra 401/403 sem autorização e não comprova acesso aos IDs na conta configurada. As fontes documentais oficiais corroboram os IDs/capacidades documentados, mas o acesso real aos provedores, CA-32 e o comportamento real de custo/erro permanecem pendentes; não os considero validados por mocks.
- A comparação OpenAPI foi leitura GET local do ambiente sintético fornecido pelo Supervisor. Não é evidência externa de JEV nem rebuild independente do Dockerfile canônico.
- Não rodei suíte completa, browser/Streamlit contra provedor, nem QA da história. Esta revisão não declara QA ou release concluídos.

## Próximo responsável

Encaminhar o achado P2 ao Developer para separar a reserva estimada do mapa de parâmetros efetivos e fixar regressão que verifique comparação e snapshot JEV vazios nesse campo. Depois da correção, congelar novo candidato e revisar o delta afetado; QA continua sendo etapa separada.
