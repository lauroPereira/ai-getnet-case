# Resultado da v1.1.0

## Capacidades

- O lojista consulta seus tickets de atendimento humano em qualquer conversa: protocolo, estado no idioma dele e a resposta da atendente, pelo protocolo completo ou pelo final (`get_handoff_cases`).
- A interface retoma a última conversa depois de recarregar a página, com o histórico e a resposta da atendente; a mensagem seguinte recebe resposta própria.
- A resposta escrita pela atendente chega ao lojista com as palavras dela; o rascunho aprovado continua passando pela Personality e pela guarda de saída.
- A interface oferece só os perfis e o motor de Router que o backend consegue executar e nomeia a chave que falta.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte estrita | 3.060 casos de teste: 3.059 aprovados no ambiente de desenvolvimento, sem falhas, e o caso do exportador OTLP, que roda com o extra `otel` na imagem e na CI. Cobertura de 93,8% das instruções ([registro](v110-cobertura.md)). Ruff, links e caminhos pessoais limpos |
| Interface | 203 testes aprovados e 6 de integração contra a API em processo |
| História com modelo real | Dez momentos pela interface, com Docker e navegador em largura de celular: disponibilidade com o nome da chave, retomada com a resposta da atendente, resposta própria à pergunta seguinte, três formas de perguntar pelo ticket atendidas pelo suporte com a ferramenta, busca pelo final do protocolo e o JEV com a chave configurada |
| Isolamento | Outro lojista não recebe dado do ticket; uma linha de auditoria por chamada, cada uma com o próprio lojista; `GET /v1/conversations` responde `403` a operador e `422` fora do limite |
| Resposta da atendente | Texto idêntico na interface, em `GET /v1/conversations/{id}` e na ferramenta, com valor e data intactos; a retomada não chama modelo; aprovar o rascunho segue pela Personality e pela guarda de saída |
| Registro de acesso | A linha do login sai sem a query |

Gasto: US$0,018 em três campanhas (tetos US$0,10, US$0,05 e US$0,03).

Validação momento a momento e revisão independente: [v110-validacao.md](v110-validacao.md).

As decisões estão na [especificação](../specs/tickets-retomada-v110.md) e na emenda da [ADR 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).
