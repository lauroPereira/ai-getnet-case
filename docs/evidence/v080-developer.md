# Passagens do Developer — v0.8.0

Registros do Time A, seguidos dos registros do Time B.

## Tarefa 68b

- **Papel e responsável:** Developer (Time A), subagente despachado pelo Supervisor.
- **Objetivo e critérios:** [tarefa 68b](../tasks/68b-ticket-id-no-caso.md): depois do primeiro evento aceito do ticketing, `GET /v1/handoffs` e `GET /v1/handoffs/{id}` mostram o `ticket_id` (observação O-8 do QA da v0.7.0).
- **Escopo:** `tests/integration/test_v080_ticket_id.py` (novo), seções Validação e Status da tarefa e esta passagem. Nenhum arquivo de `src/` mudou.
- **Estado:** defeito **não reproduzido**; teste de regressão entregue; aguarda revisão.
- **Branch e base:** `codex/v0.8.0-replan`, base `5134eff`. Identidade conferida antes do commit: `lauroPereira <lauro.s.pereira@gmail.com>`.
- **Independência:** não se aplica (implementação).

### Evidência

- Em processo, com o ticketing real (`AppTransport`): o teste da v0.7.0 `test_case_becomes_a_ticket_worked_on_the_ticketing_and_closed` já exige o `ticket_id` no detalhe depois de `ticket.assigned` e passa na base.
- Com soquetes reais (roteiro exploratório fora do repositório: assistente, ticketing e receptor em três servidores uvicorn em threads, loopback): `POST /tickets/{id}/assign` → `delivered`, `accepted`; `GET /v1/handoffs` → `claimed`, `op_ana`, `ticket_id` igual ao ticket.
- Cópia somente leitura do banco do QA da v0.7.0 (`.pytest_cache/v070-qa-real-runtime/merchant.sqlite3`, copiado para fora do repositório; o diretório original não foi tocado): 5 casos; os 4 que tiveram `ticket.assigned` aceito em `webhook_inbox` têm `ticket_id` (o do momento 9 da história, `hc_154e13748dc742da`, é `tkt_c6d9b62237d4`, o mesmo ticket citado no QA); o único `null`, `hc_bd1b4d4e05924eb9`, não tem evento do ticketing e foi trabalhado direto por `operator:op_ana` (CLI, caso E da O-4). A única amostra com `ticket_id: null` no relato do QA (momento 6) é de antes de qualquer evento.
- Teste novo: 5 passam (`.pytest_cache/t68b-dev-20261104e`). Na cópia da base fora do repositório com o `UPDATE handoff_cases SET ticket_id` removido, os 5 falham. Ruff: `All checks passed`.
- Nenhuma chamada paga, nenhuma rede além de loopback; não li `.env`.

### Decisões tomadas além do texto

1. **Não alterei código de produção.** Sem defeito reproduzível, mudar `integrations.py` seria inventar uma correção. O critério "teste que falhava antes da correção" não se aplica; no lugar dele, a mutação acima prova que o teste detecta a ausência da gravação.
2. **Os testes cobrem os três tipos de primeiro evento** (`assigned`, `action`, `solved`), o ciclo inteiro (o primeiro ticket vence) e as recusas (`unknown_operator`, payload inválido, `claimed_by_other`), que a tarefa pedia.

### Achados e limitações

- **Sugestão ao Supervisor (não implementada):** entre `handoff.created` e o primeiro evento do operador o caso fica com `ticket_id` nulo, embora a resposta do ticketing a `handoff.created` traga o `ticket_id` (`{"status": "received", "ticket_id": ...}`). Quem lê a fila na Recepção vê `null` e pode ter entendido isso como o defeito. Gravar na criação muda o comportamento definido na 66 ("do primeiro evento aceito") e tocaria `api/webhooks.py`; deixo para decisão.
- O QA pode confirmar a leitura repetindo o roteiro do momento 9 e lendo a fila depois do `Assumir`.

### Próxima ação

Supervisor: aceitar o fechamento sem correção (ou pedir a gravação na criação) e revisar o teste.

## Tarefa 69

- **Papel e responsável:** Developer (Time A), subagente despachado pelo Supervisor.
- **Objetivo e critérios:** [tarefa 69](../tasks/69-replanejamento.md): nó `replan` depois de `knowledge` e de `support` (e do novo `web`), regras determinísticas e `replan.v1` só na ambiguidade, orçamento de saltos, passo de trace, quatro cenários do RF-88, ADR 0019 proposta. Spec v0.8.0 D1 a D8, D16, D18.
- **Branch e base:** `codex/v0.8.0-replan`, base `5134eff`. Commits: `c1dd2d5` (68b), `686d545` (código), `1ba296f` (testes, cenários, catálogo); ADR, tarefa e esta passagem no commit seguinte. Identidade conferida antes de cada commit: `lauroPereira <lauro.s.pereira@gmail.com>`. Sem push, sem troca de branch.
- **Independência:** não se aplica (implementação).

### Arquivos

- Novos: `src/merchant_assistant/agents/replanner.py` (observação, 10 regras nomeadas, chamada ao modelo, guardas, nó), `prompts/replan.v1.md`, `docs/architecture/decisions/0019-replanejamento.md` (Proposta), `tests/scenarios/replan.jsonl`, `tests/unit/test_replanner_rules.py` (31), `tests/integration/test_v080_replan.py` (28).
- Alterados: `orchestration/graph.py` (nós `web` e `replan`, aresta única `knowledge|web|support → replan`, `_after_replan`; `_after_knowledge` e `_after_support` saíram; `_traced` ganhou `mark`, que registra `plan.ran`/`plan.last`; `plan_hops` no detalhe da requisição), `orchestration/state.py` (`ReplanDecision`, `GraphState.plan: dict`), `agents/knowledge.py` (`run_web`, `_with_web`), `agents/support.py` (resumo de prefixo vazio vira "nada checado"), `agents/personality.py` (`unconfirmed` quando há lacuna declarada), `config.py` (`max_plan_hops=3`, acréscimo no fim do bloco de limites), `.env.example` (`MAX_PLAN_HOPS=3`, acréscimo no bloco de gasto), `evaluation/scripted_policy.py` (`replan` programado; web programada), `api/v1.py` (campos do passo `replan` em `GET /v1/runs/{id}`), `data/scenarios/catalog.json` (+4), `tests/integration/test_v060_api.py` (10 → 14 cenários), tarefa 69.
- Intocados: `escalation.py`, `build_review_graph`, `human_review`, `data/migrations.py` (schema continua 10), `evaluation/runner.py`, `prompts/judge*`, `test_v070_story.py` e demais testes da trava.

### Evidência

- Pytest, um por vez, basetemp novo: novos e afetados **164 passed**; trava da v0.7.0 (story, webhooks, resume, resume_r2, ticketing_integration, closing) **94 passed** sem alterar nenhum desses arquivos; `tests/unit` **278 passed**; os 14 demais arquivos de `tests/integration` **199 passed**. Ruff em `src tests`: ok. Não rodei `lint_and_tests.py --strict`.
- Regressão programada: 40 casos + `followup.jsonl` na `main` (`git archive`, `bee6ab5`) e na branch, sem `.env`: 25/40 e 4/4 nas duas; **idênticos campo a campo**, inclusive `agents`, resposta, fontes, ferramentas e total de chamadas (123 = 123), depois de normalizar o sufixo aleatório do protocolo `HO-`. Nada a justificar.
- Quatro cenários do RF-88 (programados, 11 checagens do runner cada): caminhos `router → knowledge → web → personality`, `router → customer_support → knowledge → personality`, `router → customer_support → escalation → personality` (serviço de preços injetado fora do ar), `router → knowledge → customer_support → personality`; todos por regra, 0 chamadas a `replan`.
- Modelo só na ambiguidade: 40 casos com 0 chamadas; o caso "produto fora das páginas e que depende do meu plano" faz 2 chamadas (duas regras discordam; depois nenhuma se aplica), esforço `none`, ≤ 80 tokens.
- Mutações numa cópia fora do repositório: 9 de 9 mortas pelos testes novos (repetição, orçamento, `plan_pending`, modelo sempre, limites da requisição, `escalate` livre, `complete` sem olhar o Support, lacuna não declarada, web com o índice fora).
- Nenhuma chamada paga, nenhuma rede, `.env` não lido, sem Docker. Cópias e scripts em scratchpad, fora do repositório.

### Decisões tomadas além do texto do plano (todas reversíveis)

1. **O que é salto (D6):** decisão que sai do plano do Router (especialista que a rota não previa, ou `escalate`). Seguir o plano (`plan_pending`, por exemplo `support` depois do `knowledge` de `knowledge_and_support`) não conta nem é barrado: contar bloquearia o plano do próprio Router com orçamento baixo. `escalate` e `clarify` encerram o fluxo e passam mesmo no limite; o máximo alcançável com o padrão é 3 (`knowledge → web → support → escalate`). Com `MAX_PLAN_HOPS=0` nenhum especialista extra roda.
2. **`evidence_sufficient=True` encerra por regra** mesmo que o Knowledge liste `missing` (a Personality já diz o que não confirmou), para não colocar uma chamada de modelo em toda resposta real com `missing` preenchido. A dependência da conta é a exceção: marcadores na mensagem ("meu plano", "my rates"...) ou na lacuna declarada ("merchant's contracted plan"). "Como faço" idem. Marcadores só em português e inglês; falso positivo custa um especialista a mais, falso negativo mantém o comportamento da v0.7.0.
3. **Índice fora (`knowledge_unavailable`) não aciona a web:** a web daria fonte não oficial a uma falha de infraestrutura; encerra com a lacuna declarada, como na v0.7.0. A web também não é tentada quando o Knowledge rodou em modo procedimento.
4. **Support por replanejamento roda sem o prefixo de abertura** (histórico e healthcheck): sem 2 chamadas de ferramenta a mais; o resumo vazio vira "nada checado".
5. **`web` junta ao resultado do Knowledge** (pontos, fontes e evidências); busca que falha deixa o resultado anterior e acrescenta o motivo.
6. **`plan` é um dicionário em `GraphState`** (`ran`, `last`, `hops`, `next`, `gap`) para não registrar tipo novo nos checkpoints; `ran` e `last` são gravados pelo `_traced` (também quando o nó falha), o que impede laço por nó que explode.
7. **A lacuna chega à Personality como `unconfirmed`** nas contribuições, sem prompt novo (o `personality.v4` já manda dizer o que não foi confirmado). Para a qualidade com modelo real, é o ponto que a campanha precisa olhar.
8. **Agente `replan` fora de `profiles.AGENTS`:** usa o modelo padrão do orquestrador (`ctx.llm_for("replan")`); perfis de comparação não o configuram nesta versão.
9. **Catálogo:** versão continua "1" (o teste da v0.6.0 espera "1"); os `SC-REPLAN-*` têm `source_case: null` (o teste de fechamento da v0.7.0 só confere os que citam caso das três listas) e o de falha de ferramenta ganhou `precondition`. `replan.jsonl` usa só os campos de `Case`, então o `REPLAN-TOOL-DOWN` só vira escalada com o serviço de preços fora do ar (no QA, parar o `mocks`; nos testes, `faults`); sem isso a pergunta é respondida normalmente.
10. **Web programada:** o texto de câmbio continua para tudo, menos a mensagem com "get xyz" (gatilho de evidência insuficiente que já existia), que ganha uma página de terceiros; foi o que permitiu o cenário `REPLAN-WEB` sem alterar os 40 casos.
11. **`GET /v1/runs/{id}`:** os campos `next`, `reason`, `review`, `hops`, `origin` e `observed` aparecem só no passo `replan`; os demais passos não mudam.
12. **O teste `test_v060_api` (10 → 14)** é a única mudança em teste existente.

### Para o Time B (D16)

- `agents` traz o caminho executado na ordem real. Rótulos: `router`, `knowledge`, `web` (busca web escolhida pelo replanejamento), `customer_support`, `escalation`, `personality`. `replan` **não** entra em `agents` (só no trace, para as respostas simples seguirem com a mesma lista). Na rota `general_web` a busca web continua aparecendo como `knowledge`, como antes. Sem `router` e `personality`, o `executed_path` sai direto: `knowledge → web`, `customer_support → knowledge`, `knowledge → customer_support`, `customer_support → escalation`.
- **Não gravei `detail.evidence`** em nenhum passo do Knowledge. O passo `replan` guarda o resumo em `observed` (por exemplo `evidence_sufficient`, `knowledge_gap`), e o detalhe da requisição ganhou `plan_hops`. O passo `personality` já tinha `evidence` desde a v0.7.0, mas é a evidência do estado do caso (`resolved`, `tool_verified`...), não a do Knowledge.
- `route` da resposta continua sendo o plano inicial; `route_ok` não muda.
- Schema segue 10; `test_v070_story.py` não foi tocado (a linha `== 10` fica como está nesta branch).

### Achados e limitações

- Nada foi exercitado com modelo real: se o `knowledge_rag` preenche `missing` e se o Router manda o cenário de procedimento para `knowledge_and_support` (nesse caso o replanejamento não roda; o rótulo aceita as duas rotas) são perguntas da campanha `v080-qa`, junto com a taxa de `origin=model` e o texto da lacuna declarada.
- Pergunta de produto sem evidência passa a ir à web (D4); a resposta mostra a fonte web. Para produtos que não existem na web, o resultado real será a lacuna declarada, não uma busca vazia, desde que o modelo da busca diga que não achou.
- O processo `lint_and_tests.py --strict` que apareceu na máquina às 02:59 é do Supervisor, no mesmo checkout; depois dele só entram commits de documentação desta passagem.

### Próxima ação

Supervisor: revisar (Reviewer independente) as duas tarefas e rodar a suíte estrita; QA real depois do merge com o Time B (migração 0011 e a linha do `test_v070_story.py` se resolvem na integração).

## Tarefa 69, rodada 2

- **Papel e responsável:** Developer (Time A), mesma tarefa, correção pedida pela revisão independente ([v080-reviewer-t69.md](v080-reviewer-t69.md), candidato `e1cbffb`, parecer em `046a30d`).
- **Branch e base:** `codex/v0.8.0-replan`, base da rodada `046a30d`. Commit da rodada: o que contém esta seção (o SHA vai no retorno ao Supervisor). Identidade conferida antes do commit: `lauroPereira <lauro.s.pereira@gmail.com>`.
- **Achados atendidos:** P2-1 (obrigatório), P3-1 e P3-2 (parcial, com o motivo abaixo). P3-8 e os demais P3 ficam como registrados, sem mudança.

### P2-1: `knowledge` na rota `general_web` era um apelido da busca web

- **Causa:** nessa rota o nó `knowledge` é a busca web e grava `ran = "web"`; `allowed_next` e `_guard` só olhavam `ran`, então o modelo podia pedir `knowledge` de novo, o que refazia a busca e sobrescrevia o resultado.
- **Correção (`agents/replanner.py`):** `Observed.done` = `ran` mais `knowledge` quando a rota é `general_web` (ali o nó não tem outro modo). `allowed_next` e `_guard` passam a usar `done`: pedir `knowledge` ou `web` nessa rota vira `finish` com `rule:no_repeat`. As regras não são afetadas (nenhuma regra escolhe `knowledge` nessa rota, e `ran` continua verdadeiro no trace). Nenhuma mudança em `graph.py`: separar o nó mudaria o rótulo `knowledge` em `agents` e o nome do passo, que os testes da v0.6.0 fixam.
- **Outro apelido com o mesmo efeito?** Revisto: `support` e `web` têm um rótulo cada; `knowledge` mapeia para `web` só em `general_web`; nas demais rotas o modo do nó (rag ou procedimento) vem da rota e o rótulo é `knowledge`. `escalate`, `clarify` e `finish` encerram o fluxo. Não há outro.
- **Prova:** enumeração exaustiva das escolhas do planejador (regras desligadas, todas as decisões do modelo, `knowledge`/`web`/`support`/`escalate`/`clarify`/`finish` em cada decisão) no grafo real, quatro rotas (script fora do repositório). Antes (`046a30d`): `general_web` 37 execuções, 26 com especialista repetido e até 3 buscas web. Depois: `knowledge` 31 execuções, `general_web` 13, `support` 31, `knowledge_and_support` 31; **nenhuma repete especialista, no máximo 1 busca web, no máximo 3 saltos (2 na `general_web`)**. Testes novos: `test_on_the_general_web_route_the_search_runs_once_whatever_the_planner_asks` (4 roteiros, inclusive um planejador que só pede `knowledge`; 1 busca, `plan_hops` ≤ 3) e `test_on_the_general_web_route_knowledge_is_the_web_search_and_cannot_run_again` (unitário). Sem a correção os dois falham numa cópia fora do repositório.
- **ADR 0019:** o máximo de saltos que ela cita (3) continua valendo; acrescentei o apelido da `general_web`, a enumeração e a lacuna do modelo (P3-1).

### P3-1: `finish` do modelo com `review=incomplete`

`_ask_model` grava a `reason` como lacuna (`plan.gap` → `unconfirmed`), como as regras. Testes: `test_a_finish_the_model_calls_incomplete_declares_its_reason_as_the_gap` e o par `..._complete_declares_no_gap`. Mutante que remove a gravação morre no teste.

### P3-2: rótulos (catálogo e `replan.jsonl` iguais; teste de acordo mantido)

- **`REPLAN-PROCEDURE`:** ganhou o grupo `["app", "aplicativo"]` (o mesmo marcador do caso PT06 de antecipação, que o Knowledge dá pelas páginas oficiais); o Support sozinho não o satisfaz. O teste novo `test_the_labels_need_what_each_replanned_step_brings` mostra a resposta só com os valores da conta reprovando `content_ok`.
- **`REPLAN-TOOL-DOWN`:** ganhou `expected_tools: ["simulate_pricing"]` (a escalada vem depois de uma consulta que falhou; um pedido de atendente ou uma escalada sem tentativa passa a reprovar `tools_ok`). **Distinguir a escalada do replanejamento da escalada que o Support já faz sozinho não é possível pelos rótulos:** as duas dão `status=handoff`, protocolo `HO-` e a mesma `reason` (`tool_error:UNAVAILABLE`), e os rótulos não enxergam o trace; só o passo `replan` (`origin=rule:tool_failure_no_alternative`) mostra a diferença, o que `test_the_four_scenarios...` já afirma. Na campanha real, a prova é ler o trace.
- **`REPLAN-WEB`:** o conteúdo vazio virou `[["NFC", "não encontrei", "não consegui confirmar", "não localizei", "não tenho", "não há"]]`: reprova resposta inventada ou fora do assunto e aceita o trecho da busca (`NFC`, no texto programado) ou a admissão clara que o `NOEV` já usa. **Não pus `expect_sources` nem exigi só o trecho:** o produto do cenário (Get XYZ) é fictício, então com busca real o resultado correto é a lacuna declarada, normalmente sem fonte; exigir fonte e conteúdo reprovaria o comportamento certo (a spec da história aceita "a fonte web ou a lacuna declarada"). A exigência estrita (resposta com o texto da busca e a fonte web) está no teste programado `test_the_labels_need_what_each_replanned_step_brings`. Se o Supervisor preferir um rótulo estrito para a campanha real, precisa de uma pergunta sobre um produto Getnet que exista na web e esteja fora dos 40 documentos do índice, que eu não consigo conferir sem rede.

### Evidência

- `ruff check src tests`: ok.
- Pytest, um por vez, basetemp novo (`.pytest_cache/t69-r2-dev-*`): novos e afetados (unit do replanner 32, `test_v080_replan` 35, `test_v080_ticket_id` 5, `test_use_cases`, `test_evaluation_runner`, `test_v060_api`) **172 passed**; trava da v0.7.0 (story, webhooks, resume, resume_r2, ticketing_integration, closing) **94 passed**, arquivos sem alteração.
- Regressão programada de novo (40 casos e 4 conversas contra a `main`): idêntica campo a campo, 25/40 e 4/4, 123 chamadas nas duas. Quatro cenários programados: passam com os rótulos novos.
- Mutações da rodada (cópia fora do repositório): sem `Observed.done` e sem a lacuna do modelo, ambos mortos.
- Não rodei a suíte estrita. Nenhuma chamada paga, rede ou `.env`.

