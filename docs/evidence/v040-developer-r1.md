# Passagem Developer r1 — v0.4.0

**Data:** 2026-10-27  
**Escopo:** backend, API `/v1`, perfis e migração 0006, adaptadores/catálogo, cliente e interface Streamlit, contratos, README/CHANGELOG e tarefas 27–29/31–32. O Supervisor mantém plano/status, ADR 0013, evidência de base web e tarefa 30.  
**Estado:** candidata Developer pronta para congelamento pelo Supervisor. Reviewer e QA ainda não revisaram este candidato. Não houve commit, push, PR, tag, integração nem publicação.

## Implementado

- Migração reversível `0006_profiles_api` para perfis/versionamento, principals/sessões, comparações e snapshots; rollback `0006 → 0005` preserva os dados anteriores.
- API versionada `/v1` com `SessionBearer`, chave backend demo/admin, token opaco de 60 minutos armazenado só por SHA-256, revogação, papel e dono conferidos pelo backend. `POST /messages` legado permanece.
- Perfis Reference, Hybrid e Adjusted; publicação imutável, atualização otimista de rascunho e snapshot por execução. Modelos são limitados pelo catálogo conhecido; modelos/custos/capacidades desconhecidos bloqueiam seleção.
- Comparação executa somente os dois Routers sobre a mesma mensagem/estado. O `comparison_id` é vinculado ao dono, conversa, mensagem, estado, perfil, versão, método e prazo; a decisão selecionada é consumida em transação atômica uma vez e passa ao atendimento sem nova chamada do Router.
- Adaptador TypeSafe usa `POST /v1/systemone`, valida a decisão tipada, limita JEV ao Router e não faz fallback. DeepSeek é selecionável somente nos agentes cujas capacidades foram confirmadas. Valores conservadores são registrados como **estimativas**, sem alegação de fatura exata.
- Projeto web independente usa somente HTTP `/v1`; cliente gerado do OpenAPI, modos Simulado/Gravado/Real, conversa, comparação, inspeção e telas admin para criar, versionar e publicar rascunhos. O cliente HTTP é reutilizado dentro da sessão e fechado no logout/troca de modo.

## Validação executada

Backend, PowerShell, a partir de `C:\workspace\ai-getnet-case`:

```powershell
$env:PYTEST_ADDOPTS = '--basetemp=.pytest_cache/v040-strict-r2-20261027'
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\Scripts\python.exe tools\scripts\lint_and_tests.py --strict
```

**Resultado:** exit 0; **202 testes passaram**, Ruff e validação de skills passaram. O diretório basetemp era novo. `git diff --check` também passou depois da normalização de LF em `agents/knowledge.py` e `api/app.py` (sem alteração semântica).

Web, a partir de `C:\workspace\ai-getnet-case-web`:

```powershell
python -m pip install --no-cache-dir -e ".[test]"
.\.venv-v040\Scripts\python.exe -m pip check
.\.venv-v040\Scripts\python.exe -m pytest -q --basetemp=.pytest_cache\v040-web-final-r2-20261027
..\ai-getnet-case\.venv\Scripts\ruff.exe check --no-cache .
..\ai-getnet-case\.venv\Scripts\ruff.exe format --check --no-cache .
```

**Resultado:** instalação editável concluída no venv próprio do web; `pip check` sem dependências quebradas; **7 testes passaram**; Ruff check e format passaram. Não foi instalado pacote no venv backend além do runtime já usado pelos testes.

Validações HTTP/UI com loopback, apenas dados/modelo programados:

- `tools/scripts/run_synthetic_v040_api.py --port 8792 --runtime-dir .pytest_cache\v040-http-logout-fix-20261027`: runtime novo, `Settings(_env_file=None)`, chaves de provedor ausentes, modelo programado e Qdrant em memória. Login, perfil, comparação, atendimento, trace, uso único, 401 e revogação passaram.
- Regressão do logout na **mesma conexão keep-alive**: `DELETE /v1/sessions/current` devolveu 204 sem corpo; GET subsequente sem sessão devolveu 401 com `len(body) == Content-Length`. Log de erro do servidor ficou vazio.
- AppTest Real(API) no venv web, contra o servidor sintético: login demo, leitura de perfis, uma mensagem HTTP, rerun sem reenvio e logout/fechamento do cliente passaram. AppTest admin criou uma versão imutável de rascunho e publicou-a via HTTP sintético.
- `streamlit run app.py --server.headless=true --server.address=127.0.0.1 --server.port=8502` iniciou no venv web próprio; GET HTTP local retornou 200 e o shell da aplicação. O servidor foi encerrado após a verificação.
- OpenAPI tem 10 operações protegidas com `SessionBearer`; `POST /v1/sessions` é pública. Cliente web contém o mapa gerado para as 10 operações.

## Reproduzir API sintética + Streamlit

O runtime precisa ser um **novo filho de `.pytest_cache`**; se o nome já existir, escolha outro. O servidor liga somente em `127.0.0.1`, sem ler `.env`, sem credenciais de provedor e sem inferência paga.

Terminal backend:

```powershell
.\.venv\Scripts\python.exe tools\scripts\run_synthetic_v040_api.py `
  --port 8765 `
  --runtime-dir .pytest_cache\v040-http-local-dev
```

Terminal web:

```powershell
$env:BACKEND_API_URL = 'http://127.0.0.1:8765'
.\.venv-v040\Scripts\python.exe -m streamlit run app.py `
  --server.headless=true --server.address=127.0.0.1 --server.port=8501
```

O seletor **Real (API)** recebe chave demo/admin sintética do harness; o frontend nunca recebe chave OpenAI, DeepSeek ou TypeSafe. Os modos Simulado e Gravado não precisam de servidor.

## Catálogo e lacunas

Fontes e valores verificados em 2026-10-27 estão em [v040-catalogo-fontes.md](v040-catalogo-fontes.md). Os IDs/preços/capacidades disponíveis no catálogo vêm de documentação oficial. Não foi executado `GET /models` autenticado: não encontrei comprovação oficial de que a chamada é gratuita, e não usei credenciais. Esse critério fica aberto. Nenhuma chamada real a `POST /v1/systemone`, OpenAI ou DeepSeek foi feita; **CA-32 (JEV real) segue pendente**. Nenhum saldo de v0.3.0 foi reutilizado.

Também permanecem para o Supervisor: congelar/manter manifesto candidato dos dois projetos, encaminhar Reviewer e depois QA independentes, e decidir o fluxo de release. A tarefa 32 não está concluída até essas passagens e a avaliação das lacunas.

## Hashes do candidato Developer

O manifesto SHA-256 lista 48 arquivos do backend e web (código, OpenAPI, produto e documentos v0.4.0) em [v040-developer-r1-hashes.json](v040-developer-r1-hashes.json). SHA-256 do manifesto: `235eb22ab260a1f7f5f6a157a50a252415077cf307f34fe3804b380e0126a0e9`. A base limpa da web e seus 72 hashes permanecem no manifesto do Supervisor [v040-base-web.json](v040-base-web.json).
