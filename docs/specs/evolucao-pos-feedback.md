<!-- Papel: especificação da evolução do case após o feedback V4 do avaliador (2026-11-03), com a meta de nota 9,5+. -->

# Especificação: evolução pós-feedback (v0.7.0 a v1.0.0)

Versão 0.2 — 2026-11-03 — **aprovada em parte pelo responsável** (Q14, Q15 e Q17 respondidas; Q16 decidida nesta versão; Q18 sem prazo informado pelo avaliador). Reabre a expansão funcional encerrada pela [ADR 0015](../architecture/decisions/0015-recorte-final-v060.md) por meio da [ADR 0016](../architecture/decisions/0016-reabertura-pos-feedback.md). O plano técnico derivado está em [evolucao-pos-feedback-plano.md](evolucao-pos-feedback-plano.md).

Mudanças da 0.1 para a 0.2: webhook e integração de ticketing entram na v0.7.0; `POST /messages` sem modo aberto; ações do operador nomeadas como no feedback (`approve`, `reply`, `reject`); reranker medido, não condicional; v0.10.0 nova para operação e resiliência; matriz de cobertura do e-mail; seção de eficiência de execução.

## Problema

A v0.6.0 recebeu do avaliador a nota **8,6/10** (quadro V4, confiança alta). A referência para aprovação é acima de 9, idealmente 9,5+. O avaliador foi objetivo sobre o que separa o case da faixa 9+:

1. **Human-in-the-loop (HITL) simulado** (7% do peso, nota 4,0): o encaminhamento grava um caso local com protocolo `SIM-…` e termina. Não existe fila de operador, identidade de operador, resposta humana que volte ao agente, nem interrupção e retomada do fluxo. "Não há integração operacional real com humano/ticketing que devolva a resposta ao agente e permita continuidade do fluxo."
2. **Identidade externa incompleta** (13%, nota 7,8): `user_id` continua sendo autoridade do payload de `POST /messages`. O isolamento contra o modelo é forte, mas falta credencial → principal autenticado → autorização → lojista, com cada tool call autorizado.
3. **Orquestração pré-definida** (15%, nota 8,5): a rota combinada Knowledge → Support é colaboração real, mas não há ciclo observar resultado → Router reconsidera → replanejar → outro agente → revisar, com limite de saltos.
4. **Qualidade semântica agregada** (14%, nota 9,0): o juiz por modelo existe, mas o relatório principal não traz groundedness, correção, relevância e utilidade agregadas, juiz independente, múltiplas execuções, calibração humana nem holdout. As jornadas de negócio ficaram 7/13 pela rubrica literal.
5. **Retrieval sem holdout e sem híbrido** (10%, nota 9,4): Recall@6 = 1,00 num conjunto pequeno usado durante o desenvolvimento; sem BM25 + denso, RRF ou reranker.
6. **Production Engineering** (5%, nota 9,0): `/messages` sem auth; handoff sem integração humana; comparação em thread do processo; acesso externo não testado; credenciais de demo/admin a configurar pelo responsável.

O texto integral do feedback está em `discovery/feedback-v4-2026-11-03.md` (material local, não versionado).

## Cobertura do e-mail, ponto a ponto

Cada ressalva do avaliador, onde é atendida e em que versão. Nenhuma ressalva fica sem item.