### Arquivos da rodada

`src/merchant_assistant/agents/replanner.py`, `tests/unit/test_replanner_rules.py`, `tests/integration/test_v080_replan.py`, `tests/scenarios/replan.jsonl`, `data/scenarios/catalog.json`, `docs/architecture/decisions/0019-replanejamento.md`, `docs/tasks/69-replanejamento.md`, esta passagem.

### Próxima ação

Supervisor: segunda revisão do candidato desta rodada e suíte estrita.


## Tarefa 72b

- **Papel e responsável:** Developer (Time A), subagente despachado pelo Supervisor.
- **Objetivo e critérios:** [tarefa 72b](../tasks/72b-jornadas-router-v6.md): jornadas de negócio de 6/13 (v0.7.0 real) para pelo menos 12/13 pela rubrica, sem afrouxar o que protege o lojista. Spec v0.8.0 D15, D16, D18; spec 0.2 RF-93, CA-51. Acréscimo do Supervisor: três P3 da revisão da tarefa 69 (rodada 2) que caem nos mesmos arquivos.
- **Branch e base:** `codex/v0.8.0-replan`, base `5da3de5`. Commits: `b1b4951` (prompts e política programada), `46e5600` (rótulos, testes da regressão, snapshot), `046cb73` (acréscimo do Supervisor); tarefa e esta passagem no commit seguinte. Os dois commits de documentos do Supervisor (`724996c`, `d96e8b2`) entraram na branch no meio da tarefa e não foram tocados. Identidade conferida antes de cada commit: `lauroPereira <lauro.s.pereira@gmail.com>`. Sem push, sem troca de branch.
- **Independência:** não se aplica (implementação).

### Arquivos

- Novos: `prompts/router.v6.md`, `prompts/personality.v5.md`, `prompts/replan.v2.md` (os arquivos v5, v4 e v1 ficam como estavam; um teste confere), `tests/integration/test_v080_journeys.py` (41 testes).
- Alterados: `tests/scenarios/business_journeys.jsonl` (5 rótulos), `tests/scenarios/replan.jsonl` e `data/scenarios/catalog.json` (`REPLAN-WEB`, em acordo), `src/merchant_assistant/evaluation/scripted_policy.py` (regra de condições), `agents/personality.py` e `agents/common.py` (texto de reserva com a lacuna), `orchestration/state.py` (descrição de `ReplanDecision.reason`), `agents/replanner.py` (só docstrings), `api/v1.py` (snapshot), `tests/integration/test_v080_replan.py` (+28 testes e `replan@2`), `tests/integration/test_evaluation_runner.py` (`version == "6"`), ADR 0019 (`replan.v2`, a lacuna e a razão vazia).
- Intocados: `evaluation/runner.py`, `data/migrations.py`, `prompts/judge*`, `support.v7`, `escalation.v2`, `personality.v4`, `router.v5`, os testes da trava da v0.7.0, `tests/scenarios/holdout_v080*` (não abri), `.env`, `_tmp/`, `Claude outputs/`, worktrees.

### Caso a caso (D15)

Fonte: respostas reais gravadas em `docs/evidence/v070-qa-regressao-real.json` e `v070-qa-regressao-repeticao.json` (e, para a redação, as campanhas reais da v0.3.0 em `v030-real-*.json`). Critério que usei: **só mudei rótulo onde há resposta real gravada, correta, que o rótulo rejeitou**; onde a resposta estava errada, mudei prompt. Valores (`must_include_amounts`), ferramentas, status, rota e fontes dos cinco rótulos alterados ficam exatamente como estavam (um teste confere); o catálogo não mudou nos irmãos (`PT-PRICE-DIVERGENCE`, `PT-ENABLEMENT-PENDING`, `PT-SALE-CANCELLATION` não foram tocados), e o teste de acordo entre catálogo e JSONL passa.

| Caso | v0.7.0 real | Classe | Mudança | Antes → depois | Justificativa |
| --- | --- | --- | --- | --- | --- |
| `V030-PRICE-CONSISTENT` | `content` falhou: "matches the applicable pricing … both R$ 1,94, with a difference of R$ 0,00" | resposta correta, rótulo literal | **rótulo** | `[["consistent"]]`, sem proibições → `[["consistent","matches the applicable pricing","matches the pricing rule","no difference","difference of r$ 0,00"]]` e `must_not_include` com `inconsistent`, `not consistent`, `does not match` (e variantes com apóstrofo curvo), `fees differ`, `fees are different`, `there is a divergence` | A resposta está certa (valor 194 e ferramenta conferem). O irmão em português já aceitava "sem diferença". O rótulo antigo tinha um furo: "consistent" é substring de "inconsistent"; as frases-guarda fecham o furo. |
| `V030-PRICE-CONDITIONS` | `clarify` ("Which type of credit sale or installment…"): rota, status, ferramenta, conteúdo e fonte falharam | resposta errada (Router) | **prompt** `router.v6` | rótulo igual | O Router exigia a contagem de parcelas. A v6 trata a pergunta de condições (e sua forma interrogativa) como `support`/`pricing` e diz que a contagem é opcional. Regressão programada abaixo; efeito real só na campanha. |
| `V030-PRICE-DIVERGENCE` | `content` falhou: "shows a fee discrepancy … the discrepancy needs human review" | resposta correta, rótulo literal | **rótulo** | inclui só "divergence", "fee difference" e duas frases longas → soma `fee discrepancy`; `must_not_include`: `no discrepancy was found` → `no discrepancy` (mais amplo) + `no fee discrepancy` | O status `handoff`, o valor 75 e a ferramenta continuam exigidos. "Discrepancy" é sinônimo recorrido; a negação ("no discrepancy") continua reprovando. |
| `V030-PRICE-INSUFFICIENT` | passou | — | nenhuma | — | — |
| `V030-ENABLEMENT-PENDING` | `content` falhou: "still pending … not been activated yet", sem o protocolo (na repetição real o protocolo veio e passou) | resposta correta, rótulo literal | **rótulo** (decisão de julgamento, ver abaixo) | `[["sim-bnd-1988-001"]]` → `[["pending"],["visa"]]` e `must_not_include`: `no longer pending`, `is not pending`, `isn't pending`, `has been approved`, `was approved`, `has been enabled`, `is now enabled`, `is now active` | A mensagem em inglês ("can you check it?") não pede o protocolo; a de português ("qual é o protocolo?") pede e **mantém** a exigência do protocolo. O rótulo passa a exigir o status da ferramenta (pendente) e o assunto (Visa). |
| `V030-SALE-CANCELLATION` | passou | — | nenhuma | — | — |
| `V030-CONTRACT-TERMINATION` | `content` falhou: "handed to a member of our support team" (o rótulo exige "human") | resposta aquém do esperado; causa no prompt | **prompt** `personality.v5`, rótulo **mantido** | rótulo `[["human"]]` igual | Ver a decisão logo abaixo. |
| `V030-PT-PRICE-CONSISTENT` | passou | — | nenhuma | — | — |
| `V030-PT-PRICE-CONDITIONS` | primeira execução: `clarify` (Router); repetição: `support`, resposta correta, `content` falhou: "Essa diferença indica **condições distintas**" | as duas: errada na primeira (Router), correta com rótulo literal na repetição | **prompt** `router.v6` **e rótulo** | `…"condições diferentes","planos distintos","planos são diferentes"]` → soma `condições distintas`; `must_not_include` soma `não houve condições`, `não há condições diferentes`, `não há condições distintas` | A oscilação `clarify`/`support` é do Router (mesma causa do caso inglês); a redação "distintas" é sinônimo gravado. As negações novas impedem que a palavra nova aceite "não houve condições distintas". |
| `V030-PT-PRICE-DIVERGENCE` | passou | — | nenhuma | — | — |
| `V030-PT-PRICE-INSUFFICIENT` | `content` falhou: "Não há **uma** regra de preço aplicável ou uma cobrança registrada disponível para comparação" | resposta correta, rótulo literal | **rótulo** | soma `não há uma regra de preço aplicável` ao grupo; `must_not_assert` (a taxa está correta, evidência suficiente…) igual | A frase do rótulo era "não há regra…" (sem "uma"). A resposta admite a falta de evidência, que é o que o caso mede. |
| `V030-PT-ENABLEMENT-PENDING` | passou | — | nenhuma | — | — |
| `V030-PT-SALE-CANCELLATION` | passou | — | nenhuma | — | — |

**Re-pontuação sem modelo** (as respostas reais gravadas passadas pelo `_checks` do runner, com `tools_called`, fontes e status gravados): 6/13 com os rótulos de antes (confere com a campanha), **10/13** com os de agora. Os três que faltam são os que um prompt precisa resolver e que só a campanha real mede: as duas perguntas de condições na primeira execução e `V030-CONTRACT-TERMINATION`. A repetição real do `V030-PT-PRICE-CONDITIONS` passa no rótulo novo. Logo: o `router.v6` resolvendo as duas perguntas de condições dá 12/13; o `personality.v5` dizendo "human agent" dá 13/13. **O 12/13 depende do `router.v6` consertar as duas perguntas**; se só uma ceder, é preciso o `personality.v5` para chegar a 12.

### Decisão: `V030-CONTRACT-TERMINATION` (prompt, não rótulo)

- **O que a resposta real diz:** "Your case has been handed to a member of our support team, who will reply here. Protocol: HO-…". Honesta, mas não diz que quem responde é uma pessoa.
- **Causa:** o `personality.v4` manda "confirm that the case went to a member of the support team". O modelo copiou. Na v0.3.0 (`personality.v3`) a mesma pergunta recebia "I've handed your case to a human agent". A frase que o sistema escreve sozinho (`HANDOFF_LINE`, usada como contribuição e como complemento quando falta o protocolo) já diz "human agent on our support team".
- **Escolha:** `personality.v5` pede "human agent" (em português, "um atendente"), explica por quê (o lojista precisa saber que uma pessoa, e não o assistente, vai responder) e manda manter o texto de `handoff.message`. O rótulo `"human"` continua: aceitar "support team" derrubaria o único check que mostra ao lojista quem responde; "a member of our support team" não é falso, mas é vago. Teste: o rótulo rejeita a frase da v0.7.0 e aceita a linha do sistema.
- **Risco:** só a campanha real diz se o modelo obedece. Se não obedecer, a saída barata é o complemento determinístico (acrescentar `HANDOFF_LINE` quando a resposta não diz "human agent"); não o fiz porque a tarefa pede ajuste de prompt e porque mudaria o texto de todos os encaminhamentos.

### `router.v6` e a regressão programada

- **Texto:** estende a regra de `pricing` à pergunta sobre "condições, plano ou taxa diferentes" numa cobrança específica, com a forma interrogativa em inglês e em português ("Were different conditions used for yesterday's credit charge?", "Was yesterday's credit sale charged under a different plan?", "Did the conditions change on yesterday's debit sale?", "A cobrança de crédito de ontem foi feita em condições diferentes?"); diz que é "never `knowledge` and never `clarify`"; acrescenta ao `clarify` que mensagem sobre cobrança própria com tipo de pagamento ou período não é vaga (e que pergunta sobre taxas gerais da Getnet continua `knowledge`); e uma regra: a contagem de parcelas é opcional, nunca perguntar tipo de venda, parcelas ou qual venda (a ferramenta pergunta depois, se precisar). O resto é a v5 palavra por palavra (a regra de falha persistente depois do encaminhamento, por exemplo, continua; o teste da v0.7.0 que a fixa passa, agora com `version == "6"`).
- **Os exemplos são do conjunto de desenvolvimento** (`V030-*` é `dev`); não abri nada de `holdout_v080*`.
- **Regressão programada** (`test_v080_journeys.py`): a pergunta e oito variações (inglês e português; crédito, débito, Pix; "Were/Was/Did", "Foi/Foram", "mudou") passam pelo grafo programado e terminam em `support` com tópico `pricing`, `simulate_pricing` chamado, status `answered`, fonte presente e, nas de crédito, "conditions differ"/"condições registradas diferem"; a regra programada não engole "Qual a diferença entre a Get Clássica e a Get Smart?", "…disponível no meu plano?" nem "it's not working". A política programada (`scripted_policy.py`) ganhou a mesma regra (`CONDITIONS_QUESTION`: palavra de diferença ou mudança, condições ou plano, cobrança ou venda) e escolhe o tipo de pagamento pelo que a mensagem cita. Numa cópia do `HEAD` de partida, 21 dos testes novos falham (os de prompt, 6 das variações em crédito, 2 de outro tipo de pagamento, os de rótulo), medido antes dos últimos acréscimos.
- **O que a regressão programada não prova:** que o Router real obedece. O modelo programado segue uma regra escrita à mão. A prova real é a campanha do QA, lendo a rota do passo `router` no trace dos dois casos de condições.

### Acréscimo do Supervisor (P3 da revisão da 69, rodada 2)

1. **`REPLAN-WEB`** (`replan.jsonl` e `SC-REPLAN-WEB`, iguais campo a campo; o teste de acordo passa). Antes: `[["NFC","não encontrei","não consegui confirmar","não localizei","não tenho","não há"]]`, sem proibições. Depois: o "NFC" nu saiu (aceitava invenção) e o "não há" nu também; entram as admissões `não consegui encontrar/localizar`, `não foi possível confirmar/encontrar/localizar`, `não é possível confirmar`, `não posso confirmar`, `não consta`, `não há informa…`, `não existem informa…`, `não há confirmação`, `sem confirmação`, `nenhuma informação` e a atribuição `de terceiros`/`não oficial(is)` (o texto programado da busca é "uma página pública de terceiros informa que… (NFC)", que passa pela atribuição). `must_not_include`: `sim, a get xyz aceita`, `sim, aceita`, `sim, ela aceita`, `sim, a get xyz tem/possui`, `a get xyz aceita/suporta/tem/possui nfc`. Não deu para proibir "aceita pagamento por aproximação" sozinho: o texto programado da busca o contém, atribuído a terceiros. Testes: 6 respostas honestas passam, 8 inventadas (inclusive híbridas "não encontrei…, mas sim, aceita…") reprovam, e "A maquininha tem NFC" não satisfaz. Sem `expect_sources`, como na rodada 1 (produto fictício).
2. **Mutantes A08 e A09** (`replanner.py`, linha do `gap`): `test_only_a_finish_declares_the_models_reason_as_the_gap` (`clarify`, `escalate`, `web`, `support` com revisão incompleta e razão não vazia: nenhuma `unconfirmed`; só o `clarify` vê a diferença de fato, porque é o único destino que guarda lacuna além do `finish`) e `test_an_empty_reason_on_an_incomplete_finish_is_not_declared_as_an_empty_gap` (`""`, `"   "`, `"\n\t "`). Numa cópia fora do repositório: sem `next == "finish"`, morre; sem `and reason`, morre; sem `.strip()`, morre (o espaço puro).
3. **A lacuna chega ao texto.** `personality.v5` ganhou a instrução para dizer com clareza o que `unconfirmed` lista, sem palpite. O texto de reserva (`deterministic_answer`, usado quando o modelo cai ou o guarda de saída o recusa) ignorava a lacuna: agora acrescenta uma frase fixa por idioma (`policy("unconfirmed")`: "Não consegui confirmar uma parte do que você perguntou, então não posso afirmar essa parte." / "I could not confirm part of what you asked, so I can't state that part."), **uma vez**: não repete quando a parte do Knowledge já diz que nada foi encontrado. A lacuna é texto interno em inglês e livre (a razão do modelo, por exemplo), por isso o reserva usa a frase fixa e não a cita. `replan.v2` e a descrição de `ReplanDecision.reason` (`orchestration/state.py`) deixam de dizer só "para o trace": no `finish` incompleto a razão é o que o lojista lê, então o planejador deve escrever o fato que faltou. `replan.v1` fica; o passo do trace agora grava `replan@2`; o teste que fixava `replan@1` foi atualizado, e a ADR 0019 também. Testes: o prompt da Personality leva a lacuna e a instrução; o reserva traz a frase em inglês e em português, não duplica, e não muda quando nada foi declarado.

### Evidência

- `ruff check src tests`: ok. Pytest, um por vez, basetemp novo (`.pytest_cache/t72b-dev-20261104a` a `p`), `-p no:cacheprovider`, caminhos Windows, no `HEAD` `046cb73`: novos e afetados **256 passed**; trava da v0.7.0 (story, webhooks, resume, resume_r2, ticketing_integration, closing) **94 passed**, arquivos sem alteração; `tests/unit` **279 passed**; os outros 14 arquivos de `tests/integration` **199 passed**. Nenhum `WinError 5` nem outro bloqueio de ambiente.
- Regressão programada de novo (40 casos e 4 conversas, sem `.env`, `Settings(_env_file=None)`): `main` (`git archive`, `bd0920a`), o `HEAD` de partida e a árvore atual são **idênticos campo a campo** (25/40 e 4/4, 123 chamadas, resposta, `agents`, fontes, ferramentas e os nove checks por caso; sufixo aleatório do protocolo `HO-` normalizado). Não há diferença a justificar: os rótulos novos passam igual nos casos programados, e as mudanças de prompt não entram no modelo programado.
- Mutações (cópia fora do repositório, 9 sondas): A08, A09, `.strip()`, reserva sem a lacuna, reserva que repete, rótulo web com "NFC" nu, rótulo web sem a proibição "sim, aceita" (só depois de pôr duas respostas híbridas no teste) e prompt da Personality sem a instrução, **todas mortas**. **Sobreviveu** uma: apagar "It goes to the trace." do `replan.v2`, que não muda o que o teste afirma (equivalente).
- Nenhuma chamada paga, nenhuma rede, `.env` não lido, sem Docker; scripts e cópias no scratchpad, fora do repositório.

### Decisões tomadas além do texto do plano (todas reversíveis)

1. **`V030-ENABLEMENT-PENDING` em inglês: troquei a exigência do protocolo pela do status.** É a mudança que mais se aproxima de afrouxar um check que protege um valor, então fica registrada como julgamento: a mensagem não pede o protocolo, a resposta real gravada está certa e, na repetição, trouxe o protocolo; o que o lojista pediu (o estado da solicitação) passa a ser exigido, com proibições para "aprovada/habilitada". O irmão em português mantém o protocolo. Alternativa não adotada: `support.v8` mandando sempre citar o protocolo; para reverter, devolver `[["sim-bnd-1988-001"]]` ao rótulo. Se o Supervisor preferir o protocolo sempre, o caminho é o `support.v8`.
2. **`api/v1.py`:** o snapshot de execução gravava o literal `"router.v5"` em `prompt_versions`; com a v6 ficaria errado. Agora usa o `prompt_versions()` que já gravava em `prompt_set`. Arquivo fora da lista do D18, mas já tocado na tarefa 69; um teste novo cobre.
3. **`personality.v5` foi editado depois do primeiro commit** (instrução de `unconfirmed`), na mesma tarefa: a v5 ainda não existia em nenhum candidato nem campanha, então não é edição de versão publicada.
4. **Política programada:** o tipo de pagamento da pergunta de condições passa a vir da mensagem (Pix, débito, senão crédito); para as mensagens que já existiam (crédito) nada muda.
5. **Só mudei rótulo com resposta real gravada que o rejeitou.** Não alarguei `V030-PRICE-CONDITIONS` (inglês): as respostas reais de suporte gravadas dele já passam no rótulo atual; ele falhava só pelo Router.

### Achados e limitações

- **O efeito real é da campanha `v080-qa`:** (a) rota dos dois casos de condições no passo `router` do trace; (b) a frase de encaminhamento do `V030-CONTRACT-TERMINATION`; (c) se o `V030-PT-PRICE-CONDITIONS` deixa de oscilar; (d) se o Router não passou a mandar perguntas de taxas gerais para `support` (a v6 diz que continuam `knowledge`; a regressão real de 40 casos olha isso); (e) a lacuna `unconfirmed` dita pelo modelo nos casos de falha do `REPLAN-*`. O texto de reserva só cobre a queda do modelo.
- **README** (`README.md:27`) cita `prompts/router.v5.md`: fica para a tarefa 73 (README e CHANGELOG).
- **Scratchpad compartilhado:** um arquivo `mutate.py` de outro agente (apontando para o worktree `time-b`) apareceu no mesmo diretório de rascunho que o meu e sobrescreveu o meu depois que minhas sondas terminaram; nada no repositório foi afetado. Vale separar os rascunhos por agente.
- A suíte estrita não foi rodada, como combinado.

