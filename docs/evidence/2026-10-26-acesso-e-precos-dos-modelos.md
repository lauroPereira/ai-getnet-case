# Evidência: acesso e preços dos modelos

Tarefa: [02](../tasks/02-verificar-acesso-e-precos-dos-modelos.md). Data: 2026-10-26. Verificação automatizada com as chaves do `.env` local (valores não registrados) e leitura das páginas oficiais de preço.

## Acesso

| Provedor | Verificação | Resultado |
| --- | --- | --- |
| OpenAI | Listagem de modelos (136 disponíveis) | `gpt-6-luna` e `text-embedding-3-small` disponíveis |
| OpenAI | `responses.parse` com saída estruturada, `reasoning.effort = none` | Rota correta (`general_web`); 75 tokens de entrada, 17 de saída; 3,7 s |
| OpenAI | `responses.create` com a ferramenta `web_search`, `reasoning.effort = low` | Resposta com citação (xe.com); **2 buscas** na mesma chamada; 8.583 tokens de entrada, 115 de saída; 4,9 s |
| OpenAI | Embeddings | 1.536 dimensões; 1,4 s |
| TypeSafe (Jev) | `GET /v1/models` | Acesso confirmado: `jev-latest`, `jev-preview` (ambos apontam para `jev-1.14.0`) |
| DeepSeek | `GET /models` | Acesso confirmado: `deepseek-flash`, `deepseek-v4-pro` (não usado no núcleo) |

## Preços vigentes

Registrados em [src/merchant_assistant/llm/prices.json](../../src/merchant_assistant/llm/prices.json).

| Item | Preço |
| --- | --- |
| `gpt-6-luna` (Standard) | US$0,10 entrada, US$0,01 entrada em cache, US$0,50 saída, por milhão de tokens |
| `text-embedding-3-small` | US$0,02 por milhão de tokens |
| Busca web | US$10 por mil chamadas, mais o conteúdo pesquisado cobrado como entrada |
| `jev-1.14.0` | US$0,042 por milhão de tokens de entrada; saída gratuita |

## Gasto desta tarefa

US$0,0209 estimado pela tabela acima (quase todo na busca web). Dentro do limite de US$0,05 da tarefa e da reserva de ingestão e calibração.

## Consequências para a implementação

- Uma pergunta geral com busca web custa cerca de US$0,02 quando o modelo faz duas buscas. O Knowledge Agent deve usar `max_tool_calls = 1` na busca web e a guarda de orçamento deve reservar o valor da chamada antes de executá-la.
- `gpt-6-luna` é modelo de raciocínio (esforço padrão `medium`). Router, Personality e Escalation devem usar `reasoning.effort = none` ou `low` para reduzir custo e latência.
- As chamadas usam `store = false` para não guardar conversas no provedor.
- O Jev documenta que o inglês é o idioma com melhor acurácia; a comparação com mensagens em português precisa ser medida (fatia 4).
- A decisão 0005 continua válida sem alteração.
