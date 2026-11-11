# Tarefa: Customer Support Agent

## Objetivo

Implementar o Customer Support Agent com prefixo determinístico, uso das ferramentas permitidas, composição com o procedimento do Knowledge e fatos estruturados para a verificação de saída.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-15 a RF-19, RF-21, UC-03, 05, 08, 13, 17.

## Pré-condições

- Tarefas 06 e 08 concluídas; tarefa 10 para a rota combinada.

## Arquivos prováveis

- `src/merchant_assistant/agents/support.py`, `prompts/support.v1.md`
- `tests/integration/test_support.py`

## Passos

1. Prefixo sem modelo: histórico e healthcheck do assunto, uma vez por conversa.
2. Chamada de ferramentas restrita à lista de permissões do agente e ao limite por requisição; datas por presets resolvidos pelo relógio.
3. Pergunta de seleção quando a ferramenta indicar vários candidatos.
4. Na rota combinada, compor a resposta com o procedimento do Knowledge, indicando as duas origens.
5. Registrar fatos estruturados (ferramenta, campo, valor, origem, instante) no estado.
6. Sinalizar encaminhamento quando uma ferramenta essencial falhar ou faltar evidência.
7. Cliente desconhecido conforme RF-21.

## Critérios de conclusão

- [x] Testes determinísticos de UC-03, 05, 08, 13 e 17 conferem ferramentas chamadas, fatos e status.
- [x] Nenhuma afirmação de crédito sem confirmação do repasse.

## Resultado

Customer Support Agent com prefixo determinístico, ferramentas permitidas, composição com o procedimento do Knowledge e fatos estruturados. 110 testes determinísticos sem rede e sem custo (`tests/integration/test_use_cases.py` e `tests/unit/`) e execução real dos 10 exemplos em 2026-10-26. Evidência: [execução real](../evidence/2026-10-26-execucao-real-desenvolvimento.md).

## Status

```text
concluída (v0.1.0)
```
