# Validação da v1.1.0

Registro da validação e da revisão independente da v1.1.0: consulta dos próprios tickets pelo lojista, retomada da conversa depois de recarregar a página, resposta da atendente com as palavras dela e disponibilidade de perfis e Routers conforme as chaves do backend. Critérios CA-76 a CA-79 da [especificação](../specs/tickets-retomada-v110.md), versão 0.4, e a [história](../historias/tickets-retomada-v110.md). Resultado consolidado: [v110-resultado.md](v110-resultado.md).

## Candidato

| Item | Valor |
| --- | --- |
| Backend integrado na `main` | commit `0345ccd` ("Release v1.1.0"), árvore `8fb5015`, pelo merge `cb4c312` (2026-11-11) |
| Interface integrada | commit `44408d8`, árvore `e2aa753`, pelo merge `507955b` na `main` do repositório da interface |
| Validação com modelo real | três campanhas na linha da versão; a terceira rodou sobre o mesmo código, os mesmos prompts e os mesmos testes do backend integrado. A coluna "Campanha" indica de qual vem cada medição |

## Ambiente

- Docker Desktop 29.8.0; o compose construiu a imagem do candidato; `/ready` com `ready: true`, aplicação 1.1.0, esquema 16, 145 trechos e prompts `support` 11, `personality` 7 e `router` 7.
- Só a chave da OpenAI; a `TYPESAFE_API_KEY` entrou no momento do JEV e saiu em seguida, com a API recriada nas duas vezes.
- Interface Streamlit; Chrome em modo headless, com eventos reais de mouse e teclado e popup real de login. Lojista com tela de celular emulada (412 × 915); operadora num contexto de navegador separado, a 1.440 px. Credenciais fictícias de `.env.example`.
- Três campanhas, cada uma com ledger novo: 1 (teto US$0,10), 2 (teto US$0,05) e 3 (teto US$0,03, só pela API).

## Momento a momento