| Dimensão | Ressalva do avaliador | Requisito | Versão |
| --- | --- | --- | --- |
| Agentic | Sem loop observar → reconsiderar → replanejar → outro agente → revisar | RF-86, RF-87 (o passo `finish` só depois da revisão do resultado) | v0.8.0 |
| Agentic | Fluxo combinado pré-definido, sem planner adaptativo | RF-86, RF-88 | v0.8.0 |
| Memória | Sem gap explícito; "comparação perdida em reinício fica `failed`" (Production) | RF-104 (comparação retomável), RF-105 (resumo rolante de conversas longas), checkpoint durável do grafo (RF-82) | v0.10.0, v0.7.0 |
| RAG | Amostra pequena e usada no desenvolvimento, não é holdout | RF-95 | v0.9.0 |
| RAG | Sem hybrid BM25+dense, RRF, reranker | RF-94, RF-96 (reranker implementado e medido) | v0.9.0 |
| Security | `user_id` não é autenticação; falta credential → principal → authorization → merchant | RF-76, RF-77 | v0.7.0 |
| Security | "autorizar cada tool call" | RF-78 (escopo por tool call, auditoria com principal em todo acesso) | v0.7.0 |
| HITL | Handoff simulado, sem fila, sem operador | RF-80, RF-81 | v0.7.0 |
| HITL | Sem interrupt → human → reply → agent resumes | RF-82 | v0.7.0 |
| HITL | reply/approve/reject | RF-81 (ações com esses nomes) | v0.7.0 |
| HITL | Idempotência / double-resume protection | RF-83 | v0.7.0 |
| HITL | Sem integração operacional com humano/ticketing que devolva a resposta | RF-84, RF-85, RF-100 (webhooks assinados nos dois sentidos, receptor de ticketing na demo) | v0.7.0 |
| Evaluation | Jornadas 7/13 pela rubrica literal | RF-93 | v0.8.0 |
| Evaluation | Sem groundedness, correctness, relevance, usefulness agregadas | RF-89 | v0.8.0 |
| Evaluation | Avaliação por IA não é revisão humana | RF-91 | v0.8.0 |
| Evaluation | Juiz independente, múltiplas runs, calibração humana, holdout | RF-90, RF-91, RF-92 | v0.8.0 |
| Observability | "Production next steps" só descritos (OTel, dashboards, alertas) | RF-97 (métricas, OTLP, regras de alerta e painel versionados) | v0.10.0 |
| Production | Core `/messages` sem auth | RF-76 | v0.7.0 |
| Production | Comparação em thread do processo | RF-104 | v0.10.0 |
| Production | Acesso externo não testado | RF-98 | v1.0.0 |
| Production | Credenciais demo/admin a configurar pelo responsável | RF-77 (chaves sintéticas no `.env.example`; `docker compose up` funciona sem edição) | v0.7.0 |
| Production | Sem CI | RF-103 | v0.10.0 |
| Gate Semantic Quality | Pass com ressalvas | RF-89 a RF-93 | v0.8.0 |
| Comparação com o perfil ideal | HITL, identidade, adaptive agency, semantic evaluation | coberto acima | — |

## Usuário afetado

- **Avaliador** do desafio: precisa encontrar, em cada dimensão do quadro V4, evidência verificável de que o gap foi fechado.
- **Operador humano** (novo papel): recebe casos encaminhados, responde, aprova ou rejeita o rascunho do agente.
- **Lojista** (demo): autentica-se com credencial própria; recebe a resposta humana dentro da mesma conversa, por consulta ou por webhook.
- **Sistema de ticketing** (demo): recebe o caso encaminhado por webhook e devolve a resposta pela API.
- **Responsável** (Lauro): decide escopo, orçamento e ordem; calibra a avaliação semântica com notas humanas.

## Resultado desejado

Uma nova submissão (`main`, tag `v1.0.0`) em que cada gap do feedback tem uma mudança de código, um teste determinístico, uma validação com modelos reais e uma linha no README apontando para a evidência. Projeção de nota com as metas abaixo (pesos do quadro V4):