### Próxima ação

Supervisor: revisar (Reviewer independente) as três mudanças de prompt e a nota de julgamento do `V030-ENABLEMENT-PENDING`; rodar a suíte estrita; QA real depois do merge com o Time B.


## Tarefa 72b, rodada 2

- **Papel e responsável:** Developer (Time A), mesma tarefa, correção pedida pela revisão independente ([v080-reviewer-t72b.md](v080-reviewer-t72b.md), candidato `c861bee`, parecer em `ae7d8b9`).
- **Branch e base:** `codex/v0.8.0-replan`, base da rodada `ae7d8b9`. Commit de código e testes: `915ab72`; esta passagem e a Validação da tarefa no commit seguinte. Identidade conferida antes de cada commit: `lauroPereira <lauro.s.pereira@gmail.com>`. Sem push, sem troca de branch.
- **Achados atendidos:** P2-1 (obrigatório) e P3-1 a P3-6. P3-7 e P3-8 ficam como registrados, sem mudança.
- **Independência:** não se aplica (implementação).

### Arquivos da rodada

`tests/scenarios/business_journeys.jsonl` (4 rótulos de jornada, só `must_not_include`: `V030-ENABLEMENT-PENDING`, `V030-PT-PRICE-CONDITIONS`, `V030-PRICE-CONSISTENT`, `V030-PRICE-DIVERGENCE`), `tests/scenarios/replan.jsonl` e `data/scenarios/catalog.json` (`REPLAN-WEB`, em acordo; o teste de acordo passa), `prompts/router.v6.md` (editado no lugar: a v6 ainda não rodou em nenhuma campanha), `src/merchant_assistant/evaluation/scripted_policy.py` (quarta parte da regra de condições), `tests/integration/test_v080_journeys.py` (41 → 86 testes) e `tests/integration/test_v080_replan.py` (63 → 79). Nenhum arquivo de `src/` além da política programada; `router.v5`, `personality.v4`, `replan.v1`, `runner.py`, migrações, `judge*` e `holdout_v080*` não foram tocados.

### P2-1: `V030-ENABLEMENT-PENDING` (inglês) não aceita mais a negação do status

- **Antes:** `[["pending"],["visa"]]`, proibições só para "no longer pending", "is not pending", "isn't pending" e aprovação (9 frases).
- **Depois:** as 9 e mais 23: `no pending`, `not pending`, `nothing pending`, `nothing is pending`, `no more pending`, `not in pending`, `not in the pending`, `isn't in the pending`, `will be approved`, `is already enabled`, `no visa`, `could not find`, `couldn't find`, `can't find`, `don't see`, `was rejected`, `was completed`, `canceled`, `cancelled` e as variantes com apóstrofo curvo (o modelo real escreve `’`). **Não usei** `is active`: a resposta real certa diz "does not mean account enablement is active".
- **Prova:** as seis frases do parecer ("I could not find any pending Visa enablement request.", "You have no pending Visa enablement request.", "The Visa enablement request is not in pending status.", "Your Visa enablement is active. There are no pending requests.", "Your Visa request has been canceled, nothing pending.", "…is pending, and it will be approved tomorrow.") e mais três ("was rejected, so it is no more pending", "I don’t see a pending Visa request…", "was completed and is already enabled") entraram no `STILL_WRONG`: todas têm "pending" e "visa" (passariam no conteúdo) e reprovam em `forbidden_ok`. As quatro respostas reais certas (as duas da v0.7.0 e as duas da v0.3.0) continuam passando.

### P3, caso a caso

| Item | Caso | Antes → depois | Observação |
| --- | --- | --- | --- |
| P3-1 | `V030-PT-PRICE-CONDITIONS` | proibições `condições são iguais`, `mesmas condições`, `mesmo plano`, `não houve condições`, `não há condições diferentes/distintas` → soma `não foram usadas`, `não foram aplicadas`, `não encontrei condições`, `não identifiquei condições`, `não há indícios de condições`, `não foi possível verificar se havia condições`, `foram as mesmas`, `foram iguais` | As quatro negações do parecer reprovam. Escolhi frases que carregam a palavra "condições" ("não encontrei condições", não "não encontrei"), para não reprovar uma resposta correta que diga, por exemplo, "não encontrei indício de erro". A resposta real certa da repetição da v0.7.0 e as duas da v0.3.0 passam. |
| P3-2 | `V030-PRICE-CONSISTENT` | soma `mismatches`, `mismatched`, `there is a mismatch`, `there was a mismatch` | **Não usei "mismatch" sozinho:** "there is no mismatch" é uma forma legítima de dizer que a taxa confere. O que cria o furo é "mismatches the applicable pricing" conter "matches the applicable pricing"; é isso que as frases fecham. |
| P3-3 | `V030-PRICE-DIVERGENCE` | soma `did not find a fee discrepancy`, `didn't`/`didn’t` find a (fee) discrepancy, `did not find any discrepancy`, `found no (fee) discrepancy`, `was/were not detected`, `not detected`, `no fee difference` | `no fee discrepancy` e `no discrepancy` já estavam. As respostas reais certas gravadas (v0.7.0 e v0.3.0) passam. |
| P3-4 | `REPLAN-WEB` (jsonl e catálogo) | admissões: soma `não consegui verificar`, `não consigo verificar/confirmar/encontrar`, `não identifiquei`, `não foi possível identificar/verificar`, `não achei`, `não sei`, `não posso afirmar`, `não tenho como confirmar`, `não existe informa…`; proibições: soma `mas a get xyz aceita`, `porém (,) a get xyz aceita`, `no entanto (,) a get xyz aceita`, `contudo (,) a get xyz aceita`, `mas aceita`, `mas ela aceita`, `mas a get xyz tem/possui/suporta`, `porém a get xyz tem/possui` | **Achado meu, na rodada anterior:** as quatro frases de NFC (`a get xyz aceita/suporta/tem/possui nfc`) estavam em `must_not_include`, o que reprovava a admissão honesta "Não foi possível confirmar se a Get XYZ aceita NFC." Passaram para `must_not_assert`, que aceita a forma com dúvida ("não foi possível confirmar se", "não sei se", "não posso dizer") e continua reprovando a afirmação direta. "mas sim" ficou de fora: reprovaria "…mas sim uma página de terceiros diz…", que é atribuída. O texto programado da busca ("página pública de terceiros informa que…") continua passando pela atribuição. Testes: 16 admissões honestas passam (dez delas novas), 13 invenções (cinco com ressalva) reprovam. |
| P3-5 | `router.v6` | sem exemplos contrastivos → "Contrast: a general question that does not point at a charge the merchant already had stays `knowledge` ("What are the fees for credit sales?", "Can I change my plan?", "Do the conditions change for sales above R$ 1.000?"); a question about the merchant's own recorded charge (…) is support with topic `pricing`" | Editado no lugar. A regra programada ganhou a quarta parte (um período que aponte para uma cobrança que o lojista já teve: yesterday, today, last, latest, ontem, hoje, passado, último); sem ela, "Do the conditions change for sales above R$ 1.000?" ia para `pricing` na política programada, contra o que o prompt ensina. Teste: as quatro perguntas gerais (três em inglês, uma em português) não viram `pricing`. |
| P3-6 | sobreviventes | cinco mutantes sem teste | Ver abaixo. |
| P3-7, P3-8 | — | sem mudança | — |

### P3-6: testes dos sobreviventes

- **Tipo de pagamento no Support programado:** débito responde "consistent values"/"valores coerentes", Pix vira `handoff` com "divergence"/"divergência", crédito "conditions differ" (antes o teste só olhava rota e ferramenta).
- **Regra de condições:** cada uma das quatro partes tem um caso que a regra deixa passar quando a parte falta (sem palavra de diferença, sem condições ou plano, sem cobrança ou venda, sem período) e cada alternativa de palavra de diferença (`differ`, `change`, `mudou`, `mudaram`, `distintas`, `diferentes`) e de período (`today`, `latest`, `hoje`) tem um caso que casa.
- **`personality.v5`:** "Say that it is a human agent (in Portuguese, "um atendente"), not only "a member of the team"" e "Keep the wording of the `handoff.message` contribution" são afirmados.
- **Texto de reserva com o Support presente:** o texto traz os pontos da conta (receivables, em português) antes da frase fixa, uma vez só.

### Evidência

- **Sondas de rótulo com as respostas reais gravadas** (v0.7.0 real e repetição, v0.3.0 `real-r1` e `real-http-r2`; 44 respostas dos casos de jornada, das quais 38 passam e 6 são as erradas de verdade, com `tools_called`, fontes e status gravados): os veredictos com os rótulos de agora são **idênticos aos da rodada 1** em todas as respostas; nenhuma resposta real certa passou a ser reprovada. A re-pontuação da campanha segue 6/13 → **10/13**.
- `ruff check src tests`: ok. Pytest, um por vez, basetemp novo (`.pytest_cache/t72b-dev-20261104s` a `v`, apagados depois de cada execução), `-p no:cacheprovider`, caminhos Windows, no `HEAD` `915ab72`: novos e afetados **317 passed**; trava da v0.7.0 **94 passed**, arquivos sem alteração; `tests/unit` **279 passed**; os outros 14 arquivos de `tests/integration` **199 passed**.
- **Regressão programada** (40 casos e 4 conversas, `Settings(_env_file=None)`): `main` (`bd0920a`, por `git archive`) e a árvore atual idênticas campo a campo, 25/40 e 4/4, 123 chamadas. Nada a justificar.
- **Mutações** (cópia fora do repositório, 19 sondas novas: tipo de pagamento ×3, cada parte e cada palavra da regra de condições ×11, as duas frases do `personality.v5`, o contraste do `router.v6`, o texto de reserva ×2): **19 de 19 mortas**. Uma primeira tentativa não valeu (o diretório pai do basetemp não existia e todos os mutantes "morreram" no `setup`); foi descartada e refeita.
- Nenhuma chamada paga, nenhuma rede, `.env` não lido, `holdout_v080*` não aberto.

### Decisões tomadas além do texto do pedido (reversíveis)

1. `mismatches`/`mismatched`/`there is(was) a mismatch` no lugar de `mismatch` (P3-2), pelo motivo acima.
2. NFC de `REPLAN-WEB` em `must_not_assert` (P3-4), por um falso positivo que eu mesmo tinha criado.
3. Frases de P3-1 com a palavra "condições", para não reprovar resposta correta com outra negação.
4. Período como quarta parte da regra programada de condições (P3-5).

### Achados e limitações

- **Disco cheio no ambiente:** durante a rodada o volume `C:` ficou com 0 MB livres ("Disk full" na ferramenta; um `eval` programado falhou com `database or disk is full`; foi repetido depois de liberar espaço e o resultado é o da tabela). Liberei só o que eu tinha criado (cópias de `git archive`, cópias de mutação e basetemps `t72b-dev-*` em `.pytest_cache`); o volume segue em 100% (cerca de 1,5 GB livres), então vale avisar o responsável. Não toquei nos diretórios que já existiam em `.pytest_cache` nem em arquivos de outros agentes no scratchpad.
- Continua valendo tudo o que a campanha real mede (rota dos dois casos de condições, frase de encaminhamento, perguntas gerais de taxa não irem para `support`, lacuna dita pelo modelo).
- Cobertura de frases proibidas: alguns termos são variantes de outros (apóstrofo curvo, "not in the pending"), e uma análise de remoção termo a termo mostra que nem todos têm uma resposta de teste que dependa só deles. O que protege o lojista são as frases do parecer, e todas têm resposta de teste; as demais são redundância deliberada.

### Próxima ação

Supervisor: nova revisão estreita dos rótulos (`V030-ENABLEMENT-PENDING`, `REPLAN-WEB`) e do contraste do `router.v6`; suíte estrita; QA real depois do merge com o Time B.

---

## Tarefa 72a, rodada 1

- Papel e responsável: Developer do Time B (subagente), despachado pelo Supervisor.
- Objetivo e critérios: [tarefa 72a](../tasks/72a-holdout-respostas-v080.md), RF-92 e CA-50 da [spec 0.2](../specs/evolucao-pos-feedback.md), decisão técnica 15 do [plano](../specs/evolucao-pos-feedback-plano.md). Escrever e lacrar por hash o holdout de respostas antes de qualquer ajuste de prompt da v0.8.0, por quem não ajusta prompts.
- Escopo: arquivos novos `tests/scenarios/holdout_v080.jsonl`, `tests/scenarios/holdout_v080.sha256`, `tests/unit/test_holdout_v080.py`, `docs/evidence/v080-holdout-derivacao.md` e esta passagem; alterada só a tarefa 72a (Validação e Status). Nenhum arquivo do Time A tocado (`cli.py`, `evaluation/`, `orchestration/`, `api/`, `prompts/`), nenhum JSONL existente alterado. Repositório: `C:\workspace\ai-getnet-case-wt\time-b`.
- Estado: em andamento até a revisão; implementação concluída pelo Developer.
- Branch e PR: `codex/v0.8.0-avaliacao`, sem PR, sem push.
- Base e versão final: base `d7acaec`; versão final é o commit único desta tarefa, que traz esta passagem (SHA informado ao Supervisor no retorno). Hash do holdout: `4002fdc9b9efd667d253c5fe9ae6b48d7cd03eac6c489a0119984d8139e1e626` (SHA-256 do conteúdo UTF-8 com quebras normalizadas para `\n`; coincide com `sha256sum` do arquivo, que já está em LF).
- Independência: não-independente; é o próprio autor relatando. A revisão independente cabe ao Reviewer.

### Regra de autoria

`prompts/` não foi aberto. Também não foram abertos traces, avaliações nem respostas reais de modelo em `docs/evidence/`. As mensagens são paráfrases das páginas oficiais versionadas (`data/snapshots/public/pages/`, listadas em `data/sources/public-sources.json`), dos procedimentos de `data/knowledge-demo/` e dos fatos da seed. Os JSONL existentes serviram só para formato e para evitar repetição. Código lido para entender rótulos: `evaluation/runner.py` (`Case`, `load_cases`, checagens), `guardrails/output.py` (`amounts`), `tools/domain.py`, `tools/registry.py`, `data/seed.py`, `data/clock.py`, `testing.py`, `api/schemas.py` (rotas e status) e, por busca, a linha de passagem com o protocolo `SIM-` em `agents/escalation.py` e `agents/personality.py`.

### Evidência

- Composição: 25 casos, 13 pt (52%) e 12 en. Rotas: `knowledge` 6, `general_web` 2, `support` 10 (recebíveis, liquidação, dispositivo, autorização, contrato, preço ×2, cancelamento, habilitação, isolamento), `knowledge_and_support` 3, `human_handoff` 2, `out_of_scope` 2. Difíceis (`-HARD`): `HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD` e `HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD` (inglês sobre produto descrito só em português, sem o nome do produto), `HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD` (paráfrase distante) e `HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD` (duas intenções).
- Derivação: [v080-holdout-derivacao.md](v080-holdout-derivacao.md), com o comando em processo (seed, relógio `2026-10-26T10:00:00`, banco em `.pytest_cache/v080-b-holdout/`, `in_process_client()`), a saída de cada ferramenta e, para cada caso, a página oficial ou o procedimento demo com trecho curto.
- Teste de lacre: `tests/unit/test_holdout_v080.py`, 6 testes. Prova de violação: troquei um byte do JSONL (`smartphone` → `smartphonE`) e 2 testes falharam (`test_seal_matches_content` e `test_seal_ignores_line_endings_but_not_content`); com o arquivo restaurado, os 6 passaram e `sha256sum` voltou a `4002fdc9…e626`.
- Suíte estrita: `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v080-b-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` terminou com código 0, 355 testes aprovados em 231,95 s, ruff sem achados, estrutura e skills válidas. A primeira execução tinha 355 testes aprovados, mas terminou com código 1 por um SIM300 (comparação invertida) na linha 62 do teste novo. Corrigi a comparação antes da segunda execução.
- Ambiente: `.venv` do worktree, Python 3.13.3; `import merchant_assistant` resolve para `C:\workspace\ai-getnet-case-wt\time-b\src\merchant_assistant`. Nenhuma chamada paga, sem `.env`, sem Docker.

### Decisões além do texto do plano

- 25 casos em vez dos 24 sugeridos: o recebível líquido do débito ficou como caso próprio, para separar recebíveis de liquidação.
- Difíceis marcados pelo sufixo `-HARD` no id, porque o `Case` não tem campo `notes` e `load_cases` falharia com chave extra.
- Valores das páginas oficiais (R$ 50,00 mínimo de antecipação; R$ 1,00 por link pago) em `must_include_amounts` (5000 e 100), como os valores das ferramentas.
- Teste extra que refaz as chamadas às ferramentas sobre a seed e confere que todo valor de caso com ferramenta esperada sai delas. Ele prende o holdout à seed: se a seed mudar, o teste falha. Isso é intencional, porque nesse caso os rótulos ficariam velhos.
- Todos os casos usam `cliente1988`; o isolamento é testado pelo recurso de outro lojista citado na mensagem (`dev_002_tap01`), não por `user_id` trocado.

### Rótulos que julguei ambíguos (notas, não suposições)

1. `HV080-EN-SUP-PRICE-CREDIT-CONDITIONS`: a ferramenta retorna `different_conditions`. Rotulei `answered`, seguindo `V030-PRICE-CONDITIONS`. Porém o lojista reclama de cobrança maior, e o procedimento demo diz que "contrato e pricing incompatíveis exigem análise". Uma resposta com `handoff` é defensável e falharia em `status_ok`.
2. `HV080-PT-OOS-BUYER-PERSONAL-DATA`: rotulei `out_of_scope`/`refused` pelo RF-06 (dados de terceiros). Uma resposta `answered` dizendo que não há esses dados falharia.
3. `HV080-PT-SUP-FOREIGN-DEVICE`: rotulei `support`/`answered` sem dado alheio, como o UC-13. Uma recusa `out_of_scope` falharia.
4. `HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD`: exige "38" e "inicializa", das páginas de erro ADQ. O FAQ do crediário dá outro caminho de inicialização ("Suporte > Bandeiras > Funções Técnicas > Inicialização"), sem "38". Uma resposta que use só esse caminho falha no primeiro grupo.
5. `HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD` e `HV080-EN-SUP-PAYOUT-LINK-SALE` exigem `get_payout_status` além da agenda. Uma resposta que conclua "pago" só pelo `SETTLED` da agenda falha em `tools_ok`.
6. `HV080-EN-KS-WIFI-NEW-PASSWORD` aceita só `knowledge_and_support`, como o UC-05.

### Limitações

- Checagens por substring: `must_not_assert` só neutraliza as formas de incerteza listadas no runner. Uma negação como "não há confirmação de que o dinheiro já voltou para o cartão" seria marcada indevidamente em `HV080-PT-SUP-CANCELLATION-REFUND`. Valores oficiais só contam com prefixo `R$` ou `BRL` (por exemplo, "50 reais" não conta).
- `HV080-PT-SUP-PRICE-LINK-CONSISTENT` exige que o agente descubra a data da venda pela agenda, porque `simulate_pricing` não filtra por canal. "Semana passada" corresponde a 6 dias antes, e com `SystemClock` a expressão nem sempre é exata.
- Na campanha real o relógio é o do sistema: as datas mudam, os valores não. "Agora há pouco" depende do evento em `now − 3h10`.
- As páginas oficiais têm taxas conflitantes (por exemplo, débito do Get Tap a 1,69% numa página e 0,99% em outra). Por isso evitei perguntas de taxa pública.
- O holdout ainda não foi rodado contra nenhum modelo; nenhuma medição foi feita.

### Critérios

- Comprovados localmente: ≥ 20 casos e ≥ 50% em pt; rotas cobertas; 4 difíceis marcados; derivação reproduzível; teste de lacre passa e falha com um byte alterado; suíte estrita com código 0; nenhuma chamada paga; `prompts/` não foi aberto.
- Não verificados: comportamento do sistema real no holdout (campanha do QA na v0.8.0).

