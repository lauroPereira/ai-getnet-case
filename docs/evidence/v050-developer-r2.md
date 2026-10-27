# Passagem Developer r2 — correção da revisão r1 (tarefa 45)

- **Papel e responsável:** Developer, Claude Sonnet 5.5, contexto novo, despachado pelo Supervisor. Substitui o Developer `gpt-6-luna/high` da r1 por autorização do responsável em 2026-10-27. Único escritor de produto nesta etapa.
- **Objetivo e critérios:** corrigir R1-01 a R1-06 do [parecer r1](v050-reviewer-r1.md) conforme a [tarefa 45](../tasks/45-correcao-revisao-v050-r1.md), sem ampliar API, permissões ou orçamento.
- **Escopo:** somente backend `C:/workspace/ai-getnet-case`. O web (`ai-getnet-case-web`) **não foi alterado nem reexecutado**: nenhuma correção exigiu mudança de contrato ou de cliente.
- **Estado:** correções implementadas e validadas pela estrita; **em andamento até o Supervisor fixar o candidato r2 e o Reviewer independente revisar**. Sem autoaprovação.
- **Branch e PR:** `codex/v0.5.0-base-versionada`, sem commit/push/PR. Branch e HEAD não foram trocados nem alterados; sem stash/reset/checkout.
- **Base e versão final:** backend base `ea2355b5ba8fa8dcff66200f34461ae063183250`; delta v0.5 e esta passagem estão no working tree. SHA-256 (16 primeiros hex) dos arquivos tocados nesta etapa:

| Arquivo | SHA-256 (16) |
| --- | --- |
| `src/merchant_assistant/cli.py` | `c6b20a98474d098d` |
| `src/merchant_assistant/config.py` | `5f58d4479c77a7ec` |
| `src/merchant_assistant/rag/embed.py` | `cd830c5026a7f80f` |
| `src/merchant_assistant/rag/index.py` | `e9c30b94cd7cf3a1` |
| `src/merchant_assistant/rag/kb.py` | `e05e2ac96025cac3` |
| `src/merchant_assistant/orchestration/graph.py` | `57952046929b6a00` |
| `src/merchant_assistant/orchestration/budget.py` | `fd0e927d603dd497` |
| `tests/unit/test_budget_and_router.py` | `22e4ace39f2faef1` |
| `tests/unit/rag/test_rag_pipeline.py` | `d35c448dcdaf964d` |
| `tests/unit/test_cli_index_guard.py` (novo) | `79ceef81c8c90d16` |
| `tests/integration/test_kb_safety.py` (novo) | `176c864a4747d6c4` |
| `README.md` (2 linhas), `.env.example` (comentário) | `72fd221929fc9d14`, `71474a0d6728e041` |

- **Independência:** não-independente (Developer; não revisa nem aprova o próprio trabalho).

## Ponto de partida a conhecer

`orchestration/budget.py` **já chegou ao meu contexto alterado em relação ao candidato r1**: hash `bc90a12a…` contra `495ba608…` do [manifesto r1](v050-candidato-r1.json), mtime 13:42, depois do parecer. Era a única fonte de produto divergente do manifesto. Ele já trazia `settle` só a partir de `reserved`, teto 0–5, teto persistente em arquivo `<ledger>.limit`, validação de valores e `FixedBudgetGuard`/`CombinedBudgetGuard`. Não sei quem o editou. Tratei como estado de partida: **auditei, testei, corrigi dois erros de Ruff (ordem de imports e linha > 120) e introduzi constantes nomeadas**. Para provar que as regressões R1-04/R1-06 falham no comportamento anterior, restaurei numa cópia de scratchpad a liquidação incondicional e a ausência de teto descritas no parecer.

## Achado → correção → arquivos → testes

**R1-01 — embeddings pagos do CLI sem guarda.**
- `build_embedder` recusa (`SystemExit`) embedder real sem guarda **antes** de criar o cliente do provedor. `index` e `eval-retrieval` passaram a montar `BudgetGuard(runtime/budget.sqlite3, BUDGET_LIMIT_USD)` (só no modo pago; `--fake` não toca ledger); `bootstrap` monta a guarda só quando vai construir.
- `OpenAIEmbedder.embed` lança `RuntimeError` sem `budget` antes de qualquer lote. O caminho `on_usage` (registro posterior ao envio) foi removido; sem chamadores. Resposta sem `usage` válido (ausente, negativo, não inteiro) mantém a reserva conservadora e devolve os vetores.
- Arquivos: `cli.py`, `rag/embed.py`. Testes: `test_cli_index_guard.py` (guarda ausente; reserva antes de cada lote com o ledger observado dentro do transporte falso; negação; uso desconhecido sem retry; `index`, `bootstrap` e `eval-retrieval` parametrizados) e uso inválido no embedder.

