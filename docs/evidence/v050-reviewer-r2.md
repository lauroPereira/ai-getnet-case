# Parecer independente — base versionada v0.5.0 (r2)

- Papel: Reviewer independente (Sonnet 5.5), contexto novo, sem participação na implementação. Não substitui QA.
- Estado: **apto para QA** — nenhum achado P1/P2. Sete achados P3 (R2-01 a R2-05, R2-07, R2-08) e uma decisão humana pendente (R2-06) descritos abaixo; a decisão R2-06 deve ser tomada **antes** de o QA montar o ledger real.
- Repositórios/branches: `C:\workspace\ai-getnet-case` e `C:\workspace\ai-getnet-case-web`, ambos em `codex/v0.5.0-base-versionada`.
- Base e HEAD (não houve commit): backend `ea2355b5ba8fa8dcff66200f34461ae063183250`; web `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`. O candidato é o working tree local.
- Candidato: `v0.5.0-local-r2` (manifesto `v050-candidato-r2.json`, pai `v050-candidato-r1.json`).
- Próxima ação: Supervisor decidir R2-06 e encaminhar ao QA com o candidato fixado; Developer pode tratar os P3 (R2-01, R2-02, R2-05, R2-07 e R2-08 são baratos e isolados) sem reabrir revisão completa, ou o Supervisor pode aceitá-los como pendências conhecidas.

## Independência e limites desta revisão

Não li `v050-developer-r1.md`, `v050-developer-r2.md` nem a seção "Validação" da tarefa 45 como evidência. **Declaração de exposição incidental:** duas buscas textuais minhas (uma por `.limit|sidecar`, outra por `force-index`) devolveram, no resultado, algumas linhas desses relatórios e de `v050-supervisao.md`. Não as usei como evidência nem como guia de conclusão; cada afirmação abaixo foi re-derivada por inspeção do código ou por execução própria. Registro a exposição para que o Supervisor pese a independência.

Sem chamada paga ou de rede a provedores. Sem leitura de valores de `.env`. `data/runtime/` não foi aberto nem alterado (uma única consulta de existência, sem abrir o arquivo, confirmou que **não** há `budget.sqlite3.limit` ao lado do ledger real após a validação estrita). `_tmp/`, containers e coleções existentes não foram tocados. Nenhum arquivo de produto, teste, contrato, documento ou configuração foi alterado; o único arquivo escrito no repositório é este parecer. Scripts e saídas temporárias: scratchpad `review-r2/` e `.pytest_cache/v050-review-r2-*` (`-strict`, `-web`, `-mut`).

## Identidade e integridade do candidato

Recalculei os SHA-256 dos bytes dos arquivos dos mapas do manifesto antes e depois das verificações. Resultado igual ao manifesto nas duas medições (a medição "depois" está no fim deste documento).

| Mapa | Arquivos | Fingerprint recalculado | Resultado antes |
| --- | ---: | --- | --- |
| Fonte backend | 38 | `d81a35ca72807fe2df5193e69b575e7b8eb6241dad741aacd22bdc285ad6e18e` | 38/38 iguais |
| Fonte web | 84 | `ba17a02b65e38251182939d32632a93fce0e6ec6f2532f4136c9d3aa059c296a` | 84/84 iguais |
| Fingerprint de fonte (mapa `{"backend":…, "web":…}`) | 122 | `22b0c92dd79ac9db710ecb69e95eb69101b0c332951a2653b21ffcc5e92786b0` | igual ao manifesto |
| Runtime backend | 128 | `22556665c215a837fa5d9cc1b7b8dacd52fa3b06b40ed46e8e1b86b9ef40ce0e` | 128/128 iguais; fingerprint igual |
| Entradas de build backend | 129 | `c74764b0d0932851a123ff8f5f13b11e96e266f8530b2a4ae5ee2e1016d1c3a5` | 129/129 iguais; fingerprint igual |

Também conferi: `changed_from_parent` do r2 é exatamente a diferença entre os mapas r1 e r2 (15 arquivos backend, nenhum web); e toda alteração do working tree fora de `docs/evidence/` e `_tmp/` está coberta por algum mapa. O fingerprint combinado só reproduz com o mapa aninhado `{"backend", "web"}`; a descrição de `hash_algorithm` do manifesto não diz isso — sugiro explicitar.

## Situação dos achados do parecer r1