### Ação externa, identidade e próxima ação

- Ação externa: nenhuma (sem push, sem PR). Commit local único com identidade `lauroPereira <lauro.s.pereira@gmail.com>`, conferida no worktree.
- Próxima ação: o Supervisor despacha o Reviewer independente para a 72a. Depois da aprovação, o holdout fica congelado. Recomendo que quem ajustar prompts na 72b não leia o conteúdo do JSONL, para cumprir "nunca usado em ajuste".
- Decisão humana pendente: nenhuma para esta rodada. As notas de rótulo ambíguo acima ficam para o Reviewer e o Supervisor decidirem se mantêm o rótulo, sabendo que qualquer mudança exige novo hash antes da campanha.

## Tarefa 72a, rodada 2

- Papel e responsável: Developer do Time B, sobre o [parecer do Reviewer, rodada 1](v080-reviewer.md) (correções necessárias: 1 P1, 4 P2, 4 P3).
- Escopo: `tests/scenarios/holdout_v080.jsonl` (só rótulos; mensagens, ids, idiomas e valores iguais), `tests/scenarios/holdout_v080.sha256`, `tests/unit/test_holdout_v080.py`, `docs/evidence/v080-holdout-derivacao.md`, a tarefa 72a e esta passagem. `prompts/` continua sem ser aberto.
- Estado: correções implementadas; em andamento até a revisão da rodada 2.
- Base e versão final: base `2c0fc0f`; versão final é o commit único desta rodada, que cita o novo hash. Hash novo `a3e7342ea15854356c5378b7ba00bb6c6cd58319d7d610bceb3cd2a5e099653d` (antes `4002fdc9…e1e626`).
- Independência: não-independente (relato do autor).

### Correções

- **P1-1:** `HV080-PT-HANDOFF-CALLBACK` e `HV080-EN-HANDOFF-END-AGREEMENT` exigem `["HO-"]`, sem `SIM-`.
- **P2-1** (os termos positivos deixaram de aprovar a conclusão oposta):
  - `PRICE-LINK-CONSISTENT`: termos como "mesmo valor", "sem divergência", "está correta", "bate com"; `must_not_assert` com "não está correta", "não confere", "não bate", "cobrança a mais" e semelhantes.
  - `PRICE-CREDIT-CONDITIONS`: removido o "differ" solto; proibidos "overcharged", "charged more than", "you will be refunded", "the fee is correct" e "conditions match".
  - `CANCELLATION-REFUND`: proibições com o sujeito colado ("cancelamento foi concluído", "valor foi devolvido", "venda foi estornada"). A forma sugerida pelo parecer ("foi concluído") reprovaria a resposta certa "ainda não foi concluído", porque o runner não neutraliza "ainda não".
  - `ENABLEMENT-MASTERCARD-DEVICE`: removidos "update" e "initializ"; proibidos "can accept mastercard" e "can already accept". "cannot accept" não contém "can accept".
  - `PIX-PAID-AND-ADVANCE-HARD`: removidos "caiu" e "pago" soltos; proibidos "ainda não caiu", "não foi creditado", "não foi pago" e semelhantes.
- **P2-2:** `FOREIGN-DEVICE` exige negativa de acesso ("não pertence", "não tenho acesso", "não consigo consultar"…). Proíbe "Android 14" e "9 min", e afirmar que `dev_002_tap01` ou "ela" está ligada, online ou conectada. Não proibi "está online" solto porque a resposta certa pode dizer que a Get Smart do próprio lojista "não está online".
- **P2-3:** `DEVICE-SIGNAL` aceita "não está conectada"/"não está online"; `SAME-DAY-REVERSAL` aceita "day of the", "that day", "today"; `CONTRACT-SETTLEMENT` aceita "dia útil seguinte", "dia seguinte", "próximo dia útil".
- **P2-4:** o teste normaliza para LF antes de gerar a variante CRLF. Converti o JSONL de fato para CRLF e os 8 testes passaram; com um byte alterado, 2 falharam; o arquivo foi restaurado (`sha256sum` = hash novo). O `.gitattributes` não foi alterado: está fora dos arquivos permitidos, e o teste já não depende dele.
- Verificação dos rótulos: as 26 respostas sintéticas (certas e erradas, incluindo os exemplos do parecer) foram passadas por `_checks` do runner, sem modelo: 0 divergências.

### Decisões sobre os P3

- **P3-1, corrigido:** o teste agora deriva os valores das chamadas de cada caso (`TOOL_DERIVATION`) e confere os valores de conhecimento na página oficial versionada com o trecho (`SOURCE_DERIVATION`: "o valor mínimo para antecipação é de R$50,00" → 5000; "R$1,00 por link pago" → 100). Outro teste exige que todo caso com valor tenha derivação.
- **P3-2, mantido:** a sobreposição com os casos dev é de cenário, não de texto, e cobre os usos mais frequentes. Recomendo reportar o holdout por caso e marcar esses quatro (`CREDIT-DECLINE-NOT-DEVICE`, `WIFI-NEW-PASSWORD` e os dois web) ao ler o resultado.
- **P3-3, corrigido:** `WHATSAPP-PAY-MIGRATION` aceita `knowledge` e `knowledge_and_support`.
- **P3-4, corrigido:** `RECEIVABLE-DEBIT-NET` não exige ferramenta específica, porque o valor 14806 só vem de dado do lojista; `PHONE-AS-TERMINAL` aceita "Android version 12", "version 12 of Android" e "Android OS 12".

### Ausência de ajuste de prompt

`git log --oneline 07ca28e..main -- prompts/` → nenhum commit (a `main` está em `07ca28e`). `git log --all --oneline 07ca28e.. -- prompts/` → nenhum commit em nenhuma branch. O re-lacre ocorre antes de qualquer ajuste de prompt da v0.8.0.

### Evidência

