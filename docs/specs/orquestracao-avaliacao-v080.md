<!-- Papel: especificação complementar curta da v0.8.0 (orquestração adaptativa e avaliação semântica), derivada da evolução pós-feedback. -->

# Especificação: v0.8.0 — orquestração adaptativa e avaliação semântica

Versão 1 — 2026-11-04 — escrita pelo Supervisor e **aprovada pelo responsável em 2026-11-04**, com as decisões D12 e D16 a D19 tomadas por ele na revisão. Vale a "Autorização por versão" do AGENTS.md; o ciclo começa depois do merge local da v0.7.0 na `main`.

**Execução confirmada pelo responsável em 2026-11-04:** (1) o checkout principal passa para a branch nova `codex/v0.8.0-replan`, criada da `main` local com a v0.7.0, sem pull nem push; a `codex/v0.8.0-avaliacao` (worktree `time-b`) recebe a `main` e o lacre do holdout é reconferido; spec, história e tarefas chegam à branch do Time A por cherry-pick dos commits só de docs, sem o holdout. (2) Subagentes em `sonnet`/`xhigh`. (3) Teto da campanha `v080-qa`: US$0,50, ou até US$1,00 numa única montagem se a estimativa medida passar, com o motivo registrado; acima disso, para e pergunta. (4) O ciclo vai até o QA técnico e o CSV de calibração; o merge local da v0.8.0 espera a calibração do responsável; push e tags continuam com ele. Deriva da [especificação 0.2](evolucao-pos-feedback.md) (RF-86 a RF-93; CA-49 a CA-51; UC-23, UC-24) e do [plano](evolucao-pos-feedback-plano.md) (decisões técnicas 9 a 16, tarefas 69 a 73). História em [orquestracao-avaliacao-v080.md](../historias/orquestracao-avaliacao-v080.md). O holdout de respostas (tarefa 72a) já está escrito e lacrado nesta branch (`tests/scenarios/holdout_v080.jsonl`, SHA-256 `91aa5158…4f1bac`).

Esta spec não repete a 0.2: fixa o que o plano deixou aberto e as pré-condições que a v0.7.0 deixou.

## Problema

O avaliador apontou que o grafo segue um plano fixo, sem observar o resultado de um especialista e decidir o próximo passo, e que a avaliação por IA é literal: juiz do mesmo modelo, uma execução, sem evidência, sem revisão humana e sem holdout. As jornadas de negócio fecharam a v0.6.0 em 7/13 pela rubrica literal.

## Resultado desejado

1. Depois de cada especialista, um passo de replanejamento observa o resultado e decide concluir, chamar outro especialista, buscar na web, escalar ou pedir esclarecimento, dentro de um orçamento de saltos e com o motivo no trace.
2. A avaliação real usa uma rubrica de quatro critérios com evidência, um juiz de outro provedor ou modelo, três execuções com dispersão e concordância, uma amostra calibrada pelo responsável e o holdout reportado à parte.
3. As jornadas de negócio passam de 7/13 para pelo menos 12/13.

## Escopo

| Bloco | Conteúdo | Requisitos | Tarefa | Time |
| --- | --- | --- | --- | --- |
| Replanejamento | Nó `replan` depois de `knowledge` e de `support`, regras determinísticas e `replan.v1` só na ambiguidade, orçamento de saltos, passo de trace, quatro cenários | RF-86 a RF-88 | 69 | A |
| Rubrica e juiz | `judge.v3` com quatro critérios e evidência, juiz independente, `eval --repeat`, agregação, migração 0011 | RF-89, RF-90 | 70 | B |
| Calibração | `eval-calibrate --sample` (CSV sem os scores do juiz) e `--import` (concordância e kappa) | RF-91 | 71 | B |
| Jornadas | Correções das jornadas de negócio e `router.v6` | RF-93 | 72b | A |
| Fechamento | Regressão, candidato, campanha `v080-qa` com 3 execuções e holdout, calibração pelo responsável, evidência, ADR 0019, README e CHANGELOG | CA-49 a CA-51 | 73 | A |