| Critério | Peso | Hoje | Meta | Ganho na final |
| --- | ---: | ---: | ---: | ---: |
| Human Oversight & Risk Management | 7% | 4,0 | 9,5 | +0,39 |
| Security & Identity | 13% | 7,8 | 9,5 | +0,22 |
| Agentic Reasoning & Orchestration | 15% | 8,5 | 9,5 | +0,15 |
| Evaluation & Quality Engineering | 14% | 9,0 | 9,7 | +0,10 |
| Context, Knowledge & RAG | 10% | 9,4 | 9,8 | +0,04 |
| Memory, State & Resilience | 8% | 9,0 | 9,5 | +0,04 |
| Production Engineering | 5% | 9,0 | 9,5 | +0,03 |
| Observability, Reliability & Cost | 6% | 9,2 | 9,6 | +0,02 |
| **Projeção** | | **8,6** | | **≈ 9,6** |

## Escopo

Cinco entregas curtas e um fechamento, cada uma com spec complementar curta, tarefas, revisão independente e QA real, como nas versões anteriores. O responsável prefere mais versões a versões maiores (Q17).

| Versão | Entrega | Gaps |
| --- | --- | --- |
| **v0.7.0 — Identidade e HITL real** | Credenciais por lojista e por operador; principal autenticado e escopo em todo tool call; `user_id` sem autoridade; fila persistente de operador; interrupção e retomada do grafo; `approve`/`reply`/`reject`; idempotência e proteção contra retomada dupla; webhooks assinados (caso criado, resposta pronta) e receptor de ticketing na demo | 1, 2, 6 |
| **v0.8.0 — Orquestração adaptativa e avaliação semântica** | Nó de replanejamento com orçamento de saltos; rubrica de quatro critérios com juiz independente, três execuções, calibração humana e holdout de respostas; correção das jornadas | 3, 4 |
| **v0.9.0 — Retrieval híbrido** | BM25 + denso com RRF; reranker medido; holdout de retrieval; nDCG | 5 |
| **v0.10.0 — Operação e resiliência** | `/metrics`, OTLP, regras de alerta e painel versionados; CI; comparação retomável após reinício; resumo rolante de conversas longas | 6 e margem |
| **v1.0.0 — Fechamento e ressubmissão** | README "Resposta ao feedback", evidência consolidada, túnel externo testado, vídeo curto dos deltas | todos |

## Fora do escopo

- Ticketing comercial (Zendesk, Jira, Teams): o contrato de webhook é documentado e demonstrado contra um receptor próprio; um adaptador real é configuração de URL e segredo.
- Provedor de identidade externo (OIDC): o ponto de troca fica isolado na criação de sessão; a credencial da demo é chave por lojista com sessão.
- Evaluation Agent autônomo e ciclo de propostas (mantido fora, ADR 0015).
- Novas jornadas de negócio ou novas ferramentas de Support.
- Treinamento ou ajuste fino de modelos.

## Requisitos funcionais

### Identidade (v0.7.0)

- **RF-76** Toda chamada a `POST /messages` e `POST /v1/messages` exige sessão autenticada; o lojista é derivado do principal. Não existe modo sem autenticação. `user_id` no payload passa a ser opcional e, quando presente e diferente do principal, a requisição recebe `403 identity_mismatch`. O smoke, o `/docs` e o README mostram a criação de sessão em uma chamada.
- **RF-77** Credenciais sintéticas por lojista (dois lojistas da seed) e por operador, configuráveis por variável de ambiente, presentes no `.env.example` e documentadas como fictícias, para que `docker compose up` funcione sem edição; sessões com expiração e revogação, como as atuais de demo e admin; limite de requisições por principal.
- **RF-78** Cada sessão carrega escopos derivados do papel (`support:read`, `handoff:operate`, `kb:admin`, …); cada ferramenta declara o escopo exigido; a execução verifica escopo e lojista antes de rodar; todo tool call, aceito ou recusado, gera registro de auditoria com o principal. O MCP passa a exigir a chave do lojista.
- **RF-79** O ponto de troca por um provedor de identidade externo é um único adaptador (`resolve_credential`), descrito na ADR e no README com o diagrama credencial → principal → escopos → lojista.

### HITL (v0.7.0)