- Suíte estrita: `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v080-b-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → código 0, 357 aprovados (355 + 2 testes novos de derivação), ruff limpo.
- Composição inalterada: 25 casos, 13 pt, 12 en, 4 `-HARD`.

### Limitações

- O `must_not_assert` do runner só neutraliza as formas de incerteza da sua lista. "Não há confirmação de que o valor foi devolvido" e "não consigo dizer se ela está ligada" ainda seriam marcadas. Os termos foram escolhidos para que as respostas certas mais prováveis não os contenham, mas o risco não é zero.
- Comportamento real do modelo não verificado (sem chamada paga).

### Próxima ação

O mesmo Reviewer revê na rodada 2 os casos alterados, o teste e o novo lacre.

## Tarefa 72a, rodada 3

- Papel e responsável: Developer do Time B, sobre o [parecer do Reviewer, rodada 2](v080-reviewer.md) (P2-5 novo; P3-5, P3-6 e P3-2).
- Escopo:
  - Rótulos de 6 casos em `tests/scenarios/holdout_v080.jsonl`: linhas 4 e 14 a 18. Mensagens, ids, idiomas, rotas, status e valores ficaram iguais.
  - Também `holdout_v080.sha256`, `docs/evidence/v080-holdout-derivacao.md`, a tarefa 72a e esta passagem.
  - O teste e `evaluation/` não foram alterados, e `prompts/` continua sem ser aberto.
- Base e versão final: base `e1886ed`; commit único da rodada, citando o hash novo `46474c0aa38ca2a828493a4d000844e10882d7098cf519d87922de594ccfd0ff` (rodada 2: `a3e7342e…099653d`).
- Independência: não-independente (relato do autor).

### P2-5

- **Diagnóstico:** `_assertion_is_present` corta orações em vírgula, ponto e vírgula e "mas", e só desconta qualificadores fixos. Uma resposta cautelosa que nega a afirmação proibida com outro lead-in ("não houve", "não há confirmação de que", "não posso afirmar que", "não tenho acesso para informar se", "does not mean", "can't promise", "once … it can") era reprovada como falha crítica.
- **Âncoras afirmativas não servem:** testei a sugestão "sim, "/"yes, ". Ela não funciona, porque a vírgula separa a âncora da afirmação; essas entradas nunca disparariam. Por isso não as mantive.
- **Regra adotada:** em `must_not_assert`, só conclusões erradas de polaridade negativa, que a resposta certa não contém. Isso vale só para o caso 14: "não está correta", "não está coerente", "não é coerente", "a taxa não confere", "a taxa não bate". Nos casos 15 a 18, a lista ficou vazia; a conclusão errada afirmativa fica para o grupo positivo e para o juiz.
- **Caso 18:** mantém `must_not_include` "Android 14" e "9 min" e a negativa de acesso obrigatória.
- **Caso 14:** o grupo positivo ganhou "a mesma" e "mesma taxa".

### P3

- **P3-5, corrigido:**
  - Caso 4 sem "today" e "that day" soltos (ficaram "same day", "day of the transaction/sale/purchase", "that same day", "only today"…).
  - Caso 17 sem "not yet" solto (ficaram "not yet available", "not yet enabled", "cannot accept mastercard yet"…).
- **P3-5, mantido:** a resposta mista do caso 16 ("cancelamento aprovado… status solicitado") não tem como ser pega por substring sem reprovar respostas certas. Fica para o juiz.
- **P3-6, aceito:** o vínculo do valor é por caso, sustentado pela tabela da derivação.
- **P3-2:** sobreposição de cenário segue registrada.

### Bateria pelo `_checks` real (sem modelo)

- **Rodada 3:** 40 respostas para os casos 4 e 14 a 18 e o Pix.
  - 22 certas, com os lead-ins de negação pedidos: 22/22 passam.
  - 18 erradas: 17/18 reprovam. A que passa é "Sim, o dinheiro já voltou para o cartão do cliente; o status é solicitado." (caso 16).
- **Bateria da rodada 2 refeita:** 26 respostas, 25 com o resultado esperado. A diferença é "Não pertence a você, mas ela está ligada." (caso 18), que agora passa. É o custo de não reprovar a resposta certa "não tenho acesso para informar se ela está ligada".

### Evidência

- Suíte estrita (`--basetemp .pytest_cache/v080-b-strict`) → código 0, **357 aprovados**, ruff limpo. O lacre confere com o hash novo.
- `git log --all --oneline 07ca28e.. -- prompts/` → nenhum commit.

### Limitações

Checagem por substring tem teto: duas respostas erradas mistas passam, e o juiz independente da v0.8.0 cobre esse resíduo. A alternativa seria mudar o runner (`evaluation/`), que é do Time A e está fora desta tarefa.

### Próxima ação

O mesmo Reviewer revê, na rodada 3, os casos 4 e 14 a 18 e o lacre.

## Tarefa 72a, rodada 4

- Papel e responsável: Developer do Time B, sobre o [parecer do Reviewer, rodada 3](v080-reviewer.md) (P2-6; P3-7 aplicado por decisão do Supervisor).
- Escopo: rótulos dos casos 14, 15, 16 e 18 em `tests/scenarios/holdout_v080.jsonl`, `holdout_v080.sha256`, `docs/evidence/v080-holdout-derivacao.md`, a tarefa 72a e esta passagem. Teste, `evaluation/` e `prompts/` intocados; `prompts/` continua sem ser aberto.
- Base e versão final: base `a113720`; commit único da rodada, citando o hash novo `115728126d2a3d6b2d62f63b61cafbb45823f4cbf57d211cb7a03d8afeff1bac` (rodada 3: `46474c0a…ccfd0ff`).
- Independência: não-independente (relato do autor).

### Correções

- **Caso 14:** `must_not_assert` = "não está correta", "não está coerente", "não é coerente", "não confere", "não bate". Todas têm polaridade negativa.
- **Caso 15:** segundo grupo obrigatório de ressalva: "analysis", "analyse", "analyze", "review", "can't say", "cannot say", "can't confirm", "cannot confirm", "can't determine", "cannot determine", "does not mean", "doesn't mean", "not necessarily", "before saying", "before confirming", "not clear", "unclear". Os dois últimos são acréscimo meu, porque "it is not clear that the fee is correct" é resposta certa da bateria.
- **Caso 16:** segundo grupo obrigatório de não-confirmação: "ainda não", "não foi concluído", "não há confirmação", "sem confirmação", "não foi confirmado", "não posso afirmar", "não consta", "não confirma", "não foi processado", "sem processamento".
- **Caso 18 (P3-7):** `must_not_include` = "Android 14", "9 min", "Get Tap", "dados móveis". As respostas certas da bateria continuam passando.

### Bateria pelo `_checks` real (sem modelo)

- **Rodada 4:** 51 respostas, somando a bateria da rodada 3, as erradas listadas no parecer e novas certas.
  - Certas: 26/26 passam.
  - Erradas: 25/25 reprovam. Isso inclui "A taxa cobrada de R$ 15,75 não bate com o plano; houve cobrança a mais.", "Yes, you were overcharged… You will be refunded.", "Sim, o dinheiro já voltou para o cartão do cliente; o status é solicitado." e "Não pertence a você, mas aparece como Get Tap online em dados móveis."
- **Bateria da rodada 2 refeita:** 25/26. O único resíduo é "Não pertence a você, mas ela está ligada.", resposta mista do caso 18 que fica para o juiz, como aceito no parecer.

### Prompts

O critério desta vez não deu vazio:
- `git log --all --oneline 07ca28e.. -- prompts/` → um commit, o `868a07f`, "feat(hitl): interrupt and resume the flow by the operator (task 65)", do Time A, na branch `codex/v0.7.0-identidade-hitl`. Ele acrescenta `prompts/escalation.v2.md` e `prompts/personality.v4.md`; vi só os nomes, pelo `--name-status`, sem abrir os arquivos.
- `git log --oneline 07ca28e..main -- prompts/` → nenhum commit.

Leitura: é mudança de prompt da v0.7.0 (HITL), feita por quem não escreveu nem leu o holdout, e não é ajuste da v0.8.0. O RF-92 continua atendido. Registro o fato para o Supervisor decidir se a condição de lacre precisa citar a base `07ca28e..main`, em vez de `--all`.

### Evidência

- Suíte estrita (`--basetemp .pytest_cache/v080-b-strict`) → código 0, **357 aprovados**. O lacre confere com o hash novo.

### Próxima ação

O mesmo Reviewer revê na rodada 4 os casos 14, 15, 16 e 18 e o lacre.

## Tarefa 72a, rodada 5

- Papel e responsável: Developer do Time B, sobre o P3-8 do [parecer da rodada 4](v080-reviewer.md) (apto para QA) e a decisão do Supervisor de aplicá-lo antes do lacre definitivo.
- Escopo:
  - Segundos grupos dos casos 15 e 16 em `tests/scenarios/holdout_v080.jsonl`.
  - `holdout_v080.sha256`, a derivação, a tarefa e esta passagem.
  - Mensagens, ids, valores, teste, `evaluation/` e `prompts/` intocados.
- Base e versão final: base `aed374a`; commit único citando o hash novo `acb512cadcce37ed5d7f69c46053e8d389276a8559c77412b874b7306a0c66c8` (rodada 4: `11572812…eff1bac`).
- Independência: não-independente (relato do autor).

### Mudanças

- **Caso 15:** + "directly comparable", "not comparable". "check" e "flagged" ficaram de fora, porque reabririam respostas erradas. A certa "I've flagged it for the team to check" fica para o juiz, como no parecer.
- **Caso 16:** + "pendente de processamento", "não volta", "não voltou", "só acontece depois", "só ocorre depois", "após o processamento".

### Bateria pelo `_checks` real (sem modelo)

- **Rodada 5:** 55 respostas, a bateria da rodada 4 mais as quatro certas do P3-8.
  - Certas: 30/30 passam.
  - Erradas: 25/25 continuam reprovando.
- **Bateria da rodada 2:** 25/26. O resíduo continua sendo "Não pertence a você, mas ela está ligada.", aceito para o juiz.

### Evidência

- `git log --oneline 07ca28e..codex/v0.8.0-avaliacao -- prompts/` → nenhum commit.
- Suíte estrita (`--basetemp .pytest_cache/v080-b-strict`) → código 0, **357 aprovados**. O lacre confere com o hash novo.

### Próxima ação

O Reviewer faz a revisão curta dos casos 15 e 16 e do lacre. Em seguida, o Supervisor declara o lacre definitivo.

## Tarefa 72a, rodada 6

- Papel e responsável: Developer do Time B, sobre o [parecer da rodada 5](v080-reviewer.md). É a última rodada; nenhum outro termo mudou.
- Escopo:
  - Segundos grupos dos casos 15 e 16 em `tests/scenarios/holdout_v080.jsonl`.
  - `holdout_v080.sha256`, a derivação, a tarefa e esta passagem.
  - Mensagens, ids, valores, teste, `evaluation/` e `prompts/` intocados.
- Base e versão final: base `f1b2f9f`; commit único citando o hash novo `91aa51588afdf4afccb1ea8f230a47d3d61686004ec599f4c547e7881b4f1bac` (rodada 5: `acb512ca…0c66c8`).
- Independência: não-independente (relato do autor).

### Mudanças

- **Caso 15:** "directly comparable" foi trocado por "not directly comparable", "aren't directly comparable" e "isn't directly comparable". "not comparable" ficou.
- **Caso 16:** "após o processamento" saiu do segundo grupo.

### Bateria pelo `_checks` real (sem modelo)

- **Rodada 6:** 57 respostas, a bateria da rodada 5 mais as duas erradas novas do parecer ("O dinheiro já voltou ao cartão do cliente após o processamento; o status ainda aparece como solicitado." e "The legacy and standard fees are directly comparable: R$ 37,80 versus R$ 36,00, so you were overcharged.").
  - Certas: 30/30 passam, inclusive as quatro do P3-8 ("aren't directly comparable", "not comparable", "só acontece depois", "pendente de processamento").
  - Erradas: 27/27 reprovam.
- **Bateria da rodada 2:** 25/26. O resíduo é o misto do caso 18, aceito para o juiz.

### Evidência

- `git log --oneline 07ca28e..codex/v0.8.0-avaliacao -- prompts/` → nenhum commit.
- Suíte estrita (`--basetemp .pytest_cache/v080-b-strict`) → código 0, **357 aprovados**. O lacre confere com o hash novo.

### Próxima ação

O Reviewer faz a revisão final dos casos 15 e 16 e do lacre. Em seguida, o Supervisor declara o lacre definitivo.

## Tarefa 70

- Papel e responsável: Developer do Time B (subagente), despachado pelo Supervisor. Tarefa [70](../tasks/70-rubrica-juiz-independente.md); spec v0.8.0 D9, D11, D12, D13, D14, D16 e D19; plano, decisões 12 e 13 e "Modelo de dados".
- Escopo:
  - **Novos:** `prompts/judge.v3.md`; `evaluation/judge.py`, `evidence.py`, `aggregate.py`, `scripted_judge.py`; `tests/unit/evaluation/` (3 arquivos) e `tests/integration/test_eval_campaign.py`.
  - **Alterados:** `data/migrations.py` (0011), `evaluation/runner.py`, `evaluation/on_demand.py`, `cli.py`, `config.py`, `llm/prompts.py`, `tools/registry.py`, `.env.example`, a tarefa 70 e esta passagem.
  - **Testes ajustados:** os de migração, de versão de esquema e do avaliador padrão, listados em "Testes alterados fora da tarefa".
  - **Fora do escopo, intocados:** `orchestration/`, `agents/`, `api/`, `evaluation/scripted_policy.py`, `data/scenarios/catalog.json`, outros prompts, `tests/scenarios/` e o holdout. O worktree do Time A, `_tmp/` e `.env` (que nem existe no worktree) não foram abertos.
- Estado: implementada; em andamento até a revisão independente.
- Branch e PR: `codex/v0.8.0-avaliacao`, sem PR, sem push.
- Base e versão final: base `8f2baa6`; commits `75edaf2` (migração 0011), `dbb9d5b` (`judge.v3`, evidência, juiz independente), `8897809` (repetições, agregação, caminho executado, CLI), `c974e2c` (veredito crítico listado) e o commit desta passagem (SHA no retorno ao Supervisor). Árvore limpa depois dele.
- Independência: não-independente (relato do autor).

### O que a tarefa entrega

- **Migração 0011 (D13).** `run_evaluations` ganha `scores` (JSON), `repetition` (padrão 1) e `unsupported_claim` (0/1, com `CHECK`), mais o índice `run_evaluations_rubric`; nova tabela `calibrations`. `rubric_version` não foi acrescentada: já existe desde a 0008, assim como o `evaluator` (provedor e modelo). A descida preserva todas as avaliações, porque o `result` guarda o julgamento inteiro, e **recusa** (`RollbackRefused`, como a 0010) enquanto `calibrations` tiver nota humana, a única coisa que ninguém reconstrói. O formato de `calibrations` é o que a tarefa 71 grava: campanha, amostra, caso, rota, split, avaliador humano, notas, veredito e nota livre, único por (campanha, amostra, avaliador).
- **`judge.v3` (D9).** Quatro critérios 1–5 com justificativa (uma frase) e `unsupported_claim`, em `JudgeScoreV3`. A escala é validada no modelo, não no esquema, porque a saída estruturada estrita recusa limites numéricos; nota fora de 1–5 vira julgamento `failed`, nunca nota inventada. `judge.v2` continua carregável (`load_prompt(dir, "judge", "2")`) e a avaliação sob demanda de `/v1` ficou fixada nele: o web e a comparação de perfis leem `answers_question`/`clarity_and_tone`/`honesty`.
- **Evidência (D9).** A entrada do juiz traz a mensagem e a resposta, a rota, o status, os títulos das fontes e a lista `evidence` com os resultados das ferramentas e os trechos citados pelo Knowledge, tudo passado por `mask_sensitive` antes do corte. Limite de 6 000 caracteres no total; os itens curtos ficam inteiros e os longos dividem o que sobra, então um trecho longo não empurra um resultado de ferramenta para fora. O registro (`limit_chars`, `original_chars`, `kept_chars`, `items`, `items_cut`, `truncated`) vai dentro da entrada do juiz e na linha do relatório (`evidence_truncation`).
- **Juiz independente (D11).** Padrão `deepseek`/`deepseek-flash` (`config.py`, `.env.example`), pelo cliente DeepSeek que os perfis já usam. `resolve_judge` recusa, antes de construir o cliente e sem nenhuma chamada: par igual ao do agente; provedor sem saída estruturada (por exemplo `typesafe`); chave ausente ou vazia; modelo sem preço em `prices.json`. A mensagem diz o que fazer e termina com "No call was made." Em `eval`, a recusa vem antes de montar o sistema. Provedor, modelo, `model_used`, versão da rubrica e o tipo de independência (`different_provider` ou `same_provider_different_model`) ficam em cada julgamento e em `run_evaluations.evaluator`.
- **Repetições (D12).** `eval --repeat N` repete o agente e o juiz avalia cada resposta uma vez. `eval --judge-repeat N --answers-from <relatório.json>` julga N vezes as respostas da **primeira execução** do relatório, sem rodar o agente. As duas juntas são recusadas ("not combined"). Os relatórios guardam a evidência de cada resposta (`judge_input`) para a segunda etapa poder julgar de novo; `--repeat` sem `--judge` também a guarda.
- **Agregação e relatório.** `evaluation/aggregate.py`, por critério, rota e split, nos dois lados. Definições, para a revisão conferir: **média** de todos os scores do recorte; **desvio** = média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso; **concordância exata** e **±1** = parte dos **pares** de repetições do mesmo caso com score igual ou com diferença de até 1; para `unsupported_claim`, a taxa de verdadeiro e a concordância exata. Recortes com menos de 10 casos levam `*`. A seção traz a ressalva de amostra pequena (D19). O Markdown lista também, uma a uma, as respostas com `unsupported_claim` (nunca só a média), e o julgamento gravado leva isso como `critical_failures`.
- **D16.** Cada linha do runner tem `executed_path` (os agentes de `agents` menos `router` e `personality`, na ordem, por exemplo `knowledge → customer_support`); o relatório tem a tabela "rota planejada e caminho executado". `route_ok` não mudou: segue comparando a rota do Router com as aceitas. O campo no **trace** é do Time A (D18).
- **D14 e D17.** `--split holdout_v080` carrega `holdout_v080.jsonl` só quando pedido; `--split all` nunca o inclui; para esse split as conversas de dev não rodam. O relatório já separa por split (`by_split` no resumo e na variação).
- **Substituto programado** em módulo próprio (`scripted_judge.py`): regras fixas sobre a mesma entrada JSON (valor monetário da resposta que não está na evidência nem na pergunta derruba fundamentação e correção e liga o veredito). `eval --scripted --judge` agora funciona offline, a custo zero.
- **Persistência.** `eval --judge` grava cada julgamento em `run_evaluations` (principal `cli:eval`, que nenhuma sessão da API lista), no banco do runtime (`settings.db_path`; offline, o banco temporário). Isso dá um escritor às colunas novas e liga a amostra de calibração (71) ao julgamento por `request_id`.

### Decisões além do texto do plano

1. **Captura da evidência sem tocar o grafo.** O trace guarda só a chamada de uma ferramenta, não o dado, e do Knowledge guarda ids e um trecho de 400 caracteres. Para ler o dado, `tools/registry.py` ganhou uma lista `OUTCOME_OBSERVERS` (vazia em produção, 6 linhas) e o runner a registra durante cada caso. Os trechos citados vêm do corpus por `chunk_id` (texto inteiro, mesmo código de chunking do índice), com o trecho do trace como alternativa. `tools/` não está na lista do D18 nem tem outro dono no plano. **Pedido ao Supervisor para o Time A:** se o grafo passar a gravar `detail.evidence` no trace, o runner pode trocar a captura por essa leitura. Hoje o runner lê passos de trace chamados `knowledge`; um passo novo de busca web com outro nome precisa manter `detail.mode = "web"` ou avisar.
2. **O texto da busca web não é gravado em lugar nenhum.** Para respostas `general_web` o juiz recebe só os títulos das fontes e uma nota (`evidence_notes`) dizendo que o texto não está disponível. Uma resposta web pode ser marcada com mais rigor do que merece; a calibração humana é quem mede isso.
3. **O avaliador padrão mudou em `config.py`** (duas linhas existentes, não só acréscimo) de `openai`/`gpt-6-luna` para `deepseek`/`deepseek-flash`. Efeito colateral: a avaliação sob demanda de `/v1` (v0.6.0) usa as mesmas configurações e agora precisa de `DEEPSEEK_API_KEY` ou de `EVALUATOR_*` explícito; sem isso responde `503 evaluator_unavailable`. **O `.env` do responsável provavelmente ainda tem `EVALUATOR_PROVIDER=openai` e `EVALUATOR_MODEL=gpt-6-luna`** (era o `.env.example` da v0.6.0; não li o `.env`). Com isso, `eval --judge` recusa por ser o mesmo modelo do agente. O QA precisa trocar essas duas linhas (ou apagá-las). A linha da tabela de variáveis do `README.md` fica desatualizada: é do fechamento (73).
4. **Só o par idêntico é recusado.** Mesmo provedor com modelo diferente passa e fica registrado como `same_provider_different_model`. A spec D11 pede "de outro provedor quando houver chave" e permite "outro modelo do mesmo provedor, se o responsável aceitar"; se o responsável quiser exigir outro provedor, é uma linha em `check_independence`. O provedor do agente é a constante `AGENT_PROVIDER = "openai"` (o sistema real só monta o cliente OpenAI).
5. **`MAX_OUTPUT_TOKENS` do juiz = 400.** Quatro justificativas de até 25 palavras mais os scores cabem em cerca de 220 tokens; o teto é também a reserva por chamada no orçamento.
6. **A suíte da 72a quebrou com o merge da v0.7.0**, não por esta tarefa: `test_tool_backed_amounts_come_from_the_calls_of_each_case` montava um `CustomerContext` sem escopos, e a v0.7.0 falha fechado. Corrigi só a montagem do contexto (`CustomerContext.for_principal(Principal.merchant(...))`). O JSONL e o lacre não foram tocados.
7. **Entradas para o QA com o teto da campanha.** A CLI usa o guarda de orçamento do orquestrador (o primário) tanto para o agente quanto para o juiz. O teto `v080-qa` combinado (como no teste da v0.7.0) é montado por quem chama o runner; o juiz aceita o medidor depois (`judge.meter = BudgetMeter(orchestrator.budget)`), então um roteiro do QA que troque `orchestrator.budget` pelo guarda combinado usa `resolve_judge(...)`, `run(...)` e `rejudge(...)` diretamente.

### Testes alterados fora da tarefa

- `tests/unit/data/test_migrations.py`: listas de subida e descida com a 0011 (5 testes novos). `test_v060_api.py` (migração 0008, avaliador padrão), `test_v060_r2.py` (`INSERT` com colunas nomeadas, porque a tabela ganhou colunas), `test_v1_api.py` (descida até a 0006), `test_use_cases.py` (`/ready`, esquema 11).
- `tests/integration/test_v070_story.py`, **arquivo de trava do Time A (D18)**: uma linha, `versions["schema"] == 10` virou `== 11`. É consequência direta da 0011; avise o Time A para não reverter ao fazer o merge.
- Conflito provável no merge com o Time A: `cli.py` (`cmd_eval`, se eles acrescentarem `replan.jsonl` à lista de casos) e `config.py` (linhas do avaliador, ao lado de onde entrará `MAX_PLAN_HOPS`).

### Evidência

- Comandos: Python do worktree (`merchant_assistant.__file__` → `C:\workspace\ai-getnet-case-wt\time-b\src\merchant_assistant\__init__.py`), `-p no:cacheprovider`, `--basetemp .pytest_cache/t70-dev-<data>`, um pytest por vez. A suíte estrita completa não foi rodada: é do Supervisor.
- Resultados: `tests/unit`: **294 aprovados** (84 s). `tests/integration`, os 24 arquivos em quatro grupos, um pytest por vez: **80** (campanha 14, `test_evaluation_runner`, `test_v070_closing`, `test_v060_api`, `test_v060_r2`), **88** (`test_v1_api`, `test_use_cases`, `test_v070_story`, `test_v070_identity_r2`), **97** (conversas, KB, MCP, contrato, ticketing, `doc_effect`, `r4`) e **142** (handoffs, identidade, retomada, `review_gaps`, ticketing, webhooks): **407** na integração, sem falha. Total **701 testes aprovados**. Novos desta tarefa: 34 em `tests/unit/evaluation/`, 14 em `test_eval_campaign.py` e 5 em `test_migrations.py`. Depois desses grupos só mudou o teto de saída do juiz (600 para 400 tokens); `tests/unit/evaluation`, `test_eval_campaign.py` e `test_holdout_v080.py` foram reexecutados: 56 aprovados.
- `ruff check src tests`: sem achados. Lacre do holdout: `sha256sum tests/scenarios/holdout_v080.jsonl` → `91aa5158…`, igual ao `.sha256`; `git diff 8f2baa6..HEAD -- tests/scenarios` vazio; os 8 testes de `test_holdout_v080.py` verdes.
- Execução offline de ponta a ponta: `merchant-assistant eval --scripted --judge --repeat 2 --split dev --no-conversations --out <fora do repositório> --name demo` → 46 linhas, 46 julgamentos gravados, relatório com variação, ressalva D19, tabela de caminhos e lista de afirmações sem suporte; JSON de cerca de 250 KB (a evidência de cada resposta vai nele). Custo zero.
- Estimativa do juiz (a partir da evidência dessas 46 respostas, `deepseek-flash` na tabela): reserva média de **US$ 0,0010 por julgamento** (máximo 0,0015) com o teto de 400 tokens de saída, sem cache e com toda a saída reservada (com 600 tokens eram 0,0013). A campanha da spec (69 casos × 3 execuções, mais 3 julgamentos das respostas da primeira: cerca de 414 julgamentos) reservaria perto de **US$ 0,4 só no juiz**; o gasto real deve ficar bem abaixo (saída curta, instruções em cache), mas a conta do QA nos 5 casos medidos precisa incluir o juiz, não só o agente.

### Critérios

- **Comprovados localmente:** agregação e concordância com números fixos (fixtures de mão em `test_aggregate.py`); `judge.v3` programado devolve os quatro critérios e o veredito; evidência longa truncada, com o registro; juiz igual ao agente, sem chave, sem preço ou de provedor sem saída estruturada recusado antes de qualquer cliente ou chamada (a CLI não monta o sistema); migração 0011 sobe e desce com dados sintéticos e a descida é recusada com nota humana; `--repeat` e `--judge-repeat` separados, com a contagem de chamadas do agente e do juiz; `executed_path` sem mudar `route_ok`; `--split holdout_v080` por um split sintético em árvore temporária; lacre verde.
- **Não verificados (dependem de chamada paga, do QA):** `deepseek-flash` aceitar o esquema estruturado do `JudgeScoreV3` e `reasoning.effort = none` pela Responses API do DeepSeek (o mesmo caminho dos perfis, mas com este esquema); latência e custo reais do juiz; a qualidade do juiz com a evidência (calibração humana, tarefa 71); o texto real de busca web na evidência.

### Achados e limitações

- A evidência de respostas web é só títulos (decisão 2); a de conhecimento são os trechos citados, que podem ser menores do que o recuperado.
- O desvio é entre repetições do mesmo caso; a dispersão entre casos fáceis e difíceis não está nele. Com 3 repetições e poucos casos por recorte, as taxas de concordância têm passos largos (por exemplo, 1/3).
- Se a rota mudar entre repetições do agente, o recorte "por rota" usa a rota da primeira repetição do caso. A tabela de casos mostra a rota de cada linha, mas a agregação não separa isso.
- Os relatórios de campanha ficam maiores (evidência por resposta).
- `README.md` e `CHANGELOG.md` não foram alterados.

### Ação externa, identidade e próxima ação

- Ação externa: nenhuma (sem push, sem PR, sem rede, sem chamada paga). Commits locais com `lauroPereira <lauro.s.pereira@gmail.com>`, conferida antes de cada um.
- Próxima ação: Reviewer independente na tarefa 70. Pontos a pedir a ele: as definições de agregação acima; a regra de independência (decisão 4); o hook em `tools/registry.py` (decisão 1); a mudança do avaliador padrão e seu efeito na avaliação sob demanda (decisão 3). Depois, a tarefa 71 usa `calibrations` e as linhas `run_evaluations` do `cli:eval`.
- Decisão humana pendente: nenhuma bloqueante. Reversíveis para o relatório do Supervisor: avaliador padrão `deepseek-flash`; só o par idêntico é recusado; tabela `calibrations` com o formato acima.

## Tarefa 70, rodada 2

- Papel e responsável: Developer do Time B (subagente), sobre o [parecer da revisão independente, rodada 1](v080-reviewer-t70.md) do candidato `f3872d6` (correções necessárias: 1 P2 e 10 P3; o Supervisor decidiu o P2-01 pela opção (a) e pediu os P3-01 a P3-07).
- Escopo:
  - **Alterados:** `config.py`, `.env.example`, `main.py`, `data/migrations.py` (comentário e uma instrução na 0011), `tools/registry.py`, `evaluation/judge.py`, `evidence.py`, `aggregate.py`, `runner.py`, `scripted_judge.py`, `cli.py`, `prompts/judge.v3.md`, a tarefa 70 e esta passagem.
  - **Testes:** `test_judge_v3.py`, `test_judge_independence.py`, `test_migrations.py`, `test_eval_campaign.py`, `test_v060_api.py` e o arquivo novo `tests/integration/test_evaluator_settings.py`.
  - **Intocados:** `orchestration/`, `agents/`, `api/`, `scripted_policy.py`, `catalog.json`, `tests/scenarios/` e o holdout (lacre `91aa5158…` conferido), `.env`, o README.
- Estado: correções implementadas; em andamento até a revisão da rodada 2.
- Base e versão final: base `0ebcda2`; commit desta rodada citado no retorno ao Supervisor.
- Independência: não-independente (relato do autor).

### P2-01: avaliador sob demanda e juiz da campanha separados

- `EVALUATOR_PROVIDER`/`EVALUATOR_MODEL` voltam ao padrão da v0.6.0 (`openai`/`gpt-6-luna`). A avaliação sob demanda do `/v1` não pede chave da DeepSeek.
- O juiz da campanha tem `JUDGE_PROVIDER`/`JUDGE_MODEL`, padrão `deepseek`/`deepseek-flash`, com a mesma checagem de independência contra o agente. `resolve_judge` lê só essas variáveis, e as mensagens de recusa citam `JUDGE_*`. O `.env.example` volta ao bloco `EVALUATOR_*` da v0.6.0 e ganha o bloco do juiz, com comentário.
- **Efeito no `.env` do responsável:** o `.env` antigo (`EVALUATOR_*=openai/gpt-6-luna`) deixa de fazer o `eval --judge` recusar; ele só precisa de `DEEPSEEK_API_KEY`. A decisão 3 da rodada 1 (mudança do padrão do avaliador e aviso para trocar o `.env`) fica substituída por esta.
- `main.model_factory(settings)` é a fábrica de modelos que estava dentro de `build_orchestrator`, extraída sem mudar o comportamento; o orquestrador e o juiz a usam, e o teste do `/v1` a usa como o servidor real.
- **Testes** (`test_evaluator_settings.py`, 2): instalação só com `OPENAI_API_KEY`, fábrica real e cliente simulado: a estimativa responde 200, a confirmação 201 com `gpt-6-luna` e uma chamada simulada. O segundo teste põe um avaliador DeepSeek nessa instalação e vê `503 evaluator_unavailable`, a falha que o padrão da rodada 1 causava (prova de que o primeiro teste a pegaria). `eval --judge` numa instalação só com a chave da OpenAI recusa com `DEEPSEEK_API_KEY` na mensagem, antes de qualquer chamada: `build_orchestrator`, `openai_client` e `deepseek_client` trocados por funções que falham o teste se forem chamadas.

### P3

- **P3-01.** O julgamento grava `repetition` também no `result` (e, no julgamento que falhou, só ela). A subida da 0011 reconstrói `repetition`, `unsupported_claim` e `scores` a partir do `result` das linhas `rubric_version = '3'` (`json_extract`); as linhas do `judge.v2` ficam com os padrões. O comentário da migração diz isso. O teste faz subir, descer e subir com linhas v2, v3 (repetições 2 e 3, veredito falso e verdadeiro) e v3 que falhou, e confere os valores reconstruídos duas vezes, a integridade e as chaves estrangeiras.
- **P3-02.** `OUTCOME_OBSERVERS` é uma `ContextVar` com uma tupla de observadores; `record_tool_results` registra e restaura pelo token. Uma exceção de observador é registrada no log e não atravessa `execute()`, e os demais observadores continuam. Testes: duas threads com chamadas intercaladas por uma barreira, cada gravador só com as suas; observador que falha. O grafo copia o contexto para as threads que usa: os testes de ponta a ponta continuam vendo os resultados das ferramentas do caso de suporte.
- **P3-03.** `resolve_judge` confere o par na tabela de preços: o modelo precisa existir e ser do provedor configurado (`deepseek`/`gpt-6-luna` e `openai`/`deepseek-flash` são recusados), e precisa ter preço de saída (`openai`/`text-embedding-3-small`, que o parecer citou, é recusado). Tudo antes de construir o cliente.
- **P3-04.** O erro do provedor vai para `run_evaluations.error` e para o relatório como a classe e uma mensagem de uma linha, mascarada e com no máximo 160 caracteres (`short_error`). Teste com `Bearer sk-…`, `password:`, 400 caracteres e quebra de linha.
- **P3-05.** Testes novos para os sobreviventes: M11 e M12 (CPF, cartão e e-mail mascarados nas passagens do corpus e do trace e na mensagem do lojista); M28 (custo do agente zerado no relatório do juiz, com custo de origem diferente de zero, que o agente programado nunca tem); M32 (`--repeat` sem juiz seguido de `--judge-repeat`, pela CLI); M34 (os argumentos da ferramenta fazem parte da evidência).
- **P3-06.** O `judge.v3` ganha o parágrafo das `evidence_notes`: numa resposta de web, em que só os títulos das fontes chegam, não se baixa a fundamentação nem se liga `unsupported_claim` só porque falta um trecho; só se liga se a resposta contradiz as fontes, se contradiz a si mesma ou afirma detalhes da conta do lojista que nenhuma ferramenta mostra, e as justificativas dizem que o texto da web não estava disponível. A regra "sem evidência nenhuma, afirmação específica é sem suporte" passa a valer "e sem `evidence_notes`". O juiz programado segue a mesma regra. Como o prompt é lido por um modelo, o teste só prova que o texto está lá e que o substituto programado o segue. **Efeito esperado, a medir na campanha e na calibração:** menos respostas `general_web` marcadas como afirmação sem suporte; a taxa dessas respostas na campanha real é o indicador, e o responsável confere na amostra de calibração. Editei o `judge.v3` no lugar porque ele ainda não rodou em nenhuma campanha nem foi integrado; se o Supervisor preferir manter a regra de "prompt novo, versão nova", vira `judge.v4`.
- **P3-07.** Células de tabela passam por `aggregate.cell` (`|` vira `\|`, quebras de linha viram espaço) nos casos, nos caminhos, nas rotas e na justificativa das afirmações sem suporte. O Markdown resume o truncamento ("Evidência truncada em X de N respostas"). O nome padrão do relatório de `--split holdout_v080` é `avaliacao-holdout-v080`, e o de `--judge-repeat` é `avaliacao-juiz`; `--name` explícito vale sempre. `--judge-repeat` recusa, antes de julgar, um nome que sobrescreveria o arquivo `--answers-from`. `--split` diferente de `all` com `--judge-repeat` avisa no erro padrão que é ignorado.
- **P3-08, P3-09, P3-10.** Sem mudança, como decidido.

### Evidência

- Python do worktree, `-p no:cacheprovider`, `--basetemp .pytest_cache/t70-dev-<data>`, um pytest por vez; a suíte estrita completa não foi rodada.
- `tests/unit`: **304 aprovados** (84 s). `tests/integration`, os 25 arquivos em quatro execuções: **161** (v0.6.0, `/v1`, runner, fechamento v0.7.0, casos de uso, identidade r2), **21** (campanha 19 e avaliador 2), **88** (conversas, KB, MCP, contrato, ticketing, `doc_effect`) e **144** (handoffs, identidade, retomada, história, ticketing, webhooks): 414. Total **718 aprovados**, sem falha.
- Novos ou reescritos nesta rodada: 44 testes em `tests/unit/evaluation/` (eram 34), 19 em `test_eval_campaign.py` (eram 14), 2 em `test_evaluator_settings.py`, 22 em `test_migrations.py` (um reescrito).
- ruff `check src tests` sem achados. Lacre do holdout: `sha256sum tests/scenarios/holdout_v080.jsonl` → `91aa5158…`; `git diff 8f2baa6..HEAD -- tests/scenarios` vazio; `test_holdout_v080.py` verde. Nenhuma chamada paga, nenhuma rede.

### Para o Supervisor

- README: a linha de `EVALUATOR_PROVIDER`/`EVALUATOR_MODEL` (`openai`, `gpt-6-luna`) volta a estar correta; falta acrescentar `JUDGE_PROVIDER`/`JUDGE_MODEL` (`deepseek`, `deepseek-flash`) na tabela, no fechamento (73).
- Reversíveis: separação em duas variáveis (a) em vez de uma; `judge.v3` editado no lugar; modelo sem preço de saída recusado como juiz.
- Não verificado (chamada paga, do QA): efeito do parágrafo das notas de evidência no juiz real; esquema estruturado do `JudgeScoreV3` na DeepSeek.

## Tarefa 70, P3 da rodada 2

- Papel e responsável: Developer do Time B (subagente), sobre os quatro P3 registrados no [parecer da revisão da 70, rodada 2](v080-reviewer-t70.md) (apto para QA; o Supervisor mandou os quatro entrarem antes da calibração, em commit próprio). O README fica para o fechamento (73).
- Escopo:
  - **Alterados:** `cli.py` (texto de ajuda do `eval --judge` e `--name`; `_report_name`; a ordem de `cmd_eval_rejudge`), `evaluation/evidence.py`, `evaluation/scripted_judge.py`, `evaluation/runner.py` (`summarize` e `write_report`).
  - **Testes:** `tests/unit/evaluation/test_judge_v3.py` (7 testes, 4 deles um só parametrizado) e `tests/integration/test_eval_campaign.py` (3).
  - **Intocados:** `orchestration/`, `agents/`, `api/`, `evaluation/scripted_policy.py`, `catalog.json`, prompts (inclusive `judge.v3`), `tests/scenarios/` e o holdout (lacre `91aa5158…4f1bac` conferido por `sha256sum`, sem abrir o conteúdo).
- Base e versão final: base `69f2fca`; este commit.
- Independência: não-independente (relato do autor).

### O que mudou

- **(A) `--help`.** `eval --judge` diz que o juiz é definido por `JUDGE_PROVIDER` e `JUDGE_MODEL` (padrão `deepseek/deepseek-flash`), que isso exige `DEEPSEEK_API_KEY` e que a recusa vem antes de qualquer chamada quando o juiz é igual ao agente ou falta a chave. Nenhuma menção a `EVALUATOR_*` (teste). O `--name` descreve o novo padrão do item B.
- **(B) Nome do relatório do `--judge-repeat`.** `_report_name(args, answers_split)`: o padrão é `avaliacao-juiz` e, quando as respostas gravadas pertencem a um único split, o split entra no nome (`avaliacao-juiz-dev`, `avaliacao-juiz-holdout`, `avaliacao-juiz-holdout-v080`). Respostas de vários splits (`--split all`) mantêm `avaliacao-juiz`. O split vem das linhas das respostas gravadas, não de `--split` (que o `--judge-repeat` ignora). `--name` explícito vale sempre. Para isso `cmd_eval_rejudge` passou a carregar as respostas antes de calcular o nome; a recusa de sobrescrever o arquivo de origem continua antes de qualquer julgamento.
- **(C) Juiz programado sob a nota de web.** Sob `evidence_notes`, um valor em R$ da resposta que não tem a ver com a conta do lojista (ex.: tarifa pública) continua sem rebaixar; mas valor dito sobre a conta do lojista ("seu saldo", "sua agenda", "your balance"…) só é aceito se a mensagem ou **um resultado de ferramenta** o mostrar. Um trecho de página não sustenta valor da conta. Sem a nota, a regra é a de antes (mensagem e toda a evidência). É um substituto determinístico da regra do prompt (`_ACCOUNT`, lista curta de palavras em português e inglês), não uma leitura de significado. O relatório ganhou `summary.overall.judge_web_note` (`judged_answers`, `answers` sob a nota, `unsupported` entre elas) e a linha "Respostas julgadas sob a nota de busca web: X de N", com quantas foram marcadas como afirmação sem suporte; aparece sempre que há julgamento (zero incluído) e não aparece sem juiz.
- **(D) Passo `web`.** `evidence.py` lê os passos `knowledge` e `web`: um passo chamado `web` levanta a nota de web com ou sem `detail.mode`; `detail.mode == "web"` em qualquer passo de leitura continua levantando. A nota sai uma vez só, e as passagens citadas antes do passo `web` continuam na evidência. Passos de outros nomes (`router`, `websearch`) não levantam nada.

### Testes e evidência

- Python do worktree (`merchant_assistant.__file__` → `time-b\src`), `-p no:cacheprovider`, `--basetemp .pytest_cache/t71-dev-<hora>`, um pytest por vez.
- `tests/unit/evaluation` + `tests/integration/test_eval_campaign.py` + `tests/unit/test_holdout_v080.py`: **81 passed**. `test_evaluation_runner`, `test_evaluator_settings` e `test_cli_index_guard`: **51 passed**. `ruff check src tests/...`: sem achados nos arquivos alterados.
- Mutação: 10 mutantes (passo `web` fora da tupla, fora da condição; juiz programado sem a regra da conta, aceitando trecho como apoio, ou sinalizando todo valor; nome sem split, com o split do CLI; contagem de web zerada; contagem de marcadas zerada; ajuda ainda citando `EVALUATOR_`): **10 mortos**.
- O teste de web com conta cobre os quatro casos: valor da conta sem ferramenta (marcado), com resultado de ferramenta (não), dito pelo próprio lojista (não) e apoiado só por trecho (marcado); e o par "valor público sob a nota (não) × sem a nota (sim)".

### Limites

- A regra da conta no substituto programado é lista de palavras; o juiz real decide pelo prompt, que o `judge.v3` já tem. Efeito no juiz real continua para o QA e a calibração.
- Nada de chamada paga nem de rede.

## Tarefa 71

- Papel e responsável: Developer do Time B (subagente), despachado pelo Supervisor. Tarefa [71](../tasks/71-calibracao-humana.md); spec v0.8.0 D10, D12, D14, D16 e D19; RF-91 e CA-50 da spec 0.2; plano, decisão técnica 14.
- Objetivo e critérios: gerar uma amostra de respostas para o responsável avaliar com a rubrica do juiz, sem ver os scores dele, e calcular a concordância humano × juiz por critério. Critérios da tarefa: CSV sem nenhum score do juiz (teste procura os valores); kappa e concordâncias com números fixos e casos de borda; CSV malformado com erro claro e a linha; nenhuma chamada paga. A marcação é do Supervisor.
- Escopo:
  - **Novos:** `src/merchant_assistant/evaluation/calibration.py`; `tests/unit/evaluation/test_calibration.py` (57 testes); `tests/integration/test_calibration_flow.py` (5); `docs/evidence/v080-calibracao-modelo.md` (formato do relatório, com dados inventados).
  - **Alterados:** `cli.py` só por acréscimo (`cmd_eval_calibrate`, o subcomando `eval-calibrate` e a entrada em `handlers`; 78 linhas, nenhuma removida), a tarefa 71 (Validação e Status) e esta passagem.
  - **Intocados:** `orchestration/`, `agents/`, `api/`, `scripted_policy.py`, `catalog.json`, todos os prompts, `config.py`, `migrations.py` (a tabela `calibrations` é a da 0011, sem mudança), `tests/scenarios/` e o holdout (lacre `91aa5158…4f1bac` conferido por `sha256sum` e pelo teste, sem abrir o conteúdo), `_tmp/`, `.env`, o checkout principal e os outros worktrees.
- Estado: implementada; em andamento até a revisão independente.
- Branch e PR: `codex/v0.8.0-avaliacao`, sem PR, sem push.
- Base e versão final: base `3598a48` (P3 da rodada 2 da tarefa 70); versão final é o commit desta tarefa (SHA no retorno ao Supervisor).
- Independência: não-independente (relato do autor).

### Como o responsável e o QA usam

1. Depois da campanha real (`eval --judge`, que grava os julgamentos no banco do runtime), sortear a amostra: `merchant-assistant eval-calibrate --sample 24 --from docs/evidence/<relatório da campanha>.json`. Escreve `docs/evidence/v080-calibracao-amostra.csv` (ou `--out`); o responsável preenche as colunas em branco.
2. Importar no mesmo banco em que a campanha gravou os julgamentos: `merchant-assistant eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv --rater <nome>`. Grava em `calibrations` e escreve `docs/evidence/v080-calibracao.md` (ou `--out`).

O relatório de origem precisa ter a evidência das respostas (campanha com `--judge` ou `--repeat`). A amostra sai da **primeira execução** do relatório. Uma campanha `--scripted` grava os julgamentos num banco temporário que se perde; só a campanha real pode ser importada. Para o `holdout_v080` (D14, D17), que o QA roda à parte, o QA pode sortear outra amostra do relatório dele (`--campaign` dá outro nome); a escolha é do Supervisor.

### O que a tarefa entrega

- **Amostra (`--sample N --from`).** Balanceada por estrato (rota, split): uma resposta de cada estrato por vez, na ordem que só a semente decide, até completar N (todo estrato aparece antes de algum aparecer duas vezes). Com 24 e os estratos de uma campanha típica cada rota e cada split entram; um estrato raro não é pulado, como seria numa amostra proporcional. A ordem usa SHA-256 de `semente|papel|chave`, não o gerador do Python, então o mesmo relatório e a mesma semente dão o mesmo CSV em qualquer versão. A lista final sai embaralhada pela semente, sem agrupar por rota. Elegíveis: primeira execução, com a evidência gravada e julgamento completo. Se houver menos que N, leva todos; menos de 24 avisa no erro padrão (RF-91).
- **CSV.** UTF-8 com BOM, separador `;` (padrão), 10 linhas de instruções em português que começam com `#`, uma linha `# amostra: campanha=…; semente=…; origem=…; sorteadas=…; pedidas=…; elegiveis=…; rubrica=judge.v3`, o cabeçalho e uma linha por resposta: `sample_id` (S01…), `route`, `split`, `status`, `message`, `answer`, `sources`, `evidence`, as colunas do avaliador (`groundedness`, `factual_correctness`, `relevance`, `usefulness`, `unsupported_claim`, `note`; vazias) e, ao final, `request_id` e `case_id`. As instruções trazem a rubrica dos quatro critérios 1-5 e o veredito, com as mesmas definições do `judge.v3`, a regra do resultado de ferramenta e a da nota de busca web.
- **Sem o juiz.** `sample_rows` lê só `judge_input` (a entrada que o juiz recebe) e os rótulos da linha (`route`, `split`, `id`, `request_id`). O registro `judge` do relatório não é lido em lugar nenhum além do filtro de elegibilidade (`state == completed`).
- **Importação (`--import`).** Valida tudo antes de gravar, mostra os problemas juntos (até 25) com a linha física e o `sample_id`. Meio preenchida é erro; vazia é pulada; nada é gravado se uma linha estiver errada ou sem julgamento. Ligação ao julgamento: `run_evaluations` com a mesma `request_id`, principal `cli:eval`, rubrica `judge`, `state = completed`, `repetition = 1`, com `scores`, o mais antigo (a campanha, não uma reavaliação posterior da mesma resposta). Importar o mesmo arquivo atualiza as linhas.
- **Medidas.** Por critério: exata, ±1, kappa quadrático ponderado, médias e viés. Veredito: exata, kappa e tabela 2×2. Intervalos de 95%: Wilson (fórmula fechada) para as proporções e bootstrap com semente (2 000 reamostragens das respostas) para o kappa. Definição do kappa: `1 - observado/esperado`, peso `((a-b)/4)²`, esperado pelas marginais das duas séries; as categorias são sempre 1 a 5 (0 e 1 no veredito), não as que apareceram.
- **Relatório.** Markdown em português: cabeçalho com campanha, avaliador, rubrica, juiz, semente e contagens; ressalva de amostra pequena (D19); tabela por critério; veredito; casos de borda do kappa; divergências de 2 pontos ou mais ou veredito oposto; cobertura por rota e split; "Como ler".

