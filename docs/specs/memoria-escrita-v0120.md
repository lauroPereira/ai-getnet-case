
# Memória de conversa, ablação do replanejamento e escrita com confirmação — v0.12.0

Deriva do [roadmap](roadmap-v0110-v100.md) (RF-116 a RF-119) e do [plano](roadmap-v0110-v100-plano.md) (decisões 9 a 13, tarefas 92 a 96).

## Problema

1. A conversa lembra só as últimas 10 mensagens (até 1.200 tokens); numa conversa longa, protocolo e valores do começo se perdem.
2. O ganho do replanejamento está medido em quatro cenários, não no conjunto de casos.
3. A escolha do desenho de orquestração (grafo com replanejamento por regras, em vez de um supervisor com especialistas como ferramentas) não tem registro próprio.
4. As ações do domínio são de leitura e de abertura de caso; o cancelamento de venda só consulta o status.

## Resultado desejado

1. Conversa de 20+ turnos devolve, no fim, protocolo e valor ditos no começo, com os valores vindos de um registro determinístico e aceitos pela guarda de saída.
2. `eval --replan off` e um relatório pareado com e sem replanejamento, por critério e por rota.
3. ADR 0024 com o desenho alternativo, ganhos, perdas e condição de revisão.
4. Cancelamento de venda como escrita com confirmação explícita, idempotente e auditada.

## Decisões

| ID | Decisão | Motivo |
| --- | --- | --- |
| D1 | Resumo rolante por `summary.v1` (esforço mínimo, ≤ 200 tokens, mascarado), guardado com o id da última mensagem resumida; entregue a Router, Support e Personality como bloco de dados. Avança quando há pelo menos 3 turnos (6 mensagens) fora da janela ainda não resumidos; até 12 mensagens não resumidas ficam disponíveis aos agentes de resposta mesmo quando o histórico recente deles é menor. Cada chamada do resumo recebe o texto completo das mensagens que cobre, até 12 por chamada; o contexto dos agentes de resposta limita mensagens antigas a 600 caracteres cada. Se esse limite ou o limite de 12 mensagens omitir conteúdo, o contexto é marcado como incompleto até uma chamada de resumo bem-sucedida cobrir as mensagens; falha de provedor ou orçamento conserva o cursor anterior e o aviso. Mensagens além desse limite continuam armazenadas e entram no resumo em avanços posteriores. A chamada tem folga própria de uma por turno, fora de `max_model_calls` (o custo segue no ledger e no teto de custo do turno), e só roda depois da guarda de entrada | Uma chamada a cada 3 turnos numa conversa longa (8 em 30 turnos, contra 24 com uma chamada por avanço da janela); contexto antigo disponível em blocos limitados; o turno mantém o limite de chamadas inteiro |
| D2 | Registro de fatos por conversa (protocolos, valores, datas, produtos, status) extraído só de `ctx.outcomes` e de `cases.py`, com ferramenta e turno de origem; nunca do texto do modelo. A guarda de saída aceita valores do registro; o resumo nunca é fonte da guarda. Nos prompts, Support e Personality veem só os fatos de mensagens que já saíram da janela (protocolos primeiro, depois os mais recentes, até 40); `personality.v6` e `support.v8` dizem que fatos registrados podem ser citados exatamente como estão e que o resumo é contexto, nunca fonte de valor; o Router não recebe fatos | Números corretos em conversa longa sem confiar em texto gerado |
| D3 | `Settings.replan = on\|off`; com `off`, o grafo volta às arestas fixas da v0.7.0 (plano inicial do Router mantido; `knowledge → support` na rota combinada; `support → escalation` quando o Support pede humano; sem `replan` nem `web`). `eval --replan off` grava a configuração; `eval-compare --a --b` sem chamada gera o relatório pareado por caso, critério e rota, com bootstrap da diferença, e lista as decisões de origem `model` lidas dos traces | Medida do ganho no conjunto de casos |
| D4 | ADR 0024 (documento): supervisor com especialistas como ferramentas × grafo com replanejamento; ganhos e perdas (origem nomeada de cada decisão, garantias estruturais de saltos e escopo, testes reproduzíveis com modelo roteirizado, custo por decisão) e a condição que faria rever | Registro da escolha |
| D5 | `request_sale_cancellation(sale_id)` (escopo `support:write`) cria `pending_confirmation` com venda, valor e data; `confirm_sale_cancellation(request_id)` é executada por código, não por function calling, quando o turno seguinte é confirmação explícita (rótulo `confirmation` do Router com `yes\|no\|other`); `no` ou 2 turnos sem confirmação → `declined`/`expired`; idempotente; auditado; `support.v9` (o `support.v8` ficou com a regra dos fatos da D2) mostra o resumo e pede confirmação. Sem confirmação nada muda | Escrita segura no domínio |
| D6 | Migração **0014** reversível: `conversations.summary`, `conversations.summary_until_message_id`, `conversation_facts`, `sale_cancellation_requests` | Numeração do plano |

## Critérios de aceitação

- **CA-65** Conversa de 20+ turnos devolve protocolo e valor do início; resumo gerado em blocos de 3 turnos fora da janela (8 chamadas em 30 turnos), com folga própria fora do limite de chamadas do turno; valores aceitos pela guarda vindos do registro.
- **CA-66** Relatório pareado com e sem replanejamento por critério e rota, com intervalo, e as decisões de origem `model` listadas.
- **CA-67** Cancelamento só executa após confirmação explícita; repetição idempotente; recusa ou silêncio deixa a conta intacta; auditoria com o escopo de escrita.
- **CA-75** ADR 0024 aceita.

## Tarefas

92. [Resumo rolante e registro de fatos](../tasks/92-resumo-rolante-fatos.md).
93. [Ablação do replanejamento](../tasks/93-ablacao-replan.md).
94. [Cancelamento de venda com confirmação](../tasks/94-cancelamento-confirmacao.md).
95. [ADR 0024: desenho da orquestração](../tasks/95-adr-orquestracao.md).
96. [Documentação e metadados da versão](../tasks/96-fechamento-v0120.md).

Ordem: 92 e 95 em paralelo; depois 93; depois 94 (92 e 94 tocam a mesma migração).
