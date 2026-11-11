# Validação da v0.12.0

Registro da validação e da revisão independente da v0.12.0: memória de conversa longa, replanejamento medido com e sem o recurso e cancelamento de venda com confirmação explícita. Critérios CA-65, CA-66, CA-67 e CA-75 da [especificação](../specs/memoria-escrita-v0120.md). Resultado consolidado: [v0120-resultado.md](v0120-resultado.md).

## Candidato

| Item | Valor |
| --- | --- |
| Integrado na `main` | commit `02df79b` ("Release v0.12.0"), árvore `ee4f8a4`, pelo merge `4d4843b` (2026-11-09) |
| Validação do candidato integrado | suíte estrita e percursos com modelos roteirizados, na mesma árvore |
| Validação com modelo real | campanha `v0120-qa`, na linha de desenvolvimento da versão, antes da integração sobre a v0.11.0 |

## Ambiente

- **Candidato integrado:** sem rede, sem Docker e sem chamada paga; modelos roteirizados; padrões `judge.v5` e retrieval híbrido com rerank ligado.
- **Modelo real:** API local (`uvicorn`) e CLI, caixa-preta, sem Docker nem interface; runtime e ledger isolados; agente `gpt-6-luna`; Router `jev-1.14.0` quando pedido; juiz `deepseek/deepseek-flash` com `judge.v3` na ablação; embeddings `text-embedding-3-small`; lojista sintético `cliente1988` e operadora sintética `op_ana`; teto da campanha US$0,60.

## Candidato integrado, com modelos roteirizados

| Verificação | Resultado |
| --- | --- |
| Suíte estrita | 2.698 testes aprovados, sem falhas nem pulados; Ruff, links, caminhos pessoais e skills limpos |
| Conversa longa | 27 turnos com fatos exatos, aviso e recuperação do contexto incompleto |
| Cancelamento | confirmação, idempotência, recusa, expiração e isolamento entre lojistas |
| Replanejamento | 4 casos pareados pela CLI: 0 decisões de origem `model` com `REPLAN=off` e 8 com `REPLAN=on` |
| Arquivos selados | CSVs e prompts da v0.11.0 idênticos byte a byte; os dois holdouts conferidos pelo hash normalizado, sem abrir os casos |

## Validação com modelo real, momento a momento

| Momento | Esperado | Observado | Evidência |
| --- | --- | --- | --- |
| Ablação do replanejamento (CA-66) | Relatório pareado por critério e rota, com intervalo, e decisões de origem `model` listadas | Desenvolvimento, 44 pares: aprovados B − A = +0,045, IC 95% [−0,045; +0,136]. Holdout, 25 pares: −0,080, IC [−0,240; +0,080]. Nenhum critério com intervalo que exclua o zero. Decisões `model`: 2 de 49 no desenvolvimento e 2 de 27 no holdout, nenhuma recusada pela guarda. Lado `off` sem passo `web` nem `replan` nos 69 casos | Bootstrap com 2.000 reamostras, semente 93; uma execução por lado |
| Conversa longa (CA-65) | Protocolo e valor do início devolvidos depois de 20 turnos ou mais | 29 turnos, com renovação do token depois do 20º, na mesma conversa. Turnos 25 a 29 devolvem `SIM-BND-1988-001`, R$ 1.200,00 e R$ 1.162,20; no turno 27, sem nenhuma ferramenta, só pelo registro de fatos | `conv_34d57585e27449089169`; `req_ee20e98847344721bd6c`, `req_a33646ac9a6e43738bae`, `req_5d7e0beb4e634f3bace9` |
| Resumo e fatos (CA-65) | Resumo em blocos de 3 turnos; fatos com origem | Passo `summary` nos turnos 9, 12, 15, 18, 21, 24 e 27 (7 chamadas em 27 turnos, US$0,00121). `summary` com 798 caracteres e 20 `facts`, cada um com a mensagem de origem. `checks.violations` vazio em todos os turnos | `GET /v1/conversations/{id}` |
| Pedido de cancelamento (CA-67) | Venda certa e pedido de "sim" ou "não" uma única vez | 11 de 11 pedidos com a linha fixa uma vez: débito, parcelada, link, link com `jev`, Pix em duas conversas e "Sim" que refaz o pedido | `req_0b9fe5152fa244da8100`, `req_59271328ccb743b0876e`, `req_a7ffe363d2324ee184ff` |
| Confirmação (CA-67) | Escrita só depois do "sim"; repetição idempotente | 3 de 3 confirmações com protocolo; "Sim" repetido devolve o mesmo protocolo, sem registro novo | `CAN-20261107-8B4A3E`, `CAN-20261107-8C49FA` (`jev`; repetição `req_c4df2c1eb8c54f4c9a41`), `CAN-20261107-1E49F3` |
| Recusa e silêncio (CA-67) | Conta intacta | 4 "Não" e 3 turnos sem resposta sem nenhum registro em `sale_cancellations`; o pedido sem resposta fica `pending_confirmation` | Banco do runtime lido em modo somente leitura |
| Auditoria (CA-67) | Escrita com o escopo de escrita | `request_sale_cancellation` (11), `confirm_sale_cancellation` (3), `decline_sale_cancellation` (4) e `count_unanswered_cancellation_turn` (3), todos `ok`, com `support:write` e principal `merchant:cliente1988` | `audit_events` |
| Status de cancelamento | Bloco de status só em pergunta de cancelamento | 7 de 7 "Quanto vendi ontem?" sem o bloco; 2 de 2 perguntas de cancelamento com o status escrito pelo código, uma linha por venda; 2 de 2 perguntas de procedimento (português e inglês) respondidas pela Knowledge; o "Sim" confirma uma vez, com protocolo | `req_6f7e7c0c58f54708a109`, `req_43fa51a67dba448f842b`, `req_0b917897663a41dc9489`, `CAN-20261108-8147E5` |
| Atendente | Texto da atendente intacto | `reply`, `approve` e `reject` depois de pedido expirado chegam com `via=operator`, sem linha trocada nem acrescentada | `HO-20261107-6AC237`, `HO-20261107-8FA607`, `HO-20261107-EA06ED` |