### Decisões além do texto do plano

1. **Separador `;` e BOM.** O responsável usa Windows em português: o Excel pt-BR só separa as colunas com `;` e só lê acentos de UTF-8 com BOM. `--delimiter ,` troca o separador do arquivo gerado, e a importação aceita `;`, `,` e tabulação pelo cabeçalho. Reversível: uma linha.
2. **Amostra balanceada, não proporcional.** Com 24 de ~69 casos em ~10 estratos, a proporcional deixaria rotas raras de fora e a calibração dessas rotas (web, encaminhamento) seria cega. O custo: o conjunto sorteado não reproduz as proporções da campanha; o relatório lista a cobertura. Reversível trocando o laço de `draw_sample`.
3. **Ordem por hash.** Para a semente valer entre versões do Python e máquinas.
4. **`request_id` e `case_id` no CSV.** São identificadores, não notas; `request_id` é o elo com o julgamento (a instrução diz para não apagar). Quem abrir o banco pode achar a nota do juiz; a regra vale para o arquivo.
5. **A evidência é resumo de 2 000 caracteres**, não os 6 000 do juiz, como o texto da tarefa pede ("evidências resumidas"); a instrução diz isso e que `[...cut]` marca corte. Se o responsável precisar do trecho todo para decidir, a linha tem `request_id` para buscá-lo no relatório JSON da campanha. Mudar o limite é uma constante.
6. **Mensagens de erro em português** (o leitor é o responsável preenchendo a planilha); o resto da CLI segue em inglês.
7. **Sem UTF-8, recusa** com a instrução "salvar como CSV UTF-8", em vez de adivinhar a codificação e gravar texto torto.
8. **Kappa sem intervalo quando um lado não varia** (toda reamostra daria 0): o relatório diz "sem intervalo" e explica na seção de bordas. Com uma linha ou duas séries constantes e iguais, "n/d".
9. **Modelo do relatório** em `docs/evidence/v080-calibracao-modelo.md`, gerado pelo mesmo código sobre 48 respostas e um avaliador inventados, com a faixa de aviso no topo; o relatório real não se chama assim.
10. **Importação no banco do runtime.** `calibrations` está no banco onde `eval --judge` real grava os julgamentos; `--import` se recusa a criar um banco que não existe.

### Evidência

- Python do worktree (`merchant_assistant.__file__` → `time-b\src`), `-p no:cacheprovider`, `--basetemp .pytest_cache/t71-dev-<hora>`, um pytest por vez; a suíte estrita completa não foi rodada.
- `tests/unit`: **368 aprovados** (117 s); novos: 57 de calibração e 7 dos P3. Integração: `test_eval_campaign` (22), `test_calibration_flow` (5), `test_evaluation_runner`, `test_evaluator_settings`, `test_v060_api` e `test_v060_r2`: **88 aprovados** (135 s). ruff `check src tests` sem achados.
- Números conferidos à mão no teste: `[1,2,3,4,5]` × `[1,3,3,4,4]` → exata 0,6, ±1 1,0, kappa 0,875; 12 notas → exata 7/12, ±1 1,0, kappa 0,8404; um lado constante → 0; pior caso → -1; Cohen em 8 pares → 0,5; Wilson 24/24 → 0,862 a 1,0 e 12/24 → 0,314 a 0,686; mais 400 séries aleatórias contra a fórmula `1 - N·Σd² / Σ(aᵢ-bⱼ)²`.
- Mutação: 35 mutantes de `calibration.py` (pesos do kappa, bordas, Wilson, bootstrap, balanceamento, semente, ordem, máscara, BOM, nota de web, validação de faixa e de veredito, duplicados, número da linha, colunas a mais, repetição, principal e rubrica do julgamento, upsert, mais antigo, `scores` nulo, resumo de evidência, três formas de vazar o juiz para o arquivo, tabela do veredito, sinal do viés, limiar das divergências, ressalva, intervalo sem variação) e 10 de `cli.py` (modos exclusivos, `--from`, banco ausente, caminhos padrão, aviso de amostra curta, truncamento de erros, avaliador, semente, registro do subcomando): **45 mortos** (a rodada final do módulo, sem cache de bytecode, repetiu os 35). Na primeira passada sobreviveram 4 (repetição, upsert, mais antigo e `scores` nulo); os testes eram fracos (a nota do exemplo já valia o valor novo; o horário de criação deixava o desempate ao relógio, e esse era intermitente), reforcei e rodei de novo.
- Execução de ponta a ponta fora dos testes: campanha programada de 40 casos, amostra de 24, notas inventadas, importação e relatório pelo código real (descartável; serviu para ler o formato).
- Nenhuma chamada paga, nenhuma rede, `.env` não lido.

### Critérios

- **Comprovados localmente:** CSV sem nenhum score do juiz (teste procura os valores nas formas JSON, `chave=valor`, `chave: valor` e `chave;valor`, a justificativa, o identificador, o modelo e o provedor do juiz, e confere as colunas vazias); kappa e concordâncias com números fixos e casos de borda (todos iguais, uma linha, sem variação, pior caso); CSV malformado com a linha e o `sample_id` (a linha é a física do arquivo, mesmo com células de várias linhas); importação ligada por `request_id` ao julgamento; relatório com a ressalva D19 e intervalos; a descida da 0011 recusada depois de uma importação.
- **Não verificados:** planilha real do responsável (Excel pt-BR, LibreOffice); amostra e juiz de uma campanha real; leitura do relatório pelo responsável.

### Achados e limitações

