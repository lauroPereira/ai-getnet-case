# Tarefa: Contrato da API de mensagens

## Objetivo

Expor `POST /messages` com schemas de entrada e saída, corpo de erro documentado e um orquestrador provisório atrás de uma interface.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-01, RF-02. [Plano](../specs/assistente-multiagente-lojista-plano.md), seção APIs ou interfaces.

## Pré-condições

- Tarefa 03 concluída.

## Arquivos prováveis

- `src/merchant_assistant/api/schemas.py`, `api/errors.py`, `api/app.py`
- `tests/integration/test_messages_contract.py`

## Passos

1. Schemas Pydantic de entrada (`message` de 1 a 2000 caracteres, `user_id` com formato restrito, `conversation_id` opcional) e de saída, conforme o plano.
2. Corpo de erro com `code`, `message` e `request_id` para validação e falhas técnicas.
3. Gerar `request_id` por requisição e devolvê-lo também em cabeçalho.
4. Injetar o orquestrador por dependência; o provisório devolve `needs_clarification`.
5. Incluir os 10 exemplos do enunciado como exemplos no OpenAPI.
6. Testar sucesso, erro de validação e formato do erro.

## Critérios de conclusão

- [x] Contrato visível em `/docs` com os exemplos.
- [x] Testes de contrato passam.
- [x] O orquestrador pode ser trocado sem alterar a camada HTTP.

## Validação

2026-10-26: testes de contrato em `tests/integration/test_messages_contract.py` (sucesso, campo ausente, limites, campo desconhecido, exemplos no OpenAPI, rota de traces só em modo demonstração) passaram. Revisão não independente (mesma sessão).

## Status

```text
concluída
```