**R1-02 — CLI/bootstrap apagavam ou reconstruíam coleção existente.**
- `KnowledgeIndex.rebuild` agora **recusa por padrão** (`replace_existing=False`) e gera os embeddings **antes** de criar a coleção; falha paga não deixa coleção vazia. `build_index` recusa coleção existente. `bootstrap` constrói só se a coleção não existe; existente e atual → pula (idempotente); existente e defasada → mantém e avisa; `--force-index` com coleção existente → recusa. Nenhum código de `src` remove coleção.
- Arquivos: `rag/index.py`, `cli.py`. Testes: `test_cli_index_guard.py` (índice, `--force-index`, defasada, idempotência), `test_rag_pipeline.py` (padrão recusa; falha não cria coleção) e `test_kb_safety.py` (CLI recusa coleções ativa e anterior referenciadas no registro; colisão de ID de candidata e coleção que aparece durante o build não são substituídas). Todos em Qdrant `:memory:`.

**R1-03 — ativação/retorno aceitavam coleção vazia; readiness olhava índice fixo.**
- `KnowledgeIndex.inspect()` (somente leitura, sem embedding): dimensão, pontos, digest dos `chunk_id`. `KnowledgeBase._verify_integrity` compara com o manifesto: existência, pontos > 0, modelo e dimensão do embedder, contagem e `point_digest`. Roda em `transition` (ativar e retornar, dentro da transação, ponteiro intacto na recusa), em `test_version` (falha → `failed`, sem busca) e após o build. `rebuild` grava `point_digest`; `kb_initial` registra contagem e digest da coleção preservada. `Orchestrator.readiness()` conta o índice da versão ativa atual (`capture_active`), sem chamada paga.
- Arquivos: `rag/kb.py`, `rag/index.py`, `orchestration/graph.py`. Testes: `test_kb_safety.py` (vazia, removida, ponto perdido, ponto trocado e dimensão errada, na ativação e no retorno; 409 pela API; teste de versão corrompida; readiness) e `test_rag_pipeline.py` (`inspect`).

**R1-04 — liquidação duplicada reduzia gasto.**
- `BudgetGuard.settle` (já parcialmente corrigido): só a partir de `reserved`, repetição igual idempotente, valor diferente, uso desconhecido sobre liquidada, cancelada ou id desconhecido recusados; NaN/inf/negativo recusados em `reserve`, `settle` e `record`. `CombinedBudgetGuard` herda a semântica: liquida primário e depois campanha, e falha parcial mantém a reserva conservadora e é completada por retry com o mesmo valor. `KnowledgeBase` valida o teto em dólares (`max_cost_usd` NaN/inf/negativo).
- Arquivos: `orchestration/budget.py`, `rag/kb.py`. Testes (`test_budget_and_router.py`): liquidação única, cancelada/desconhecido, valores inválidos x4, concorrência (12 threads), composto repetido/divergente, uso desconhecido, falha parcial na campanha e no primário, concorrência do composto em 15 rodadas.

**R1-05 — testar versão publicada a rebaixava.**
- `test_version` só aceita `testing`/`ready`; `_set_version(..., from_states=)` atualiza condicionalmente e informa se aplicou, então ativação concorrente nunca é sobrescrita (409, estado preservado). A UI web só oferece teste a `testing`/`ready`.
- Arquivo: `rag/kb.py`. Testes (`test_kb_safety.py`): ativa/retirada recusadas com estado e ponteiro intactos, 409 `version_not_testable` pela API e corrida determinística com ativação entre a leitura e a escrita.

**R1-06 — teto absoluto de US$5.**
- `Settings.budget_limit_usd` aceita 0–5, finito (`ABSOLUTE_BUDGET_LIMIT_USD`, em `budget.py`, usado também por `BudgetGuard`). O teto persistente por ledger não aumenta por remontagem (`__init__`); ledger legado sem registro fica no US$1 nativo. Cap adicional segue `0 < cap ≤ 0,25` (`CAMPAIGN_CAP_LIMIT_USD`), fixado uma vez por ID e valor.
- Arquivos: `config.py`, `orchestration/budget.py`; documentado em `README.md` e `.env.example`. Testes: limites 5,01/6/1000/negativo/NaN/inf em `Settings` e guarda, exatamente US$5, teto persistido, ledger legado e cap de campanha nos dois sentidos.

## Evidência executada

