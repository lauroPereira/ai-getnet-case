# Tarefa: Servidor MCP e demonstração

## Objetivo

Expor as ferramentas de suporte por um servidor MCP local sobre a camada de domínio existente, com demonstração verificável.

## Especificação relacionada

[Especificação principal](../specs/assistente-multiagente-lojista.md): RF-31, CA-20. [Complementar](../specs/incrementos-pos-nucleo.md): RF-45, UC-22, CA-30. [Decisão 0010](../architecture/decisions/0010-servidor-mcp-sobre-o-dominio.md).

## Pré-condições

- Tarefa 15 concluída; decisão 0010 aceita.

## Arquivos prováveis

- `pyproject.toml` (dependência `mcp`)
- `src/merchant_assistant/mcp_server.py` (novo), `cli.py` (comando `mcp`)
- `tools/mcp_demo.py` ou comando `mcp-demo`
- `tests/integration/test_mcp.py`

## Passos

1. Servidor stdio com o cliente fixado pelo processo (`--customer`), nunca por argumento de ferramenta.
2. Uma ferramenta MCP por ferramenta do registro, com schema derivado do mesmo modelo Pydantic; execução por `registry.execute`.
3. Erros estruturados como resultado de erro da ferramenta, com o mesmo código.
4. Teste de equivalência: mesmo resultado pela camada de domínio e pelo MCP, inclusive `FORBIDDEN_RESOURCE`.
5. Demonstração: cliente que lista as ferramentas, chama duas e mostra o bloqueio; instruções no README.

## Critérios de conclusão

- [x] Cliente MCP lista e chama as ferramentas com os mesmos resultados.
- [x] Recurso de outro cliente é bloqueado e auditado também via MCP.
- [x] Instruções de execução no README.

## Resultado

Servidor MCP stdio com o SDK oficial `mcp` 2.3, schemas e execução pelo mesmo registro. `tests/integration/test_mcp.py` confirma as mesmas ferramentas e resultados, `FORBIDDEN_RESOURCE` auditado, argumento inválido e cliente desconhecido; `mcp-demo` em subprocesso real lista 5 ferramentas, faz 2 chamadas com dados e mostra o bloqueio do recebível de outro cliente.

## Status

```text
concluída (v0.2.0)
```
