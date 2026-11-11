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

## Resultado

Contratos `/v1` com sessão opaca por digest, expiração e revogação, papel e dono em cada rota e comparação de Routers com uso único da decisão. HTTP sintético cobriu login, catálogo, perfis, comparação, atendimento, trace e logout (`204` seguido de `401` íntegro na mesma conexão). Suíte estrita do backend: 214 testes, sem chamada de provedor. Evidência: [resultado da v0.4.0](../evidence/v040-resultado.md).

## Status

```text
concluída (v0.4.0)
```
