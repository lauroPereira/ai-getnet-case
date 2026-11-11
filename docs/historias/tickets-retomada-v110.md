# História de uso: tickets e retomada da conversa (v1.1.0)

## Objetivo e pessoa usuária

Um lojista sintético (`cliente1988`) pede atendimento humano pelo celular, recarrega a página antes de ver a resposta e quer encontrar o que a atendente escreveu; noutro dia, abre uma conversa nova e pergunta pelo ticket. Quem roda o backend só com a chave da OpenAI não deve ver opções que falham no envio.

## Critérios e candidato

CA-76, CA-77 e CA-78 da [spec da v1.1.0](../specs/tickets-retomada-v110.md); tarefas 109 a 112. Candidato: SHAs do backend e da web fixados pelo Supervisor no briefing do QA.

## Condições iniciais

Pilha do compose do candidato com `.env` gerado do `.env.example`, só `OPENAI_API_KEY` e `BUDGET_LIMIT_USD=0.10`; interface da branch web no host; navegador local (janela do lojista em largura de celular e janela privada da operadora). Dados sintéticos. Campanha `v110-qa`, teto US$0,10.

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
| 9 | Com `TYPESAFE_API_KEY` acrescentada ao `.env` do QA e a API recriada: JEV habilitado, uma mensagem pelo JEV | Resposta com Router `typesafe:jev-1.14.0` | CA-78 | Resultados e ledger | remover a chave ao fim |
| 10 | `GET /v1/conversations` com o token da operadora e com `limit=50` | `403 insufficient_scope`; `422` | CA-77 | saída HTTP | não se aplica |

Percorra a tarefa completa. Inspecione cada evidência relevante antes de seguir. Não antecipe atalhos que a pessoa não teria.

## Experiência e exceções

Lista de conversas indisponível não bloqueia o atendimento (aviso curto e conversa nova). Nenhum valor de chave aparece na interface, na API ou nos logs.

## Resultado da rodada

(preenchido pelo QA)

## Como terminou

(preenchido pelo QA)