| Achado | Situação | Evidência própria (resumo) |
| --- | --- | --- |
| R1-01 embeddings pagos do CLI sem guarda (P1) | **Corrigido** | `build_embedder`/`build_index` pagos sem guarda → `SystemExit` antes de criar cliente; `OpenAIEmbedder` sem guarda → `RuntimeError` antes do provedor (0 chamadas). `index`, `bootstrap` e `eval-retrieval` com transporte falso: 3, 3 e 17 chamadas, 3/3/17 linhas no ledger, todas `settled`, e em cada despacho havia exatamente 1 reserva aberta. Negação (limite 1e-8): `BudgetExceeded`, 0 chamadas, 0 coleções. Erro do provedor: 1 chamada (sem retry), reserva conservada como gasto, 0 coleções. Clientes OpenAI: `max_retries=0` em `main.openai_client`, no cliente DeepSeek e no cliente do CLI; não há outro laço de retry em `src/`. |
| R1-02 CLI apaga/reconstrói coleção (P1) | **Corrigido** | `cmd_index`, `build_index`, `bootstrap --force-index` e `rebuild` (padrão e `replace_existing=False`) recusam coleção existente e deixam `inspect()` (pontos, dimensão, digest) idêntico, com 0 chamadas ao provedor. `bootstrap` comum: cria só se a coleção não existe; repetido, "current; skipping"; coleção defasada fica intocada com aviso. Nenhum chamador em `src/` usa `replace_existing=True` nem `delete_collection` fora do ramo opt-in de `rebuild`. Embeddings são gerados **antes** de criar a coleção (falha paga não deixa coleção vazia). |
| R1-03 ativação/retorno aceitam coleção vazia (P1) | **Corrigido** (com o limite descrito em "Limites da verificação de integridade") | Reproduzi o cenário do r1: coleção candidata substituída por vazia → `activate` recusa (`RuntimeError`, 409 pela API), ponteiro e estado `ready` intactos; idem retorno com anterior vazia. Também recusados na minha execução: ponto extra e dimensão errada (8 vs 512); e, pelos testes da suíte que executei (`test_kb_safety.py`), coleção removida, ponto removido e `chunk_id` adulterado, na ativação e no retorno. `readiness()` agora conta a coleção da versão ativa: com a ativa esvaziada devolve `ready=False`, `index_chunks=0` enquanto a coleção inicial continua com 145 pontos. Nenhum embedding/chamada paga na verificação. |
| R1-04 liquidação duplicada (P1) | **Corrigido** | `reserve 0.05 → settle 0.01 → settle 0.001` agora `ValueError`, gasto permanece 0,01; repetir 0,01 é idempotente; `settle(None)` após valor conhecido, liquidação de cancelada e de id desconhecido recusadas; `nan`, `inf`, negativo recusados sem liberar saldo. 12 threads liquidando a mesma reserva: exatamente 1 vence. Guard composto: reenvio com mesmo valor completa o par após falha parcial; valor divergente recusado; `None` conserva a reserva nos dois ledgers; negação do primário cancela a reserva da campanha (0 gasto) e negação da campanha não toca o primário. |
| R1-05 testar versão publicada rebaixa estado (P2) | **Corrigido** | `test_version` só aceita `testing`/`ready`; em `kb_initial` ativa, versão ativa e `retired` devolve `RuntimeError` (409 `version_not_testable` pela API) sem mudar estado nem ponteiro; `failed` não é retestável nem ativável. A escrita do resultado é condicional ao estado (`from_states`): 6 rodadas com 3 threads testando + 2 capturando + 1 ativação, e 8 rodadas de duas ativações + um retorno concorrentes, terminaram sempre coerentes (um vencedor, um `active`, anterior correta, 0 capturas vazias, 0 erros). |
| R1-06 teto absoluto de US$5 ausente (P1) | **Corrigido** | `Settings(budget_limit_usd=6)` e `BUDGET_LIMIT_USD=7` → `ValidationError`; `BudgetGuard` com 6,0, `nan`, `inf`, negativo, ou `model_copy` forçando 9,0 → `ValueError`; reserva de 5,01 com limite 5,0 → `BudgetExceeded`. `FixedBudgetGuard` rejeita 0, 0,2500001, 0,26, 5,0, `nan`, `inf`; o valor fixado não muda por remontagem (0,25/0,2/0,1 contra 0,15 e outro `cap_id` recusados). O teto persistente em `<ledger>.limit` impede subir o limite por remontagem (ver R2-01, R2-02, R2-06 para as arestas desse mecanismo). |

