# Passagens do Developer — v0.8.0 (Time A)

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
