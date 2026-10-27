# Fontes oficiais — parâmetro de limite de saída v0.4.0

**Verificado em:** 2026-10-27. Leitura somente documental; nenhuma API de inferência foi chamada.

## Parâmetro adotado

`max_output_tokens` é aceito pelo adaptador Responses que este produto já usa.

- OpenAI documenta `max_output_tokens` como limite superior dos tokens gerados, incluindo texto visível e tokens de raciocínio, com mínimo 16 na [referência Create a model response](https://developers.openai.com/api/reference/resources/responses/methods/create). A documentação do [modelo GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) confirma o ID `gpt-6-luna`, endpoint Responses e teto do modelo de 128.000 tokens.
- DeepSeek lista `deepseek-flash` no [Responses API](https://api-docs.deepseek.com/api/create-response/) e descreve `max_output_tokens` como teto dos tokens visíveis e de raciocínio. A referência não estabelece um mínimo para esse campo; a interface usa o mínimo comum de 16 que é exigido pela referência OpenAI.

## Limites implementados pelo produto

O produto oferece somente esse parâmetro e apenas para `openai:gpt-6-luna` e `deepseek:deepseek-flash` nos agentes suportados. As faixas são: Router 16–300; Knowledge 16–500; Support 16–1200; Escalation 16–400; Personality 16–600. Esses máximos são os limites de saída que os respectivos agentes já usavam; a configuração só pode reduzi-los. Knowledge conserva o menor limite entre seus caminhos de geração (500 e 900).

O wrapper aplica `min(limite_do_perfil, limite_da_chamada)` ao `CallSpec` antes que o adaptador reserve custo e antes de construir o payload. Reserva e envio recebem o mesmo número. Assim, configuração não amplia a chamada reservada. Evaluation continua sem parâmetro até a v0.6.0; JEV/TypeSafe não tem esse campo no adaptador atual e não o aceita.

Regras de entrada: objeto de parâmetros sem chaves desconhecidas; valor deve ter tipo Python inteiro estrito (booleanos não contam como inteiros); mínimo 16; máximo por agente/modelo como acima. Erro de validação acontece antes de persistir nova versão ou invocar um provedor.

## Evidência de implementação

O catálogo `/v1/catalog/models` expõe tipo, mínimo, máximo por agente, descrição e URL oficial por modelo. Perfis persistem os parâmetros dentro da versão e digest; o snapshot registra tanto configuração do perfil quanto `effective_parameters_by_agent` medido pelo meter. Testes usam `ScriptedLLM` e adaptador OpenAI fake; nenhuma inferência paga foi executada.