### Limites da verificação de integridade (R1-03)

`_verify_integrity` confere existência, contagem > 0, modelo, dimensão e, quando o manifesto os tem, contagem e digest dos `chunk_id`. O `chunk_id` embute o hash do corpo do trecho, então trocar conteúdo por outro `chunk_id` é detectado. **Não detecta** vetores substituídos por outros da mesma dimensão com os mesmos ids, nem `payload.text` alterado mantendo o `chunk_id` (reproduzi os dois: a ativação passa). Isso exige escrita direta no Qdrant e é coerente com o critério "contagem, dimensão/modelo e pontos/digest"; registro como limite aceito, não como defeito.

### Compatibilidade com registros da r1 (versões sem digest)

Manifestos sem `chunks`/`point_digest` continuam ativáveis e permitem retorno quando a coleção está saudável (testado com `kb_initial` reduzido a `collection/embedding_model/dim/source`); coleção vazia é recusada mesmo sem digest. Um manifesto sem a chave `dim` **e** sem `dimension` é recusado (conservador). Não encontrei nenhum registro r1 persistente: o ambiente sintético r1 do Supervisor usava runtime em tmpfs. Sem impacto conhecido.

## Achados novos

Nenhum P1/P2. Todos os itens abaixo são P3 (não bloqueiam aptidão) ou decisão humana.

### R2-01 — Teto persistente gravado com 12 dígitos recusa a própria montagem (P3)

**Condição e impacto:** o arquivo `<ledger>.limit` é gravado com `f"{ceiling:.12g}"`. Um `limit_usd` cujo `float` tem mais de 12 dígitos significativos (por exemplo `1/3` ou `0.1+0.2`) é gravado truncado (`0.333333333333`, `0.3`) e, na leitura imediata, `limit_usd > ceiling` é verdadeiro: a **primeira** montagem falha com "Configured budget limit exceeds the persistent ceiling" e deixa o arquivo truncado, de modo que toda montagem seguinte com o mesmo valor também falha. Valores usuais (1.00, 0.5, 2.5, 0.25) não são afetados; o impacto é de robustez da configuração, sem efeito financeiro.

**Localização:** [budget.py](../../src/merchant_assistant/orchestration/budget.py:57), [budget.py](../../src/merchant_assistant/orchestration/budget.py:62).

**Reprodução:** `BudgetGuard(tmp/"x.sqlite3", 1/3)` → `ValueError`; `Path("x.sqlite3.limit").read_text()` → `0.333333333333`.

**Correção esperada:** gravar com `repr(float)`/`.17g` (round-trip exato) ou comparar com tolerância ≥ 1e-9.

### R2-02 — Criação do arquivo de teto não é atômica (P3)

**Condição e impacto:** `os.open(O_CREAT|O_EXCL)` cria o arquivo vazio e só depois o conteúdo é escrito. Outro processo/thread que montar nessa janela vê o arquivo existente e vazio e falha com "Persistent budget ceiling is missing or invalid". Com 8 threads montando juntas um ledger novo, 46–52 de 300 tentativas tiveram ao menos uma falha (106 falhas no total na execução que registrou as mensagens); uma montagem sequencial posterior sempre funcionou. Um processo interrompido entre `open` e `write` deixaria o arquivo vazio e todas as montagens falhariam até remoção manual. No fluxo previsto (bootstrap e API em sequência, um worker) a janela é improvável; vira relevante se o QA montar o ledger por mais de um processo ao mesmo tempo.

**Localização:** [budget.py](../../src/merchant_assistant/orchestration/budget.py:52).

**Reprodução:** mesma de R2-01, com threads sincronizadas por `Barrier` em caminhos novos.

**Correção esperada:** escrever em arquivo temporário no mesmo diretório e publicar com `os.link`/`os.replace` (ou tentar reler algumas vezes quando o conteúdo estiver vazio).

### R2-03 — `readiness()` escreve no banco e toma o lock de escrita a cada chamada (P3)