## Fora do escopo

Retrieval híbrido e reranker (v0.9.0); métricas, comparação retomável e resumo rolante (v0.10.0); replanejamento dentro do grafo de retomada do operador (ver D3); formulário de calibração na interface web (ver D10); mudança de regras financeiras, de ferramentas de Support ou de snapshots públicos; reabrir ou relacrar o holdout 72a.

## Pré-condições herdadas da v0.7.0

- A v0.7.0 integrada na `main` local. A branch `codex/v0.8.0-avaliacao` (Time B, worktree `time-b`) traz a `main` antes da tarefa 70 (regra 3 do plano), sem mexer no holdout; o lacre é reconferido depois do merge.
- **Migração 0011** é a da v0.8.0 (a 0010 virou a outbox da v0.7.0). A cópia do plano nesta branch ainda diz 0010 até o merge da `main`.
- O Time A abre `codex/v0.8.0-replan` a partir da `main` atualizada, no checkout principal.
- Prompts da v0.7.0 em vigor: `router.v5`, `support.v7`, `personality.v4`, `escalation.v2`, `judge.v2`. Ajuste de prompt da v0.8.0 só depois do lacre (já feito) e nunca guiado pelo holdout.

## Decisões que o plano não fixou

Todas reversíveis; vão também para o relatório do Supervisor.

