# Catálogo de modelos v0.4.0 — verificação de fontes

Verificação feita em 2026-10-27. O catálogo limita as opções de perfil a
identificadores com preço e capacidades confirmados por documentação oficial.
Uma chave ou presença em `GET /models` não prova capacidades.

| Provedor / ID usado | Versão identificada | Preço adotado para estimativa | Capacidades comprovadas | Fontes oficiais |
| --- | --- | --- | --- | --- |
| OpenAI `gpt-6-luna` | `gpt-6-luna` | US$ 0.10 entrada / US$ 0.50 saída por Mtok; entrada cacheada US$ 0.01 | Responses API, tools (functions, web search, file search), visão e structured outputs | [Modelos OpenAI](https://developers.openai.com/api/docs/models), [preços OpenAI](https://developers.openai.com/api/docs/pricing), [Responses create](https://developers.openai.com/api/reference/resources/responses/methods/create) |
| DeepSeek `deepseek-flash` | DeepSeek-V4.1-Flash-1017 (alias rotativo) | Conservador: peak US$ 0.30 entrada uncached / US$ 0.006 entrada cacheada / US$ 1.20 saída por Mtok. Tarifas off-peak são menores e não usadas na reserva. | Responses API, function tools e JSON Output | [Modelos e preços](https://api-docs.deepseek.com/quick_start/pricing/), [Responses API](https://api-docs.deepseek.com/api/create-response/), [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/), [changelog](https://api-docs.deepseek.com/updates/) |
| TypeSafe `jev-1.14.0` | `jev-1.14.0` (fixo; alias `jev-latest` é mutável) | US$ 0.042 entrada / US$ 0 saída por Mtok | `POST /v1/systemone`; saída decisória tipada (`choice`, `score`, `noul`); texto; 64k tokens/request, 32k por pergunta. Não oferece chamadas de ferramentas ou geração de prosa. | [Modelos TypeSafe](https://docs.typesafe.ai/models), [API TypeSafe](https://docs.typesafe.ai/api/system-one), [release 1.14](https://typesafe.ai/blog/jev-1-14) |

## Regras de disponibilidade

- O catálogo publicado usa `jev-1.14.0`, sem alias, para congelar a versão.
- DeepSeek aplica preço peak na estimativa e mantém o alias do modelo reportado
  como versão de chamada; a API não oferece pin de versão imutável.
- Cache input do DeepSeek é cobrado pelo token quando o provedor informa
  `prompt_cache_hit_tokens`; se o uso não separar cache, a estimativa peak
  uncached continua conservadora.
- Embedding não é editável em perfil. Os modelos não comprovados ou sem preço
  registrado não podem ser publicados nem chamados.
- Nenhuma chamada real foi executada nesta verificação. A existência de preço
  e contrato não representa autorização para consumir API.

## Semântica de snapshot

Este documento é uma evidência versionada para o snapshot de catálogo. A
verificação de preços deve ser refeita antes de oferecer o catálogo em outro
candidato; os valores aqui não devem ser tratados como estáveis.
