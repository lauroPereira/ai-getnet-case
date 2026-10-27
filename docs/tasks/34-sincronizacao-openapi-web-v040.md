# Tarefa: sincronizar o contrato OpenAPI consumido pelo web

## Objetivo

Atualizar o snapshot/cliente da interface para refletir integralmente o
contrato backend após a adição do erro operacional de orçamento.

## Especificação relacionada

RF-42, CA-34/CA-37, tarefa 33 e [revisão r2](../evidence/v040-reviewer-r2.md).
O plano completo autoriza contrato e cliente; não há nova funcionalidade.

## Pré-condições

Backend r2 congelado; orçamento corrigido e revalidado pelo Reviewer.
Runtime, build e guarda do backend permanecem inalterados nesta correção.

## Arquivos prováveis

`openapi-v1.json` e artefatos gerados no projeto web, evidência/checagem de
sincronização. Alterar gerador/teste apenas se necessário para consistência.

## Passos

1. Obter o OpenAPI atual de um backend sintético isolado, sem provedor/chaves;
   não inicializar o runtime real do responsável para exportar schema.
2. Regenerar o snapshot e cliente de forma determinística, incluindo a
   resposta 429 com referência a ErrorBody no endpoint de comparação.
3. Conferir igualdade dos contratos aplicáveis e idempotência do gerador;
   verificar o consumidor para o envelope estruturado de orçamento.
4. Registrar comandos/hash/delta, fixar r3 e devolver ao mesmo Reviewer.

## Critérios de conclusão

- [x] Snapshot consumido documenta todas as respostas da API atual aplicáveis.
- [x] Cliente gerado e fonte do schema estão identificados e coerentes.
- [x] Nenhuma mudança de comportamento/guarda/backend para contornar o contrato.
- [x] Revalidação é sem custo e ligada ao novo candidato r3.

## Validação

GET `http://127.0.0.1:18841/openapi.json` no servidor sintético r2 retornou
200 (13 paths). O snapshot `openapi-v1.json` foi gravado em JSON canônico e
comparado byte a byte ao schema servido. `POST /v1/router/compare` contém 201,
422 e 429; o 429 referencia `#/components/schemas/ErrorBody`.

`python tools/generate_client.py` executado duas vezes: ambas as execuções
geraram as 10 operações e o SHA-256 de `src/getnet_web/generated_api.py` foi
idêntico (`0bce171011eb24f83b37029dcd7cfcc08175e5057396cdff8b3f571ef261362c`).
O conteúdo do mapa de rotas permaneceu igual: o schema atualizado não muda os
operation IDs. O gerador agora emite literais compatíveis com Ruff sem precisar
formatar manualmente o resultado.

Adicionados testes do contrato 429/ErrorBody e do `APIClient` propagando o
envelope em `APIError(429, "request_budget_exceeded", ...)`.
`.venv-v040/Scripts/python.exe -m pytest -q
--basetemp=.pytest_cache/v040-openapi-r3-final-20261027`: **9 passaram**.
Ruff `check --no-cache .` e `format --check --no-cache .`: passaram; 72 arquivos
formatados. Nenhum backend/guarda, runtime, chave ou chamada de inferência foi
alterado/utilizado nesta tarefa. A [passagem Developer r3](../evidence/v040-developer-r3.md)
registra arquivos e resultados.

## Status

Sincronização e verificações do Developer r3 concluídas; aguarda congelamento e
reavaliação independente pelo mesmo Reviewer. Revisões r1/r2 e suas evidências
permanecem preservadas; QA ainda não iniciou.