**Condição e impacto:** `readiness()` chama `capture_active()`, que chama `bootstrap()`: abre `connect()` (que também aplica migrações pendentes) e executa `BEGIN IMMEDIATE`. Num banco ainda sem registro KB, a **primeira** chamada de `/ready` (rota sem autenticação) grava 40 documentos, a versão `kb_initial` e um evento; depois é idempotente (conferi 40/1/1 linhas após 4 chamadas e após 2 `bootstrap()` extras), mas cada chamada continua tomando o lock de escrita. Não há chamada paga nem alteração de conteúdo publicado; o efeito é um sondeio de saúde com escrita e contenção com ativações.

**Localização:** [graph.py](../../src/merchant_assistant/orchestration/graph.py:362), [kb.py](../../src/merchant_assistant/rag/kb.py:57), [kb.py](../../src/merchant_assistant/rag/kb.py:547).

**Reprodução:** `Settings` temporário + `offline_orchestrator`; contar linhas de `kb_documents/kb_versions/kb_events` antes e depois de `readiness()`: (0,0,0) → (40,1,1).

**Correção esperada:** caminho somente leitura para readiness/captura quando o registro já existe (consultar sem `BEGIN IMMEDIATE`), reservando a escrita para a primeira inicialização.

### R2-04 — I/O de Qdrant dentro da transação de escrita do SQLite (P3)

**Condição e impacto:** `transition()` executa `_verify_integrity` (get_collection, scroll e count no Qdrant) dentro de `BEGIN IMMEDIATE`; `bootstrap()` faz `inspect()` e `create_version` faz `exists()` também sob o lock. Como cada mensagem de atendimento e cada `/ready` passam por `capture_active()` → `BEGIN IMMEDIATE`, um Qdrant lento durante ativação/retorno (timeout do cliente 10 s) pode superar o `busy_timeout` de 5 s da conexão e fazer o atendimento falhar com "database is locked" enquanto a transição dura. Com Qdrant em memória/local e 145 pontos não é perceptível (stress sem erro); o risco aparece com Qdrant remoto degradado.

**Localização:** [kb.py](../../src/merchant_assistant/rag/kb.py:523), [kb.py](../../src/merchant_assistant/rag/kb.py:89), [kb.py](../../src/merchant_assistant/rag/kb.py:327).

**Reprodução:** não reproduzida com Qdrant real (sem rede); derivada da leitura do código e dos timeouts.

**Correção esperada / mitigação:** verificar integridade antes do `BEGIN IMMEDIATE` e repetir só a conferência barata do estado dentro dela, ou aceitar o risco e observá-lo no QA (latência de `/ready` e mensagens durante ativação).

### R2-05 — Cliente OpenAI do CLI sem timeout explícito (P3)

**Condição e impacto:** `_openai_client` cria `OpenAI(api_key=…, max_retries=0)` sem `timeout`; o padrão do SDK é leitura de 600 s. Um provedor pendurado durante `index`/`bootstrap` (inclusive o `bootstrap` do `entrypoint.sh`) segura o comando por até 10 min por lote. Não há efeito financeiro adicional (a reserva já foi feita e fica conservada), apenas disponibilidade do arranque.

**Localização:** [cli.py](../../src/merchant_assistant/cli.py:18) (compare com [main.py](../../src/merchant_assistant/main.py:27), `timeout=30`).

**Correção esperada:** passar `timeout=30` (ou configurável) como no runtime.

### R2-06 — Decisão humana: novo arquivo persistente `<ledger>.limit` ao lado do ledger (decisão, não defeito)

**Condição:** o teto persistente foi implementado como arquivo `budget.sqlite3.limit` criado na primeira montagem. Comportamento verificado por mim com ledgers sintéticos:

- Ledger preexistente sem o arquivo: o teto vira `min(limite_configurado, 1.0)`; os bytes do SQLite não mudam (SHA-256 idêntico antes/depois da montagem) e o gasto lido (0,34) é preservado. Limite 5,0 sobre esse ledger é recusado; 1,0 é aceito.
- Primeira montagem **mais estrita** trava o teto nesse valor: legado montado com 0,25 → teto 0,25; montar depois com 1,0 é recusado no arranque. Apagar o arquivo devolve `min(limite, 1.0)` — nunca acima de 1,0 para ledger existente; subir acima disso exige editar o arquivo à mão (máximo 5).
- Ledger apagado com o arquivo mantido: novo ledger vazio, mesmo teto; não zera nem sobe o teto sozinho.
- Conteúdo inválido (`nan`, `inf`, negativo, 6, vazio, texto) é recusado.
- Não pode alterar, zerar ou apagar o ledger; só leitura/validação do limite montado, e nunca baixa um teto já gravado.

