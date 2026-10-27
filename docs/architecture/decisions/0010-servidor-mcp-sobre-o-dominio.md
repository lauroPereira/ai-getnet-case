# 0010. Servidor MCP sobre a camada de domínio

## Título

Expor as ferramentas de suporte por um servidor MCP local com o SDK oficial `mcp` (2.x), transporte stdio, reutilizando o registro e as funções de domínio.

## Status

```text
proposta
```

## Contexto

A decisão 0004 previu o MCP como adaptador posterior. As ferramentas já têm schemas, validação, isolamento entre clientes, auditoria e erros estruturados no registro (`tools/registry.py`). O cliente não pode vir de argumento do modelo.

## Decisão

- Comando `merchant-assistant mcp --customer <id>` inicia o servidor stdio com o contexto de cliente fixado pelo processo, nunca por argumento de ferramenta.
- Cada ferramenta MCP chama `registry.execute`; schemas MCP derivam dos mesmos modelos Pydantic.
- Erros estruturados viram resultados de ferramenta com `isError` e o mesmo código.
- Demonstração: script cliente MCP que lista ferramentas, chama duas e mostra o bloqueio de recurso de outro cliente; teste automatizado com cliente em memória.

## Alternativas consideradas

- **Transporte HTTP:** útil para clientes remotos, mas exige autenticação própria; fica como evolução.
- **Reimplementar as ferramentas no servidor MCP:** duplicaria regras de negócio.

## Consequências

Mesmo comportamento por dois transportes, com teste de equivalência. Adiciona a dependência `mcp`.

## Data

2026-10-26