- **RF-80** O caso encaminhado entra numa fila persistente com estado (`open`, `claimed`, `answered`, `rejected`, `closed`), operador responsável, carimbo e histórico de eventos.
- **RF-81** O operador lista a fila, reivindica um caso e executa uma de três ações: **approve** (libera a resposta rascunhada pelo agente), **reply** (texto próprio ao lojista) ou **reject** (recusa o rascunho com uma instrução; o agente continua, por exemplo "verifique o status do dispositivo antes de responder").
- **RF-82** A ação do operador volta ao grafo: o fluxo é retomado do ponto de interrupção, passa por Personality e guarda de saída, grava o turno na conversa e atualiza o estado do caso. `reject` reexecuta o especialista com a instrução, limitado a um ciclo; o estado do grafo fica durável entre a interrupção e a retomada.
- **RF-83** A mesma ação enviada duas vezes (chave de idempotência) devolve o resultado existente; uma segunda retomada de um caso já retomado é recusada com `409 already_resumed`.
- **RF-84** O lojista recebe a resposta humana: na próxima mensagem da conversa, ao consultar a conversa, ou por webhook assinado (RF-100). A resposta sai marcada como vinda de um atendente e o caso passa a `awaiting_customer` ou `resolved` conforme a ação.
- **RF-85** A fila e as ações existem na API, na CLI (`merchant-assistant operator …`) e numa área "Operador" da interface Streamlit.
- **RF-100** Webhooks: ao criar um caso encaminhado, o sistema envia o caso a `HANDOFF_WEBHOOK_URL` (ticketing); ao concluir a retomada, envia a resposta a `CONVERSATION_WEBHOOK_URL` ou à URL registrada na sessão. Entregas assinadas com HMAC, com até três tentativas e registro de entrega consultável. O serviço `mocks` do compose ganha um receptor de ticketing que registra os casos recebidos, para a demonstração mostrar a ida e a volta.

### Orquestração adaptativa (v0.8.0)

- **RF-86** Depois de cada especialista, um passo de replanejamento observa o resultado (evidência suficiente, informação faltante, falha de ferramenta, pedido de seleção, instrução do operador) e decide entre concluir, acionar outro especialista, buscar na web, escalar ou pedir esclarecimento. Concluir exige que a revisão do resultado o considere completo para a pergunta.
- **RF-87** O replanejamento é limitado por orçamento de saltos (padrão 3), nunca repete o mesmo especialista sem informação nova e respeita os limites atuais de chamadas, tempo e custo; cada decisão fica no trace com o motivo e a origem (regra ou modelo).
- **RF-88** Ao menos quatro cenários rotulados exercitam o replanejamento com modelo programado e com modelos reais: conhecimento insuficiente → web; suporte com lacuna de procedimento → conhecimento; falha de ferramenta → escalada; pergunta de produto que depende da conta → suporte.

### Avaliação semântica (v0.8.0)

- **RF-89** Rubrica `judge` v3 com quatro critérios (groundedness, correção factual, relevância, utilidade) em escala 1–5, cada um com justificativa curta, e um veredito crítico booleano para afirmação sem suporte; o juiz recebe o conteúdo das evidências (trechos e resultados de ferramenta), não só os títulos.
- **RF-90** Juiz independente: provedor ou modelo diferente do perfil avaliado, registrado em cada avaliação; a campanha roda cada caso três vezes e reporta média, dispersão e concordância.
- **RF-91** Calibração humana: o responsável avalia uma amostra (mínimo 24 respostas) com a mesma rubrica; o relatório traz a concordância humano × juiz por critério.
- **RF-92** Holdout de respostas: conjunto novo (mínimo 20 casos, metade em português), escrito depois do congelamento dos prompts e nunca usado em ajuste; resultados reportados separados dos casos de desenvolvimento.
- **RF-93** Jornadas de negócio: as quatro falhas de redação e a pergunta de condições em inglês passam na rubrica, por ajuste de prompt ou de rótulo justificado caso a caso.

