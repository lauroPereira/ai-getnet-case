# Tarefa: estabilização e contratos da v0.6.0

## Objetivo

Corrigir as pendências que afetam orçamento, integridade e funcionamento demonstrável, e registrar as demais como risco aceito, antes das funcionalidades novas.

## Especificação relacionada

[Spec v0.6.0, bloco E](../specs/fechamento-v060.md#e-estabilização), [plano](../specs/fechamento-v060-plano.md), [tarefa 46](46-pendencias-revisao-v050-r2.md) e [tarefa 48](48-diagnostico-timeout-chat-ui-v050.md).

## Pré-condições

- Sem chamada paga. Ledgers reais, `.limit` gravados e coleções existentes não são tocados.

## Arquivos prováveis

`orchestration/budget.py`, `rag/kb.py`, `orchestration/graph.py`, `cli.py`, `main.py`, `docker-compose.yml`, `api/v1.py` (limite por sessão), web `src/getnet_web/api.py`, `pyproject.toml` do web e testes.

## Passos

1. Gravar o teto com representação exata ou comparar com tolerância; a primeira montagem nunca recusa o próprio valor.
2. Publicar o `.limit` de forma atômica, sem sobrescrever um existente.
3. Prontidão e captura em caminho somente leitura quando o registro da base existe.
4. Timeout explícito de 30 s no cliente OpenAI do CLI.
5. Remover `BudgetGuard.record`/`record_embedding` se não houver chamador, ajustando o teste.
6. Testes de `max_retries == 0` nos três clientes reais (sem rede) e de ativação/retorno com manifesto sem `chunks`/`point_digest` e coleção vazia.
7. Timeout do cliente web para `POST /v1/messages` coerente com `MAX_REQUEST_SECONDS` mais margem, configurável; GET continua curto; recuperação por GET preservada.
8. Compose publica a API só em `127.0.0.1:8000`.
9. Limite configurável de mensagens por sessão demo, recusado no backend com erro claro e testado.
10. Ambiente web com Ruff disponível para o script estrito (dependência de desenvolvimento ou instrução), sem duplicar ambientes.
11. Verificação de integridade no Qdrant registrada como risco aceito, sem mudança de código.

## Critérios de conclusão

- [x] Cada correção tem regressão sintética que falha antes e passa depois.
- [x] Nenhum teto gravado alterado; montagem concorrente não falha.
- [x] `POST /messages` legado, MCP e contratos `/v1` existentes inalterados.
- [x] Validação estrita backend e web com código 0; nenhuma chamada paga.

## Resultado

Teto gravado com representação exata e publicado de forma atômica, prontidão sem bloqueio de escrita, clientes reais sem retry do SDK, timeout de 105 s para operações pagas na interface e 20 s para leituras, API só em `127.0.0.1:8000` e limite de 20 mensagens por sessão demo (migração 0008). Suíte estrita: backend 326 testes, web 30. Evidência: [resultado da v0.6.0](../evidence/v060-resultado.md).

## Status

```text
concluída (v0.6.0)
```