| ID | Decisão | Motivo | Como reverter |
| --- | --- | --- | --- |
| D1 | **Onde entra o `replan`:** no grafo de atendimento, depois de `knowledge` e de `support`, no lugar das arestas `_after_knowledge` e `_after_support`. A saída do Router continua sendo o plano inicial | RF-86 sem reescrever o Router | Voltar às arestas fixas atuais |
| D2 | **Destinos:** `finish`, `knowledge`, `web`, `support`, `escalate`, `clarify`. `escalate` passa pelo nó `escalation` atual; `clarify` vai à Personality com `status=needs_clarification` | Mesmos nós de hoje; nada novo de saída | — |
| D3 | **Grafo de retomada sem `replan`:** depois do `reject`, continua `support → personality` (D14 e D25 da v0.7.0) | Não reabrir o HITL recém-validado | Acrescentar `replan` depois do `support` da retomada, sem `escalate` |
| D4 | **Regras antes do modelo.** Casos claros sem chamada: evidência suficiente e revisão completa → `finish`; evidência insuficiente vinda do Knowledge → `web`; lacuna de procedimento no Support → `knowledge`; falha de ferramenta sem alternativa → `escalate`; pedido de seleção pendente → `clarify`; pergunta de produto que depende da conta, vinda do Knowledge → `support`. O `replan.v1` (esforço `none`, ≤ 80 tokens de saída) decide só quando nenhuma regra se aplica ou duas se contradizem | Custo e previsibilidade; RF-87 pede a origem no trace | Ligar o modelo em toda decisão |
| D5 | **"Sem informação nova":** cada especialista (`knowledge`, `web`, `support`) roda no máximo uma vez por requisição; `escalate` e `clarify` encerram | Regra verificável por teste, sem heurística de novidade | Permitir repetição com consulta reformulada |
| D6 | **Orçamento:** `MAX_PLAN_HOPS=3` em `Settings`, contado por decisão do `replan` que leva a outro especialista. No limite, `finish` com a lacuna declarada (a Personality diz o que não conseguiu confirmar). Os limites atuais de chamadas, tempo e custo continuam valendo | RF-87 | Mudar o padrão |
| D7 | **Trace:** passo `replan` com `next`, `reason`, `review` (completo/incompleto), `hops`, `origin` (`rule:<nome>` ou `model`) e o resumo observado | RF-87, CA-49 | — |
| D8 | **Cenários de replanejamento:** os quatro do RF-88 em `tests/scenarios/replan.jsonl` e no catálogo da bancada (`SC-REPLAN-*`), com a política programada atualizada; contam como desenvolvimento, não como holdout | RF-88, CA-49 | — |
| D9 | **`judge.v3`:** `groundedness`, `factual_correctness`, `relevance`, `usefulness` (1–5, justificativa curta cada) e `unsupported_claim: bool`; recebe o conteúdo mascarado das evidências (trechos e resultados de ferramenta), até 6 000 caracteres, com o truncamento registrado na avaliação. O `judge.v2` fica para comparar campanhas antigas | RF-89 | Voltar ao v2 |
| D10 | **Calibração só por CSV nesta versão:** `eval-calibrate --sample 24` gera um CSV estratificado por rota e split, com instruções e sem os scores do juiz; `--import` calcula concordância exata, ±1 e kappa ponderado (quadrático) por critério e grava `docs/evidence/v080-calibracao.md`. O formulário na área Resultados fica para depois | RF-91 com o menor escopo; o formulário é opcional no plano | Fazer o formulário no web |
| D11 | **Juiz independente:** `EVALUATOR_MODEL` diferente do `AGENT_MODEL` e de outro provedor quando houver chave; candidato `deepseek-flash` (preço já na tabela), escolhido pelo custo medido em 5 casos antes da campanha; provedor e modelo gravados em cada avaliação. O responsável confirmou em 2026-11-04 que a chave da DeepSeek já está no `.env`; se ela falhar na hora, a campanha fica **bloqueada** e a decisão volta ao responsável | RF-90 exige provedor ou modelo diferente | Outro modelo do mesmo provedor, se o responsável aceitar |
| D12 | **Repetições sem misturar variações (responsável, 2026-11-04):** primeiro o agente roda 3 vezes cada caso e o juiz avalia cada resposta uma vez (variação do assistente); depois o juiz avalia 3 vezes as respostas da primeira execução (variação do juiz). `eval --repeat N` repete o agente; `eval --judge-repeat N` repete só o juiz sobre respostas já gravadas. Relatório com média, desvio, concordância exata e ±1 de cada lado, por critério, rota e split (`dev`, `holdout`, `holdout_v080`) | RF-90; separar as duas fontes de variação mostra quanto confiar no juiz | Repetir agente e juiz juntos |
| D13 | **Migração 0011:** `run_evaluations.rubric_version`, `scores` (JSON), `repetition`, `unsupported_claim`; tabela `calibrations`. Reversível, com dados | Plano, "Modelo de dados" | — |
| D14 | **Holdout v0.8.0:** só na campanha do QA, `--split holdout_v080`, reportado à parte; nenhum ajuste depois de ver o resultado; o lacre é testado na suíte | RF-92 | — |
| D15 | **Jornadas:** rótulo só muda onde a resposta real está correta, com justificativa por caso na passagem; `router.v6` resolve a pergunta de condições em inglês (forma interrogativa) com regressão programada | RF-93 | — |
| D16 | **Rota avaliada é o plano inicial (responsável, 2026-11-04):** `route_ok` continua comparando a rota escolhida pelo Router com as rotas aceitas do caso; o caminho executado depois do replanejamento vai num campo à parte (`executed_path`, por exemplo `knowledge → web`) na resposta do runner, no trace e no relatório | Os rótulos do holdout foram escritos sem replanejamento e estão lacrados; medir o caminho final os invalidaria sem possibilidade de ajuste | Medir o caminho final, com rótulos novos |
| D17 | **Holdout só no fim (responsável, 2026-11-04):** o QA roda o `holdout_v080` uma única vez, como último passo técnico, depois de todos os outros momentos aptos. Se houver nova rodada de QA depois dele, o relatório marca "holdout já visto" e esse resultado não decide a aprovação | O holdout perde o valor se alguma correção for feita sabendo o resultado dele | — |
| D18 | **Dono único dos arquivos do grafo e da política programada (responsável, 2026-11-04):** `orchestration/` (`graph.py`, `state.py`, `run.py`), `agents/`, `evaluation/scripted_policy.py` e `data/scenarios/catalog.json` têm um só time no período: o Time A. O Time B não os edita; o substituto programado do `judge.v3` vai num módulo novo do B. O teste da história da v0.7.0 e os de webhooks e retomada são trava obrigatória da tarefa 69. O responsável sugeriu o time com menos tarefas; só a 69 toca o grafo, e passá-la ao B (que ficaria com 69 → 70 → 71 em série) deixaria o A parado esperando a 69 para a 72b | Conservador: o grafo guarda a suspensão, a outbox e a recuperação do encaminhamento da v0.7.0 | Passar a 69 ao Time B |
| D19 | **Calibração é indicação, não prova forte:** com 24 respostas, a concordância e o kappa têm margem grande; o relatório mostra os números com essa ressalva (e o intervalo, se o cálculo for simples) | RF-91 pede o mínimo de 24 | Amostra maior, com mais tempo do responsável |