**Impacto:** a primeira montagem do ledger real (QA ou serviço) cria um arquivo novo em `data/runtime/`, e um valor mais estrito usado por engano nessa primeira montagem prende o teto até intervenção manual. O mecanismo está documentado em `README.md` e `.env.example` e atende "não aumentar o limite por remontagem", mas é um controle de segurança/orçamento persistente novo, não descrito no plano/ADR aprovados. Pelo AGENTS.md ("alterações em políticas de segurança", "configurações persistentes") o responsável deveria aceitá-lo explicitamente.

**Ação:** Supervisor apresentar ao responsável e registrar a decisão antes de o QA montar o ledger real; QA deve montar o ledger real exatamente uma vez com `BUDGET_LIMIT_USD=1.00` (o nativo) e conferir o conteúdo do arquivo gerado.

### R2-07 — Resíduo: `BudgetGuard.record`/`record_embedding` gravam gasto sem reserva (P3, limpeza)

**Condição e impacto:** depois da migração para reserva por lote, nenhum chamador em `src/` usa `BudgetGuard.record` nem `record_embedding`, mas ambos continuam públicos e gravam entrada `settled` sem reserva nem verificação de limite. Não há caminho ativo que os use; é um atalho que contraria "toda tentativa paga com reserva prévia" se for reutilizado no futuro.

**Localização:** [budget.py](../../src/merchant_assistant/orchestration/budget.py:150), [budget.py](../../src/merchant_assistant/orchestration/budget.py:164); o teste de valores inválidos ainda exercita `record` ([test_budget_and_router.py](../../tests/unit/test_budget_and_router.py:144)).

**Correção esperada:** remover os dois métodos (e o teste associado) ou documentá-los como uso interno.

### R2-08 — Duas lacunas de teste: "sem retry de SDK" e coleção vazia com manifesto sem contagem (P3)

**Condição e impacto:** (a) nenhum teste afirma `max_retries == 0` nos clientes reais (`main.openai_client`, cliente DeepSeek, `cli._openai_client`); os testes usam um transporte falso no lugar do SDK, então restaurar `max_retries=1` (mutação M16) não é detectado, embora "sem retry opaco" seja critério da tarefa. (b) a condição `facts["points"] > 0` de `_verify_integrity` só é exercida quando o manifesto tem `chunks`; um registro sem contagem (como o `kb_initial` legado) com coleção vazia não tem teste (M11). Conferi manualmente que o código atual **recusa** esse caso (retorno para `kb_initial` legado com coleção vazia → "Collection integrity could not be confirmed"); falta apenas a regressão.

**Localização:** [main.py](../../src/merchant_assistant/main.py:27), [main.py](../../src/merchant_assistant/main.py:66), [cli.py](../../src/merchant_assistant/cli.py:18), [kb.py](../../src/merchant_assistant/rag/kb.py:409).

**Correção esperada:** um teste de uma linha por cliente (`client.max_retries == 0`, sem rede) e um caso de retorno/ativação com manifesto sem `chunks`/`point_digest` e coleção vazia.

## Regressões e riscos avaliados nos arquivos alterados

- **Contrato público:** OpenAPI gerado em memória com `create_app(offline_orchestrator, Settings(demo_mode=True))` é igual (comparação semântica, chaves ordenadas) a `C:\workspace\ai-getnet-case-web\openapi-v1.json`: 25 rotas e 23 schemas. Sem `demo_mode` faltam apenas `/conversations/{id}` e `/traces/{id}`, como na v0.4. `api/v1.py` não mudou desde o r1; rotas, papéis (`ADMIN`/`AUTH`) e mapeamento de erros seguem iguais.
- **Permissões:** nenhuma rota nova nem alteração de autorização no delta r2; a suíte estrita cobre admin/demo/sessão.
- **Bootstrap e `docker/entrypoint.sh`:** o entrypoint (`set -e`, `merchant-assistant bootstrap`, depois uvicorn) não usa `--force-index`. Execução própria com Qdrant em memória e transporte falso: 1ª execução cria 145 pontos (3 chamadas, 3 reservas liquidadas); 2ª execução não chama provedor e deixa ledger, coleção e manifesto idênticos; `--force-index` recusa sem alterar nada. O arquivo de teto nasce com `1`. Mudança de comportamento: `bootstrap --force-index` deixou de reconstruir (agora recusa) — coerente com R1-02 e o README.
- **Compatibilidade de dados:** ver seção de registros r1. Contas e ledger legados não são reescritos.
- **Limite nativo US$1:** preservado; ver R2-06.
- **Teto US$5 / cap ≤ US$0,25 / reserva prévia / liquidação única:** conferidos acima. O cap fixo vale **por arquivo de ledger de campanha** (`cap_id` dentro desse SQLite) e o teto de US$5 vale **por ledger**; um runtime novo sem `budget=` injetado cria ledger novo com o limite das settings. O QA deve injetar `CombinedBudgetGuard(primário real, campanha)` e reutilizar o mesmo caminho de campanha em todas as tentativas. `max_retries` passou de 1 para 0 em `main.py`: falhas transitórias do provedor passam a aparecer como erro (intencional), o que pode afetar a estabilidade percebida no QA.
- **Concorrência:** ativação × teste × captura e ativação × ativação × retorno validadas (acima); liquidação concorrente simples e composta coberta pelos testes e por execução própria.

