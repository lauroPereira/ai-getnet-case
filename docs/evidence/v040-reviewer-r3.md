# Parecer independente — candidato v0.4.0 r3

## Identificação e independência

- Candidato: `v0.4.0-local-r3`.
- Backend: branch `codex/v0.4.0-perfis-interface`, HEAD/base `bd549cc921ccffb37bd304a0959b8a4b690d6421`.
- Frontend: `C:\workspace\ai-getnet-case-web`, sem Git no manifesto.
- Fingerprint combinado: `31f10d7dfb249bdc7f517ee0ef6144a40061aaac766ad2dd5c63bd018d9f1e8e`.
- Fingerprints do runtime/build do backend: `0aee1a1e01b1c4c298c99cc005335b8dd9bb2d9de47bf1132d872adb9658a98a` / `52059b77c561d2090da2c9d68be4371f61781622744422d318282a9213f746a3`.
- Contexto independente do Developer: sim. Reavaliei o novo candidato sem consultar passagens ou diagnóstico do Developer.
- Integridade: os 41 hashes backend, 83 frontend, 127 runtime e 128 build inputs conferem; fingerprints e HEAD também conferem. Não alterei produto, contratos ou testes.

## Parecer

**Apto para seguir à etapa de QA deste candidato.** O achado P2 da r2 foi corrigido: o snapshot web agora corresponde ao OpenAPI servido, e o consumidor preserva a resposta 429 estruturada. Não encontrei novo defeito no escopo revisado.

## Reavaliação do achado da r2 — corrigido

- O GET autorizado a `http://127.0.0.1:18841/openapi.json` respondeu `200`. Comparei o objeto OpenAPI completo recebido com `openapi-v1.json`: igualdade estrutural verdadeira, com 13 paths em ambos.
- `POST /v1/router/compare` declara `201`, `422` e `429`; a resposta 429 referencia `#/components/schemas/ErrorBody`, consistente com o contrato backend e seu envelope `{error:{code,message,request_id}}`.
- Recalculei em memória a saída determinística de `tools/generate_client.py`, sem executar o script que escreveria no projeto: as 10 operações requeridas estão presentes e o resultado coincide byte a byte com `src/getnet_web/generated_api.py`. O mapa HTTP não depende da ordem nem do conteúdo das respostas; repetir a geração com o mesmo snapshot produz o mesmo artefato.
- O `APIClient` transforma resposta 429 estruturada em `APIError`, preservando status, código e mensagem. Isso foi confirmado pelo teste do projeto web e por inspeção do cliente.

## Verificações próprias

- Frontend: `.venv-v040\Scripts\python.exe -m pytest -q --basetemp=.pytest_cache/v040-review-r3-target4` — `9 passed`.
- Backend: `PYTHONDONTWRITEBYTECODE=1 .venv\Scripts\python.exe -m pytest -q tests/integration/test_v1_api.py -k "budget_rejection or router_comparison_is_router_only or openapi_declares" --basetemp=.pytest_cache/v040-review-r3-target5` — seis testes passaram: os quatro casos dos limites, comparação de sucesso/uso único e contrato protegido/legado.
- Os quatro casos de orçamento cobrem limite por requisição e global antes da primeira e da segunda reservas. Nos casos da segunda reserva, o primeiro custo permanece liquidado no ledger, a segunda chamada programada não ocorre e não é gravada comparação incompleta.
- A comparação repetida depois do atendimento é recusada com `409`; o teste confirma que não há nova chamada de Router. AppTest também cobre rerun sem reenvio.
- A comparação contratual foi feita somente por GET ao servidor sintético de loopback; não chamei provedores, endpoint autenticado de modelos ou API paga.

## Limites e pendências

- CA-32 e integração real do JEV continuam pendentes: não houve chamada paga autorizada. O servidor sintético e os testes programados comprovam apenas o fluxo simulado/contratual.
- Não executei nesta revisão a suíte completa do backend, Docker/MCP ou a história integral; QA deve validar o candidato fixado e registrar essas lacunas sem declarar CA-32 concluído.
- Basetemps foram novos e isolados. Não removi nem reutilizei runtimes r1/r2.
- Nenhum commit, push, PR, publicação, alteração de fonte ou acesso a credenciais foi realizado.

## Próximo responsável

QA pode executar a história `perfis-interface-v040` sobre `v0.4.0-local-r3`, mantendo o candidato e suas hashes fixos e relatando os critérios reais não exercitados.
