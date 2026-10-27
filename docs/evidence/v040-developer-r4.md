# Passagem Developer r4 — tarefas 35 e 36

**Data:** 2026-10-27  
**Branch:** `codex/v0.4.0-perfis-interface`  
**Base:** `bd549cc921ccffb37bd304a0959b8a4b690d6421`  
**Escopo:** corrigir o rótulo de Gravado e implementar a capacidade positiva de RF-49 com parâmetro documentado e limitado por orçamento. Pareceres QA r3 e Developer r1–r3 permanecem históricos e inalterados. Esta passagem registra trabalho do Developer; não é aprovação de Reviewer, QA ou release.

## Alterações

- `SimulatedAPI` deriva a resposta e o snapshot do mesmo `execution_mode`; a jornada AppTest confirma que Gravado mostra `[Modo recorded]`, mantém snapshot `recorded` e não se identifica como Simulado.
- O catálogo e a administração por agente agora oferecem apenas `max_output_tokens` para `openai:gpt-6-luna` e `deepseek:deepseek-flash`, conforme documentação oficial do Responses API. TypeSafe/JEV não oferece o campo; Evaluation permanece reservado à v0.6.0.
- Validação de perfil rejeita campos desconhecidos, agente/modelo incompatível, boolean, valor não inteiro, mínimo abaixo de 16 e valor acima do teto por agente. Os tetos são Router 300, Knowledge 500, Support 1200, Escalation 400 e Personality 600. São os máximos já usados pelas chamadas dos agentes; a configuração só pode reduzi-los.
- `OutputTokenLimitLLM` aplica `min(limite configurado, limite da chamada)` antes do adaptador. O teste com adaptador OpenAI fake comprova que o mesmo limite efetivo entra na reserva e no payload e que o perfil não amplia uma chamada com teto menor. O snapshot registra o valor efetivamente reservado/enviado; a configuração persiste na versão publicada e digest.
- OpenAPI v1 foi atualizado a partir de `GET /openapi.json` em backend sintético local (`127.0.0.1:18842`, HTTP 200, 15.309 bytes). O processo foi encerrado depois da exportação. O gerador web foi executado duas vezes, produzindo 11 rotas e o mesmo SHA-256. A API sintética foi configurada com chaves de provedores ausentes, modelos programados e runtime novo em `.pytest_cache/v040-openapi-r4-synthetic-20261027`.
- Corrigida a referência documental ao snapshot web: ele pertence ao projeto irmão `C:\workspace\ai-getnet-case-web`, não ao repositório backend.

## Validação executada

Backend, strict completo (Windows socket local autorizado), com bytecode desabilitado e `basetemp` novo:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_ADDOPTS = '--basetemp=.pytest_cache/v040-strict-r4-final-20261027'
.venv\Scripts\python.exe tools\scripts\lint_and_tests.py --strict
```

**Resultado final:** exit 0; **214 testes passaram em 163,05 s**, Ruff check passou e skills válidas. Uma execução estrita anterior passou os mesmos 214 testes, mas mostrou um `SIM114` e duas linhas longas; os três apontamentos foram corrigidos antes da execução final.

Interface, ambiente `.venv-v040` independente, sem chaves de provedor:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.venv-v040\Scripts\python.exe -m pytest -q --basetemp=.pytest_cache\v040-web-r4-final2-20261027
..\ai-getnet-case\.venv\Scripts\ruff.exe check --no-cache .
..\ai-getnet-case\.venv\Scripts\ruff.exe format --check --no-cache .
```

**Resultado:** 12 testes passaram em 3,54 s; Ruff check passou; 72 arquivos já estavam formatados. Após adicionar a jornada UI Gravado, seu teste direcionado também passou: 1 teste em 2,13 s, Ruff check e format passaram. Em seguida foi reexecutada a suíte web completa acima.

Contrato/cliente: o GET sintético ao OpenAPI retornou 200. `tools/generate_client.py` executou duas vezes, cada uma gerando 11 operações; SHA-256 de `generated_api.py` permaneceu `F3DBA99C39FB0CB55B533CA97992ECC1C7F884D023E25042BCBF5BF50164472D`. Nenhuma inferência, chamada de embedding ou API paga foi usada. Não foi executado endpoint da API antiga v0.3.0.

## Como repetir a jornada sintética

