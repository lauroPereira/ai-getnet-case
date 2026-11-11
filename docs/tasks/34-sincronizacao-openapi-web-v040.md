# Tarefa: sincronizar o contrato OpenAPI consumido pelo web

## Objetivo

Atualizar o snapshot/cliente da interface para refletir integralmente o
contrato backend após a adição do erro operacional de orçamento.

## Especificação relacionada

RF-42, CA-34/CA-37 e tarefa 33.
O plano completo autoriza contrato e cliente; não há nova funcionalidade.

## Pré-condições

Backend congelado com o erro de orçamento da tarefa 33 revalidado.
Runtime, build e guarda do backend permanecem inalterados nesta correção.

## Arquivos prováveis

`openapi-v1.json` e artefatos gerados no projeto web, evidência/checagem de
sincronização. Alterar gerador/teste apenas se necessário para consistência.

## Passos

1. Obter o OpenAPI atual de um backend sintético isolado, sem provedor/chaves;
   não inicializar o runtime real para exportar schema.
2. Regenerar o snapshot e cliente de forma determinística, incluindo a
   resposta 429 com referência a ErrorBody no endpoint de comparação.
3. Conferir igualdade dos contratos aplicáveis e idempotência do gerador;
   verificar o consumidor para o envelope estruturado de orçamento.
4. Registrar comandos, hash e delta e fixar novo candidato para revisão.

## Critérios de conclusão

- [x] Snapshot consumido documenta todas as respostas da API atual aplicáveis.
- [x] Cliente gerado e fonte do schema estão identificados e coerentes.
- [x] Nenhuma mudança de comportamento/guarda/backend para contornar o contrato.
- [x] Revalidação é sem custo e ligada ao novo candidato.

## Resultado

Snapshot `openapi-v1.json` em JSON canônico, igual byte a byte ao schema servido (13 paths), com 429 e `ErrorBody` na comparação; gerador idempotente nas 10 operações (mesmo SHA-256 em duas execuções). Suíte web: 9 testes, com o contrato 429 e o `APIClient` propagando o envelope; Ruff aprovado. Evidência: [resultado da v0.4.0](../evidence/v040-resultado.md).

## Status

```text
concluída (v0.4.0)
```
