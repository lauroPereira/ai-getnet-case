# Tarefa: Knowledge Agent

## Objetivo

Implementar o Knowledge Agent nos modos RAG, busca web e procedimento, com citações obrigatórias e resposta explícita quando faltar evidência.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-07, RF-12, RF-13, RF-14, RF-19, UC-01, 02, 04, 06, 07, 09, 10.

## Pré-condições

- Tarefas 07 e 08 concluídas.

## Arquivos prováveis

- `src/merchant_assistant/agents/knowledge.py`, `prompts/knowledge.v1.md`
- `tests/integration/test_knowledge.py`

## Passos

1. Modo RAG: reescrever a consulta para português quando a mensagem estiver em inglês, se a medição da tarefa 07 indicar ganho; recuperar; gerar com citações obrigatórias e a regra de "sem evidência".
2. Modo web: busca web da OpenAI com consulta saneada (sem `user_id` nem dados do cliente), devolvendo fontes e horário.
3. Modo procedimento, para a rota combinada: `procedure_id`, passos e campos faltantes.
4. Delimitar conteúdo recuperado como dado no prompt.
5. Resposta controlada quando o índice ou a busca estiverem indisponíveis.

## Critérios de conclusão

- [ ] Testes determinísticos dos sete casos de uso conferem caminho e citações.
- [ ] Testes de "sem evidência" e de busca indisponível.
- [ ] Nenhuma consulta web contém `user_id` ou dados do cliente.

## Validação

A preencher na execução.

## Status

```text
pendente
```
