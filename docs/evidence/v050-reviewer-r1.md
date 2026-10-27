# Parecer independente — base versionada v0.5.0 (r1)

- Papel: Reviewer independente; contexto novo, sem participação na implementação. Não consultei o relatório do Developer nem tratei seus relatos como evidência. Não substitui QA.
- Estado: **correções necessárias; ainda não apto para QA**.
- Repositórios/branches: `C:\workspace\ai-getnet-case` e `C:\workspace\ai-getnet-case-web`, ambos em `codex/v0.5.0-base-versionada`.
- Base e HEAD: backend `ea2355b5ba8fa8dcff66200f34461ae063183250`; web `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`.
- Candidato: `v0.5.0-local-r1`; versão 1 da história `docs/historias/base-versionada-v050.md`.
- Próxima ação: Developer corrigir os achados; depois fixar candidato novo, repetir revisão independente e só então encaminhar para QA.

## Identidade e integridade

Recalculei os SHA-256 dos arquivos fixados antes da revisão e após as verificações. Os dois resultados coincidiram:

| Mapa | Arquivos | Fingerprint recalculado | Resultado |
| --- | ---: | --- | --- |
| Fonte backend | 32 | `046310f0b5b3a7f2ee1ee3b0d738e2559b1f69a28015a716c063552962cbd852` | 32/32 iguais |
| Fonte web | 84 | `ba17a02b65e38251182939d32632a93fce0e6ec6f2532f4136c9d3aa059c296a` | 84/84 iguais |
| Runtime backend | 128 | `2168ca8bfcc638034bc9c7c68865878f83fbc8ef36fa89eadee5a47fb16005d5` | 128/128 iguais |
| Entradas de build backend | 129 | `d40d4d3b1cae5a0c6e67baedfb6a7eb402dcb9583f5e7d8d683115f35d57399b` | 129/129 iguais |
| Fingerprint combinado das fontes | 116 | `0f9a4af3a7026877c7d1764a08f31b585cbe1e00cb6afd123fcdd6eeaaf22f7b` | Igual ao manifesto |

O HEAD dos dois worktrees permaneceu nos SHAs-base indicados. O delta v0.5 do backend é local. No web, o HEAD `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe` é a base v0.4; o candidato v0.5 está no working tree e difere de HEAD em `app.py`, `openapi-v1.json`, `pyproject.toml`, `src/getnet_web/api.py`, `src/getnet_web/generated_api.py`, `tests/test_interface.py` e `tools/generate_client.py`. Os 84 hashes congelados coincidem com os bytes locais do candidato, não com HEAD. Os diretórios `_tmp` usados pelos testes foram isolados e não fazem parte dos mapas do candidato. Nenhuma fonte do produto, teste, contrato, fixture ou configuração foi alterada nesta revisão.

## Achados acionáveis

### R1-01 — Embeddings pagos do CLI contornam a guarda financeira (P1)

**Condição e impacto:** `cmd_index` e `cmd_eval_retrieval` chamam `build_embedder` sem passar `budget`. A embedder real então fica com `budget=None`; em `OpenAIEmbedder.embed`, esse caminho envia o lote sem reservar e não registra uso. Esses comandos podem pagar embeddings fora do teto persistente do projeto.

**Localização:** [cli.py](../../src/merchant_assistant/cli.py:21), [cli.py](../../src/merchant_assistant/cli.py:60), [cli.py](../../src/merchant_assistant/cli.py:71), [embed.py](../../src/merchant_assistant/rag/embed.py:36).

**Reprodução estática:** `main()` mapeia `index` a `cmd_index`; `cmd_index` chama `build_index(settings, fake=args.fake)`; esse caminho chama `build_embedder(..., budget=None)`. `eval-retrieval` também chama `build_embedder(settings, fake=args.fake)` sem guarda. A condição `if self.budget` em `embed.py` pula a reserva. Não executei esses comandos contra provedores reais.

**Correção esperada:** fornecer a guarda persistente nesses caminhos ou recusar qualquer modo pago sem guarda; conferir também que o limite absoluto não possa exceder US$5.

### R1-02 — Comandos de índice ainda apagam/reconstroem coleção versionada (P1)

