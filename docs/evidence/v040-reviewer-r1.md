# Parecer independente — candidato v0.4.0 r1

## Identificação e independência

- Candidato: `v0.4.0-local-r1`.
- Backend: branch `codex/v0.4.0-perfis-interface`, HEAD/base `bd549cc921ccffb37bd304a0959b8a4b690d6421`.
- Frontend: `C:\workspace\ai-getnet-case-web`, sem Git no manifesto.
- Fingerprint combinado: `91184b73d1c91f5b1790b831038e9853a54b20a1791407447ecd4a7380eeeaec`.
- Fingerprints do runtime/build do backend: `c5adab307e7e2e1a6f0519d64dc6b70ce25471520c4de44b8d843ee07e7da41c` / `9848a565296e330e5ee00b5b0394c21e2ed9d7636a57ef1fad886de9af426420`.
- Contexto independente: sim. Recebi apenas o escopo, os critérios canônicos, o manifesto e os limites; não consultei a passagem ou diagnóstico do Developer.
- Integridade antes e depois da revisão: os 39 hashes backend, 83 frontend, 127 runtime e 128 build inputs conferem; HEAD backend e os três fingerprints também conferem. Nenhum arquivo de produto foi alterado.

## Parecer

**Correções necessárias antes de considerar este candidato apto à revisão.** Há um defeito de resposta da API quando a guarda de orçamento bloqueia uma comparação. A proteção impede a chamada seguinte, mas o endpoint deixa escapar uma exceção sem tratamento específico e devolve erro interno 500 em vez de erro explícito de limite/custo. O resto do fluxo sintético que pude verificar comportou-se conforme os critérios centrais.

## Achado

### P2 — comparação sem orçamento suficiente responde como erro interno

- **Condição:** sessão autenticada chama `POST /v1/router/compare` e a estimativa/reserva de qualquer Router excede `max_request_cost_usd` ou o saldo global. Isso pode ocorrer também depois de a primeira decisão ter sido reservada/contabilizada e antes da segunda.
- **Evidência:** `RunContext.reserve()` chama `pricing.estimate()` e `BudgetGuard.reserve()`, que lança `BudgetExceeded` (`src/merchant_assistant/orchestration/run.py`, `reserve`; `src/merchant_assistant/orchestration/budget.py`, `BudgetGuard.reserve`). O handler `compare()` em `src/merchant_assistant/api/v1.py` captura `RuntimeError` e `LLMError`, mas não `BudgetExceeded` (linhas 475–478); `BudgetExceeded` herda diretamente de `Exception`. A exceção chega ao handler global e vira `500 internal_error`.
- **Impacto:** o limite financeiro continua bloqueando a próxima chamada, mas o consumidor não recebe o erro operacional explícito prometido para orçamento/custo; a comparação pode ter custo parcial e falhar de forma opaca.
- **Reprodução:** configurar um limite por solicitação/saldo restante menor que a reserva, autenticar e enviar `POST /v1/router/compare` com perfil publicado. O ponto de falha é `meter.reserve()` antes da chamada ao provedor. Não fiz chamada real nem tentei reproduzir com cobrança; a condição decorre do fluxo de exceção e do tipo da classe.
- **Correção sugerida:** tratar `BudgetExceeded` (e definir código/status estruturado de limite) em `compare`, sem fallback e sem registrar uma comparação incompleta como sucesso; preservar a reserva/ledger já contabilizada conforme a semântica existente.

## Verificações próprias

- Backend: `.venv\Scripts\python.exe -m pytest -q tests/integration/test_v1_api.py tests/unit/test_jev_adapter.py tests/unit/data/test_migrations.py` — processo terminou com código 0; todos os testes selecionados passaram.
- Frontend: `.venv-v040\Scripts\python.exe -m pytest -q tests\test_interface.py` — `7 passed`.
- Fluxo HTTP ponta a ponta contra harness sintético em loopback `127.0.0.1:18743`, runtime novo `.pytest_cache\v040-review-r1-runtime`: login demo/admin (201), listagem de perfil (200), escrita admin tentada por demo (403), comparação (201, modo simulado, decisões LLM/JEV), atendimento da decisão JEV (200), consulta do run (200, modelo `typesafe:jev-1.14.0`), repetição da comparação consumida (409) e `POST /messages` legado (200). Harness encerrado depois da execução.
- OpenAPI e cliente web: inspeção confirmou operações `/v1` alinhadas ao arquivo OpenAPI e bearer enviado apenas como token de sessão; Streamlit acessa o backend via cliente HTTP e distingue simulado/gravado/real. AppTest cobriu rerun sem reenvio.
- Autorização/isolamento: código e testes selecionados cobrem segredo/token armazenado por digest, TTL/revogação, papéis por rota, perfil demo permitido, dono de conversa/comparação/run, expiração e consumo único. O cliente não determina papel ou dono.
- Perfis/snapshots: validação rejeita combinação fora do catálogo/parâmetros não implementados; versões publicadas são imutáveis e edição/publicação usa transação/versão esperada. O caminho de atendimento congela digest/configuração/modelos e o grafo existente aceita decisão do Router via `router_override`, mecanismo equivalente reutilizado.
- JEV: o adaptador está limitado a `RouterDecision`, valida versão/resposta/usage e lança `LLMError` sem fallback. A documentação oficial aberta confirma `POST /v1/systemone`, `jev-1.14.0`, preço por token de entrada e saída sem custo ([modelos TypeSafe](https://docs.typesafe.ai/models), [referência System One](https://docs.typesafe.ai/api/system-one)). DeepSeek e GPT-6 Luna também têm preço/capacidades documentados nas fontes oficiais referenciadas no catálogo ([DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/), [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna)). Nenhuma API de inferência ou endpoint autenticado de modelos foi chamada.
- Migração: a migração 0006 cria/remover entidades próprias e não contém alteração das tabelas 0005. Testes executados verificam downgrade/upgrade e preservação de registros legados; o ledger de orçamento é armazenado em arquivo separado. Não reiniciei banco anterior nem ledger.

## Lacunas e limites

- Não concluo CA-32 nem a integração real do JEV: não houve chamada paga autorizada. Harness, fixtures e transportes programados provam somente o caminho simulado/contratual.
- Não executei a suíte completa de regressão de 202 testes nem Docker/MCP nesta revisão; o QA deve validar a história inteira e regressões v0.3.0 no mesmo candidato, além de manter CA-32 explicitamente pendente.
- Não foi necessário escrever fora dos repositórios além do runtime sintético ignorado, autorizado para o harness. Não houve commit, push, PR, publicação ou acesso a credenciais.

## Próximo responsável

Devolver o achado ao Developer para correção e novo candidato. Depois, repetir a revisão sobre hashes atualizados; QA só deve começar após parecer apto.