### Retrieval (v0.9.0)

- **RF-94** Recuperação híbrida: BM25 sobre os chunks + denso, fundidos por RRF, com a mesma filtragem por tipo de fonte; comparação denso vs híbrido em dev e holdout.
- **RF-95** Holdout de retrieval: mínimo 20 perguntas novas, com paráfrases e perguntas difíceis, rotuladas antes de medir.
- **RF-96** Reranker (modelo, esforço mínimo) sobre os 12 primeiros do híbrido, configurável; medido em dev e holdout com e sem; ligado por padrão só se melhorar, e a decisão fica registrada com os números.

### Operação e resiliência (v0.10.0)

- **RF-97** `GET /metrics` em formato Prometheus (mistura de rotas, encaminhamentos, bloqueios de guarda, latência, custo); exportação OTLP opcional dos spans; regras de alerta (taxa de erro, consumo de orçamento, deriva do score de retrieval) e um painel versionados em `observability/`.
- **RF-103** CI no GitHub (`validate.yml`): Ruff e suítes estritas do backend em cada PR e push na `main`, sem chamadas pagas.
- **RF-104** Comparação de perfis como trabalho retomável: estado persistido por célula; reinício da API retoma o que faltava em vez de marcar `failed`.
- **RF-105** Conversas longas: além das últimas dez mensagens, um resumo rolante das anteriores, gerado uma vez e reaproveitado, entregue a Router, Support e Personality como dado.

### Fechamento (v1.0.0)

- **RF-98** Acesso externo testado por túnel documentado, com evidência.
- **RF-99** README com a seção "Resposta ao feedback": uma linha por dimensão do quadro V4 → o que mudou → evidência; CHANGELOG e vídeo curto (10–15 min) só sobre os deltas.

## Requisitos não funcionais

- **RNF-11** Nenhum teste automatizado faz chamada paga; validação real por campanha com teto fixo, como hoje.
- **RNF-12** Orçamento total das validações reais: até US$1,00 adicional (acumulado do projeto hoje: US$0,69 de US$5,00).
- **RNF-13** Migrações reversíveis e aditivas; contrato `/v1` aditivo; a quebra de `POST /messages` (sessão obrigatória) é a única mudança incompatível e vem documentada no CHANGELOG.
- **RNF-14** Toda nova decisão estrutural (identidade, retomada do grafo, webhooks, híbrido) tem ADR.
- **RNF-15** O fluxo de execução segue a seção "Eficiência de execução" abaixo, depois de aprovada.

## Casos de uso

- **UC-20 Encaminhamento com retorno humano.** Lojista pede atendente → Escalation grava o caso → webhook ao ticketing → grafo interrompe → operador aprova, responde ou rejeita → o grafo retoma, Personality redige, guarda de saída valida → webhook ao lojista e resposta visível na conversa, com a marca de atendente.
- **UC-21 Rejeição com instrução.** Operador rejeita o rascunho com "verifique o status do dispositivo e responda" → Support reexecuta com a instrução → resposta ao lojista sem nova intervenção humana.
- **UC-22 Identidade.** Sessão do `cliente1988` pede dados; payload com `user_id` de outro lojista recebe `403`; auditoria registra principal e escopo em cada tool call.
- **UC-23 Replanejamento.** Pergunta de produto sem evidência nas páginas oficiais → replanejador escolhe web ou esclarecimento, dentro do orçamento de saltos, com trace do motivo.
- **UC-24 Avaliação agregada.** Campanha real com juiz independente, três execuções e amostra calibrada por humano, reportada no README por critério, dev e holdout separados.

## Critérios de aceitação