## Qualidade dos testes (mutação em cópia)

Para verificar que os testes novos/ampliados realmente exercitam os cenários, copiei `src/`, `tests/`, `prompts/` e os dados públicos (sem `data/runtime`) para o scratchpad, apliquei uma regressão de cada correção e rodei os quatro arquivos de teste focados contra a cópia mutada (PYTHONPATH apontando para a cópia; confirmei que o módulo importado era o mutado).

Resultado: 16 mutações, **13 detectadas** pelos testes e **3 sobreviventes**; a linha de base sem mutação passou (87 testes nos quatro arquivos).

| Mutação (regressão aplicada na cópia) | Resultado |
| --- | --- |
| M1 R1-04: `settle` com `UPDATE` incondicional | detectada (`test_cancelled_reservation…`, `test_combined_guard_*` e outros) |
| M2 R1-06: remover o teto de US$5 do construtor de `BudgetGuard` | **sobrevive — mutante equivalente** em ledger de arquivo: a conferência do teto persistente (`0 ≤ teto ≤ 5`) recusa o mesmo valor (defesa em profundidade); o caminho `:memory:` não é utilizável pela guarda |
| M3 R1-06: `Settings` sem `le=5` | detectada |
| M4 R1-06: teto persistente não aplicado (`limit_usd > ceiling`) | detectada (2 testes) |
| M5 R1-01: `cmd_index` sem guarda | detectada (3 testes) |
| M6 R1-01: embedder pago chega ao provedor sem guarda | detectada |
| M7 R1-02: `rebuild` substitui por padrão | detectada |
| M8 R1-02: `index` do CLI substitui coleção existente | detectada (2 testes) |
| M9 R1-02: `bootstrap --force-index` reconstrói | detectada (3 testes) |
| M10 R1-03: `transition` sem verificação de integridade | detectada (3 testes) |
| M11 R1-03: integridade sem a condição `points > 0` | **sobrevive** — ver R2-08 |
| M12 R1-03: digest não comparado | detectada (2 testes) |
| M13 R1-05: `test_version` aceita versões publicadas | detectada (3 testes) |
| M14 R1-05: escrita do teste sem condição de estado (corrida) | detectada |
| M15 R1-03: `readiness()` usa o índice de partida | detectada |
| M16 SDK: `max_retries=1` restaurado em `main.openai_client` | **sobrevive** — ver R2-08 |

Os testes usam transporte falso no nível do cliente SDK com `OpenAIEmbedder` e `BudgetGuard` reais, ledgers SQLite temporários e Qdrant em memória, e verificam o estado do ledger no instante de cada despacho — não são mocks que tornem o teste trivial.

## Evidência executada

- Validação estrita do backend: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="--basetemp C:/workspace/ai-getnet-case/.pytest_cache/v050-review-r2-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → **293 passed** em 265,88 s, Ruff "All checks passed!", "Estrutura básica válida.", "Skills válidas." e "Validação estrita concluída sem falhas." (exit 0).
- Web (somente regressão, sem alterar): `C:/workspace/ai-getnet-case-web/.venv-v040/Scripts/python.exe -m pytest --basetemp C:/workspace/ai-getnet-case/.pytest_cache/v050-review-r2-web` → **15 passed**.
- Reproduções próprias (scratchpad `review-r2/`): `repro_cli.py` (R1-01/R1-02), `repro_kb.py` e `repro_race2.py` (R1-03/R1-05/compatibilidade/readiness/concorrência), `repro_budget.py` e `repro_race_msg.py` (R1-04/R1-06/arquivo de teto), `repro_boot.py` (idempotência do bootstrap), `repro_legacy_empty.py` (registro legado com coleção vazia), `repro_openapi.py` (contrato), `mutate.py` (testes). Todas com SQLite temporário, Qdrant `:memory:` e transporte falso.
- Nenhuma chamada paga, de rede a provedores ou leitura de `.env`.