## Custo

Campanha `v0120-qa`: US$0,47133030 (teto US$0,60), em 1.485 lançamentos, todos liquidados. A validação do candidato integrado não usou chamada paga.

## Revisão independente

Cada tarefa e a versão inteira passaram por revisão em contexto novo, sobre clone limpo, sem acesso às conclusões da implementação.

### Re-derivado

- **Memória:** o resumo tem folga própria fora de `max_model_calls`, ainda dentro do custo do turno, do teto e do ledger; roda depois da guarda de entrada; avança em blocos de 3 turnos (8 chamadas em 30 turnos). Cada agente vê os fatos anteriores ao próprio histórico (Support 8 mensagens, Personality 4); a guarda de saída lê o registro inteiro.
- **Ablação:** com `REPLAN=off`, arestas idênticas às do grafo da v0.7.0 e nenhum passo `replan` ou `web` nos 69 casos; com o padrão `on`, traces e respostas idênticos byte a byte nos 69 casos, com os protocolos mascarados. `eval --replan` e `eval-compare` reproduzíveis byte a byte.
- **Cancelamento:** confirmar e recusar ficam fora das ferramentas oferecidas ao modelo e do MCP. O "sim" só vale com pedido pendente no banco e leitura determinística da mensagem inteira. Sondas como "sim, cancela a outra", "sim, não", marcação de sistema forjada, caracteres invisíveis e letra cirílica não executam nada. O pedido é gravado em transação, com teste de corrida.
- **Status e atendente:** o status de cancelamento é escrito pelo código, uma linha por venda consultada; o texto do atendente chega intacto; nenhuma venda de outro lojista nem dado sem máscara na consulta ou no bloco.
- **Comparação de Routers:** a decisão do modelo gravada na comparação, reaplicada, chega à mesma decisão validada; decisão adulterada, de outra conversa ou de estado mudado não executa nada (`409` ou falha fechada).
- **Migração 0014** nos dois sentidos sobre banco com dados; a descida é recusada com pedido confirmado. OpenAPI e MCP só com acréscimos.
- **ADR 0024:** números conferidos contra as evidências e afirmações conferidas contra o código (regras do replanejador, arestas do grafo, limites e garantias das ferramentas).
- **Candidato integrado:** preservação da v0.11.0, comportamento do resumo e limites de chamadas com o rerank ligado.

### Testes rodados

- Suíte estrita em clone limpo em cada escopo revisado, de 2.383 a 2.563 testes aprovados conforme o escopo.
- 236 testes dos arquivos da versão; 14 sondas próprias na linha fixa do pedido; o detector do bloco de status comparado com 7.662 textos do repositório, sem regressão.

### Mutações

| Escopo | Mutações aplicadas | Não detectadas no código final |
| --- | ---: | --- |
| Resumo e registro de fatos | 36 | 1 equivalente; 1 sem teste dedicado (guarda lendo só os fatos do prompt), com o código correto |
| Ablação do replanejamento | 45 | só equivalentes numa comparação `off` × `on` |
| Cancelamento com confirmação | 33 | 1 equivalente; 1 de defesa em profundidade (reaplicação da linha fixa depois da guarda de saída) |
| Versão inteira (tarefas 92 a 95 integradas) | 43 | 2 equivalentes; 1 na regra de estado do caso pela comparação |
| Decisão do Router gravada na comparação | 13 | nenhuma |
| Status de cancelamento, memória e linha de confirmação | 15 | 1 |

Nas regras da linha fixa do pedido e do bloco de status, todas as mutações aplicadas foram detectadas.

### Conclusão

Apto em todos os escopos; ADR 0024 aceita (CA-75). Decisões de produto registradas: o pedido de cancelamento expira em dois turnos sem resposta, não por tempo; respostas curtas valem como "sim" quando o modelo concorda.
