# Passagem Developer r5 — parâmetros efetivos do JEV

**Data:** 2026-10-27  
**Branch:** `codex/v0.4.0-perfis-interface`  
**Base:** `bd549cc921ccffb37bd304a0959b8a4b690d6421`  
**Escopo:** resolver o achado P2 do Reviewer r4 em que a reserva interna `max_output_tokens=80` do JEV era apresentada como parâmetro efetivo, apesar de o corpo System One não aceitar esse campo. A correção não altera preço estimado, reserva/liquidação, guarda, ledger, decisão, fallback ou contrato de payload.

## Delta

- `Meter.reserve` agora distingue os argumentos usados para estimar/reservar custo de `effective_parameters`, metadado opcional dos campos realmente encaminhados pelo adaptador.
- `RunContext.reserve` continua estimando com o `max_output_tokens` recebido e reservando o mesmo valor monetário; só inclui no mapa efetivo parâmetros explicitamente informados pelo adaptador.
- OpenAI registra o `max_output_tokens` enviado em parse, tool calls e web search. `OutputTokenLimitLLM` encaminha ao Meter o limite efetivo já limitado por `min(limite do perfil, limite da chamada)`, preservando a igualdade entre reserva e payload e o teste positivo do LLM.
- `JevRouter` continua reservando com 80 tokens para estimativa, sem mudar seu payload (`model`, `state`, `questions`). Como não declara parâmetro efetivo, a comparação retorna `{}` para JEV.
- `_decision` deriva a configuração efetiva do adaptador/limite da chamada, em vez de copiar o mapa agregado compartilhado da comparação. Assim, a passagem do Router LLM antes do JEV não contamina a decisão JEV.
- Reutilização de comparação foi preservada: o atendimento escolhido usa a decisão guardada sem executar novo Router. O snapshot fica vazio para Router JEV e mantém `{"max_output_tokens": 300}` para a decisão Router LLM selecionada.
- Contrato documental esclarece que o mapa efetivo exclui valores usados apenas em reserva. Não houve alteração de OpenAPI, JSON da API ou migração.

## Regressões

`tests/unit/test_jev_adapter.py` verifica que o meter ainda recebe `max_output_tokens=80`, que a reserva não tem `effective_parameters` e que o payload fake não recebe limite de saída.

`tests/integration/test_v1_api.py::test_comparison_and_reused_run_report_only_provider_applied_router_parameters` usa transporte System One fake e cliente Responses fake. Faz comparação com duas escolhas e confirma mapas de decisão JEV vazios e LLM com limite efetivo de 300. Os snapshots de atendimentos reutilizando cada escolha preservam os mesmos mapas. Contadores confirmam duas chamadas JEV e duas LLM nas duas comparações, sem nova chamada Router no atendimento selecionado.

O caso positivo de perfil configurado continua em `test_output_token_parameter_is_catalogued_published_and_effective_in_snapshot` e `test_profile_output_cap_reaches_provider_and_never_exceeds_reserved_tokens`: perfil limita a 128, e os 128 aparecem tanto em reserva quanto em payload/snapshot; um teto de chamada menor (64) não é ampliado.

## Validação

Testes direcionados e lint/format dos arquivos afetados:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.venv\Scripts\python.exe -m pytest -q `
  tests\integration\test_v1_api.py::test_comparison_and_reused_run_report_only_provider_applied_router_parameters `
  tests\integration\test_v1_api.py::test_router_comparison_is_router_only_and_consumed_once `
  tests\integration\test_v1_api.py::test_output_token_parameter_is_catalogued_published_and_effective_in_snapshot `
  tests\unit\test_profile_output_parameters.py `
  tests\unit\test_jev_adapter.py `
  --basetemp=.pytest_cache\v040-effective-jev-r5-verified-20261027
```

**Resultado:** 8 testes passaram; Ruff check passou; 7 arquivos já estavam formatados. Um primeiro teste focal também passou o fluxo, mas a asserção de contagem esperava quatro chamadas por adaptador. A contagem correta é duas, porque a decisão comparada é reutilizada sem nova chamada; a asserção foi corrigida e a rodada final passou.

Validação estrita backend após a correção (inclui toda a suíte, skills e Ruff):

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_ADDOPTS = '--basetemp=.pytest_cache/v040-strict-r5-final-20261027'
.venv\Scripts\python.exe tools\scripts\lint_and_tests.py --strict
```

**Resultado:** exit 0; **216 testes passaram em 150,72 s**, Ruff check e skills válidas. Nenhuma chamada a provedor, inferência, embedding, Judge ou acesso ao serviço v0.3.0 foi feito. A interface não foi modificada; os testes e Ruff web r4 permanecem aplicáveis e não foram repetidos.

## Limites

- Os testes usam modelos e transportes fake; não validam tarifa, comportamento de erro ou payload real cobrado por TypeSafe/OpenAI/DeepSeek.
- CA-32 (JEV real) continua pendente por ausência de chamada paga.
- Não houve mudança de contrato público nem atualização OpenAPI; o consumidor web não requer geração nova.
- Este relatório registra somente a passagem do Developer. O Supervisor ainda deve congelar r5; Reviewer e QA permanecem pendentes.
- Sem commit, push, tag, chamada remota ou publicação.

## SHA-256

| Arquivo | SHA-256 |
| --- | --- |
| `src/merchant_assistant/llm/base.py` | `276F661F9E0ECD0935C5BAFBA7A30B2466B9B7454A3726C91E2824C4E381D1D3` |
| `src/merchant_assistant/llm/openai_llm.py` | `D817D8FE502865EED62DEAEFAD65D20DD1439AEF3E6D48C32CF642BFEF6B3C01` |
| `src/merchant_assistant/orchestration/run.py` | `61CA71451DDB3C2C930681F15CB9D9199FE7E550EC2FE09338A1480624B842D2` |
| `src/merchant_assistant/api/v1.py` | `6CAA42C3A6A8D0F7C9CFBFA96D416EA1DEAFD3CA7F976432AE607B53E67F0070` |
| `tests/integration/test_v1_api.py` | `FEDF0135CE65A3DE88DB017CACF60F3923FD9EC50A734D13B1696F7D8B219F32` |
| `tests/unit/test_profile_output_parameters.py` | `434CDDFE60DF48F09DFF6A2CF19DABD97C5A978F5D39FB7E578A7FAC406398AE` |
| `tests/unit/test_jev_adapter.py` | `4FB97A9947F75C8ADB4B341BABA589433136684D9F302D87B7F1DF2C5BD64175` |
| `docs/tasks/37-parametros-efetivos-jev-v040.md` | `03951187AE6D61D53F565789504740BF3A6ADE273BA834226EF4F626962B9A18` |
| `docs/contracts/api-v040.md` | `D9C79273F15B6828EFD7981686D41A7A8033299159BA32C56776F2FCA3DA1623` |
| `CHANGELOG.md` | `A9EB6465FE83BA1E0883948FFCD4ABB2EBFE0505A4DFE5F5F0811E10FE48E6A9` |
