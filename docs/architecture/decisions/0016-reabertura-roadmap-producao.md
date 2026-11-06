# 0016. Reabertura do escopo: roadmap de produção

## Status

**Aceita pelo responsável em 2026-11-03** (respostas Q14, Q15 e Q17 da [especificação](../../specs/evolucao-producao-v070-v0100.md)). Revoga, da [decisão 0015](0015-recorte-final-v060.md), apenas a cláusula "após o aceite da v0.6.0 a expansão funcional termina e pendências não originam uma v0.7.0". Mantém o restante da 0015 (sem Evaluation Agent, sem workflow de propostas). As adoções de fluxo (Q19) e o modelo por papel (Q20) ficaram para decisão própria, registrada na etapa 0 do plano.

## Contexto

A v0.6.0 cobre o desafio, mas uma operação real exige o que o recorte da 0015 deixou de fora: o encaminhamento humano era simulado (caso local, sem fila, sem resposta humana de volta ao agente); o `user_id` do payload era a autoridade do lojista; a rota era um plano fixo, sem observar o resultado de um especialista; a qualidade das respostas não tinha métricas semânticas agregadas, juiz independente, calibração humana nem holdout; o retrieval era só denso e medido num conjunto usado no desenvolvimento.

## Decisão

- Reabrir a expansão funcional em quatro entregas curtas (v0.7.0, v0.8.0, v0.9.0, v0.10.0) e um fechamento (v1.0.0), conforme a especificação e o plano. O responsável prefere mais versões curtas a versões maiores.
- **Identidade:** o lojista passa a ser derivado de um principal autenticado por sessão, com credenciais sintéticas por lojista e por operador e escopos verificados em cada tool call; `user_id` deixa de ter autoridade e **não existe modo sem autenticação**. O ponto de troca por um provedor de identidade externo fica isolado na criação de sessão. A [decisão 0017](0017-identidade-principal-escopos.md) trocou a sessão por JWT com emissor próprio.
- **HITL:** o encaminhamento interrompe o grafo (interrupção nativa do LangGraph com checkpointer em SQLite) e a ação do operador (`approve`, `reply`, `reject`) retoma o mesmo fluxo; a fila é própria, persistente e idempotente; webhooks assinados levam o caso a um ticketing e a resposta ao lojista, com um receptor de ticketing na demonstração. Ticketing comercial continua fora. A [decisão 0018](0018-interrupcao-retomada-webhooks.md) trocou o receptor por um serviço de ticketing próprio.
- **Orquestração:** um nó de replanejamento observa e revisa o resultado de cada especialista e decide o próximo passo dentro de um orçamento de saltos; o grafo pré-definido permanece como plano inicial do Router.
- **Avaliação:** juiz independente, rubrica de quatro critérios com evidências completas, múltiplas execuções, calibração humana e holdouts (respostas e retrieval) passam a fazer parte do relatório principal; retrieval ganha híbrido BM25 + denso com RRF e reranker medido.
- **Operação:** métricas, alertas, CI e comparação retomável. O resumo rolante de conversas, previsto aqui, passou para o [roadmap v0.11.0 a v1.0.0](../../specs/roadmap-v0110-v100.md).

## Alternativas

- **Manter o recorte da 0015:** o assistente ficaria sem humano no circuito, sem identidade verificada e sem medição semântica, que uma operação real exige.
- **Só HITL e identidade:** deixaria orquestração, avaliação e retrieval como estavam na v0.6.0.
- **Retomada em nível de aplicação, sem checkpointer:** mais simples; não adotada porque não interrompe nem retoma o grafo, que é o comportamento pedido.
- **Modo sem autenticação para desenvolvimento (`AUTH_MODE=open`):** não adotado; a identidade vem sempre do token, sem um segundo caminho a manter e explicar.
- **Entrega da resposta humana só por consulta, sem webhook:** não adotada; a operação precisa que a resposta chegue ao lojista e o fluxo continue.
- **Ticketing externo (Zendesk, Teams):** não adotado; dependência externa na demonstração sem ganho sobre o contrato de webhook demonstrado.

## Consequências e retorno

Mais superfície (fila, papéis, escopos, checkpointer, webhooks, replanejador, rubrica, híbrido) e uma mudança incompatível em `POST /messages` (sessão obrigatória, hoje token), documentada no CHANGELOG com as credenciais sintéticas no `.env.example`. Cada entrega tem retorno pela tag anterior e migração reversível. Orçamento adicional de validação real: até US$0,95.

## Data

2026-11-03
