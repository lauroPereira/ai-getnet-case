# Tarefa: ativação, retorno e base capturada por execução

## Objetivo

Trocar a base atomicamente sem alterar o atendimento em curso.

## Especificação relacionada

RF-64–65, CA-41 e [ADR proposta0014](../architecture/decisions/0014-ciclo-kb-v050.md).

## Pré-condições

Plano aprovado; candidata íntegra/pronta e anterior preservada.

## Arquivos prováveis

Registro/serviço KB, grafo/RunContext, trace/snapshot e API.

## Passos

1. Ativar com ativa esperada e confirmação; registrar ator/evento.
2. Resolver/capturar índice e versão no início de cada atendimento.
3. Retornar explicitamente à anterior íntegra, sem apagar coleções.
4. Testar corrida de ativação e execução presa à versão inicial.

## Critérios de conclusão

- [ ] Conflito409; demo não ativa; estado inválido não muda ponteiro.
- [ ] Uma versão por run, registrada; nova execução vê a nova ativa.
- [ ] Rollback e legado/MCP preservados, sem remoção de dados.

## Validação e status

Implementada pelo Developer r1. CAS de ativação/retorno, ator e evento exercitados; teste mantém índice antigo utilizável após ativação e confirma a versão capturada no trace. Conflito obsoleto retorna `409`. Nenhum banco ou ledger do responsável foi aberto.
