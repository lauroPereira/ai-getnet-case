# 0019. Replanejamento: um nó que observa o resultado de cada especialista e decide o próximo passo

## Título

Substituir as arestas fixas que saem de `knowledge` e de `support` por um nó `replan`, com regras determinísticas nomeadas, o modelo só na ambiguidade e um orçamento de saltos.

## Status

**Proposta** (v0.8.0, 2026-11-04; implementada na tarefa 69 da branch `codex/v0.8.0-replan`, a aceitar depois da revisão e do QA real da campanha `v080-qa`).

## Contexto

O avaliador apontou que o grafo segue um plano fixo: o Router escolhe a rota e os especialistas rodam na ordem da rota, sem observar o que um deles devolveu para decidir o passo seguinte (RF-86, RF-87). Em v0.7.0 a única decisão depois de um especialista era `_after_knowledge` (ir ao Support só na rota `knowledge_and_support`) e `_after_support` (ir ao Escalation se `escalate`). Perguntas cuja resposta não está onde o Router mandou procurar primeiro (produto sem evidência nas páginas oficiais, conta que pede também um "como faço", produto que depende do plano do lojista) terminavam com uma resposta incompleta ou com a lacuna escondida.

Restrições: o grafo de retomada do operador (ADR 0018) acaba de ser validado e não pode mudar; as rotas avaliadas e lacradas (holdout) foram rotuladas sem replanejamento; o gasto por pergunta simples não pode subir; os limites de chamadas, tempo e custo da requisição continuam valendo.

## Decisão

- **Onde:** no grafo de atendimento, um nó `replan` depois de `knowledge`, de `web` (nó novo, a busca web que o replanejamento pode escolher) e de `support`, no lugar das duas arestas fixas. A rota do Router continua sendo o plano inicial (D1). O grafo de retomada e o nó `escalation` ficam como estão (D3, D18).
- **Destinos (D2):** `finish`, `knowledge`, `web`, `support`, `escalate` (passa pelo nó `escalation` atual) e `clarify` (Personality com `status=needs_clarification`). `finish` e `clarify` terminam na Personality.
- **Regras antes do modelo (D4):** funções puras do resumo observado, cada uma com nome, avaliadas todas. Um só destino distinto → decisão por regra (`origin = rule:<nome>`). Nenhuma regra, ou duas com destinos diferentes → `replan.v1` (esforço `none`, 80 tokens de saída, saída estruturada `next`, `reason`, `review`; `origin = model`).

| Regra | Condição | Destino | Revisão |
| --- | --- | --- | --- |
| `specialist_failed` | um nó falhou e já há resposta controlada, sem passo do plano pendente | `finish` | incompleta |
| `plan_pending` | a rota do Router ainda tem um especialista a rodar (por exemplo `support` depois do `knowledge` da `knowledge_and_support`) | esse especialista | incompleta (não é salto) |
| `tool_failure_no_alternative` | Support: ferramenta essencial `UNAVAILABLE`/`TIMEOUT` e nenhum dado utilizável | `escalate` | incompleta |
| `support_asked_for_human` | Support pediu um humano | `escalate` | incompleta |
| `selection_pending` | Support pede que o lojista escolha entre opções | `clarify` | incompleta |
| `account_dependent_question` | depois do Knowledge, a pergunta fala do plano, contrato, conta ou taxas do próprio lojista (mensagem ou lacuna declarada) e o Support ainda não rodou | `support` | incompleta |
| `procedure_gap` | depois do Support, a mensagem também pergunta "como faço" e o Knowledge não rodou | `knowledge` | incompleta |
| `evidence_insufficient_web` | Knowledge sobre as páginas oficiais declarou evidência insuficiente (índice disponível) e a web não rodou | `web` | incompleta |
| `complete` | evidência suficiente (veredito do Knowledge), Support sem lacuna e nenhum passo aberto | `finish` | completa |
| `gap_declared` | falta algo e nenhum especialista pode acrescentar | `finish`, com `plan.gap` | incompleta |