## Critérios de aceitação e prova

| ID | Critério | Prova determinística (tarefa) | Prova real (QA, campanha `v080-qa`) |
| --- | --- | --- | --- |
| CA-49 | Quatro cenários de replanejamento passam; nenhum caso passa de 3 saltos; o trace mostra cada decisão com origem | Testes de regras, laço forçado, cenários programados (69, 73) | Os quatro cenários com modelos reais; contagem de saltos nos traces |
| CA-50 | Relatório com quatro critérios, juiz independente, 3 execuções, concordância humano × juiz e holdout separado | Agregação e kappa com números fixos; CSV de calibração; migração 0011 com dados (70, 71) | `docs/evidence/v080-*.md` e README |
| CA-51 | Jornadas de negócio ≥ 12/13 pela rubrica | Regressão programada das jornadas (72b) | Campanha real |

Regressão: 40 casos e 4 conversas sem piora em relação à v0.7.0, salvo diferença justificada pelo replanejamento; suíte estrita verde.

## Requisitos não funcionais

- Teto da campanha `v080-qa`: **US$0,50** no plano, montada uma vez, combinada com o ledger primário. Antes de montar, o QA estima o custo de 3 execuções (40 casos, 4 cenários e o holdout, com agente e juiz) a partir de 5 casos medidos. O responsável disse em 2026-11-04 que há margem ampla e que não é preciso parar para perguntar se a estimativa passar de US$0,50. Padrão proposto pelo Supervisor na aprovação: a campanha monta com US$0,50 e, se a estimativa medida passar disso, monta uma única vez com até **US$1,00**, registrando o motivo; acima disso, para e pergunta.
- Testes sem chamada paga e sem rede; `replan.v1` e `judge.v3` com modelo programado nos testes.
- O caminho sem replanejamento ambíguo não chama modelo a mais.
- Nenhum dado real; o CSV de calibração só com dados sintéticos e respostas mascaradas.

## Riscos

| Risco | Mitigação |
| --- | --- |
| `replan` cria laço ou gasto | D5, D6, teste de laço forçado, limites atuais |
| Juiz independente indisponível ou caro | Medir em 5 casos; D11 bloqueia em vez de trocar por inferência |
| Estimativa da campanha acima de US$0,50 | QA para antes de montar; responsável decide teto ou recorte |
| Calibração depende do tempo do responsável | Amostra de 24, CSV com instruções, cerca de 1 h |
| Ajuste guiado pelo holdout | D14; holdout só na campanha final |
| Arquivos do grafo compartilhados entre times | D18: dono único (Time A) do grafo, dos agentes, da política programada e do catálogo |
| Replanejamento quebrar o HITL da v0.7.0 | D3 (grafo de retomada inalterado), D18 (testes da v0.7.0 como trava) |
| Holdout visto antes da hora | D17 |
