# 0024. Desenho da orquestração: grafo com plano do Router e replanejamento por regras, não supervisor com especialistas como ferramentas

## Título

Manter a orquestração como um grafo com plano inicial do Router e um nó `replan` de regras nomeadas, com o modelo só na ambiguidade, em vez de um supervisor que chama os especialistas como ferramentas em laço.

## Status

```text
aceita
```

Aceita em 2026-11-07 (v0.12.0, tarefa 95, RF-118). Não substitui as ADRs [0002](0002-orquestracao-langgraph-estado-tipado.md) e [0019](0019-replanejamento.md): registra a comparação que elas citam em uma linha, com ganhos, perdas e a condição de revisão.

## Contexto

O atendimento é o grafo de `orchestration/graph.py`:

- Em conversa longa, antes do grafo e só para mensagem que a guarda de entrada deixa passar, o resumo rolante (`agents/summary.py`, passo `summary`) avança com folga própria de uma chamada (`OWN_ALLOWANCE` em `orchestration/run.py`), fora de `max_model_calls` e dentro dos limites de custo.
- `input_guard` mascara e bloqueia a entrada; o `router` escolhe a rota, que é o plano inicial.
- Com um pedido de cancelamento de venda esperando resposta (v0.12.0, tarefa 94), o `router` passa pelo nó `confirmation` (`agents/cancellation.py`). Um sim ou não explícito, validado por código (`router.enforce`), confirma ou recusa o pedido e segue para `personality`; qualquer outro turno conta a espera e segue a rota do Router. `confirm_sale_cancellation`, `decline_sale_cancellation` e `count_unanswered_cancellation_turn` são ferramentas de escrita executadas por código nesse nó, fora de `AGENT_TOOLS`.
- Os especialistas são nós: `knowledge` (páginas oficiais), `web` (busca web), `support` (ferramentas de conta; nas rotas do Router, precedido de `support_prefix`) e `escalation` (caso para humano).
- Depois de `knowledge`, `web` e `support`, o nó `replan` (`agents/replanner.py`) lê um resumo observado e escolhe entre `finish`, `knowledge`, `web`, `support`, `escalate` e `clarify`. Dez regras nomeadas decidem os casos claros sem chamada (`origin = rule:<nome>`); o prompt `replan.v2` (esforço `none`, 80 tokens de saída) decide só quando nenhuma regra se aplica ou duas discordam (`origin = model`).
- Guardas valem para regra e modelo: cada especialista roda no máximo uma vez (`rule:no_repeat`), as saídas do plano são limitadas por `MAX_PLAN_HOPS=3` (`rule:hop_budget`), `support` exige lojista conhecido (`rule:unknown_merchant`) e os limites da requisição (`max_model_calls=8`, `max_request_cost_usd=0.05`, tempo) continuam valendo (`rule:request_limits`). O primeiro passo da rota sai do Router sem `replan`; os passos seguintes do plano (`rule:plan_pending`) passam por `_guard` só para `no_repeat`, isentos de `unknown_merchant`, `hop_budget` e `request_limits`. Para esses passos, as garantias ficam em `support.run` (lojista desconhecido sem ferramenta; teto de chamadas de ferramenta) e em `registry.execute` (escopo, lojista conhecido e ferramentas por agente).
- `personality` redige a resposta e `output_guard` recusa valor, percentual ou data que não esteja nas evidências do turno.
- Só o agente `customer_support` recebe ferramentas do modelo (`AGENT_TOOLS` em `tools/registry.py`); a única de escrita, `request_sale_cancellation`, só registra um pedido que espera o sim, e as que confirmam, recusam ou contam a espera rodam por código no nó `confirmation`. O lojista vem do contexto do servidor, nunca do esquema. O nó `web` recebe só a mensagem mascarada, sem dado da conta.

Medido nas evidências versionadas:

