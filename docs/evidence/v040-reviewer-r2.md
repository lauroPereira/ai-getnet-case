# Parecer independente — candidato v0.4.0 r2

## Identificação e independência

- Candidato: `v0.4.0-local-r2`.
- Backend: branch `codex/v0.4.0-perfis-interface`, HEAD/base `bd549cc921ccffb37bd304a0959b8a4b690d6421`.
- Frontend: `C:\workspace\ai-getnet-case-web`, sem Git no manifesto.
- Fingerprint combinado: `48127b3309f90431f01d49a419cac48a11fa55e9f9096233804836d7385c6e5a`.
- Fingerprints do runtime/build do backend: `0aee1a1e01b1c4c298c99cc005335b8dd9bb2d9de47bf1132d872adb9658a98a` / `52059b77c561d2090da2c9d68be4371f61781622744422d318282a9213f746a3`.
- Contexto independente: sim. Reavaliei o candidato fixado e o escopo do defeito anterior sem consultar passagens ou diagnósticos do Developer.
- Integridade: 40 hashes backend, 83 frontend, 127 runtime e 128 build inputs conferem; os três fingerprints e HEAD backend também conferem. Os arquivos-fonte do candidato não foram alterados.

## Parecer

**Correções necessárias.** O defeito P2 da r1 foi corrigido: a recusa da reserva retorna 429 estruturado, não salva comparação parcial, não executa fallback/atendimento e mantém o custo já liquidado. Ainda há divergência no contrato consumido pela interface: o OpenAPI fixado no frontend não documenta a nova resposta 429.

## Reavaliação do P2 da r1 — corrigido

O handler captura `BudgetExceeded` e devolve `429` com `request_budget_exceeded` ou `installation_budget_exceeded`. O bloco de persistência da comparação continua somente depois de ambas as decisões. `BudgetExceeded` é levantado antes da chamada do modelo quando `meter.reserve()` falha; quando a segunda reserva falha, a primeira já foi liquidada e continua contabilizada.

Verifiquei quatro combinações: limite por requisição e saldo global, cada uma recusada antes do primeiro Router e antes do segundo. Os testes usam modelo programado e preço/liquidação falsos, sem inferência paga. No caso da segunda reserva, uma chamada programada ocorreu, o ledger permaneceu em `settled / reserved 0.04 / actual 0.03`, a segunda chamada não ocorreu e nenhuma comparação foi persistida. O modelo de erro também inclui `request_id` e a resposta informa que não houve comparação incompleta.

## Achado

### P2 — snapshot OpenAPI do frontend não documenta o novo 429

- **Condição:** consumidor da interface ou gerador de cliente usa o snapshot OpenAPI versionado em `C:\workspace\ai-getnet-case-web\openapi-v1.json`.
- **Evidência:** o OpenAPI gerado pelo backend para `POST /v1/router/compare` inclui respostas `201`, `429` (`ErrorBody`) e `422`. O snapshot consumido pelo frontend ainda lista somente `201` e `422`. O fingerprint r2 confirma que os 83 arquivos frontend, inclusive esse snapshot, não mudaram. O contrato backend agora declara 429 para as recusas de orçamento.
- **Impacto:** geradores e documentação baseados no snapshot não conhecem o resultado operacional novo nem o esquema `ErrorBody`, apesar de a API já o emitir. O `APIClient` atual trata qualquer status >=400 genericamente e, por isso, consegue propagar `429 request_budget_exceeded`; a divergência afeta o contrato gerado/consumido e não impediu o fluxo atual.
- **Reprodução/verificação:** comparei `create_app(...).openapi()['paths']['/v1/router/compare']['post']['responses']` com `openapi-v1.json` no candidato; o backend contém `429` com referência a `ErrorBody`, enquanto o snapshot não. Também exercitei o `APIClient` com resposta HTTP 429 estruturada; ele levanta `APIError(429, "request_budget_exceeded", ...)`.
- **Correção sugerida:** regenerar/atualizar o snapshot OpenAPI do projeto web para incluir a resposta 429 estruturada e conferir o cliente gerado no novo candidato. Não é necessário alterar o comportamento HTTP do `APIClient` atual.

## Verificações próprias

- Backend: `PYTHONDONTWRITEBYTECODE=1 .venv\Scripts\python.exe -m pytest -q tests/integration/test_v1_api.py -k "budget_rejection or router_comparison_is_router_only or openapi_declares" --basetemp=.pytest_cache/v040-review-r2-target3` — seis testes passaram: quatro limites, comparação de sucesso/consumo único e OpenAPI protegido/legado.
- Consumidor: cliente web sintético recebeu `429` com o envelope de erro e propagou `APIError` com status `429` e código `request_budget_exceeded`.
- Contrato: inspeção direta confirmou a diferença entre o OpenAPI gerado pelo backend e o snapshot OpenAPI versionado no frontend para `POST /v1/router/compare`.
- Semântica da comparação: as verificações exercitaram apenas Routers; o registro só é inserido após as duas decisões e não é consumível nos cenários de recusa. O fluxo legado `POST /messages` não foi afetado pelo escopo da correção.
- Nenhuma chamada de inferência, endpoint autenticado de modelos, commit/push/PR/publicação ou acesso a credenciais foi realizado.

## Lacunas e limites

- CA-32 e integração real do JEV continuam pendentes; não houve chamada paga autorizada.
- Não executei a suíte completa de regressão, Docker/MCP ou a história integral; QA permanece responsável pela validação da entrega no candidato fixado.
- O runtime dos testes ficou isolado em `.pytest_cache/v040-review-r2-target3`; não reutilizei runtimes r1 nem removi arquivos.

## Próximo responsável

Devolver a atualização do snapshot OpenAPI ao Developer para um novo candidato backend/web. Revalidar hashes e contrato após a atualização; QA ainda não deve iniciar neste r2.
