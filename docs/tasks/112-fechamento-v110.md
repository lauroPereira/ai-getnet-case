# Tarefa 112 — Fechamento da v1.1.0

## Objetivo

O repositório descreve a v1.1.0 como entregue: versão, CHANGELOG, README e contrato coerentes com o que as tarefas 109 a 111 fizeram.

## Especificação relacionada

[v1.1.0](../specs/tickets-retomada-v110.md): CA-76 a CA-78.

## Pré-condições

Tarefas 109 a 111 concluídas no backend e na interface. Nenhuma chamada paga.

## Arquivos prováveis

`pyproject.toml`, `uv.lock`, `src/merchant_assistant/__init__.py`, testes que fixam a versão, `CHANGELOG.md`, `README.md`, `docs/contracts/api-v1.md`; na web, `pyproject.toml` e `README.md` se a versão da interface for declarada.

## Passos

1. Versão 1.1.0 no pacote, no lockfile (`uv lock`) e nos testes que a fixam; `/health` e `/ready` informam 1.1.0.
2. CHANGELOG `[1.1.0]`: Added (ferramenta de tickets, rota de conversas, retomada na interface, disponibilidade de motor e perfis), Changed (prompt do suporte v11 e, se houver, do Router), Contract and data (rota nova, campos novos em `/v1/profiles`, nenhuma migração).
3. README: status v1.1.0, linha da v1.1.0 em "Beyond the challenge", ferramenta nova onde as ferramentas do suporte são listadas, uma frase na trilha de 10 minutos sobre recarregar a página (a conversa volta) e sobre perguntar pelo ticket; roadmap.
4. Links, caminhos pessoais e suíte estrita.

## Critérios de conclusão

- Nenhuma menção a 1.0.0 como versão atual; números e textos batem com as tarefas.
- Suíte estrita verde; links e caminhos limpos.

## Resultado

Versão 1.1.0 no pacote, no `uv.lock` e em `/health` e `/ready`; CHANGELOG 1.1.0 com Added, Changed e Contract and data (nenhuma migração, esquema 16); README com a ferramenta nova, a retomada da conversa e a linha da v1.1.0.
Suíte estrita com 3.039 aprovados; `checar-links.py` sem alvo ausente em 374 arquivos Markdown; caminhos pessoais limpos.
Evidência: [resultado da v1.1.0](../evidence/v110-resultado.md).

## Status

```text
concluída (v1.1.0)
```