- No holdout da v0.8.0 ([v080-holdout-r7.md](../../evidence/v080-holdout-r7.md)), 75 respostas: as 77 decisões de `replan` têm origem; 73 por regra (`rule:complete` 49, `rule:plan_pending` 13, `rule:gap_declared` 11) e 4 pelo modelo. O maior `plan_hops` foi 2; 73 respostas tiveram 0 saltos.
- No QA pré-holdout ([v080-d12-pre-holdout-r6.md](../../evidence/v080-d12-pre-holdout-r6.md)), a pergunta mista seguiu `support` → `replan` (`rule:procedure_gap`, 1 salto) → `knowledge` → `replan` (`rule:complete`), a US$0,00114305 pela pergunta inteira; nas 18 respostas da r6 o maior `plan_hops` foi 1.
- A métrica `replan_total{origin=...}` expõe a origem por decisão ([v0100-qa-ops-r1.md](../../evidence/v0100-qa-ops-r1.md)).

A questão é se um supervisor com especialistas como ferramentas seria um desenho melhor.

## Decisão

A orquestração continua sendo o grafo descrito acima. O Router define o plano inicial; o `replan` decide por regras nomeadas e chama o modelo só na ambiguidade; as garantias de escopo, saltos e valores ficam no código, fora do modelo. A alternativa volta à mesa só pela condição de revisão abaixo.

## Desenhos

Grafo atual:

```text
summary  (conversa longa: folga própria de uma chamada, fora de max_model_calls)
   |
   v
input_guard --+--> router --+--> confirmation --+--> personality    (sim ou não validado por código; confirma
              |             |   (pedido de      |                     ou recusa por código, fora de AGENT_TOOLS)
              |             |    cancelamento   +--> rota do Router, como nas linhas abaixo (qualquer outro turno)
              |             |    esperando)
              |             +--> knowledge                 (knowledge, general_web)
              |             +--> support_prefix --+--> support          (support)
              |             |                     +--> knowledge        (knowledge_and_support; o support
              |             |                     |                      vem depois, por rule:plan_pending)
              |             |                     +--> escalation       (human_handoff)
              |             +--> personality              (out_of_scope, clarify)
              +--> personality                            (entrada bloqueada)

knowledge | web | support --> replan --+-- finish | clarify --> personality --> output_guard --> fim
      ^                                +-- escalate --> escalation --> personality
      |                                |
      +--------------------------------+-- knowledge | web | support
           (cada especialista uma vez; no máximo MAX_PLAN_HOPS saídas do plano;
            regra nomeada decide, modelo só na ambiguidade; _guard tem a última palavra)
```

Supervisor com especialistas como ferramentas (não adotado):

```text
input_guard --> supervisor (modelo, laço de function calling) --> personality --> output_guard --> fim
                   |    ^
                   v    |  cada resultado volta ao contexto do supervisor
      ferramentas: ask_knowledge | search_web | ask_support | escalate | ask_merchant
      (o modelo escolhe qual, quantas vezes e quando parar)
```

## Alternativas consideradas

- **Supervisor em laço de function calling, especialistas como ferramentas.** Ganharia combinações não previstas pelas regras (por exemplo, consultar a conta, depois a web, depois a conta de novo com outro parâmetro); um desenho mais curto, sem roteamento por rota, sem as dez regras e sem os marcadores lexicais de `procedure_gap` e `account_dependent_question`; e uma decisão a cada passo com o contexto inteiro. Descartado pelas perdas listadas em Consequências: as garantias que hoje são estruturais virariam instrução ao modelo, e toda pergunta pagaria pelo menos uma chamada de decisão a mais.
- **Modelo em toda decisão do `replan`, mantendo o grafo.** Descartado na ADR 0019: acrescenta uma chamada a toda pergunta sem mudar os casos claros.
- **Arestas fixas da v0.7.0.** Descartado na ADR 0019: não reagem ao que o especialista devolveu.

## Consequências

O que o grafo mantém e o supervisor perderia:

