# Tarefa: recuperar conversa consumindo o formato real da API

## Objetivo

Corrigir a recuperação da tarefa 52 usando o payload real GET da conversa como referência,
sem reenviar a pergunta paga.

## Especificação relacionada

[Tarefa 52](52-recuperar-conversa-get-ui-v050.md) e tarefa 50; dentro do escopo de
recuperação já aprovado.

## Pré-condições

- Payload sintético sanitizado como referência, SHA-256
  `c43c8e2d273570be2587c05c82adb2333284da92448913ab8580c85572168b7f`.
- Campanha existente com 33 entradas e US$0,00532161, zero reservas abertas. Não abrir,
  resetar ou criar guarda/ledger, nem executar inferência.

## Arquivos prováveis

Web `app.py`, cliente se necessário, testes e fixture JSON sintética. Nenhum
código de backend, API pública, autenticação, timeout, modelo ou guarda.

## Passos

1. Conferir hash do payload e contrato da rota por leitura de fontes. O corpo
   real está em `response` no envelope de evidência; contém mensagens
   `{role: merchant, text: ...}` e `{role: assistant, text: ...}`, não apenas
   os campos inventados por um fake. Não mudar a API para corresponder ao fake.
2. Corrigir consumo/mapeamento para reconhecer pergunta pendente e resposta
   real. Preservar cursor, segurança contra histórico anterior, estado ainda
   pendente, falhas GET e ausência de request_id; não repetir POST.
3. Criar fixture versionada SOMENTE sintética a partir do corpo real capturado,
   mantendo estrutura/chaves/roles do contrato. Cobrir esse formato com
   transporte controlado, inclusive renderização e POST único.
4. Cobrir histórico anterior, resposta ausente/ambígua e GET repetido. Preservar
   compatibilidade do modo gravado e os controles/tetos já aprovados.
5. Rodar regressão focal, suíte web e Ruff necessários; nenhuma chamada real.

## Critérios de conclusão

- [x] GET no formato real recupera a resposta persistida correta na interface.
- [x] Fixture sintética mantém as chaves e roles observadas; o teste fixa explicitamente `merchant`/`assistant`.
- [x] Estado pendente, histórico anterior e erros GET continuam seguros nos testes de interface.
- [x] Atualização manual usa GET; AppTest verifica uma única POST original e nenhum reenvio em reruns/atualizações.
- [x] Suíte web completa e Ruff externo passaram; nenhum código backend, serviço real, guarda ou ledger foi alterado/acessado.

## Resultado

Fixture versionada só sintética, com as chaves e os papéis `merchant`/`assistant` do formato real; recuperação por cursor, erros GET, histórico anterior, ausência de resposta e reruns cobertos por AppTest. Suíte web: 20/20; Ruff aprovado; nenhum teste contactou API ou provedor. Recuperação comprovada no navegador sem POST repetido. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