**Condição e impacto:** `build_index` chama `KnowledgeIndex.rebuild` sem `replace_existing=False`. O padrão apaga uma coleção que já exista. `index` e `bootstrap --force-index` usam a coleção configurada, que no bootstrap da base vira a coleção do `kb_initial`; após ativações, essa coleção pode ser a anterior. Reconstruí-la a partir dos arquivos de origem muda o conteúdo sob uma identidade publicada e pode destruir a possibilidade de retorno.

**Localização:** [cli.py](../../src/merchant_assistant/cli.py:44), [cli.py](../../src/merchant_assistant/cli.py:52), [cli.py](../../src/merchant_assistant/cli.py:55), [index.py](../../src/merchant_assistant/rag/index.py:66), [kb.py](../../src/merchant_assistant/rag/kb.py:74).

**Reprodução:** no CLI, `index` chama `build_index`; `build_index` usa `settings.qdrant_collection`, e `rebuild` apaga a coleção existente nas linhas 73–78 por padrão. O caminho não valida se a coleção é ativa/anterior no registro `kb_state`.

**Correção esperada:** impedir reconstrução de qualquer coleção referenciada por versão ativa/anterior; fazer o CLI criar coleção versionada nova ou exigir um destino explicitamente descartável e isolado.

### R1-03 — Ativação e retorno aceitam coleção vazia como íntegra (P1)

**Condição e impacto:** a transição valida apenas que a coleção existe. Se os vetores forem perdidos ou a coleção for recriada vazia depois do teste, uma versão `ready` ainda pode ser ativada; rollback também aceita a coleção anterior vazia. Um atendimento passa a consultar uma versão sem índice utilizável, embora a ativa continue marcada como saudável.

**Localização:** [kb.py](../../src/merchant_assistant/rag/kb.py:458), [kb.py](../../src/merchant_assistant/rag/kb.py:472), [graph.py](../../src/merchant_assistant/orchestration/graph.py:301).

**Reprodução sintética própria:** com `offline_orchestrator`, `ScriptedLLM`, `HashEmbedder` e Qdrant `:memory:`, construí e testei uma candidata (`ready`, teste positivo); no Qdrant exclusivamente em memória, substituí sua coleção por outra vazia com o mesmo nome; `transition(..., action="activate")` retornou sucesso e `capture_active()[0].count()` retornou `0`. Em outra execução, a mesma condição na coleção anterior não impediu rollback. Nenhuma coleção persistente ou real foi removida.

**Correção esperada:** antes de ativar ou retornar, verificar a coleção contra manifesto (contagem, dimensão/modelo e digest/pontos esperados) e rejeitar versões cuja integridade não possa ser confirmada. `readiness()` também consulta `self.index` fixo, não o índice capturado pelo ponteiro atual, então pode continuar `ready` olhando para a coleção inicial depois que uma candidata ativa ficou vazia.

### R1-04 — Liquidação duplicada substitui gasto já liquidado (P1)

**Condição e impacto:** `BudgetGuard.settle` atualiza a linha pelo ID sem exigir estado `reserved`. Uma segunda liquidação com valor menor substitui o custo já gravado e libera saldo. Isso viola a liquidação única e permite que retries/callbacks duplicados reduzam o gasto persistente abaixo do valor conhecido.

**Localização:** [budget.py](../../src/merchant_assistant/orchestration/budget.py:82), [budget.py](../../src/merchant_assistant/orchestration/budget.py:89), [budget.py](../../src/merchant_assistant/orchestration/budget.py:186).

**Reprodução sintética própria:** no SQLite temporário, reservei US$0,05; `settle(id, 0.01)` resultou em `spent=0.01`; repetir `settle(id, 0.001)` alterou o gasto para `spent=0.001`.

**Correção esperada:** fazer a liquidação condicional a `status='reserved'`, definir comportamento idempotente para repetição com o mesmo valor e recusar tentativa de sobrescrever estado liquidado/cancelado. Aplicar a mesma semântica de forma consistente no guard composto.

### R1-05 — Testar versão publicada altera seu estado para candidata (P2)

**Condição e impacto:** `test_version` permite estados `active` e `retired`, mas sempre termina chamando `_set_version` com `ready` ou `testing`. Ao testar a própria ativa, a linha deixa de estar `active` enquanto `kb_state.active_version_id` continua apontando para ela; leituras e transições passam a observar estados contraditórios.

