# Tarefa: Ferramentas de suporte do núcleo

## Objetivo

Implementar as sete ferramentas do núcleo como funções de domínio com vínculo cliente-recurso, filtros por período, erros estruturados e registro com permissões por agente.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-15, RF-16, RF-17, RF-21, CA-06. [Plano](../specs/assistente-multiagente-lojista-plano.md), seção Ferramentas do núcleo.

## Pré-condições

- Tarefa 05 concluída.

## Arquivos prováveis

- `src/merchant_assistant/tools/context.py`, `errors.py`, `registry.py`
- `src/merchant_assistant/tools/domain/` (recebíveis, repasse, dispositivos, autorizações, contrato, histórico, healthcheck)
- `tests/unit/tools/`

## Passos

1. Contexto do cliente montado pelo servidor (`customer_id`, cliente conhecido ou não); nenhuma ferramenta recebe `customer_id` do modelo.
2. Argumentos validados por Pydantic, aceitando presets de período ou datas explícitas.
3. Consultas por filtro quando não houver identificador; com mais de um candidato, o retorno indica necessidade de seleção.
4. Recurso de outro cliente devolve `FORBIDDEN_RESOURCE`, sem dados, e gera evento de auditoria.
5. Falhas `UNAVAILABLE` e `TIMEOUT` injetáveis para testes.
6. Healthcheck com verificações predefinidas por assunto (recebíveis, dispositivo, autorização, contrato) e estados `ok`, `pending`, `attention`, `unknown`, `unavailable`, `not_applicable`.
7. Registro que gera o schema das ferramentas para o modelo (sem `customer_id`) e a lista de permissões por agente.

## Critérios de conclusão

- [ ] Cada ferramenta tem testes de caminho feliz, resultado vazio, outro cliente, argumento inválido e falha.
- [ ] O schema exposto ao modelo não contém `customer_id`.
- [ ] Cliente desconhecido recebe resultado conforme RF-21.

## Validação

A preencher na execução.

## Status

```text
pendente
```