- Com 24 respostas e ~10 estratos, cada recorte tem 2 a 4 casos: o relatório não calcula concordância por rota ou split, só mostra a cobertura. O kappa fica instável quando quase todas as notas são 4 ou 5; as três medidas aparecem juntas por isso.
- O CSV tem cerca de 40 KB por 24 linhas (resposta e evidência em texto), com células de várias linhas; o Excel mostra tudo numa linha, a menos que se ative a quebra de texto.
- A importação compara com o julgamento da **repetição 1** do `cli:eval`; as demais repetições do juiz (`--judge-repeat`) não entram na calibração.
- A ligação é por `request_id` no banco do runtime. Se a campanha rodou em outra máquina, o banco dela precisa estar disponível na importação.
- Uma amostra tirada de um relatório que inclua o `holdout_v080` mostra essas respostas ao responsável. Isso não vaza nada para ajuste (ele não ajusta prompts), mas D17 pede que o holdout seja visto uma vez; incluí-lo ou não na amostra é decisão do Supervisor.

### Ação externa, identidade e próxima ação

- Ação externa: nenhuma (sem push, sem PR, sem rede, sem chamada paga). Commits locais com `lauroPereira <lauro.s.pereira@gmail.com>`, conferida antes de cada um.
- Próxima ação: Reviewer independente nas tarefas 71 e P3 da 70 (commits `3598a48` e o desta tarefa). Depois o QA roda a campanha `v080-qa`, sorteia a amostra e entrega o CSV ao responsável; o merge local da v0.8.0 espera a calibração dele (spec, execução confirmada 4).
- Decisão humana pendente: nenhuma bloqueante. Reversíveis para o relatório do Supervisor: separador `;` e BOM; amostra balanceada; `request_id` visível no CSV; resumo de 2 000 caracteres de evidência.

## Tarefa 71, rodada 2

- Papel e responsável: Developer do Time B (subagente), sobre o [parecer da revisão da 71](v080-reviewer-t71.md) (candidato `31aac33`, apto para QA, 9 P3). O Supervisor mandou os P3 1 a 6 e 8 antes do QA; o 7 e o 9 ficam sem mudança.
- Escopo:
  - **Alterados:** `src/merchant_assistant/evaluation/calibration.py`; `cli.py` (só `cmd_eval_calibrate` e o subparser do `eval-calibrate`: a opção `--split` e as mensagens); `tests/unit/evaluation/test_calibration.py` (57 para 72 testes); `tests/integration/test_calibration_flow.py` (5 para 7); `docs/evidence/v080-calibracao-modelo.md` (regerado: o texto da amostra); a tarefa 71 e esta passagem.
  - **Intocados:** `orchestration/`, `agents/`, `api/`, `scripted_policy.py`, `catalog.json`, prompts, `config.py`, `migrations.py`, `tests/scenarios/` e o holdout (lacre `91aa5158…4f1bac` conferido por `sha256sum`, sem abrir o conteúdo), `.env`, `_tmp/`, o checkout principal e os outros worktrees.
- Estado: correções implementadas; em andamento até a revisão da rodada 2.
- Branch e PR: `codex/v0.8.0-avaliacao`, sem PR, sem push.
- Base e versão final: base `d11c503` (registro da revisão); versão final é o commit desta rodada (SHA no retorno ao Supervisor).
- Independência: não-independente (relato do autor).

### Os P3

1. **Amostra só de desenvolvimento (decisão do Supervisor).** `DEVELOPMENT_SPLITS = (dev, holdout)`: `load_source` só devolve respostas desses splits e conta o que deixou de fora, por split. Escolhi **excluir com aviso** em vez de recusar: um relatório de campanha pode legitimamente trazer linhas `holdout_v080` (o QA roda o split à parte, mas pode reunir relatórios), e recusar tiraria do QA o jeito de sortear a amostra do mesmo arquivo. A recusa fica para quando não sobra nada (relatório só com `holdout_v080`: "não entra na calibração"). `eval-calibrate --sample` ganhou `--split {development,dev,holdout}` (padrão `development`, que é `dev` + `holdout`): só estreita, e o `holdout_v080` não é uma opção (o argparse recusa com código 2; `make_sample` também recusa o nome). A linha `# amostra:` do CSV registra `splits=dev+holdout`, e o erro padrão diz quantas respostas de cada split ficaram de fora ("the holdout_v080 is never sampled, D17"). A importação não mudou.
2. **Reimportação não troca a amostra em silêncio.** `check_same_sample`: se o `sample_id` já gravado para (campanha, avaliador) tem outra `request_id`, a importação inteira é recusada, antes de qualquer escrita, com uma mensagem por linha: a linha, o `sample_id`, as duas requisições e a saída ("importe-a com `--campaign <outro nome>` (ou gere a amostra com `--campaign`) para guardá-la separada; nada foi alterado"). Com `--campaign` outro nome as duas amostras convivem. A chave única (campanha, amostra, avaliador) da 0011 não mudou.
3. **Linha esvaziada: retira a nota.** Escolhi **remover do banco**, e não manter a nota antiga e contá-la no relatório, porque o arquivo é a declaração do avaliador sobre a amostra (é o que a guarda da 0011 chama de fonte) e porque assim o banco, o arquivo e o relatório dizem a mesma coisa. Cuidados: só retira a nota da mesma `request_id` (a de outra requisição não se toca); um arquivo sem nenhuma linha avaliada continua recusado, então uma planilha em branco reimportada por engano não apaga nada; tudo na mesma transação das gravações; a CLI diz "N removed" e o relatório lista "Notas retiradas do banco por linha esvaziada neste arquivo (o arquivo é a fonte): S05". Conferido de ponta a ponta: banco com 22 linhas, relatório com n = 22. O caso vizinho (notas gravadas antes que não estão no arquivo, por exemplo linhas apagadas da planilha) também aparece: no relatório ("continuam no banco e não entram nestes números") e no erro padrão; elas ficam como estão.
4. **Dois `sample_id` com o mesmo `request_id`:** erro de validação com a linha ("request_id repetido (já aparece na linha N)"), como já era com o `sample_id` repetido.
5. **Intervalo do kappa.** O bootstrap só devolve intervalo se no máximo 10% das 2 000 reamostras ficarem sem kappa (`MAX_UNDEFINED_SHARE`) e se o intervalo tiver largura: um acordo perfeito continua perfeito em toda reamostra, e "1,00 a 1,00" não mede dúvida nenhuma. Nos dois casos o relatório escreve "1.000 (sem intervalo)" e lista na seção de bordas "sem intervalo do kappa: reamostras demais sem kappa definido, ou todas com o mesmo valor (série degenerada); leia a concordância exata". Corte conferido em séries de 24: 12% sem kappa (duas linhas diferentes) fica sem intervalo; 4% (três) mantém.
6. **Lacunas de teste do parecer.** Embaralhamento final da amostra (as três rodadas de oito estratos não saem em fileira); o CSV sai byte a byte igual quando mudam todos os campos do juiz (notas, veredito, justificativas, ids, modelo, provedor, repetições), com a coluna `status` igual ao status da resposta; atualização do veredito, da nota livre, das notas e do `evaluation_id` ao reimportar (a mesma linha é atualizada, o `calibration_id` não muda; a nota pode ser apagada); `ROLLBACK` (uma conexão que falha na quinta gravação deixa o banco vazio e sem transação aberta, e as mesmas gravações funcionam depois); o rótulo "95%" em todas as células de intervalo e a constante do Wilson. Não tenho a lista de mutantes do Reviewer (S4, L7, L8, I4, U1b, U3): reproduzi cada lacuna descrita com mutantes meus, abaixo.
7. **P3-8: o relatório diz que a amostra é balanceada e não ponderada**, no parágrafo do cabeçalho ("balanceadas por estrato de rota e split, sem ponderar pelo tamanho de cada um") e numa linha de "Como ler" ("não ponderada … as médias e as concordâncias valem para estas respostas e não estimam as da campanha inteira").
8. **De passagem:** os dois `lstrip` do BOM no leitor traziam o caractere invisível U+FEFF no código-fonte; agora são `"﻿"`.

### Evidência

- Python do worktree (`merchant_assistant.__file__` → `time-b\src`), `-p no:cacheprovider`, `--basetemp .pytest_cache/t71r2-dev-<hora>` (apagado depois de cada execução), um pytest por vez; a suíte estrita completa não foi rodada.
- `tests/unit/evaluation` + `test_holdout_v080` + `test_migrations`: **153 aprovados** (41 s); `test_calibration` sozinho: 72 (eram 57). Integração: `test_calibration_flow` (7, eram 5), `test_eval_campaign` e `test_evaluation_runner`: **58 aprovados** (68 s). ruff `check src tests` sem achados. Lacre `91aa5158…` igual ao `.sha256`; `git status -- tests/scenarios` vazio.
- Mutação: 29 mutantes novos no módulo (embaralhamento, status e ordenação pelo juiz, cada campo do upsert, rollback, rótulos "95%", split selado como opção, contagem do que ficou de fora, verificação de outra amostra, esvaziamento, retirada sem conferir a requisição, `request_id` repetido, cortes de 2% e 50% do intervalo, intervalo sem largura, nota do intervalo, declarações de balanceamento, lista de notas fora do arquivo, linha de splits, split inválido, relatório só com o selado) e 6 na CLI (aviso do que ficou de fora, `--split` ignorado, opção selada no parser, "removed", aviso das notas fora do arquivo, padrão do parser): **35 mortos**, rodados sem cache de bytecode. Os da rodada 1 (45) valem, e os testes só ganharam asserções.
- Disco: apaguei só o que eu criei: `.pytest_cache/t71-dev-*` da rodada 1, os `t71r2-dev-*` desta (um por execução, e o do laço de mutação, que agora apaga o seu a cada mutante) e os diretórios de rascunho `probe*`, `dbg*` e `modelo*` do `%TEMP%`. Nenhuma cópia grande.
- Nenhuma chamada paga, nenhuma rede, `.env` não lido.

### Limites e próxima ação

- Quem não passa `--split` continua sorteando de `dev` + `holdout`; a escolha entre incluir ou não o `holdout` antigo (de 2026-10) fica com o Supervisor.
- A retirada por linha esvaziada é destrutiva por desenho (só da nota da mesma requisição); o responsável precisa saber que esvaziar uma linha e reimportar apaga a nota dela. A mensagem da CLI e o relatório avisam.
- Não verificados: planilha real; campanha real.
- Próxima ação: nova revisão curta da rodada 2; depois o QA da campanha `v080-qa`.
- Decisão humana pendente: nenhuma. Reversíveis: retirada em vez de manter; exclusão com aviso em vez de recusa; corte de 10% do intervalo.

## Tarefas 75, 76 e 77 (defeitos do QA r4 e contingência)

- Papel e responsável: Developer do Time A (subagente), despacho do Supervisor de 2026-11-05 para as tarefas [75](../tasks/75-rotulo-literal-price-insufficient-v080.md), [76](../tasks/76-encerramento-contrato-pede-esclarecimento-v080.md) e [77](../tasks/77-teto-contingencia-v080-qa.md), nesta ordem, depois do [parecer do QA r4](v080-d12-pre-holdout-r4.md).
- Objetivo e critérios:
  - 75: aceitar as quatro respostas corretas de `PRICE-INSUFFICIENT` sem aceitar contradições.
  - 76: encaminhar a humano o pedido explícito de encerramento do contrato em todas as repetições.
  - 77: permitir o cap de contingência US$1,40 só para continuar a `v080-qa`, com transição ensaiada em cópia.
- Escopo:
  - **75:** `tests/scenarios/business_journeys.jsonl` (2 linhas), `tests/unit/evaluation/test_t75_price_insufficient_archived.py` (novo), tarefa 75.
  - **76:** `src/merchant_assistant/agents/router.py` (regra em `enforce`), `tests/unit/test_t76_contract_termination.py` (novo), tarefa 76.
  - **77:** `src/merchant_assistant/cli.py` (só `_evaluation_budget_guard`, a constante e o argparse do `--campaign-cap-usd`), `src/merchant_assistant/orchestration/budget.py` (`FixedBudgetGuard`), `tools/scripts/v080_contingency_transition.py` (novo), `tests/unit/test_t77_contingency_cap.py` (novo), tarefa 77.
  - **Intocados:** `prompts/` (nenhum `router.v7`), `data/scenarios/catalog.json`, `orchestration/graph.py`, `scripted_policy.py`, o holdout e o `.sha256` dele (lacre LF `91aa5158…4f1bac` conferido sem abrir o conteúdo), `data/runtime/` (só lido para a cópia), `.pytest_cache/qa-v080-r1/`, `.env`, `_tmp/`, `Claude outputs/`, `v/`.
- Estado: implementadas; em andamento até a revisão independente. A 77 também espera a aplicação pelo Supervisor.
- Branch e PR: `codex/v0.8.0-replan`, sem PR, sem push.
- Base e versão final: base `0e3f702`. Commits: 75 `d972dd0`; 76 `a9651f7`, sobre `d972dd0`; 77 `94bf7b3`, sobre `a9651f7`. Esta passagem e a validação das tarefas vão num commit só de docs sobre `94bf7b3`.
- Independência: não-independente (relato do autor).

### Tarefa 75: rótulos e justificativa por caso (D15)

As quatro respostas estão corretas. A venda de crédito em 2 parcelas de 02/11/2026 não tem regra de preço aplicável nem cobrança registrada (`simulate_pricing` devolve evidência insuficiente). Cada resposta diz isso sem afirmar que a taxa está certa ou errada, e o juiz deu 5 ou 4 em todos os critérios, sem afirmação sem suporte. Em cada caso, a forma acrescentada é a frase da própria resposta:

| `request_id` | Resposta (trecho) | Acrescentado em `must_include_any` |
|---|---|---|
| `req_evalbccfe360ff22` (EN, rep. 1) | "no fee rule or recorded charge was available to compare" | `no fee rule or recorded charge` |
| `req_evaldf38c4d80b5e` (EN, rep. 2) | "there are no pricing-rule details or recorded charge to compare" | `no pricing-rule details or recorded charge` |
| `req_evale8ee4429374a` (PT, rep. 2) | "Não há uma taxa esperada disponível na regra de preços nem uma taxa registrada para comparação" | `não há uma taxa esperada disponível` |
| `req_eval51b2a1d763e0` (PT, rep. 3) | "não havia uma regra de preço aplicável nem uma cobrança registrada para comparação" | `não havia uma regra de preço aplicável` (o pretérito da forma que já existia) |

Contradições acrescentadas a `must_not_assert`:

- EN: `the fee was confirmed`, `the fee is incorrect`, `the fee is wrong`, `the fee was charged correctly`, `the fee diverges`, `there is a fee discrepancy`, `there is a fee divergence`.
- PT: `a taxa foi confirmada`, `a taxa está incorreta`, `a taxa está errada`, `a taxa cobrada está correta`, `a taxa cobrada está incorreta`, `a taxa diverge`, `há divergência na taxa`.

As formas que já existiam ficam como estavam. Não incluí `the fee was charged incorrectly`: `req_evaldf38c4d80b5e` diz corretamente "This does not establish that the fee was charged incorrectly", e "does not establish that" não está entre os qualificadores do runner. `must_not_assert` respeita os qualificadores de incerteza ("não é possível confirmar se a taxa cobrada está correta ou se há divergência" continua aceito). O catálogo da bancada não muda: nenhum `source_case` aponta para estes dois IDs, e o teste de espelhamento da v0.7.0 continua verde.

Prova offline. O teste novo carrega `v080-healthy-r4.json` e `v080-all-r3.json` e recalcula com a própria `runner._checks`, a partir dos campos arquivados (rota, status, idioma, fontes, ferramentas e violações).

- As quatro `request_id`, que o arquivo confirma estarem com `content_ok = false`, agora passam em todas as checagens determinísticas.
- As 12 respostas da r3 e da r4 destes IDs passam.
- Os 51 controles negativos são recusados: 17 contradições sozinhas e 34 anexadas a uma das quatro respostas aceitas (nestas, `content_ok` continua verdadeiro e `forbidden_ok` fica falso).
- Reavaliei, com um script de rascunho, todas as respostas arquivadas destes dois IDs em `docs/evidence/*.json`. Só as quatro mudaram. As falhas anteriores (`v030-real-r1` e `v080-custo-*-r2` PT, com rota ou status errados) continuam iguais.

### Tarefa 76: a regra do Router e seus limites

Segui a decisão do Supervisor, sem nova versão de prompt. A regra fica em `router.enforce` e atua quando:

- a conversa é nova;
- `safety` é `none`;
- a rota do modelo não é `human_handoff`;
- a **mensagem inteira** é um pedido explícito de encerramento.

Nesse caso, a rota vira `human_handoff`, com `topic = contract` e sem pergunta de esclarecimento. Formas aceitas:

- EN: `close`, `end`, `terminate` ou `cancel` + `my`, `the` ou `our` + `[Getnet] contract` + `[with Getnet]`, com `I want/need/wish/would like to`, `I'd like to` e `please` opcionais.
- PT: `encerrar`, `cancelar`, `rescindir`, `fechar`, `terminar` ou `finalizar`, ou os imperativos (`encerre`, `cancele`…) + `[o] [meu|nosso] contrato` + `[com a|da|na Getnet]`, com `quero`, `preciso`, `desejo`, `gostaria de` e `por favor` opcionais.
- Pontuação final: só `.` ou `!`.

Ficam com o modelo, de propósito:

- perguntas ("How do I close my contract?", "Quero encerrar meu contrato?");
- mensagens com serviço ou produto ("Quero cancelar o serviço X", "contrato da maquininha", "Payment Link contract");
- negação e pedido misto ("… e cancelar a venda de ontem");
- conversas em andamento;
- mensagens com `safety` (vão para `out_of_scope`).

Outros limites:

- Formas nominais ("rescisão do contrato", "termination of my contract") não estão cobertas.
- Quando o modelo já escolheu `human_handoff`, a decisão dele fica intacta, inclusive o `topic`.
- O trace não marca que a regra atuou: `route_initial` é `human_handoff` nos dois casos.
- A política programada já encaminhava estas frases e não mudou.

Regressão. A jornada roda com o Router programado para pedir esclarecimento em toda mensagem (a falha da r4). Nas três repetições, a resposta sai com rota `human_handoff`, status `handoff`, protocolo `HO-` distinto e todas as checagens do runner verdes. Em PT, "Quero encerrar meu contrato." encaminha e "Quero cancelar o serviço X." continua em `clarify`.

### Tarefa 77: CLI, guarda, transição e ensaio

**CLI.** O valor `1.40` exige `--campaign-estimate`, verificada pelo mesmo `_verified_v080_campaign_estimate` e na faixa do cap 1,10 (acima de US$1,00 e até US$1,10). Decisão minha: a contingência não muda a estimativa e só continua a campanha que essa estimativa justificou.

Antes de abrir qualquer ledger para escrita, a CLI recusa nestes casos:

- campanha ainda em 1,10: "apply the reviewed contingency transition";
- nenhum cap `v080-qa` persistido com sidecar: "nothing was mounted".

Depois de montar os dois guardas, recusa quando o teto primário **persistido** (sidecar) menos o comprometido não cobre o restante da campanha: "persisted primary ceiling does not cover".

Minha leitura da condição (a): o cap persistido de 1,10 identifica a campanha, mas a continuação com 1,40 só é aceita depois da transição. Montar 1,40 sobre um registro de 1,10 exigiria que a CLI regravasse o cap, e isso é papel do script revisado.

**Guarda.** Acima de 1,10, `FixedBudgetGuard` exige ledger e sidecar existentes antes de criar qualquer arquivo e nunca insere um cap novo. Assim, nem uma chamada direta monta campanha nova a 1,40. Os valores 0,50, 1,00 e 1,10 não mudaram. Depois da transição, `--campaign-cap-usd 1.10` passa a ser recusado, porque registro e sidecar não batem mais, como esperado.

**Script.**

- SHA-256 lógico: as entradas de `ledger` em ordem de `id`, uma linha JSON por entrada, com `repr` dos `float`. Não é comparável ao hash da transição de 2026-11-04, que usou outro procedimento.
- Processos: o script lista as linhas de comando (`Win32_Process` no Windows, `ps` no POSIX) e recusa `merchant_assistant`, `merchant-assistant` e `uvicorn`. Exclui o próprio processo e as linhas que citam o script. Com um processo sentinela "uvicorn-sentinel", a sondagem acusou os dois PIDs (lançador da venv e intérprete). Contêineres Docker não são verificados.
- Sidecars: os reais tinham terminadores diferentes. O do primário era `1.70\n`, gravado pelo procedimento de 2026-11-04; o da campanha, `1.1\r\n`, gravado pelo guard em modo texto. O script grava `repr` e mantém o terminador de cada arquivo: `2.0\n` e `1.4\r\n`.