| ID | Critério | Como comprovar |
| --- | --- | --- |
| CA-46 | Sem sessão, `POST /messages` responde `401`; com sessão de outro lojista, `403`; dado de outro lojista nunca aparece; todo tool call tem auditoria com principal | Testes de integração e caso real na campanha |
| CA-47 | Caso encaminhado aparece na fila e no receptor de ticketing; `approve`, `reply` e `reject` produzem turno na conversa com a marca de atendente e entrega por webhook registrada | Testes com modelo programado; QA real na interface e no receptor |
| CA-48 | Retomada dupla recusada com `409`; ação repetida com a mesma chave devolve o registro existente; retomada funciona após reinício da API | Teste de unidade com transação concorrente; teste de integração com reinício |
| CA-49 | Quatro cenários de replanejamento passam com modelo programado e com modelos reais; nenhum caso ultrapassa 3 saltos; trace mostra cada decisão | Suíte estrita e campanha real |
| CA-50 | Relatório de avaliação com quatro critérios, juiz independente, 3 execuções, concordância humano × juiz e holdout separado | `docs/evidence/v080-*.md` e README |
| CA-51 | Jornadas de negócio ≥ 12/13 pela rubrica | Campanha real |
| CA-52 | Tabela denso × híbrido × híbrido+reranker em dev e holdout (Recall@6, MRR, nDCG@6), com a decisão registrada | `merchant-assistant eval-retrieval` |
| CA-53 | `/metrics` lido por um scrape de teste; regras de alerta validadas por `promtool`; CI verde na `main`; comparação retomada após reinício; conversa de 30 turnos mantém o contexto pelo resumo | Evidência com captura e testes |
| CA-54 | README "Resposta ao feedback" cobre as 11 dimensões; túnel testado; vídeo dos deltas publicado | Revisão do responsável |

## Eficiência de execução

Comparação com o fluxo do `ampeli-sdd` (mesmo template, evoluído entre setembro e novembro de 2026). O que já existe lá e cabe aqui, em ordem de ganho:

| Prática do ampeli-sdd | Efeito aqui | Precisa de |
| --- | --- | --- |
| **Autorização por versão** (AGENTS.md do Ampeli, 14/09): o ciclo avança sem esperar o responsável até a entrega de uma versão: implementar, revisar, corrigir, QA real dentro do teto, evidência, merge local. Ficam com ele: tag, push da `main`, mudança de AGENTS.md/CLAUDE.md/credenciais, calibração humana e ressubmissão | Elimina a espera entre cada passagem (na v0.6.0 houve seis decisões intermediárias); uma versão por noite de fluxo contínuo | Aprovação de uma emenda ao AGENTS.md (texto proposto no plano) |
| **Subagentes nativos em `.claude/agents/`** com modelo, esforço, ferramentas e limites no frontmatter (Developer com Edit/Write; Reviewer sem; QA com navegador) | Despacho sem reescrever limites a cada vez; limites impostos pela ferramenta, não só pelo texto | Aprovação (AGENTS.md pede autorização para subagentes e para `.claude/`) |
| **Modelo por papel medido**: linha de base Developer Sonnet medium / Reviewer e QA Opus high; ciclo Opus xhigh em medição (≈ US$4,60 e 20 min por ponto, 4 correções em 9 PRs) | Escolha com número, não por intuição; `medir-agentes.py` portado com o caminho do projeto | Nada além de copiar o script |
| **Dois escritores em paralelo** quando os arquivos não se tocam (backend e projeto web; `replan` e avaliação) | v0.7.0 e v0.8.0 encurtam em cerca de um terço | Já permitido pelo protocolo |
| **CI (`validate.yml`)** rodando Ruff e suítes estritas | Reviewer e QA param de repetir a suíte inteira; evidência automática; ponto em Production Engineering | RF-103 |
| **Despertador de 20 minutos** do Supervisor | Nenhuma passagem fica sem tratamento (no Ampeli, um retorno ficou 2h40 parado) | Agendamento na sessão |
| **Relatório do Supervisor por blocos de horário** (`docs/relatorios/`) | O responsável acompanha de manhã o que rodou à noite, com "Falta" e "Depende de você" | Copiar o modelo |
| `checar-memoria.ps1` e `limpar-ambiente.ps1` | Docker + Qdrant + dois agentes no notebook de 8 GB sem travar; limpeza após cada QA | Copiar e adaptar os alvos |
| Corpo de PR por arquivo (`--body-file`) | Evita corrupção de `|` e `&` no Windows (incidente do Ampeli) | Hábito |