- **Origem nomeada de cada decisão.** Toda decisão do `replan` grava `next`, `reason`, `review`, `hops`, `origin` e o resumo observado no trace; `origin = rule:<nome>` aponta a função que decidiu. Com o supervisor, toda decisão seria `model`, e explicar um caminho exigiria ler a justificativa do modelo.
- **Garantias estruturais.** Especialista no máximo uma vez, teto de saltos, `support` só com lojista conhecido e limites da requisição são verificados por `_guard` depois de regra e de modelo. No supervisor seriam contadores em volta do laço; o modelo receberia a recusa como resultado de ferramenta e poderia insistir, gastando chamadas até o limite.
- **Separação entre conta e busca externa.** Hoje o nó `web` monta a busca só com a mensagem mascarada e não recebe dados da conta. No supervisor, o resultado de `ask_support` voltaria ao mesmo contexto que compõe a chamada seguinte, por exemplo a consulta de `search_web`, e dados da conta poderiam chegar à busca externa; impedir isso exigiria um filtro novo entre o contexto e cada ferramenta.
- **Guarda de valores.** `output_guard` vale nos dois desenhos, mas no supervisor os resultados dos especialistas passam pelo contexto de um modelo antes da redação. Os resultados de ferramenta continuariam disponíveis para a guarda; as passagens recuperadas e o protocolo do caso precisariam ser carregados de cada chamada para o conjunto de evidências do turno.
- **Testes reproduzíveis com modelo roteirizado.** As regras são funções puras sobre o resumo observado: `tests/unit/test_replanner_rules.py` (`test_each_rule_settles_its_case_alone`) cobre cada regra isolada, e `tests/integration/test_v080_replan.py` cobre o laço forçado que termina em 3 saltos sem repetir especialista e o modelo chamado só quando as regras discordam ou nenhuma se aplica. Com o supervisor, cada caminho dependeria do roteiro do modelo, e a cobertura testaria o roteiro, não a decisão.
- **Custo por decisão.** No holdout, 73 de 77 decisões saíram por regra, sem chamada. O supervisor chamaria o modelo antes de cada especialista e depois de cada resultado, inclusive na pergunta simples, com o contexto crescendo a cada resultado.

O que o grafo aceita:

- Combinações fora das seis saídas do `replan` não acontecem; o que nenhum especialista pode acrescentar termina em `finish` com a lacuna declarada (`rule:gap_declared`).
- Cada cenário novo pede regra, teste e às vezes rótulo; o desenho é mais longo que um laço.
- Os marcadores lexicais das regras cobrem português e inglês (ADR 0019).

## Condição de revisão

A decisão é revista pela ablação da [tarefa 93](../../tasks/93-ablacao-replan.md) (`eval --replan off` e `eval-compare --a --b`, pareada por caso, critério e rota, com intervalo por bootstrap da diferença), no conjunto completo e no holdout. A condição usa as duas medidas que o `eval-compare` produz:

1. a contagem das decisões do `replan` por origem (`rule:<nome>` e `model`);
2. a diferença pareada com × sem replanejamento, separada entre casos com pelo menos uma decisão `model` e casos só com decisões por regra.

Na ordem:

- **Rever no sentido de desligar** se a ablação não mostrar ganho em nenhum critério nem rota: o caminho é `REPLAN=off`, não um supervisor. Esta condição prevalece sobre a seguinte.
- **Rever a favor de mais modelo** se o ganho (intervalo da diferença sem o zero) aparecer só nos casos com decisão `model` e não nos casos só com regra; ou se as decisões `model` passarem de um quarto das decisões do `replan`. O limiar de um quarto é escolha do projeto, revisável com o resultado da ablação; o ponto de partida medido é 4 de 77 decisões (cerca de 5%) no holdout da v0.8.0. O passo seguinte é um protótipo do supervisor atrás de configuração, comparado pelo mesmo `eval-compare` antes de substituir o grafo.
- **Manter** se o ganho aparecer nos casos só com regra ou se distribuir entre os dois grupos.

## Data

2026-11-07