- **Cada especialista uma vez (D5):** `knowledge`, `web` e `support` rodam no máximo uma vez por requisição, registrado pelo próprio nó (`plan.ran`), mesmo se ele falhar. A rota `general_web` conta como web.
- **Orçamento (D6):** `MAX_PLAN_HOPS=3` em `Settings`. Um salto é uma decisão que sai do plano do Router: um especialista que o plano não previa, ou `escalate`. Seguir o plano (`plan_pending`) não é salto. No limite, um especialista extra vira `finish` com a lacuna declarada à Personality (`unconfirmed`); `escalate` e `clarify` encerram o fluxo e não são barrados. O máximo alcançável com o padrão é 3 (`knowledge → web → support → escalate`). Os limites de chamadas, tempo e custo valem: sem espaço para mais um especialista e a resposta, `finish`.
- **Guardas (D5, D6, limites):** valem para regra e modelo. Escolha repetida, `support` sem lojista conhecido, orçamento esgotado e limites da requisição viram `finish` com a lacuna (`rule:no_repeat`, `rule:unknown_merchant`, `rule:hop_budget`, `rule:request_limits`); planner indisponível vira `finish` (`rule:planner_unavailable`).
- **Trace (D7):** o passo `replan` leva `next`, `reason`, `review`, `hops`, `origin` e o resumo observado (`observed`), e `GET /v1/runs/{id}` o mostra só nesse passo, sem mudar os campos dos demais; o prompt `replan@1` só aparece quando o modelo foi chamado. O detalhe da requisição guarda `plan_hops`.
- **Rota avaliada (D16):** a resposta continua trazendo a rota inicial do Router em `route`; o caminho executado está em `agents`, na ordem (`router`, `knowledge`, `web`, `customer_support`, `escalation`, `personality`), e é a base do `executed_path` do relatório do runner.
- **`web` junta, não substitui:** a busca web depois das páginas oficiais soma pontos, fontes e evidências ao resultado do Knowledge; uma busca que falha deixa o resultado anterior e acrescenta o motivo.
- **Support por replanejamento:** roda sem o prefixo de abertura do caso (histórico e healthcheck); o resumo vazio vira "nada checado" e não "sem casos anteriores".

## Alternativas consideradas

- **Modelo em toda decisão:** mais flexível, mas dobra a latência e acrescenta uma chamada a toda pergunta, inclusive as simples; o requisito é não gastar mais no caminho claro. Fica como plano B para medir se as regras estão perdendo casos.
- **Reescrever o Router para planejar a sequência inteira:** o Router decide sem ver resultado; não resolve o problema de reagir ao que voltou, e reabre o prompt avaliado.
- **Laço ReAct livre (o modelo chama especialistas como ferramentas):** dificulta o limite de custo e a explicação por regra; o orçamento de saltos e "uma vez por especialista" ficariam por conta do modelo.
- **Manter as arestas fixas:** é o estado da v0.7.0 e o motivo do apontamento.
- **Replanejar também no grafo de retomada:** reabriria o HITL recém-validado (D3); fica para depois.
- **Contar também o seguimento do plano como salto:** bloquearia o plano do próprio Router com orçamento baixo, e `MAX_PLAN_HOPS=3` nunca seria o limite real.

## Consequências

- Perguntas com resposta fora da rota inicial passam a ter uma segunda tentativa visível no trace, com motivo e origem; a lacuna que sobra é declarada à Personality (`unconfirmed`), sem prompt novo.
- O caminho claro (pergunta simples) não ganha chamada: o passo `replan` é uma função pura que roda em milissegundos. O modelo entra nas ambiguidades; a QA mede a taxa de `origin=model`.
- Mais um nó e mais um conceito no estado (`plan`, um dicionário simples, para não ampliar os tipos registrados nos checkpoints). A fila de revisão e o formato dos checkpoints não mudam.
- Duas regras usam marcadores lexicais da mensagem (plano, contrato, conta, taxas do lojista; "como faço") e do `missing` do Knowledge. Servem para os casos claros; ambiguidade fica com o modelo. Falso positivo custa um especialista a mais e é limitado pelo orçamento; falso negativo mantém o comportamento da v0.7.0. Os marcadores não cobrem outros idiomas além de português e inglês.
- `evidence_insufficient_web` busca informação fora das páginas oficiais da Getnet para uma pergunta sobre produto Getnet; a resposta mostra a fonte web. O índice fora do ar (`knowledge_unavailable`) não aciona a web, para não mascarar uma falha de infraestrutura com fonte não oficial.
- O roteiro do cenário de falha de ferramenta exige o serviço de preços fora do ar (parar o `mocks` no QA; falha injetada nos testes); sem isso a mesma pergunta é respondida normalmente.
- Em modelos reais o Router pode mandar o cenário "suporte com lacuna de procedimento" para `knowledge_and_support`, caso em que o replanejamento não é exercitado; o rótulo aceita as duas rotas.
- Plano B: o nó é isolado (`agents/replanner.py`, o nó e três arestas em `graph.py`); voltar às arestas `_after_knowledge` e `_after_support` da v0.7.0 desliga o replanejamento sem tocar na fila, nos checkpoints ou nos contratos. `MAX_PLAN_HOPS=0` impede qualquer especialista extra mantendo o resumo no trace.

## Data

2026-11-04
