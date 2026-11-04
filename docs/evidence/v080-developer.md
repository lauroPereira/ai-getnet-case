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