| Momento | Esperado | Observado | Evidência | Campanha |
| --- | --- | --- | --- | --- |
| Disponibilidade (CA-78) | Só o que o backend executa, com a chave que falta nomeada | Padrão Referência e LLM. Híbrido e Ajustado "indisponível neste backend"; com o Híbrido escolhido, "falta `DEEPSEEK_API_KEY` no backend" e envio desabilitado. JEV desabilitado com "JEV indisponível: falta `TYPESAFE_API_KEY` no backend.", também nas comparações. `GET /v1/profiles` com `available`, `missing_providers` e `router_mechanisms` `{llm: true, jev: false}`, sem valor de chave | `GET /v1/profiles` | 1 |
| Recebíveis e encaminhamento | Datas, valores e protocolo | Pix R$ 80,00 creditado em 10/11, débito R$ 148,06 em 11/11 e crédito R$ 1.162,20 em 12/11, rota `support`; protocolo `HO-20261111-23B888` | `req_6a3d5b551c444aab8e6e`, `req_0c041ef68a764369b9cd` | 1 |
| Operadora responde pelo Ticketing | Confirmação na tela | "Ticket assumido. Ele aparece na fila Atendimento." e "Ação enviada e aceita pelo assistente." na primeira tentativa | `req_resume_c05cf806141742bc` | 1 |
| Retomada depois de recarregar (CA-77) | Última conversa com a resposta da atendente | "Conversa retomada" e **Nova conversa**; histórico com as perguntas, as respostas e o turno `Atendente humano`. `GET /v1/conversations` com o protocolo e `pending_operator_reply: true`, sem texto | `conv_7b4aeb5e21d742ad91e8` | 1 |
| Mensagem seguinte (CA-77) | Resposta à própria pergunta, sem repetir a da atendente | "E quando cai na conta?" recebe as datas do débito e do crédito; a resposta da atendente aparece uma vez na tela e na API; a lista passa a `pending_operator_reply: false`; "Obrigado" segue na mesma conversa | `req_d6b338be30f6442c83e5`, `req_f110b65916e14dcb9256` | 1 |
| Consulta de tickets (CA-76) | Protocolo e estado, pelo suporte, sem abrir caso | "Tenho algum ticket aberto?", "Qual o status do meu atendimento humano?" e "A atendente já respondeu meu ticket?", cada uma em **Nova conversa**: rota `support`, `get_handoff_cases`, protocolo e estado; `GET /v1/handoffs` continua com um caso | `req_f61290915686460883dd`, `req_362a8b988f6c4a72b8d7`, `req_32176b32b9db42119009` | 1 |
| Final do protocolo (CA-76) | O mesmo caso pelo final | `get_handoff_cases` com `protocol: "23B888"`; auditoria com o caso como recurso | `req_689afd859f694cfb938c` | 1 |
| Outro lojista (CA-76) | Nenhum dado do caso | `cliente_demo_002`, pelo mesmo final: "Não encontrei nenhum ticket com o protocolo terminado em 23B888…"; nada do caso nos dados da execução. Auditoria com 5 linhas para 5 chamadas, cada uma com o próprio lojista | `req_e3415469ee5d4874871a` | 1 |
| JEV com a chave (CA-78) | Tudo como antes | `jev: true`; mensagem pelo Router `typesafe:jev-1.14.0` (US$0,000109 no Router). Sem a chave, `jev: false`, e a sessão aberta volta a LLM com a frase | `req_0fdec9d3859e47bbb7b2` | 1 |
| Lista de conversas (CA-77) | Só o dono; limite | Operadora: 403 `insufficient_scope`; `limit=50`: 422; `limit=20`: as 5 conversas do dono; outro lojista vê só a própria; sem token: 401 | `req_f165fb13833d4e0fa35c`, `req_0fc42e9c5a624e17bcdd` | 1 |
| Resposta da atendente (CA-79) | Texto idêntico ao enviado | "Olá! Seu estorno de R$ 150,00 cai na conta em 14/11. Qualquer dúvida, estou por aqui." Retomada com `human_review` e `operator_reply`, 0 chamadas de modelo. Texto idêntico em `GET /v1/conversations/{id}`, no caso e na tela do lojista, sem frase acrescentada | `HO-20261111-F7FF45`, `req_resume_5ce818147b4c4bf6`, `req_dbedce99f70a443cbff4` | 2 |
| Aprovar o rascunho (CA-79) | Continua pela Personality | Retomada com `human_review`, `personality` e `output_guard`; uma chamada da Personality | `HO-20261111-F7A365`, `req_resume_b4ec4c40e6a84e8a` | 2 |
| Tickets com as palavras da atendente (CA-76, CA-79) | Estado em português e a resposta dela | Com os quatro casos respondidos: "Encontrei 4 tickets…", cada protocolo com a resposta da atendente, valor e data intactos, sem código de estado. Pelo final `F7FF45`: estado em português e a resposta idêntica à enviada | `req_55e5d21172224e7e90b2`, `req_df6acf7885a54857abab` | 2 |
| Retomada com duas respostas (CA-77) | Cada resposta uma vez | Segunda resposta da atendente (R$ 37,90 em 18/11); depois de recarregar, as duas respostas aparecem uma vez cada; a mensagem seguinte recebe resposta própria (R$ 1.162,20 em 12/11); a retomada não chama modelo | `HO-20261111-59CD18`, `req_f84c2f30be05421b8a96` | 2 |
| Registro de acesso | Login sem a query | Três logins: `GET /v1/auth/authorize` sem query; 0 ocorrências de `state=`, `code_challenge` ou `code=` no log da API; outras rotas mantêm a query | Log do contêiner da API | 2 |
| Lista com um ticket aberto e um respondido (CA-76) | Pergunta pelos abertos: protocolo e estado de cada ticket; pergunta por novidades: a resposta da atendente | "Tenho algum ticket aberto?" em três conversas novas: nas três, o aberto com o estado em português ("aguardando atendimento") e o respondido com protocolo e estado; numa delas, também a resposta integral da atendente. "Alguma novidade sobre meus atendimentos?": o aberto e a resposta da atendente, com R$ 212,40 e 19/11 intactos | `HO-20261111-726B02`, `HO-20261111-AC9860`; `req_edac3ed251eb4729a000`, `req_714e8136db9648b0a570`, `req_fb96930c767b4e05aa5c`, `req_dfe4dc53326c432795e0` | 3 |

Segredos: os valores das chaves de provedor e do Telegram foram procurados nos logs dos contêineres e da interface, nas respostas de `/v1/profiles`, nas evidências e nas capturas, com 0 ocorrências; nenhum JWT, `code` ou `state` nas evidências.