## Critérios e limites

**Comprovados por mim nesta revisão:** os seis achados r1 corrigidos na causa e sem caminho alternativo encontrado (todos os chamadores de `build_embedder`/`OpenAIEmbedder`, `KnowledgeIndex.rebuild`, `settle`/`cancel`/`record`, criação de `BudgetGuard`/guards compostos e `Settings`); contrato OpenAPI inalterado; bootstrap idempotente; fingerprints do candidato; regressão backend e web.

**Não comprovados (ficam para o QA):** comportamento e custo reais dos provedores; latência do build/teste síncronos contra o timeout HTTP de 20 s do cliente web (risco já registrado no r1: confirmar no QA que a UI recupera o resultado sem repetir gasto e que o build não conclui no backend depois de o navegador desistir); Qdrant remoto sob degradação (R2-04); CA-41 completo pela interface contra o runtime v0.5; montagem do ledger real com o teto persistente (R2-06); decisão de release.

**Riscos para o QA:** (1) montar o ledger real uma única vez com o limite nativo e inspecionar `budget.sqlite3.limit`; (2) injetar o guard composto e fixar o cap de US$0,25 uma só vez, no mesmo caminho; (3) esperar que falhas transitórias do provedor não sejam repetidas (sem retry); (4) observar `/ready` e mensagens durante ativação (R2-03/R2-04); (5) o primeiro `/ready` num banco novo escreve o registro KB.

Sem ações externas: nenhum commit, push, integração, publicação ou contato com terceiros.

## Passagem de papel

- Papel e responsável: Reviewer independente (Sonnet 5.5), despachado pelo Supervisor.
- Objetivo e critérios: confirmar R1-01..R1-06 no candidato `v0.5.0-local-r2` e procurar regressões, conforme tarefa 45 e plano aprovado.
- Escopo: `C:\workspace\ai-getnet-case` e `C:\workspace\ai-getnet-case-web` (somente leitura e execução de testes).
- Estado: **apto para QA** (sem P1/P2); decisão humana pendente R2-06.
- Branch e PR: `codex/v0.5.0-base-versionada` nos dois repositórios; sem PR.
- Base e versão final: SHAs de HEAD acima; bytes do candidato identificados pelos mapas do manifesto, iguais antes e depois (ver fim do documento).
- Independência: independente, com a exposição incidental declarada no início.
- Evidência: seção "Evidência executada".
- Critérios comprovados e não verificados: seção "Critérios e limites".
- Achados e limitações: R2-01 a R2-08; limite de integridade descrito.
- Ação externa autorizada: nenhuma realizada.
- Próxima ação e responsável: Supervisor decide R2-06 e escolhe entre corrigir os P3 baratos (R2-01/02/05/07) antes do QA ou aceitá-los; depois despacha o QA com o candidato r2 (ou r3, se houver correção).
- Decisão humana pendente: aceitar o arquivo persistente `<ledger>.limit` como mecanismo do teto (R2-06); necessária porque o QA o criará ao lado do ledger real.

## Verificação final de integridade (depois das verificações)

Recalculados em 2026-10-27 18:01 UTC, depois da validação estrita, do teste web, das reproduções e das mutações: fonte backend 38/38, fonte web 84/84, runtime 128/128 e entradas de build 129/129 iguais ao manifesto; fingerprints idênticos aos da medição "antes" e ao manifesto (fonte `22b0c92d…86b0`, runtime `22556665…e0e`, build `c74764b0…3a5`). HEADs inalterados (`ea2355b…` backend, `40ff199…` web); o web continua com as mesmas sete modificações de working tree do candidato. Nenhum arquivo de produto, teste, contrato ou configuração foi alterado por esta revisão; ainda não existe `budget.sqlite3.limit` ao lado do ledger real.
