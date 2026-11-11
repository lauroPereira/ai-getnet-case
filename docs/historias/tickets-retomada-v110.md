# História de uso: tickets e retomada da conversa (v1.1.0)

## Objetivo e pessoa usuária

Um lojista sintético (`cliente1988`) pede atendimento humano pelo celular, recarrega a página antes de ver a resposta e quer encontrar o que a atendente escreveu; noutro dia, abre uma conversa nova e pergunta pelo ticket. Quem roda o backend só com a chave da OpenAI não deve ver opções que falham no envio.

## Critérios e candidato

CA-76 a CA-79 da [spec da v1.1.0](../specs/tickets-retomada-v110.md); tarefas 109 a 113. Candidato do backend e da interface identificado por hash.

## Condições iniciais

Pilha do compose do candidato com `.env` gerado do `.env.example`, só `OPENAI_API_KEY` e `BUDGET_LIMIT_USD=0.10`; interface do candidato no host; navegador local (janela do lojista em largura de celular e janela privada da operadora). Dados sintéticos. Campanha `v110-qa`, teto US$0,10.

## Momentos da história

| Momento | Ação pela entrada normal | Resultado esperado | Critério | Evidência | Ponto de retorno |
| --- | --- | --- | --- | --- | --- |
| 1 | Lojista entra (Real, API) e olha o seletor de perfil e o Router | Perfis que dependem do DeepSeek marcados indisponíveis; JEV desabilitado com a frase que nomeia `TYPESAFE_API_KEY`; padrão Referência e LLM | CA-78 | captura | não se aplica |
| 2 | Pergunta dos recebíveis e "Quero falar com um atendente humano" | Resposta com datas e valores; protocolo `HO-…` | regressão | legenda e ledger | não se aplica |
| 3 | Operadora (janela privada) assume e responde pelo Ticketing | "Ação enviada e aceita pelo assistente." | regressão | captura | Atualizar |
| 4 | Lojista recarrega a página e entra de novo | "Conversa retomada"; histórico com a pergunta, o protocolo e a resposta da atendente marcada `Atendente humano` | CA-77 | captura | não se aplica |
| 5 | Lojista envia "Obrigado" na conversa retomada | Turno na mesma conversa (mesmo `conversation_id`) | CA-77 | Resultados ou API | não se aplica |
| 6 | **Nova conversa**; "Tenho algum ticket aberto?" | Protocolo, estado e a resposta da atendente, vindos de `get_handoff_cases` (ferramenta visível em Resultados) | CA-76 | captura e trace | não se aplica |
| 7 | Nova conversa; "Qual o status do ticket que termina em <6 últimos caracteres>?" | O mesmo caso, pelo final do protocolo | CA-76 | trace | não se aplica |
| 8 | Outro lojista (`cliente_demo_002`) pergunta pelo mesmo final de protocolo | Nenhum dado do caso de `cliente1988` | CA-76 | trace e auditoria | não se aplica |
| 9 | Com `TYPESAFE_API_KEY` acrescentada ao `.env` da validação e a API recriada: JEV habilitado, uma mensagem pelo JEV | Resposta com Router `typesafe:jev-1.14.0` | CA-78 | Resultados e ledger | remover a chave ao fim |
| 10 | `GET /v1/conversations` com o token da operadora e com `limit=50` | `403 insufficient_scope`; `422` | CA-77 | saída HTTP | não se aplica |

Percorra a tarefa completa. Inspecione cada evidência relevante antes de seguir. Não antecipe atalhos que a pessoa não teria.

## Experiência e exceções

Lista de conversas indisponível não bloqueia o atendimento (aviso curto e conversa nova). Nenhum valor de chave aparece na interface, na API ou nos logs.

## Resultado da rodada

Validação com modelo real, Docker e navegador em largura de celular, registrada em [v110-resultado.md](../evidence/v110-resultado.md).

| Momento | Resultado |
| --- | --- |
| 1 | Perfis que dependem do DeepSeek indisponíveis; JEV desabilitado com o nome da chave que falta |
| 2 e 3 | Atendimento encaminhado e respondido pela operadora pelo Ticketing; a resposta aparece nos momentos 4 e 6 |
| 4 | Conversa retomada com o histórico e a resposta da atendente, marcada `Atendente humano` |
| 5 | A mensagem seguinte recebe resposta própria, na mesma conversa, sem repetir a da atendente |
| 6 e 7 | Três formas de perguntar pelo ticket atendidas pelo suporte com `get_handoff_cases`, inclusive a busca pelo final do protocolo |
| 8 | Outro lojista não recebe dado do ticket; uma linha de auditoria por chamada, cada uma com o próprio lojista |
| 9 | Com a chave configurada, a mensagem é atendida pelo JEV |
| 10 | `GET /v1/conversations` responde `403` à operadora e `422` fora do limite |

Resposta da atendente (CA-79): texto idêntico na interface, em `GET /v1/conversations/{id}` e na ferramenta, com valor e data intactos; a retomada não chama modelo, e aprovar o rascunho segue pela Personality e pela guarda de saída. Suíte estrita: 3.059 testes aprovados; interface: 203 testes e 6 de integração contra a API em processo. Gasto: US$0,018 em três campanhas (tetos US$0,10, US$0,05 e US$0,03).

## Como terminou

O lojista recarregou a página no celular e encontrou a conversa com a resposta da atendente, nas palavras dela. Numa conversa nova, perguntou pelo ticket de três jeitos, inclusive pelo final do protocolo, e recebeu o estado e a resposta; outro lojista não viu nada do caso. Quem roda o backend só com a chave da OpenAI viu as opções indisponíveis com o nome da chave que falta, e o JEV atendeu assim que a chave foi configurada.
