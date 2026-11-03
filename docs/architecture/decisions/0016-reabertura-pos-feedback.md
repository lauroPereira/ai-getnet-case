# 0016. Reabertura do escopo após o feedback V4: identidade, HITL real e replanejamento

## Status

**Aceita pelo responsável em 2026-11-03** (respostas Q14, Q15 e Q17 da [especificação](../../specs/evolucao-pos-feedback.md)). Revoga, da [decisão 0015](0015-recorte-final-v060.md), apenas a cláusula "após o aceite da v0.6.0 a expansão funcional termina e pendências não originam uma v0.7.0". Mantém o restante da 0015 (sem Evaluation Agent, sem workflow de propostas). As adoções de fluxo (Q19) e o modelo por papel (Q20) ficam para decisão própria, registrada na etapa 0 do plano.

## Contexto

A v0.6.0 foi avaliada em 8,6/10 (quadro V4, 2026-11-03). A referência para aprovação é 9,5+. O avaliador apontou gaps específicos e com peso alto: HITL simulado (7%, nota 4,0), `user_id` como autoridade do payload (13%, 7,8), orquestração sem replanejamento (15%, 8,5), avaliação semântica sem métricas agregadas, juiz independente, calibração humana e holdout (14%, 9,0), retrieval sem holdout nem híbrido (10%, 9,4). Esses itens eram limitações documentadas e aceitas no recorte da 0015; agora são a diferença entre 8,6 e a meta.

## Decisão

- Reabrir a expansão funcional em quatro entregas curtas (v0.7.0, v0.8.0, v0.9.0, v0.10.0) e um fechamento (v1.0.0), conforme a especificação e o plano. O responsável prefere mais versões curtas a versões maiores.
- **Identidade:** o lojista passa a ser derivado de um principal autenticado por sessão, com credenciais sintéticas por lojista e por operador e escopos verificados em cada tool call; `user_id` deixa de ter autoridade e **não existe modo sem autenticação**. O ponto de troca por um provedor de identidade externo fica isolado na criação de sessão.
- **HITL:** o encaminhamento interrompe o grafo (interrupção nativa do LangGraph com checkpointer em SQLite) e a ação do operador (`approve`, `reply`, `reject`) retoma o mesmo fluxo; a fila é própria, persistente e idempotente; webhooks assinados levam o caso a um ticketing e a resposta ao lojista, com um receptor de ticketing na demonstração. Ticketing comercial continua fora.
- **Orquestração:** um nó de replanejamento observa e revisa o resultado de cada especialista e decide o próximo passo dentro de um orçamento de saltos; o grafo pré-definido permanece como plano inicial do Router.
- **Avaliação:** juiz independente, rubrica de quatro critérios com evidências completas, múltiplas execuções, calibração humana e holdouts (respostas e retrieval) passam a fazer parte do relatório principal; retrieval ganha híbrido BM25 + denso com RRF e reranker medido.
- **Operação:** métricas, alertas, CI, comparação retomável e resumo rolante de conversas fecham as limitações listadas em Production e Observability.

## Alternativas

- **Não ressubmeter:** mantém 8,6, abaixo da referência.
- **Só HITL e identidade:** leva a ≈ 9,2; não alcança 9,5.
- **Retomada em nível de aplicação, sem checkpointer:** mais simples, mas não demonstra interrupção e retomada do grafo, que é o critério literal do avaliador. Fica como plano B se a serialização do estado falhar.
- **Modo sem autenticação para desenvolvimento (`AUTH_MODE=open`):** descartado; seria um caminho a explicar numa dimensão em que o avaliador já apontou a falta de autenticação.
- **Entrega da resposta humana só por consulta, sem webhook:** descartada; o avaliador pede integração operacional que devolva a resposta e permita continuidade.
- **Ticketing externo (Zendesk, Teams):** dependência externa na demo sem valor avaliativo adicional sobre o contrato de webhook demonstrado.

## Consequências e retorno

Mais superfície (fila, papéis, escopos, checkpointer, webhooks, replanejador, rubrica, híbrido) e uma mudança incompatível em `POST /messages` (sessão obrigatória), documentada no CHANGELOG com as chaves sintéticas no `.env.example`. Cada entrega tem retorno pela tag anterior e migração reversível. Orçamento adicional de validação real: até US$0,95.

## Data

2026-11-03
