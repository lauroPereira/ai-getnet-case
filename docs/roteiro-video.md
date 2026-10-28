# Roteiro do vídeo (v0.6.0)

Duração alvo: 8 a 10 minutos. Gravar com a stack do [guia](guia-demonstracao.md), dados sintéticos e saldo de orçamento conferido. Mostrar só o que foi entregue e validado; limitações ditas em voz alta.

## 1. Problema e raciocínio (1 min)

- O desafio: um ponto único de atendimento para lojistas, com agentes que cooperam (Router, Knowledge, Customer Support, Escalation e Personality).
- Princípios: respostas sustentadas por fonte ou ferramenta, isolamento por lojista, custo limitado antes de acontecer, rastreabilidade de cada execução.

## 2. Arquitetura (1 min)

- Diagrama: API FastAPI → grafo LangGraph tipado → agentes; Qdrant com snapshots oficiais e corpus fictício; SQLite com dados sintéticos; guarda de orçamento persistente; traces por etapa; MCP sobre as mesmas ferramentas; interface Streamlit separada consumindo só `/v1`.

## 3. Evolução por versões e o valor de cada uma (2 min)

| Versão | Entrega | Valor |
| --- | --- | --- |
| 0.1 | Núcleo multiagente, RAG oficial, ferramentas sobre dados sintéticos, guardrails, orçamento, avaliação | Atende os exemplos do desafio com evidência |
| 0.2 | Conversas e acompanhamento de caso, MCP | Continuidade e integração padrão |
| 0.3 | Jornadas de preço, habilitação e cancelamento; mocks HTTP | Casos de negócio reais do lojista |
| 0.4 | API `/v1` autenticada, perfis por agente, Router JEV, interface | Configuração e comparação controladas |
| 0.5 | Base de conhecimento versionada com candidata, teste, ativação e retorno | Mudar documentação com segurança |
| 0.6 | Três áreas, cenários, Resultados com verificações e avaliação sob demanda, comparação de perfis, prova do efeito da documentação | Demonstrável, auditável e compartilhável |

## 4. Caso resolvido (1 min)

- Atendimento → cenário "Recebimento das vendas de ontem" → resposta com valores e datas das ferramentas.
- Resultados: rota, etapas, ferramentas, modelos, tokens, custo, verificações aprovadas com origem no rótulo.

## 5. Exceção encaminhada (45 s)

- Cenário "Divergência de taxa encaminhada" (ou "Pedido de atendente humano"): protocolo sintético, estado `handoff`, nenhuma promessa de reembolso.

## 6. Recuperação de conversa (45 s)

- Mostrar uma pergunta pendente após falha de transporte e a recuperação por **Atualizar conversa** (GET), sem reenvio. Explicar o timeout coerente com o limite do backend.

## 7. Efeito da documentação (1,5 min)

- Diferença esperada registrada antes ([preparação](evidence/v060-qa-preparacao.md)).
- V1: sem `get_contract_snapshot`. Editar o documento fictício, construir, testar e ativar a V2. Nova conversa: a ferramenta aparece, o trecho e a versão estão no trace, a oferta depende do contrato. Retornar à V1 e mostrar o comportamento anterior.

## 8. Avaliação e comparação (1,5 min)

- Avaliação por IA de uma execução persistida: estimativa, confirmação, rubrica e avaliador registrados, custo separado, sem repetir o atendimento.
- Comparação de dois perfis: estimativa, confirmação, gráfico custo × qualidade (amostra e duração no rótulo), custo por agente/modelo com a barra abrindo as execuções, tabela; "não avaliado" em vez de zero.

## 9. Limitações e encerramento (45 s)

- Avaliação por modelo não é revisão humana; comparação pequena e em thread do processo da API; compartilhamento por IP depende de roteador, firewall e ausência de CGNAT; dados e documentos são sintéticos.
- Encerrar mostrando o saldo de orçamento e o custo total do projeto.
