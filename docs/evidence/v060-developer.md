# Passagem de papel: Developer v0.6.0 (tarefas 54–58)

## Rodada 1 — 2026-10-27

- **Papel e responsável:** Developer (subagente Claude Opus 5.5, esforço high), despachado pelo Supervisor conforme o [plano aprovado](../specs/fechamento-v060-plano.md#delegação-aprovada). Sem delegação a outros agentes.
- **Objetivo e critérios:** implementar as tarefas [54](../tasks/54-estabilizacao-v060.md) a [58](../tasks/58-execucao-compartilhamento-v060.md) conforme a [spec](../specs/fechamento-v060.md), o plano, a [história](../historias/fechamento-v060.md) e o [ADR 0015](../architecture/decisions/0015-recorte-final-v060.md), com validação estrita sem custo nos dois repositórios.
- **Escopo:** `C:\workspace\ai-getnet-case` e `C:\workspace\ai-getnet-case-web`, branches `codex/v0.6.0-fechamento`.
- **Estado:** apto para revisão (Reviewer em contexto novo) e depois QA real (tarefa 59).
- **Branch e PR:** `codex/v0.6.0-fechamento` nos dois repositórios; sem commit, push ou PR.
- **Base e versão final:** HEAD backend `c3a9027b7c218f560345576770a646d4ec2bc098`, HEAD web `4192169afc8b37f150d88fdf16e3529a0fd33b90`; o candidato é o working tree (alterações locais listadas abaixo). O Supervisor fixa os hashes.
- **Independência:** não se aplica (implementação).

### O que foi feito, por tarefa

**54 — Estabilização.**
- R2-01: `<ledger>.limit` gravado com `repr(float)`; a primeira montagem aceita o próprio valor (1/3, 0.1+0.2).
- R2-02: publicação atômica do teto (`tempfile.mkstemp` no mesmo diretório, `os.link`, remoção do temporário); nunca sobrescreve um teto existente.
- R2-03: `KnowledgeBase.bootstrap()` faz uma leitura (`_registered`) e retorna sem `BEGIN IMMEDIATE` quando documentos e versão ativa existem; a primeira inicialização continua gravando o registro uma vez.
- R2-05: `timeout=30` no cliente OpenAI do CLI. R2-08: cliente DeepSeek extraído para `main.deepseek_client` e testes `max_retries == 0` e `timeout == 30` nos três clientes reais, sem rede; regressão de ativação e retorno com manifesto sem `chunks`/`point_digest` e coleção vazia.
- R2-07: `BudgetGuard.record` e `record_embedding` removidos (nenhum chamador em `src/`); a linha do teste antigo que os exercitava foi retirada.
- R2-04: risco aceito, sem mudança de código.
- Timeout web: `APIClient` usa 105 s (`BACKEND_MESSAGE_TIMEOUT_SECONDS`, 90 s do `MAX_REQUEST_SECONDS` + 15 s) para `send_v1_message`, `compare_routers`, `create_evaluation`, `kb_build` e `kb_test`, e 20 s (`BACKEND_TIMEOUT_SECONDS`) para o resto; recuperação por GET inalterada. Respostas de erro sem corpo JSON (gateway) viram `APIError` limpo.
- Compose: API publicada em `127.0.0.1:8000`.
- Limite por sessão demo: `DEMO_SESSION_MESSAGE_LIMIT` (padrão 20, 1–1000) com contador atômico em `api_sessions.message_count`; recusa `429 demo_message_limit_reached` antes de qualquer chamada ao modelo. Admin não é limitado. Novas execuções de comparação também contam.
- Ruff web: `ruff>=0.17,<1` no extra `test` do `pyproject.toml` web e `ruff==0.17.2` instalado no `.venv-v040` existente (única ação de rede).
- Scripts estritos: os dois passam a ignorar `.pytest_cache` e `_tmp`; o web também ignora diretórios `.venv*` (antes o Ruff varreria o `.venv-v040`).

**55 — Atendimento, Resultados e avaliação.**
- Catálogo `data/scenarios/catalog.json` (8 cenários: Knowledge, recebíveis, dispositivo, transação negada, divergência de taxa com encaminhamento, pedido humano, injection e D), com rótulos copiados dos casos de avaliação; módulo `scenarios.py`.
- `GET /v1/scenarios`; `scenario_id` opcional em `POST /v1/messages` (catálogo + mensagem idêntica; gravado no snapshot). O núcleo de `messages_v1` foi extraído para `execute_run` (reutilizado pela comparação) sem mudar o comportamento existente.
- `GET /v1/runs/{id}` acrescenta `steps` (com `hits`: documento, score, `chunk_id`, trecho de até 400 caracteres), `route`, `prompts_used`, `checks` e `evaluations`. As verificações reutilizam `runner._checks` por `persisted_checks`: com rótulo, todas; sem rótulo, `grounded_ok`, `errors_ok` e `isolation_ok` (marcadores do outro cliente sintético na resposta) e o resto em `not_evaluated`. Falhas críticas individuais: `unsupported_answer`, `forbidden_assertion_or_promise`, `cross_customer_leak`, `undue_refusal`.
- Avaliação sob demanda (`evaluation/on_demand.py`): `judge` v2 + `JudgeScore`, avaliador fixo `EVALUATOR_PROVIDER`/`EVALUATOR_MODEL` com `max_output_tokens=200` e `effort=none`, estimativa pelo preço do catálogo (preço desconhecido bloqueia), confirmação com `expected_estimate_digest` e `max_cost_usd`, reserva e liquidação na guarda persistente com `request_id=eval:<run>` e teto da confirmação, custo separado, reuso do registro com a mesma configuração salvo `repeat=true`, tentativa falha registrada sem notas. Execuções anteriores à v0.6.0 usam o texto mascarado da conversa como evidência.
- Snapshot ganha `scenario_id`, `purpose`, `message` (mascarada pelo input guard) e `prompt_set`; o trace ganha `purpose`, `scenario_id`, `citations` e os trechos nos `hits`.
- Bancos novos publicam Referência, Híbrido e Ajustado; o texto do campo `evaluation` do perfil diz que é preservado e não usado no atendimento.
- Interface: abas Atendimento, Resultados e Administração (só admin); cenário do catálogo enviado por botão próprio com `scenario_id`; estado do caso; comparação só dos Routers em seção própria; Resultados com rótulo do modo, métricas, modelos/tokens/custo por agente, etapas, ferramentas, fontes, trechos, verificações com origem, falhas críticas, avaliações ou "Não avaliado" e o fluxo estimar → confirmar → avaliar (estimativa consumida após o clique); mensagens de erro com ação de recuperação (`explain`). Cliente gerado e `openapi-v1.json` regenerados; `SimulatedAPI` e fixture `fixtures/v060.json` cobrem os modos Simulado e Gravado.

**56 — Comparação de perfis** (`comparisons.py`).
- `plan` (estimativa sem custo): 2–3 perfis publicados distintos, 1–3 cenários, 1–2 repetições, reuso de execuções compatíveis do mesmo principal (cenário, mensagem, digest do perfil, Router, versão da base, conjunto de prompts e modo de execução iguais), fatores fixos, mudanças por par e `exploratory` quando um par difere em mais de um agente; estimativa = `MAX_REQUEST_COST_USD` × células novas (limite superior) e `estimate_digest`.
- `start`: confirmação, digest, teto ≥ estimativa, estimativa ≤ saldo, uma comparação viva por principal, limite demo; grava `comparisons` como `running` e inicia thread daemon.
- `_run`: cópia do banco pela API de backup do SQLite num diretório temporário (removido no fim), uma versão da base capturada para todas as células, `execute_run` com `purpose=comparison` e `profile_comparison_id`, progresso persistido por célula, parada por teto da confirmação ou negação de orçamento (`budget_denied`) com as restantes `skipped`, estado final `completed`/`partial`/`failed`.
- `read`: comparação `running` sem thread viva vira `failed` (`interrupted`); agregados por perfil (amostra, custo e duração médios, qualidade determinística, falhas críticas, nota do avaliador só com todas as execuções avaliadas pela mesma configuração) e custo por agente/modelo com os `request_id`.
- Interface: seleção, estimativa, confirmação, execução, "Atualizar comparação" (GET), gráfico custo × qualidade (Altair, rótulo com amostra e duração; sem execução concluída → "não avaliada"), gráfico de custo por agente/modelo com seleção da barra por selectbox e botão que abre as execuções por GET, tabela de células.

**57 — Efeito da documentação.** Cenário `SC-DOC-EFFECT`; V2 em `data/scenarios/kb-demo-devices-v2.md`; diferença esperada e roteiro do QA em [v060-qa-preparacao.md](v060-qa-preparacao.md); teste de integração V1 → V2 → V1 com política programada e embeddings falsos.

**58 — Execução e documentação.** [Guia](../guia-demonstracao.md), [roteiro de teste manual](../roteiro-teste-manual.md), [roteiro do vídeo](../roteiro-video.md), READMEs, CHANGELOG 0.6.0, `.env.example`, contrato (`docs/contracts/api-v040.md`, seção v0.6.0), `Dockerfile` (`COPY data/scenarios`), versão 0.6.0 nos pacotes; `LOCK_BACKEND_URL` na interface compartilhada.

### Contratos e dados

- Rotas novas (só as aprovadas): `GET /v1/scenarios`, `POST /v1/runs/{id}/evaluations/estimate`, `POST /v1/runs/{id}/evaluations`, `POST /v1/comparisons/estimate`, `POST /v1/comparisons`, `GET /v1/comparisons/{id}`. Acréscimos: `scenario_id` em `POST /v1/messages` (e resposta 429 documentada) e campos novos em `GET /v1/runs/{id}`. Comparação semântica do OpenAPI regenerado contra o snapshot 0.5.0: nenhum caminho ou schema existente mudou além de `POST /v1/messages` e `V1MessageRequest` (aditivos). `POST /messages` legado e MCP intocados. `GET /v1/runs` (listagem) não foi implementado.
- Migração 0008 `demo_results` (reversível): `run_evaluations`, `comparisons` (índice `comparisons_owner_v060`), `api_sessions.message_count`; `INSERT` de sessões passou a nomear as colunas. Testada 0007 → 0008 → 0007 → 0008 em SQLite sintético.

### Arquivos alterados

Backend — modificados: `.env.example`, `CHANGELOG.md`, `Dockerfile`, `README.md`, `docker-compose.yml`, `docs/contracts/api-v040.md`, `pyproject.toml`, `src/merchant_assistant/{__init__.py, agents/knowledge.py, api/v1.py, cli.py, config.py, data/migrations.py, evaluation/runner.py, evaluation/scripted_policy.py, main.py, orchestration/budget.py, orchestration/graph.py, profiles.py, rag/kb.py}`, `tests/integration/{test_use_cases.py, test_v1_api.py}`, `tests/unit/{data/test_migrations.py, test_budget_and_router.py}`, `tools/scripts/lint_and_tests.py`, `docs/tasks/54..58`. Novos: `data/scenarios/{catalog.json, kb-demo-devices-v2.md}`, `src/merchant_assistant/{comparisons.py, scenarios.py, evaluation/on_demand.py}`, `tests/integration/{test_v060_api.py, test_v060_doc_effect.py}`, `tests/unit/test_v060_stabilization.py`, `docs/{guia-demonstracao.md, roteiro-teste-manual.md, roteiro-video.md}`, `docs/evidence/{v060-developer.md, v060-qa-preparacao.md}`. As demais alterações do working tree (specs, tarefas 46–53 e 59, ADR 0015, história, supervisão) já existiam e não foram tocadas.

Web — modificados: `README.md`, `app.py`, `fixtures/simulated.json`, `openapi-v1.json`, `pyproject.toml`, `src/getnet_web/{api.py, generated_api.py, simulated.py}`, `tests/test_interface.py`, `tools/generate_client.py`, `tools/scripts/lint_and_tests.py`. Novos: `fixtures/v060.json`, `tests/test_v060_interface.py`. Ambiente: `ruff 0.17.2` instalado em `.venv-v040`.

### Evidência

- Backend: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider --basetemp C:/workspace/ai-getnet-case/.pytest_cache/v060-dev-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **326 passed**, Ruff "All checks passed!", estrutura e skills válidas, código 0. Linha de base antes das mudanças: 293 passed.
- Web: `PYTEST_ADDOPTS="-p no:cacheprovider" .venv-v040/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **30 passed**, Ruff "All checks passed!", estrutura e skills válidas, código 0 (antes: 20 testes e código 2 por falta de Ruff).
- "Falha antes": os 14 testes de `test_v060_stabilization.py` rodados contra `git archive HEAD` (scratchpad) → 10 falham (R2-01 ×3, R2-02, campanha US$0,50, R2-03, R2-05/08a ×2, R2-07, Compose) e 4 passam (regressões de comportamento já correto: teto não sobrescrito, primeiro registro único, R2-08b ×2). Os testes de limite demo, timeout web, catálogo, avaliação e comparação dependem de código novo.
- Nenhuma chamada paga, chave de provedor, `.env`, `data/runtime/`, `discovery/` ou build Docker.

### Critérios comprovados e não verificados

Comprovados sem custo: itens das tarefas 54–58 com os testes listados nas seções "Validação" de cada tarefa. Não verificados pelo Developer: comportamento de modelos reais (Router escolher `knowledge_and_support` em D, Support chamar `get_contract_snapshot` com a V2, qualidade e custo reais da avaliação e da comparação), stack Docker em execução (`docker compose config`/build não executados porque leriam o `.env` local), visual da interface num navegador real (só `AppTest`), acesso externo, HTTPS e regras de roteador/firewall.

### Riscos, desvios e decisões tomadas dentro do aprovado

1. **Teto de campanha:** `CAMPAIGN_CAP_LIMIT_USD` passou de 0,25 para 0,50 para permitir a campanha `v060-qa` aprovada no plano (US$0,50); sem isso o QA não montaria a campanha. É mudança num controle de orçamento — confirmar.
2. **Scripts estritos:** passaram a ignorar `.pytest_cache` e `_tmp` (e o web, `.venv*`). Motivo: a primeira execução estrita do backend falhou porque o Ruff varreu scripts de QA antigos em `.pytest_cache` (inclusive `.pytest_cache/v050-qa-real-runtime/*.py`, lidos pelo Ruff apenas para lint, sem alteração). Os scripts são do template.
3. **Timeout longo** aplicado também a comparação de Routers, avaliação e build/teste de candidata (além de mensagens), porque todos esperam trabalho pago e já tinham risco de `ReadTimeout` a 20 s.
4. **Limite demo** conta também as novas execuções de uma comparação (conservador); um `409` de comparação de Routers obsoleta consome uma unidade do limite (a contagem acontece antes do consumo da comparação).
5. **`scenario_id` exige a mensagem idêntica** à do catálogo (`422 scenario_message_mismatch`), para que os rótulos valham; a interface envia o cenário por botão próprio.
6. **Isolamento entre clientes** como verificação determinística é a ausência, na resposta, do ID e do nome de outro cliente sintético; não detecta vazamentos de outras formas.
7. **`LOCK_BACKEND_URL`** (novo, opcional) impede que visitantes troquem a URL do backend numa interface compartilhada.
8. **`BudgetMeter`** aceita `effective_parameters` (o adaptador OpenAI o envia); antes, o caminho pago do `eval --judge` falharia com `TypeError`.
9. **Perfis:** só bancos novos nascem com o Ajustado publicado; um banco v0.5 existente precisa publicar o rascunho pela Administração (documentado).
10. **Comparação em thread:** depende do processo da API; reinício → `failed` (`interrupted`). Uma comparação viva por principal (todas as sessões demo compartilham o principal `demo:default`, como já ocorria com as execuções).
11. **R2-04** permanece como risco aceito.

### Não feito

- `GET /v1/runs` (listagem) não implementado; Resultados mostra as execuções da sessão do navegador e as abertas pela comparação. Se o Supervisor quiser execuções de outras sessões na área Resultados, é preciso aprovar a rota.
- Build e execução Docker, acesso externo, HTTPS real e verificação visual em navegador ficam com o QA e o responsável.

### Perguntas ao Supervisor

1. Confirmar o aumento de `CAMPAIGN_CAP_LIMIT_USD` para US$0,50 (item 1).
2. Confirmar a exclusão de `.pytest_cache`/`_tmp`/`.venv*` nos scripts estritos (item 2).
3. Manter a contagem das novas execuções de comparação no limite demo (item 4)?

- **Ação externa autorizada, identidade e efeito confirmado:** só a instalação de `ruff==0.17.2` no `.venv-v040` (dependência de desenvolvimento prevista). Nenhum commit, push, PR, merge, tag ou porta aberta.
- **Próxima ação e responsável:** Supervisor fixa o candidato por hashes e despacha o Reviewer em contexto novo; depois QA (tarefa 59).
- **Decisão humana pendente:** perguntas 1 a 3 acima.

## Rodada 2 — 2026-10-27

- **Papel e responsável:** o mesmo Developer da rodada 1, a pedido do Supervisor, para a [tarefa 60](../tasks/60-correcoes-revisao-v060-r1.md) (P3-01, 02, 03, 05, 06, 07, 08, 09 e 10 do [parecer r1](v060-reviewer.md)); P3-04 fora por decisão do responsável.
- **Estado:** apto para revisão do delta e QA.
- **Base:** os mesmos HEADs (`c3a9027…` backend, `4192169…` web); o candidato continua sendo o working tree. Sem commit, push ou PR.

### O que mudou

- **P3-01** `comparisons.read`: a comparação interrompida só é marcada `failed` se a linha ainda estiver `running` (`UPDATE … WHERE state='running'`), e a resposta sai da linha relida; a conferência da thread foi para `_alive()`.
- **P3-02** `evaluation/on_demand.py`: a avaliação reserva uma linha `running` dentro de `BEGIN IMMEDIATE` depois de conferir que não há avaliação concluída nem em andamento com a mesma configuração. Uma requisição concorrente recebe `409 evaluation_running`, e um `repeat=true` também espera. Se o orçamento recusar antes da chamada, a linha é apagada; se a chamada falhar, o registro vira `failed`. Uma reserva abandonada expira como `failed`/`interrupted` após 10 minutos. Na migração 0008, ainda não publicada, `run_evaluations.state` passou a aceitar `running`.
- **P3-03** (decisão do responsável): o limite demo conta toda ação paga, e recusa sem inferência não consome.
  - `consume_demo_messages` roda depois das validações. Com comparação de Routers, roda dentro da mesma transação que a consome: um `409` não gasta nada e um `429` não consome a comparação.
  - Passam a contar `POST /v1/router/compare` e `POST /v1/runs/{id}/evaluations`; o reuso de uma avaliação existente não conta.
  - A nova função `refund_demo_messages` devolve a unidade quando o orçamento recusa ou o provedor não está configurado antes da primeira chamada (comparação de Routers e avaliação).
  - A variável continua `DEMO_SESSION_MESSAGE_LIMIT` e o código continua `demo_message_limit_reached`. Mudaram a mensagem e as descrições em `.env.example`, no guia, nos READMEs, no CHANGELOG e na preparação do QA.
- **P3-05** web: na Administração, `httpx.TransportError` no build, no teste, na ativação e no retorno chama `kb_unconfirmed`. Ela descarta a estimativa e todos os contextos de confirmação e mostra um aviso para recarregar (GET) antes de repetir. As leituras e escritas sem custo dessa área mostram a ação de recuperação (`explain_any`). README web atualizado.
- **P3-06**: o snapshot grava `history_turns` (turnos já existentes na conversa), e o reuso da comparação exige `history_turns == 0`. Execuções anteriores sem o campo não são reaproveitadas.
- **P3-07** web: duas novas seleções.
  - "Ponto selecionado (perfil)" no gráfico custo × qualidade abre as execuções do perfil.
  - "Célula selecionada" na tabela abre a execução de qualquer célula com `request_id`, inclusive as que falharam.
  - Ambas leem por GET, pelo helper `open_runs` (o mesmo das barras).
- **P3-08**: o catálogo ganhou `SC-ENABLEMENT` (V030-PT-ENABLEMENT-PENDING) e `SC-SALE-CANCELLATION` (V030-PT-SALE-CANCELLATION) e passou a ter 10 cenários. **Desvio:** o plano falava em 6 a 8 cenários. Segui o passo 7 da tarefa 60 ("além das jornadas atuais") e não removi nenhum.
- **P3-09**:
  - (a) Testes de ativação durante a comparação e de reuso com outra versão da base.
  - (b) Caso negativo do bloco D com o lojista sem `link_de_pagamento`.
  - (c) Custo ausente fica desconhecido em `aggregates`, que agora traz `cost_mean_usd`/`cost_total_usd` nulos e `cost_unknown_runs`. Na interface, "desconhecido" e fora do gráfico. Um agente com vários modelos numa execução vira uma barra única, sem duplicar o custo.
- **P3-10** web: com `LOCK_BACKEND_URL` ligado, o modo Simulado oferece só o papel demo.
- Interface: avaliação `running` exibida como "em andamento".

### Arquivos tocados nesta rodada

- **Backend:**
  - Código: `src/merchant_assistant/{api/v1.py, comparisons.py, evaluation/on_demand.py, data/migrations.py}` e `data/scenarios/catalog.json`.
  - Testes: `tests/integration/{test_v060_api.py, test_v060_doc_effect.py}` e o novo `tests/integration/test_v060_r2.py`.
  - Documentação: `.env.example`, `README.md`, `CHANGELOG.md`, `docs/guia-demonstracao.md`, `docs/roteiro-teste-manual.md`, `docs/evidence/v060-qa-preparacao.md`, `docs/contracts/api-v040.md`, `docs/tasks/60-correcoes-revisao-v060-r1.md` e esta passagem.
- **Web:** `app.py`, `README.md` e `tests/test_v060_interface.py`.
- **Não tocados:** `docs/evidence/v060-reviewer.md` e `v060-supervisao.md`.

### Evidência

- Backend: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider --basetemp C:/workspace/ai-getnet-case/.pytest_cache/v060-dev-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **337 passed** (r1: 326), Ruff "All checks passed!", estrutura e skills válidas, código 0.
- Web: `PYTEST_ADDOPTS="-p no:cacheprovider" .venv-v040/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **34 passed** (r1: 30), Ruff sem achados, código 0.
- "Falha antes": não reexecutei contra o r1, porque o r1 não tem commit e por isso não há base que `git archive` possa reproduzir. Na tarefa 60, cada teste traz o motivo pelo qual falharia no r1: comportamento ou chave de interface inexistente, ou a sequência que o r1 executava.
- Nenhuma chamada paga, chave, `.env`, `data/runtime/`, `_tmp/` ou `discovery/`.

### Desvios e riscos

1. Catálogo com 10 cenários (P3-08), acima dos 6–8 do plano.
2. A migração 0008 mudou dentro da própria versão candidata (`running` no CHECK de `run_evaluations.state`). Não há instalação publicada com a 0008, mas um banco sintético criado com o r1 continua com o CHECK antigo e recusaria a reserva. Para QA, criar o runtime a partir do r2 ou voltar para a 0007 e subir de novo.
3. Contratos: só acréscimos de comportamento nas rotas aprovadas (`409 evaluation_running`, `429` em comparação de Routers e avaliação para sessão demo, campos `history_turns` e `cost_unknown_runs`). O legado e o MCP não mudaram.
4. O limite continua por sessão e renova a cada nova sessão (comportamento documentado). O teto do ledger segue como controle efetivo de gasto.

### Perguntas ao Supervisor

1. Aceita os 10 cenários no catálogo (desvio 1)?
2. Ciente de que runtimes sintéticos criados no r1 precisam ser recriados (desvio 2)?

## Rodada 3 — 2026-10-27

- **Papel e responsável:** o mesmo Developer, a pedido do Supervisor, para os resíduos da revisão r2 (itens 11 a 13 da [tarefa 60](../tasks/60-correcoes-revisao-v060-r1.md)). P3-R2-02 não exigiu código: a 0008 não foi publicada.
- **Estado:** apto para revisão do delta e QA. Base inalterada (HEADs `c3a9027…` e `4192169…`, working tree); sem commit, push ou PR.

### O que mudou

- **P3-R2-01** backend. Foram criados `model_calls_made(orchestrator, request_id)` (chamadas ao modelo no trace) e um `finally` em `messages_v1` que devolve a ação quando a execução termina sem chamada ao modelo. Isso cobre `RunFailure` (por exemplo Router com orçamento negado), `RuntimeError`, `LLMError` e resposta sem inferência. No fim de `_run`, a comparação grava `model_calls` por célula nova e devolve as que não chamaram o modelo (puladas por base alterada, teto da confirmação ou orçamento, ou recusadas antes da primeira chamada). Uma falha nessa contabilidade é registrada como `demo_refund_failed` e não oculta o resultado. Guia, CHANGELOG, README e `.env.example` foram alinhados à regra.
- **P3-R2-03:** teste do consumo no envio que usa a decisão da comparação de Routers.
- **P3-R2-04** web:
  - Barras com `cost_unknown` saem do gráfico 2, aparecem numa legenda "fora do gráfico (custo desconhecido)" e continuam selecionáveis com o rótulo "custo desconhecido".
  - O custo da avaliação usa `usd()` e mostra "desconhecido" quando é nulo, por exemplo numa avaliação em andamento ou interrompida.

### Arquivos tocados nesta rodada

- **Backend:**
  - código: `src/merchant_assistant/api/v1.py`, `src/merchant_assistant/comparisons.py`;
  - testes: `tests/integration/test_v060_r2.py`;
  - documentação: `README.md`, `CHANGELOG.md`, `.env.example`, `docs/guia-demonstracao.md`, `docs/tasks/60-correcoes-revisao-v060-r1.md` e esta passagem.
- **Web:** `app.py`, `README.md`, `tests/test_v060_interface.py`.

### Evidência

- Backend `lint_and_tests.py --strict` → **340 passed** (r2: 337), Ruff limpo, código 0.
- Web `lint_and_tests.py --strict` → **35 passed** (r2: 34), Ruff limpo, código 0.
- Cada teste novo falharia no r2, pelos motivos descritos na tarefa 60: contador 1 e 4 em vez de 0 e 1, R11 não detectada antes, rótulos numéricos.
- Nenhuma chamada paga; os limites de acesso foram mantidos.

### Desvios e riscos

- A devolução usa `model_calls` do trace. Uma resposta que termina sem nenhuma chamada ao modelo (por exemplo recusa determinística do input guard com texto fixo, se não houver chamada) também deixa de contar, coerente com "recusa sem inferência não consome".
- Contratos inalterados nesta rodada, exceto o campo informativo `model_calls` nas células da comparação.

## Rodada 4 — 2026-10-28

- **Papel e responsável:** o mesmo Developer, a pedido do Supervisor, para a [tarefa 61](../tasks/61-correcoes-qa-v060-r1.md) (P1-QA-01, P3-QA-02, P3-QA-03 e P3-R3-01, mais as observações O-1 a O-4 e o CHANGELOG), a partir do [QA r1](v060-qa.md).
- **Estado:** apto para revisão do delta e QA focal. Base inalterada (HEADs `c3a9027…` e `4192169…`, working tree); sem commit, push ou PR.

### O que mudou

- **P1-QA-01** (`api/v1.py`, `execute_run`): `agent_models` agora inclui sempre o Router do perfil. Com `mechanism == "jev"`, o `Orchestrator.handle` usa `router_llm` (o adaptador TypeSafe) para a entrada `router`, como já fazia para os nomes presentes. Antes, o Router ficava fora de `agent_llms` e caía no LLM padrão. Snapshot (`models.router`), trace e ledger (`router · jev-1.14.0`) e Resultados (`models_by_agent`) passam a coincidir. A correção vale para o envio direto e para a comparação de perfis, porque os dois usam `execute_run`. A comparação só dos Routers não mudou.
- **P3-R3-01** (`api/v1.py`, `comparisons.py`): novo `paid_attempts(budget, request_id)`, que conta as linhas `reserved`/`settled` do ledger primário para o `request_id` (no guard composto, a linha primária só existe depois das duas reservas; reserva cancelada não conta). Devolve a ação só quando a contagem é 0 confirmado. `None` (ledger ilegível ou em memória) nunca devolve. Na comparação, uma célula nova sem `request_id` nunca iniciou e é devolvida; as demais seguem a mesma regra pelo ledger. `model_calls` do trace continua só como informação na célula.
- **O-3** (`orchestration/graph.py`): `/ready` ganhou `knowledge_base: {version_id, collection}` da versão ativa. `versions.index` continua descrevendo o índice inicial do arranque.
- **Web** (`app.py`):
  - **P3-QA-02:** `literal()` escapa `$` no Markdown da conversa.
  - **P3-QA-03:** `find_pending_reply` devolve a mensagem recuperada inteira, e o estado do caso usa a rota e o status dela e o estado da conversa.
  - **O-1:** os perfis publicados são ordenados com Referência, Híbrido e Ajustado primeiro, e os três padrão aparecem em português no seletor e na comparação.
  - **O-2:** o teto do teste da candidata vem pré-preenchido com a estimativa do build da própria candidata. É um limite superior: o teste faz uma única consulta curta.
  - **O-4:** o gráfico custo × qualidade deixou de ter camada de texto; amostra e duração ficam na legenda e no tooltip.
- **Documentação:** CHANGELOG com dez cenários e a seção "Fixed (QA r1, task 61)"; contagens de testes atualizadas. O README e o CHANGELOG continuam dizendo candidato com QA pendente.

### Arquivos tocados nesta rodada

- Backend:
  - código: `src/merchant_assistant/api/v1.py`, `src/merchant_assistant/comparisons.py`, `src/merchant_assistant/orchestration/graph.py`;
  - testes: `tests/integration/test_v060_r4.py` (novo);
  - documentação: `README.md`, `CHANGELOG.md`, `docs/tasks/61-correcoes-qa-v060-r1.md` e esta passagem.
- Web: `app.py`, `README.md`, `tests/test_v060_interface.py`.

### Evidência

- Backend `lint_and_tests.py --strict` → **347 passed** (r3: 340), Ruff limpo, código 0.
- Web `lint_and_tests.py --strict` → **40 passed** (r3: 35), Ruff limpo, código 0.
- Por que cada teste falharia no r3: o Router ia para o LLM e o adaptador JEV nunca era chamado; o contador era devolvido sem trace; a tela mostrava o `$` como fórmula; o estado do caso ficava com a rota anterior; os nomes apareciam em inglês e o seletor começava em Adjusted; o teto do teste era 0; `/ready` não tinha `knowledge_base`; o gráfico tinha camada de texto.
- Nenhuma chamada paga. Não acessei `.env`, `data/runtime/`, controles de campanha, `_tmp/` nem `discovery/`.

### Riscos e limites

- O teste do P1 usa um transporte JEV falso. A chamada real ao TypeSafe fica para o QA focal (CA-32), conforme a "Próxima rodada" do QA.
- `/ready` ganhou um campo aditivo (`knowledge_base`); nenhum outro contrato mudou.
- Ficaram como limitação registrada, por instrução: os casos de preço que falham só na rubrica literal e o `EN-PRICE-CONDITIONS` em `clarify`.

## Rodada 5 — 2026-10-28

- **Papel e responsável:** o mesmo Developer, a pedido do Supervisor, para os resíduos da revisão r4 (itens 7 e 8 da [tarefa 61](../tasks/61-correcoes-qa-v060-r1.md)).
- **Estado:** apto para revisão do delta e QA focal. Base inalterada (HEADs `c3a9027…` e `4192169…`, working tree); sem commit, push ou PR.

### O que mudou

- **P3-R4-01**, web (`app.py`): `literal()` escapa `$` em todo texto livre do usuário ou do backend exibido como Markdown:
  - "Pergunta pendente" e comentário do avaliador por IA;
  - mensagens de erro do backend, dentro de `explain`, o que cobre todos os `st.error` que o usam;
  - mensagem do cenário, títulos das fontes e mensagens de falha da comparação.
  O texto enviado e o gravado não mudam. Trechos recuperados já usavam `st.text`, sem Markdown.
- **P3-R4-02**, backend (`tests/integration/test_v060_r4.py`, só testes): dois testes de falha aberta na devolução das células da comparação, equivalentes aos de mensagem. Pegam as mutações J5 (decidir pelo trace) e J7 (devolver com o ledger ilegível). O código de `comparisons.py` não mudou.

### Arquivos tocados nesta rodada

- Web: `app.py`, `tests/test_v060_interface.py`, `README.md` (só contagens).
- Backend:
  - testes: `tests/integration/test_v060_r4.py`;
  - documentação: `README.md` e `CHANGELOG.md` (só contagens), `docs/tasks/61-correcoes-qa-v060-r1.md` e esta passagem.

### Evidência

- Backend `lint_and_tests.py --strict` → **349 passed** (r4: 347), Ruff limpo, código 0.
- Web `lint_and_tests.py --strict` → **42 passed** (r4: 40), Ruff limpo, código 0.
- Por que os testes falhariam no r4: os testes web, porque esses textos saíam sem escape; o J5, porque o contador voltaria a 0 sem trace; o J7, porque a célula iniciada seria devolvida.
- Nenhuma chamada paga; os limites de acesso das rodadas anteriores foram mantidos.