Na raiz backend, em PowerShell, use uma pasta nova filha de `.pytest_cache` e a API programada, sem carregar `.env`:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.venv\Scripts\python.exe tools\scripts\run_synthetic_v040_api.py `
  --port 18842 `
  --runtime-dir .pytest_cache\v040-http-new-synthetic
```

O harness fixa `Settings(_env_file=None)`, chaves OpenAI/DeepSeek/TypeSafe ausentes, credenciais de sessão sintéticas e ScriptedLLM/HashEmbedder. Na raiz web, em outro terminal, conecte o Streamlit à API local:

```powershell
$env:BACKEND_API_URL = 'http://127.0.0.1:18842'
.venv-v040\Scripts\streamlit.exe run app.py
```

Entre somente com `v040-synthetic-demo-access-key` ou `v040-synthetic-admin-access-key` do harness. Para testar RF-49, use admin, crie um perfil de rascunho, ative o limite para um agente compatível, escolha valor entre 16 e o teto mostrado, salve e publique. Em seguida use esse perfil para uma mensagem e confira `effective_parameters_by_agent` no inspetor. As chaves são constantes de teste do harness, sem validade externa. Pare o servidor sintético ao terminar.

## Limitações e estado

- CA-32 — invocação real de JEV System One — permanece pendente. Nenhuma chamada paga foi autorizada ou feita.
- Não foi feita chamada autenticada `GET /models` de conta de provedor porque sua gratuidade não foi comprovada oficialmente.
- A UI oferece o parâmetro pelo catálogo; a cobertura de aplicação efetiva no adaptador e de orçamento é offline/fake, sem alegar validação de cobrança de provedor real.
- Este candidato aguarda congelamento r4, Reviewer e QA. Não houve commit, push, tag, chamada remota, publicação ou aprovação de release.

## SHA-256 dos arquivos relevantes

| Projeto/arquivo | SHA-256 |
| --- | --- |
| backend `src/merchant_assistant/profiles.py` | `26E3F5645111E6E0C4B70B884080F7837A6204773A93B92C704256354C6AB11D` |
| backend `src/merchant_assistant/llm/base.py` | `CC9FCC44287E78ACBE3654626E8E9C3CF7B408830E66DF4209A071527D41C5F8` |
| backend `src/merchant_assistant/orchestration/graph.py` | `DC499A1A5FD0196207E01EFC048CF161292107D5C5A20C1218B1EF7FC8BB93DF` |
| backend `src/merchant_assistant/orchestration/run.py` | `0338D2009289537F9A87191D92C59DA2341877A47936E0B8604D7093E586A1BD` |
| backend `src/merchant_assistant/api/v1.py` | `637C6860CABCFC079CD316FB3872C1A3237E5010BDAEAF35255A290F19138C90` |
| backend `tests/integration/test_v1_api.py` | `6BF4F5FC2F5C4AAC8D36804969619B0E52A8AB8427F09EBA326DA9B88DBA8B83` |
| backend `tests/unit/test_profile_output_parameters.py` | `84EB7E3E6E736BE28833236B325609C9113C9FC64438E50611A05FA4074A1B9E` |
| web `openapi-v1.json` | `5AB15D34366A44A18884FB5506BD21E91AA9CDE61F9285F6DED9B0AFCCD041D8` |
| web `src/getnet_web/generated_api.py` | `F3DBA99C39FB0CB55B533CA97992ECC1C7F884D023E25042BCBF5BF50164472D` |
| web `tools/generate_client.py` | `9123ED2FD20298CCE1986BFD6C9D624AC97C687A7231D95C0BF0FFF383FB808E` |
| web `src/getnet_web/api.py` | `536FAC08946B9DC960963EE0F26895B430B2B21D9312128C01BC9010D1090CCB` |
| web `src/getnet_web/simulated.py` | `5A34083DC76547F3D1D2272C1B22E5610166120347ED0A642481658EEE23454A` |
| web `app.py` | `F002009042D26158453DAD30D39E12D98477012F9AAE9E4659C5E613A6E0AF93` |
| web `fixtures/model_catalog.json` | `C8CD7593C2D290C64F2A2F93D191B63ACEC80CD79790BDB301178F9AEF054F06` |
| web `tests/test_interface.py` | `67A8F82C1063F349B86C1C067F419FE97C1D125304397E7279CCCC49FF0AFE0` |