**Localização:** [kb.py](../../src/merchant_assistant/rag/kb.py:433), [kb.py](../../src/merchant_assistant/rag/kb.py:455).

**Reprodução sintética própria:** testar `kb_initial` com `confirmed=True` retornou sucesso; antes, `version("kb_initial")` estava `active`; depois, continuou como ponteiro capturado, mas seu estado persistido era `ready`.

**Correção esperada:** restringir teste a candidatas `testing`/`ready`, ou manter o estado publicado e guardar resultado de teste sem rebaixar `active`/`retired`.

### R1-06 — Limite configurável não impõe o teto absoluto de US$5 (P1)

**Condição e impacto:** `BUDGET_LIMIT_USD` é um `float` sem limite máximo, e `BudgetGuard` aceita qualquer `limit_usd`. Uma configuração acima de US$5 permite reservas maiores que o teto global definido para o projeto, mesmo que o exemplo de ambiente use um default menor.

**Localização:** [config.py](../../src/merchant_assistant/config.py:44), [budget.py](../../src/merchant_assistant/orchestration/budget.py:33), [budget.py](../../src/merchant_assistant/orchestration/budget.py:64).

**Reprodução sintética própria:** inicializei `BudgetGuard` em SQLite temporário com limite `6.0`; a reserva de US$5,01 foi aceita e, com uso desconhecido, permaneceu comprometida. Não usei o ledger do projeto.

**Correção esperada:** impor máximo absoluto de US$5 na configuração/guarda e validar também o limite persistente existente ao montar o runtime, sem aumentar silenciosamente um teto já fixado.

## Evidência executada

- Backend, ambiente `.venv/Scripts/python.exe`, transporte/DB sintéticos: `pytest tests/unit/data/test_migrations.py tests/unit/rag/test_rag_pipeline.py tests/unit/test_budget_and_router.py tests/integration/test_v1_api.py -k 'migration_0006 or kb_draft_build_test_activate or candidate_rebuild or embedding_budget or campaign_cap or primary_guard_denial or budget_reserve_settle_and_limit or budget_unknown_usage or budget_is_atomic' --basetemp C:\workspace\ai-getnet-case\_tmp\review-v050-r1` — **9 passaram, 32 foram filtrados**. Uma primeira execução falhou somente porque o diretório pai do `basetemp` ainda não existia; a repetição com pai criado passou.
- Backend Ruff, arquivos Python afetados — **All checks passed**.
- Web, `tests/test_interface.py`, AppTest e transportes simulados — **15 passaram**.
- Gerei OpenAPI em memória com `create_app(Settings(_env_file=None))`, sem `main`, bootstrap, banco de produção ou provedores; comparação semântica com `openapi-v1.json`: **igual**, 25 rotas e 23 schemas. O cliente gerado cobre as 22 operações v1 esperadas nos testes web.
- Nenhuma inferência, embedding, judge, chamada autenticada de modelos ou chamada paga real foi executada. Não fiz POST nos serviços históricos `18030`/`18031`, nem usei banco/ledger real.

## Critérios e limites

**Com evidência favorável nesta revisão:** mapa/fingerprints do candidato; revisão/diff de rascunho fictício; fonte oficial somente leitura; migração0007 e caminho sintético de jornada; coleção nova no fluxo KB; captura de versão no trace; snapshot OpenAPI sincronizado; estados de autorização básicos; testes focados e lint.

**Ainda não comprovados para QA:** concorrência real de ativações/capturas em HTTP, contrato MCP end-to-end, comportamento real dos provedores/custos, CA-41 completo pela interface contra o runtime v0.5 instalado, indisponibilidade/timeout dos provedores e decisão de release. O Supervisor informou que preparou um runtime sintético separado; esta revisão não o usou nem o considera QA concluído.

**Risco para QA posterior:** o cliente web tem timeout HTTP fixo de 20s (`src/getnet_web/api.py`), enquanto o cliente OpenAI do backend tem timeout de 30s por chamada (`src/merchant_assistant/main.py`) e build/teste são síncronos. Não executei provedor real para medir latência. Confirmar durante QA que o build não termina no backend depois de o navegador abandonar a chamada e que a UI consegue recuperar o resultado sem repetir gasto.

Sem ações externas: não houve commit, push, integração, publicação ou contato com terceiros.
