# Tarefa: API versionada, sessões e comparação isolada

## Objetivo

Expor os contratos /v1 com autorização backend e comparação sem duplicar atendimento.

## Especificação relacionada

RF-42–43, RF-48, RF-51–53 e CA-34–37; [plano v0.4.0](../specs/perfis-interface-v040-plano.md).

## Pré-condições

Contratos/autenticação/ADR 0013 aprovados; tarefas 27–28 disponíveis.

## Arquivos prováveis

`api/`, sessões/perfis/comparações, OpenAPI, fixtures e testes de contrato/isolamento.

## Passos

1. Implementar os contratos propostos, sessão opaca com digest/expiração/revogação e principal confiável.
2. Aplicar papel e dono em cada rota; demo não pode publicar, alterar escopo ou acessar outro recurso.
3. Comparar somente Routers; vincular e consumir comparison_id uma vez ao executar o atendimento selecionado.
4. Gerar OpenAPI e respostas simuladas antes das telas; verificar erros/custos e preservar /messages legado.

## Critérios de conclusão

- [x] Chaves de acesso/provedor não aparecem em URL, trace ou log; access key não volta na resposta; token é opaco e armazenado como digest.
- [x] 401/403/404/409 e indisponibilidade são respostas controladas sem dados de terceiros.
- [x] Comparação executa somente Routers; decisão selecionada é consumida uma vez.
- [x] OpenAPI e exemplos consistentes, legado preservado e papel validado no backend.

## Validação

O snapshot OpenAPI do projeto irmão declara `SessionBearer` nas rotas protegidas e documenta `/v1/catalog/models`, incluindo parâmetros compatíveis. Testes backend cobrem digest/expiração/revogação, papel/dono, conflito, migração e legado. HTTP sintético verificou login, catálogo, perfis, comparação, atendimento, trace e uso único. Regressão de logout: `DELETE` retorna corpo vazio `204`; o GET seguinte sem sessão retorna corpo `401` íntegro na mesma conexão persistente. Strict backend r4: 214 passed; sem chamadas de provedor.

## Status

Implementada e validada em ambiente sintético; revisão independente pendente.