Não se aplica: GitHub Apps por papel (`as-app.py`), rulesets da `main` (repositório de uma pessoa, merge local), pontos Fibonacci e planning poker (custo de cerimônia sem ganho neste prazo).

**Estimativa recalibrada.** Com a régua do Ampeli (40 pontos por noite de fluxo contínuo em Opus xhigh; a v0.6.0 deste case saiu em um dia com três passagens) e com os itens acima aprovados: v0.7.0 em uma noite mais uma hora de revisão do responsável; v0.8.0 em uma noite mais uma hora de calibração; v0.9.0 e v0.10.0 em meia noite cada; v1.0.0 em meio dia mais o vídeo. **Cerca de quatro noites de fluxo e um dia do responsável**, contra os 6 a 9 dias da versão 0.1. Sem a autorização por versão, cada noite vira dois dias.

## Riscos

| Risco | Efeito | Mitigação |
| --- | --- | --- |
| Interrupção do grafo exigir checkpointer e mudar o ciclo de vida da requisição | Regressão no caminho principal | Checkpointer sempre ligado, mas o caminho sem handoff não lê checkpoint; suíte estrita antes e depois; teste de serialização do estado |
| Exigir sessão em `POST /messages` quebrar o smoke e os exemplos do avaliador | Avaliador não consegue rodar | Chaves sintéticas no `.env.example`; smoke faz login sozinho; `/docs` com o exemplo de sessão; README com duas chamadas |
| Webhook para fora do compose expor dado | Vazamento | URLs vazias por padrão fora do compose; payload mascarado; HMAC; receptor interno na demo |
| Replanejador aumentar custo e latência | Estouro de limites | Esforço `none`, saída curta, orçamento de 3 saltos, regra determinística antes do modelo |
| Calibração humana depender do tempo do responsável | Atraso da v0.8.0 | Amostra mínima de 24, CSV com instruções, ~1 h |
| Holdout contaminado por ajuste de prompt | Métrica sem valor | Holdout congelado por hash antes da campanha; ajuste posterior reabre o conjunto |
| Fluxo contínuo noturno sem o responsável | Decisão errada tomada por padrão | Toda decisão de produto tomada por padrão fica listada no relatório como reversível; limites da autorização por versão |

## Questões em aberto

| ID | Questão | Resposta |
| --- | --- | --- |
| Q14 | Reabrir o escopo (ADR 0016) | **Sim** (responsável, 2026-11-03) |
| Q15 | HITL por interrupção nativa do LangGraph | **Sim** (2026-11-03) |
| Q16 | `POST /messages` com sessão obrigatória | **Sim, sem modo aberto**, pelo valor no feedback: o avaliador cita o "core `/messages` sem auth" em Security e em Production; um modo sem autenticação, mesmo desligado, seria um caminho a explicar. Escopos por tool call e auditoria completa entram no mesmo item (2026-11-03) |
| Q17 | Fundir v0.9.0 na v0.8.0 | **Não**; preferência por mais versões curtas: v0.10.0 criada (2026-11-03) |
| Q18 | Prazo da ressubmissão | Perguntado ao avaliador, sem resposta; o plano assume o quanto antes |
| Q19 | Aprovar a seção "Eficiência de execução": emenda ao AGENTS.md, `.claude/agents/`, CI, scripts e relatórios | Responsável |
| Q20 | Modelo e esforço por papel: Opus xhigh nos três (régua medida) ou linha de base Sonnet/Opus | Responsável |
