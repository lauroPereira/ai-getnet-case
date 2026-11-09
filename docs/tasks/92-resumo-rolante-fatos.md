# Tarefa 92 — Resumo rolante e registro de fatos

## Objetivo

Conversas longas mantêm contexto antigo por um resumo rolante e os números do caso por um registro determinístico de fatos, aceito pela guarda de saída.

## Especificação relacionada

[v0.12.0](../specs/memoria-escrita-v0120.md): D1, D2, D6, CA-65. Plano: [decisões 9 e 10](../specs/roadmap-v0110-v100-plano.md).

## Arquivos prováveis

`conversations.py`, `orchestration/graph.py`, `agents/router.py`, `agents/support.py`, `agents/personality.py`, `prompts/summary.v1.md`, `data/migrations.py`, `api/v1.py` e testes.

## Passos

1. Adicionar colunas de resumo e tabela de fatos à migração 0014, compartilhada com a tarefa 94.
2. Extrair fatos de resultados de ferramentas e registros de caso, nunca do texto do modelo; guardar tipo, ferramenta e mensagem de origem.
3. Gerar um resumo mascarado de até 200 tokens quando seis mensagens antigas ainda não resumidas se acumularem. Manter as 12 mensagens não resumidas mais recentes disponíveis; processar o texto completo de no máximo 12 mensagens por chamada. Mensagens anteriores ficam armazenadas e entram em avanços posteriores. O contexto dos agentes de resposta limita cada mensagem antiga a 600 caracteres; se houver corte ou mais de 12 mensagens pendentes, marcar o contexto como incompleto e avisar o lojista para repetir detalhes ausentes. Preservar o resumo anterior e o cursor se a geração falhar.
4. Entregar o resumo e as mensagens ainda não resumidas como contexto a Router, Support e Personality, inclusive quando excedem os históricos recentes de Support e Personality; fornecer fatos anteriores a Support e Personality. Usar fatos registrados, nunca o resumo, como evidência para valores protegidos.
5. Expor `summary` e `facts` nos endpoints de conversa sem alterar campos existentes.

## Critérios de conclusão

- CA-65 coberto por testes roteirizados de conversa longa, resumo em blocos e uso dos fatos pela guarda.
- Mensagens não resumidas permanecem armazenadas; até 12 também são entregues como contexto a quem redige a resposta, e contextos que excedem o limite são sinalizados. Fatos só vêm de resultados estruturados e mantêm a origem.
- Migração 0014 e adições à API preservam os campos existentes.