Suítes do candidato integrado: backend com 3.060 casos de teste, 3.059 aprovados e o caso do exportador OTLP, que roda com o extra `otel` na imagem e na CI; interface com 203 aprovados, 3 pulados (os módulos entre repositórios) e 6 de integração entre os repositórios.

## Custo

| Campanha | Teto | Gasto | Lançamentos |
| --- | ---: | ---: | ---: |
| 1 | US$0,10 | US$0,007820 | 44 |
| 2 | US$0,05 | US$0,006023 | 37 |
| 3 | US$0,03 | US$0,003759 | 25 |
| **Total** | | **US$0,017602** | 106 |

Todos os lançamentos liquidados; nenhum teto renovado.

## Revisão independente

A versão inteira e cada ajuste do backend e da interface passaram por revisão em contexto novo, sobre cópias dos candidatos, sem acesso às conclusões da implementação.

### Re-derivado

- **Isolamento de `get_handoff_cases`, inclusive pelo MCP:** com dois lojistas e o mesmo final de protocolo, cada um vê só o próprio caso; o protocolo completo de outro lojista devolve lista vazia; `demo` é recusado na fábrica do MCP; a consulta sempre parte do lojista do token; o filtro aceita só letras, dígitos e hífen, com pelo menos 4 alfanuméricos.
- **Origem da resposta da atendente:** o turno `via=operator` da conversa e do caso; com dois casos na mesma conversa, cada caso recebe só a própria resposta; valores e datas da resposta passam pela guarda de saída como evidência.
- **Lista de conversas:** dono, ordem e ausência de texto; `limit` 0, 21, `abc` e -1 respondem 422 e 20 responde 200; operador e serviço recebem 403; sem token, 401.
- **Disponibilidade:** uma regra única de chave por provedor, usada pela fábrica de modelos e pela rota; nenhum valor de chave no corpo; a interface trata backend sem os campos novos como tudo disponível.
- **Confirmação da resposta exibida:** só marca turno de atendente pendente da mesma conversa e do mesmo lojista, junto com os anteriores já exibidos; conversa de outro lojista responde 404; resposta mais nova da atendente continua entregue; a rota legada `POST /messages` recusa o campo com 422.
- **Resposta da atendente sem reescrita:** `reply` termina sem chamada de modelo; o mesmo texto vai ao turno gravado, à resposta da retomada e ao webhook do lojista, que mascara dado sensível como todo evento de saída; `approve` e `reject` passam pela Personality e pela guarda de saída; casos abertos com o código anterior retomam sem migração.
- **Registro de acesso:** com `uvicorn` real e dois workers, a query de `/v1/auth/authorize` fica fora do log nos dois processos; as demais rotas mantêm a query.
- **Prompt `support.v11`:** cada ticket com resposta de atendente vem com a resposta nas palavras dela; as regras 1 a 14 são idênticas às do `support.v10`.
- **Contrato da interface:** o `openapi-v1.json` da interface é idêntico à exportação do backend, versão 1.1.0.

### Testes rodados

- Versão inteira: suíte estrita do backend com 3.039 aprovados e 1 pulado; interface com 195 aprovados e 3 pulados; 6 testes de integração entre os repositórios.
- Retomada: 63 testes focados e 289 de regressão no backend; 202 na interface; 6 entre os repositórios.
- Resposta da atendente e registro de acesso: 437 testes focados e 1 pulado; 24 da retomada na interface.
- Candidato final: 144 testes focados e os 7 da resposta da atendente.

### Mutações

| Escopo | Mutações aplicadas | Não detectadas no código final |
| --- | ---: | --- |
| Tickets, lista de conversas e disponibilidade (backend) | 15 | 1 equivalente |
| Tickets, lista de conversas e disponibilidade (interface) | 8 | nenhuma |
| Confirmação da resposta exibida (backend) | 13 | 1 equivalente |
| Confirmação da resposta exibida (interface) | 8 | 2 equivalentes |
| Resposta da atendente sem reescrita e registro de acesso | 14 | 1 cosmética (lista de agentes na resposta da retomada) |
| Regra do prompt de suporte e cópia por webhook | 8 | nenhuma |

### Conclusão

Apto em todos os escopos; a última conferência terminou sem nenhum ponto em aberto. As decisões estão na [especificação](../specs/tickets-retomada-v110.md) e na emenda da [ADR 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).
