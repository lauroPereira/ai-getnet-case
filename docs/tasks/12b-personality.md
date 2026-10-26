# Tarefa: Personality

## Objetivo

Implementar a etapa Personality, que redige a resposta final com voz consistente a partir das contribuições estruturadas dos agentes, sem alterar fatos.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-37, RF-08, CA-26. Origem: diagrama do enunciado ([evidência da tarefa 01](../evidence/2026-10-26-verificacao-de-fontes.md)).

## Pré-condições

- Tarefas 09 a 12 concluídas.

## Arquivos prováveis

- `src/merchant_assistant/agents/personality.py`, `prompts/personality.v1.md`
- `tests/integration/test_personality.py`

## Passos

1. Definir a voz do assistente no prompt: cordial, direta, frases curtas, sem jargão interno, sem prometer o que o fluxo não decidiu.
2. Entrada: status, idioma, pontos, fatos, citações e, quando houver, protocolo de encaminhamento ou texto de política.
3. Saída validada: texto final e idioma; fontes e status vêm do estado, não do modelo.
4. A verificação de saída roda depois da Personality; divergência de valor ou data leva a uma resposta montada só com os fatos.
5. Testes com modelo programado para respostas fiéis e para tentativas de alterar valores.

## Critérios de conclusão

- [x] Todas as rotas passam pela Personality.
- [x] Resposta que altera um valor ou data é bloqueada e substituída.
- [x] Idioma da resposta igual ao da mensagem.

## Validação

2026-10-26: testes determinísticos em `tests/integration/test_use_cases.py` e `tests/unit/` (110 testes no total, sem rede e sem custo) e execução real dos 10 exemplos registrada em [docs/evidence/2026-10-26-execucao-real-desenvolvimento.md](../evidence/2026-10-26-execucao-real-desenvolvimento.md). Revisão não independente (mesma sessão).

## Status

```text
concluída
```