**Ensaio em cópia** (`.pytest_cache/t77-rehearsal-20261105/`). Copiei byte a byte os quatro arquivos de `data/runtime/` e conferi os SHA-256 antes e depois. Os reais não mudaram: `budget.sqlite3` `45e5a93a…5320`, `.limit` `7f24e2de…278b`, `budget-v080-qa.sqlite3` `9f5cd6f8…1441`, `.limit` `d8bb7408…2ec4`.

| Verificação (cópia) | Antes | Depois |
|---|---:|---:|
| Teto primário (sidecar) | US$1,70 | US$2,00 |
| Cap `v080-qa` (registro e sidecar) | US$1,10 | US$1,40 |
| Entradas e último ID, primário | 2.733 / 2733 | 2.733 / 2733 |
| Entradas e último ID, campanha | 1.117 / 1117 | 1.117 / 1117 |
| Comprometido, primário / campanha | US$1,14385079 / US$0,58164655 | iguais |
| Reservas abertas | 0 / 0 | 0 / 0 |
| SHA-256 lógico, primário | `845ee88e6f59d85e00d7ef3579a7da616301c56a756893dd0dae0f1190a36181` | igual |
| SHA-256 lógico, campanha | `9fae30f59ac848452424bc3c3cefbff4cb2af00bf63f18fa495c78691c8ae100` | igual |
| Folga primário / campanha | — | US$0,85614921 / US$0,81835345 |
| Processos do projeto | 0 | 0 |

Passos do ensaio:

1. Dry-run: saída 0, nada escrito, `would_change` = os três alvos.
2. `--apply`: `applied`, com todas as verificações verdadeiras.
3. Segunda execução: `already_applied`, sem criar o diretório de auditoria.
4. CLI sobre a cópia, com o artefato real `v080-custo-estimativa-r3.json` (estimativa verificada US$1,03174096): aceitou 1,40, com restante combinado de US$0,81835345, e recusou 1,10 e 1,00.

Auditoria em `audit/`: `prepared.json` (`949f33f0…c512`), `applied.json` (`07e9071a…4ac6`), os backups SQLite (verificados por `integrity_check` e pelo hash lógico) e os bytes dos sidecars.

O `prepared.json` registra o SHA-256 dos bytes do script como estão no checkout: `366e4f2c…4e14`, com CRLF. O conteúdo LF versionado tem `ecefa4e5…51c9`. O Supervisor deve conferir contra o checkout que usar.

**Não apliquei nos ledgers reais.**

### Evidência

Testes focados (`.venv` Python 3.13, `-p no:cacheprovider`):

- 75: `test_t75_price_insufficient_archived` (54 testes), mais os rótulos de `test_v080_labels_and_handoff_evidence`, `test_evaluation_runner`, `test_v080_journeys` e `test_v070_closing`: **224 passed** (37 s).
- 76: `test_t76_contract_termination` (74 testes), `test_t74_product_corrections`, `test_budget_and_router`, a trava de D18 (`test_v070_story`, `test_v070_webhooks`, `test_v070_resume`, `test_v070_resume_r2`, `test_v070_handoffs`, `test_v070_handoffs_r2`), `test_v080_journeys`, `test_v080_replan` e `test_v080_story`: **429 passed** (4 min 30 s).
- 77: `test_t77_contingency_cap`, **22 passed**; `test_budget_and_router`, `test_v080_story` e `test_campaign`, **51 passed** (18 s).

Outras verificações:

- Suíte estrita: `python tools/scripts/lint_and_tests.py --strict` no `HEAD` `94bf7b3`, com `PYTEST_ADDOPTS="--basetemp=.pytest_cache/t75-77-suite-basetemp -p no:cacheprovider"`: **1247 passed** em 10 min 35 s de pytest (1097 da linha de base + 150 novos: 54 + 74 + 22), ruff `All checks passed!`, skills válidas, exit 0, 654 s no total. Log `.pytest_cache/t75-77-suite.log`, SHA-256 `a23eb081…b0c9`.
- `ruff check` e `ruff format --check` nos arquivos novos e alterados: ok. Em `cli.py`, o `ruff format` reformataria trechos que não são meus. Reconstruí o arquivo a partir do `HEAD` só com os meus trechos, e o diff ficou cirúrgico (46 linhas).
- Nenhuma chamada paga, rede, Docker ou leitura de `.env`.
- Um `cat` do rascunho travou no início, à espera de stdin, sem efeito; foi encerrado. Nenhum processo ficou em segundo plano.

### Achados e limitações

- 75: o rótulo continua literal. Outras redações corretas podem falhar na campanha real; só acrescentei as quatro observadas.
- 76: a regra cobre as formas verbais listadas. Formas nominais e perguntas ficam com o modelo, e o `router.v6` ainda diz "goes to clarification or a human". A jornada dev não é afetada, porque a mensagem dela é verbal.
- 77: a sondagem de processos depende de PowerShell ou `ps` e não cobre Docker. A recusa com cap persistido de 1,10 é uma leitura minha da condição (a), descrita acima.
- Não verificados: a campanha real (QA) e a aplicação nos ledgers reais (Supervisor).

### Próxima ação e decisão pendente

- Próxima ação: revisão independente dos três commits. Depois, a aplicação da 77 pelo Supervisor: `--dry-run` e então `--apply --audit-dir <novo>` sobre `data/runtime/budget.sqlite3` e `data/runtime/budget-v080-qa.sqlite3`. Por fim, o reteste r5 do QA.
- Decisão humana pendente: nenhuma nova. São escolhas minhas, reversíveis e listadas para a revisão: a faixa da estimativa exigida para 1,40, a recusa com cap persistido de 1,10 e o `topic = contract`.

## Tarefas 75, 76 e 77, rodada 2 (correções da revisão)

Developer nativo, 2026-11-05. Branch `codex/v0.8.0-replan`; base `0de3b56` (produto em `94bf7b3`); HEAD final do produto `663ce09`. Parecer de origem: [v080-reviewer-t75-77.md](v080-reviewer-t75-77.md), rodada 1. Identidade conferida (`lauroPereira` / `lauro.s.pereira@gmail.com`).

| Commit | Tarefa | Achado |
|---|---|---|
| `9a962d1` | 75 | P2-75 |
| `c782bc1` | 76 | P2-76 e P3-76 |
| `663ce09` | 77 | P3-77b e P3-77d |

### Tarefa 75: ressalvas honestas no cotejo de `must_not_assert` (P2-75)

**É uma mudança de medição.** `runner.py` também pontua o holdout. A mudança vale para qualquer resultado do holdout, que nunca foi executado; não li o holdout, e o blob `22dfee8b…af9d` não mudou.

O que mudou em `src/merchant_assistant/evaluation/runner.py`:

- O apóstrofo tipográfico e seus parecidos (U+2018, U+2019, U+02BC, U+2032, U+00B4, U+0060) contam como `'` antes do cotejo. Vale para os três tipos de rótulo: `must_include_any`, `must_not_include` e `must_not_assert`.
- O travessão (U+2013, U+2014) passa a separar orações.
- Novas formas de ressalva em `_assertion_is_present`:
  - EN: "does not / doesn't / did not mean, establish, indicate, show, prove, imply, confirm (that)"; "no indication / evidence / sign / proof that"; "cannot / can't / couldn't confirm, verify, determine, tell, know, say whether, if, that"; "not possible to / no way to … whether"; "don't know whether"; "unclear whether".
  - PT: "não significa / quer dizer / indica / mostra / prova / implica / comprova / confirma que"; "não há como / não tem como / não é possível / não foi possível / não conseguimos saber, confirmar, afirmar, dizer, garantir se/que"; "não há indicação / indício / evidência de que"; "não sabemos / não se sabe / não temos certeza se"; "não posso / não podemos afirmar".
  - Condicional imediatamente anterior: "if the fee is incorrect, …", "if you think the fee is wrong, …".
- As famílias novas de negação e indicação ("does not mean", "no indication that", "não significa que", "não há indicação de que") e a condicional só qualificam a asserção que vem **logo depois**. Assim, "Pricing did not show any problem and the fee is correct." e "Isso não significa nada e a taxa está correta." continuam recusadas. As famílias de dúvida já existentes mantêm a janela de 100 caracteres de antes.

Os rótulos não mudaram. Com o cotejo corrigido, nenhuma das asserções novas ficou ambígua nas sondas, então não troquei nenhuma.

Sondas (todas em `tests/unit/evaluation/test_t75_price_insufficient_archived.py`):

- **15 ressalvas honestas passam `forbidden_ok`**, sozinhas e anexadas às quatro respostas aceitas (todas as checagens verdes). Entram as quatro reproduções do parecer: "…so I couldn’t confirm whether the fee was charged correctly." (com U+2019), "This does not mean the fee is incorrect.", "Isso não significa que a taxa está incorreta." e "…não é possível afirmar que há divergência na taxa.". Entram também "doesn’t mean that the fee is wrong", "does not establish that", "There is no indication that the fee is incorrect.", "I can’t tell whether the fee is wrong.", "cannot tell whether there is a fee discrepancy", a condicional, "Não há como saber se a taxa está correta.", "Não é possível confirmar se/que…", "Não há indicação de que a taxa está errada." e "Não sabemos se a taxa cobrada está incorreta.".
- **Recusadas**: as 17 contradições diretas, também com apóstrofo tipográfico, e 10 frases com ressalva seguida de afirmação (incluindo travessão e "mas").
- O apóstrofo tipográfico casa com o reto em `must_include_any` ("couldn’t compare its fee") e em `must_not_include`.

**Re-pontuação offline.** Pontuei 529 respostas arquivadas em `docs/evidence/*.json` com os rótulos dev (sem holdout), usando o runner de `94bf7b3` e o novo. Nenhuma checagem mudou, embora 126 dessas respostas tenham apóstrofo tipográfico.

### Tarefa 76: verbos ambíguos só com possessivo (P2-76, P3-76)

- Em `router.py`, "close", "fechar", "finalizar", "terminar" e os imperativos "feche", "finalize" e "termine" só contam com `my/our` ou `meu/nosso`. Já "end/terminate/cancel (my|the|our) contract" e "encerrar/cancelar/rescindir (o) (meu|nosso) contrato", com os imperativos, seguem como antes.
- Decisão minha: `terminar` entrou no grupo restrito porque "terminar o contrato" também significa concluí-lo. É reversível.
- Os positivos explícitos continuam valendo: "I want to close my contract.", "Quero encerrar/cancelar/rescindir meu contrato", "Cancel the contract." e "Encerrar contrato.". Somam-se três novos com possessivo: "I want to close our contract.", "Quero fechar meu contrato." e "Quero finalizar o nosso contrato com a Getnet.".
- Novos negativos, que mantêm a decisão do modelo e que **todos casavam a regex de `94bf7b3`**: os cinco do parecer, mais "Close the contract.", "Feche o contrato." e "Quero terminar o contrato.".
- P3-76: quando a regra troca a rota do modelo por `human_handoff`, o passo `router` do trace registra `rule = "contract_termination"`. A condição é "o modelo não encaminhou e a decisão final encaminhou", e só essa regra de `enforce` produz essa troca. Os testes cobrem três situações: a jornada ponta a ponta tem a nota; quando o próprio modelo encaminha, não há nota; "Quero fechar contrato com a Getnet." com Router programado em `knowledge` segue `knowledge`, sem protocolo e sem nota.

### Tarefa 77: P3 baratos (P3-77b, P3-77d)

- P3-77b: `procedure_sha256` em `prepared.json` usa `_source_sha256`, o SHA-256 do script com CRLF trocado por LF. Ele é igual ao do blob versionado em qualquer checkout: no `663ce09`, `570ac505…e607`. Os hashes de SQLite e sidecars continuam sobre os bytes. O resto do script e a CLI não mudaram.
- P3-77d: teste novo em que o backup da campanha devolve um SHA-256 lógico diferente. `apply` para antes de qualquer escrita: ledgers e sidecars ficam iguais, sem `prepared.json`, e os estágios continuam `before`. Conferi a mutação M17 (remover a conferência): o teste falha com ela e passa sem ela.
- Ficaram de fora P3-77a, P3-77c e P3-77e, porque não foram pedidos e mudariam a CLI ou o fluxo.

### Evidência

Testes focados (`.venv` Python 3.13, `-p no:cacheprovider`):

- 75: `test_t75_price_insufficient_archived`, 127 testes (54 + 73). Com `tests/unit/evaluation`, `test_evaluation_runner`, `test_v080_journeys`, `test_v070_closing` e `test_v080_replan`: **504 passed**.
- 76: `test_t76_contract_termination`, 93 testes (74 + 19). Com a trava de D18 (`test_budget_and_router` e todas as `test_v070_*` e `test_v080_*` de integração): **480 passed, 1 skipped**. O skip é preexistente: `test_v070_identity_r2` pede o `--basetemp` do projeto e passa na suíte estrita.
- 77: `test_t77_contingency_cap`, **24 passed** (22 + 2).

Suíte estrita: `python tools/scripts/lint_and_tests.py --strict` no `HEAD` `663ce09`, com `PYTEST_ADDOPTS="--basetemp=.pytest_cache/t75-77-r2-suite-basetemp -p no:cacheprovider"`.

- **1341 passed** em 649,89 s, que são 1247 da linha de base mais 94 novos (73 + 19 + 2).
- Ruff `All checks passed!`, skills válidas, exit 0.
- Log em `.pytest_cache/t75-77-r2-suite.log`, SHA-256 `e803d381…3dbb`.

Outras verificações:

- `ruff format` não muda nenhum trecho meu. Em `runner.py`, ele ainda reformataria um trecho preexistente de `persisted_checks`, que deixei como estava.
- Nenhuma chamada paga, rede, Docker ou leitura de `.env`.
- Não toquei em `data/runtime/`, `.pytest_cache/qa-v080-r1/`, holdout, `prompts/` nem `tests/scenarios/`.

### Limites

- 75: o cotejo continua sendo uma lista finita de formas EN/PT, não um detector geral de negação.
  - Uma ressalva fora das formas cobertas ainda pode cair em `forbidden_ok=False`.
  - Uma contradição colada a uma ressalva da família de dúvida, na mesma oração e sem conectivo de quebra, ainda pode passar. Exemplo: "I cannot confirm whether X and the fee is correct". O comportamento é o de antes.
  - O P3-75 ("the fee matches the plan") continua com o juiz.
- 76: formas nominais ("encerramento do contrato") e perguntas ficam com o modelo, como antes.
- 77: os P3 a, c e e seguem abertos, como no parecer.

### Próxima ação

Revisão curta de `9a962d1` (runner e testes), `c782bc1` (regex, trace e testes) e `663ce09` (hash e teste do backup), com a suíte estrita. Depois, a aplicação da 77 pelo Supervisor e o QA.

## Tarefa 75, rodada 3 (P3-R2a e P3-R2b)

Developer nativo, 2026-11-05. Branch `codex/v0.8.0-replan`; base `2228b6c` (produto em `663ce09`). Parecer de origem: [v080-reviewer-t75-77.md](v080-reviewer-t75-77.md), rodada 2. Identidade conferida (`lauroPereira` / `lauro.s.pereira@gmail.com`). Um commit: `src/merchant_assistant/evaluation/runner.py`, `tests/unit/evaluation/test_t75_price_insufficient_archived.py` e esta documentação.

### O que mudou (mudança de medição, também vale para o holdout, que não li)

- Só as formas de dúvida que já existiam em `94bf7b3` mantêm a janela de 100 caracteres: "cannot/can't/could not/couldn't/am not able to/is not able to/unable to confirm/verify/determine/tell whether/if", "not sure/uncertain/not clear whether/if", "cannot say", "não foi possível/não é possível/não consigo/não podemos/não pude/não dá para confirmar/verificar/determinar/saber se", "não sei/não tenho certeza/incerto/não está claro se" e "não posso/não dá para dizer".
- Exigem a asserção logo depois do qualificador (`that\s+$`, `que\s+$`, `se\s+$`): toda forma acrescentada na v0.8.0 (sujeitos e verbos novos, "unclear", "don't/doesn't know whether", "não sabemos/não se sabe/não temos certeza se", "não posso/podemos afirmar", "não há como/não tem como") e todo complemento com "that"/"que".
- Decisão além do pedido: "not sure that", "cannot say that" e "não posso dizer que" também passaram a exigir adjacência. As três tinham janela já em `94bf7b3`, mas são complementos com "that"/"que". Para "cannot say" e "não posso dizer", uso um lookahead `(?!\s+that\b)` e `(?!\s+que\b)`. É reversível.

### Testes

`tests/unit/evaluation/test_t75_price_insufficient_archived.py`: 165 testes (127 + 38).

- 11 frases com qualificador não adjacente são recusadas: as cinco do parecer, mais "I don’t know whether you saw it and…", "does not know whether…", "can't say that… and…", "not sure that… and…", "Não posso dizer que houve falha porque…" e "Não sabemos se você viu e…".
- 4 sondas com travessão (U+2014) e meia-risca (U+2013) depois de uma forma de dúvida com janela são recusadas. Um teste mostra que, trocando o travessão por "and", a frase passa. Ou seja, é a fronteira que recusa (P3-R2b).
- 22 ressalvas honestas adjacentes, com U+2019, U+2018 e U+02BC, continuam aceitas, entre elas "don’t/doesn't know whether", "unclear whether/if", "not possible to establish that", "no evidence that", "Não podemos afirmar que", "Não posso dizer que" e "Não há como saber se". As 15 da rodada 2 também seguem aceitas.
- Mutações (sondas no scratchpad, sem tocar o código): cada uma derruba pelo menos uma sonda nova.
  - Sem travessão na fronteira: 4.
  - "that/que" de volta à janela: 6.
  - "know whether" de volta à janela: 2.
  - Sem "don't know": 3.
  - Sem lookahead: 2.
  - "unclear" na janela: 1.

### Re-pontuação offline (obrigatória)

Pontuei as respostas arquivadas de `v080-healthy-r4.json` (63) e `v080-all-r3.json` (132) com os rótulos dev. Comparei o runner de `663ce09` com o novo, e também o de `94bf7b3` com o novo.

- **195 respostas e 1.755 checagens (9 por resposta), com 0 mudanças** nas duas comparações.
- Nenhuma resposta foi pulada.
- 24 dessas respostas têm `must_not_assert`, 52 têm U+2019 e 7 têm travessão.

### Evidência

- Testes focados (`tests/unit/evaluation`, `test_evaluation_runner`, `test_v080_journeys`, `test_v070_closing`, `test_v080_replan`): **542 passed**, que são 504 + 38.
- Suíte estrita: `python tools/scripts/lint_and_tests.py --strict`, com `PYTEST_ADDOPTS="--basetemp=.pytest_cache/t75-r3-suite-basetemp -p no:cacheprovider"`.
  - **1379 passed** em 614,57 s, que são 1.341 + 38, sem skip.
  - Ruff `All checks passed!`, skills válidas, exit 0.
  - Log em `.pytest_cache/t75-r3-suite.log`, SHA-256 `42a7fbde…c2e5`.
- `ruff format` só reformataria o trecho preexistente de `persisted_checks`, como na rodada 2.
- Nenhuma chamada paga, rede ou `.env`. Não toquei em rótulos, Router, CLI, script de transição, `data/runtime/`, `.pytest_cache/qa-v080-r1/` nem holdout.

### Limites

- As janelas que já existiam continuam com o comportamento de `94bf7b3`. Exemplos que ainda passam: "I cannot confirm whether X and the fee is correct", "I can't say anything other than that the fee is correct" e "Não posso dizer outra coisa senão que a taxa está correta".
- P3-R2c e P3-R2d seguem abertos, como pedido.

### Próxima ação

Revisão curta do commit desta rodada (runner e testes), antes do holdout.
