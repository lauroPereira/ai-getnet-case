# Passagem Developer r3 — sincronização do OpenAPI web

**Data:** 2026-10-27  
**Escopo:** resolver o achado P2 de divergência entre OpenAPI backend e snapshot web, sem mudança de comportamento do backend, guarda ou cliente HTTP. Pareceres e passagens r1/r2 foram preservados. O Supervisor forneceu servidor backend sintético r2 em `127.0.0.1:18841`, imagem SHA-256 `67f4dc3fa6c06f34950246b4ab64527ae2ffe277fc4f3c758450faec12fa62a1` e fingerprint de build `52059b77c561d2090da2c9d68be4371f61781622744422d318282a9213f746a3`.

## Delta

- Atualizado `C:\workspace\ai-getnet-case-web\openapi-v1.json` a partir do `GET /openapi.json` do backend sintético. O snapshot canônico é byte a byte igual ao JSON servido, com 13 paths. `POST /v1/router/compare` agora documenta `201`, `422` e `429`, e o 429 referencia `#/components/schemas/ErrorBody`.
- `tools/generate_client.py` continua gerando as dez operações existentes. Ajustei a emissão de literais para usar JSON strings, de modo que a saída do gerador passe Ruff de forma consistente em Windows. O mapa gerado é idêntico ao anterior, pois os operation IDs não mudaram.
- Adicionei dois testes web: o snapshot inclui 429/ErrorBody e o cliente HTTP converte o envelope 429 em `APIError` com status/código/mensagem corretos. `APIClient` não foi alterado.
- Nenhum arquivo fonte, imagem, runtime, limite, guarda ou dependência do backend foi alterado. Nenhum ambiente/runtime anterior foi usado para exportar o schema.

## Comandos e resultados

Obtenção do schema: `GET http://127.0.0.1:18841/openapi.json` retornou 200 (13.542 bytes). A verificação Python comparou os bytes do snapshot com `json.dumps(schema, ensure_ascii=False, indent=2) + newline`: igualdade exata. A rota de comparação retornou precisamente os status `201`, `422`, `429`, com `ErrorBody` para 429.

No projeto web, `.venv-v040/Scripts/python.exe tools/generate_client.py` executado duas vezes, ambas com exit 0 e dez operações. SHA-256 de `generated_api.py` igual nas duas execuções e igual ao hash r1 já registrado: `0bce171011eb24f83b37029dcd7cfcc08175e5057396cdff8b3f571ef261362c`.

Validação final, no venv isolado da web e sem chamadas pagas:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv-v040\Scripts\python.exe -m pytest -q `
  --basetemp=.pytest_cache\v040-openapi-r3-final-20261027
..\ai-getnet-case\.venv\Scripts\ruff.exe check --no-cache .
..\ai-getnet-case\.venv\Scripts\ruff.exe format --check --no-cache .
```

**Resultado:** 9 testes passaram; Ruff check passou; Ruff format passou com 72 arquivos já formatados. O teste do consumidor confirma propagação de `429 request_budget_exceeded` como `APIError`.

## SHA-256 dos arquivos alterados

| Projeto/arquivo | SHA-256 |
| --- | --- |
| web `openapi-v1.json` | `c4b4ab18610aee1c758ce9a3eefee999bf3260bc8851e95e84c3648b98ce28a5` |
| web `src/getnet_web/generated_api.py` | `0bce171011eb24f83b37029dcd7cfcc08175e5057396cdff8b3f571ef261362c` |
| web `tools/generate_client.py` | `d5a9570a540819a0d3a7789ce60cfedaa9b7e8354c9bec8aa1f9e43748d5de63` |
| web `tests/test_interface.py` | `a070039937b7629a5af1bdd809cb6fada590e274ad67d86f7193f80990aa2ffa` |
| backend `docs/tasks/34-sincronizacao-openapi-web-v040.md` | `c93d93d29d159f203cf29bf7d86d9960b11c327ab33da4791a1ece49e9b585f1` |

## Estado

Tarefa 34 implementada e validada pelo Developer. Aguarda congelamento e
reavaliação independente pelo Reviewer r2. QA ainda não começou. CA-32 JEV
real continua pendente; nenhuma inferência, endpoint de provedor, commit, push,
PR, tag ou publicação foi executada nesta sincronização.