- **Estrita:** `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="--basetemp C:/workspace/ai-getnet-case/.pytest_cache/v050-t45-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **293 passed em 196,25 s** (221 antes), Ruff "All checks passed", estrutura e skills válidas, "Validação estrita concluída sem falhas".
- **Focados (4 arquivos):** `tests/unit/test_cli_index_guard.py`, `tests/integration/test_kb_safety.py`, `tests/unit/test_budget_and_router.py`, `tests/unit/rag/test_rag_pipeline.py` → **87 passed** (basetemp `v050-t45-focused-fixed2`).
- **Falham antes, passam depois:** os mesmos quatro arquivos contra cópia pré-correção em `C:/Users/lauro/AppData/Local/Temp/claude/C--workspace-ai-getnet-case/296b957a-2ff9-46e9-9342-f6b565a4e81d/scratchpad/prefix` (arquivos originais de produto restaurados; `budget.py` com settle incondicional e sem teto) → **56 failed / 31 passed**. O teste de concorrência do guard composto falhou 3 de 3 nessa árvore.
- **Passam também antes (guardas de não regressão):** `bootstrap` reservando antes da rede (já usava guarda), coleção `dropped` (já barrada por `exists()`), ativação/retorno válidos, cap de campanha (já existia), uso desconhecido e falha do primário no guard composto, embedder `--fake`. Os dois testes de colisão de candidata usam `inspect()` e por isso falham antes por `AttributeError`, não por comportamento; o comportamento de colisão já estava correto.
- **Contrato:** OpenAPI gerado em memória com `Settings(_env_file=None, demo_mode=True)` **igual** a `ai-getnet-case-web/openapi-v1.json`. Sem demo as duas rotas de demonstração ficam fora, como no estado de partida. Nenhuma rota, schema ou permissão mudou.
- **Dados reais:** `data/runtime/*` com mtimes de 2026-10-26, nenhum `.limit` criado ao lado do ledger real. Nenhuma coleção, ledger, `_tmp/` ou arquivo foi removido. Diretórios de teste novos sob `.pytest_cache/v050-t45-*`.

## Critérios comprovados e não verificados

- **Comprovados:** os seis casos têm regressão sintética; reserva anterior em toda tentativa paga de embedding (`max_retries=0` em todos os clientes OpenAI/DeepSeek, JEV com `httpx.post` único, conferido por busca estática); imutabilidade de coleções publicadas; ponteiro intacto em recusa e corrida; liquidação única também sob concorrência; US$5 e cap persistente não ampliáveis por remontagem; estrita completa.
- **Não verificados (fora do escopo):** web reexecutado (não afetado); concorrência real por HTTP; provedores reais; QA pago; build Docker do candidato r2.

## Limitações e decisões para o Supervisor ou o responsável

1. **Teto persistente em arquivo `<ledger>.limit`.** O primeiro mount grava o teto ao lado do ledger (ledger preexistente sem arquivo fica em US$1). Efeitos: `BUDGET_LIMIT_USD` maior que o primeiro valor passa a **recusar a inicialização**, e o **primeiro uso do ledger real** (ou do runtime de QA) cria `budget.sqlite3.limit` com 1. Não toca no SQLite, mas é um arquivo novo ao lado dele. Mantive por já estar no estado de partida e atender "não aumentar por remontagem"; **confirme que aceita esse efeito.**
2. **`bootstrap` deixou de reconstruir índice defasado.** Coleção existente e diferente das fontes é mantida com aviso e exit 0 (o `entrypoint.sh` usa `set -e`); atualizar o conteúdo exige nova versão pela API administrativa. README ajustado.
3. **`/v1/kb/versions/{id}/test`** passa a responder 409 `version_not_testable` para `active`, `retired`, `failed` e `building`. Código já existente; coerente com a proposta de API e com a UI web.
4. **Manifesto de versão ganha `point_digest`** (e `chunks`/`point_digest` em `kb_initial`) como campos aditivos num dicionário já opaco no OpenAPI. `kb_initial` registrado pelo código r1, sem digest, recebe verificação mais fraca (existência, pontos > 0, modelo e dimensão), nunca mais forte que o registrado.
5. **Falha de integridade em `test_version`** leva a versão a `failed` com erro saneado; em `transition` só recusa (409) e mantém o estado.
6. `readiness()` passa a chamar `capture_active()`, que pode registrar `kb_initial` na primeira chamada (escrita no SQLite do runtime, como já ocorre no primeiro atendimento).
7. `BudgetGuard.record`/`record_embedding` continuam no código, sem nenhum caminho pago que os chame.
8. Quebras de linha: arquivos rastreados mantidos em CRLF; os dois testes novos estão em LF (`* text=auto` normaliza).
9. ADR0014, proposta de API, plano e spec **não foram editados**; ficam a critério do Supervisor.

## Ação externa autorizada

Nenhuma: sem commit, push, PR, rede, provedor, remoção ou alteração de credenciais.

## Próxima ação e responsável

Supervisor: fixar o candidato r2, incluindo os dois testes novos, `README.md`, `.env.example` e esta passagem, e despachar o Reviewer independente (Sonnet 5.5, contexto novo). QA real só depois de parecer técnico apto.

## Decisão humana pendente

Itens 1 e 2 acima: aceitar o arquivo `<ledger>.limit` como mecanismo do teto persistente e aceitar que `bootstrap` nunca reconstrua uma coleção existente.
