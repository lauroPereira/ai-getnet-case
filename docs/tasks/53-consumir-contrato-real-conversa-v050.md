# Tarefa: recuperar conversa consumindo o formato real da API

## Objetivo

Corrigir o defeito52 usando o payload real GET da conversa como referência,
sem reenviar a pergunta paga.

## Especificação relacionada

[Defeito52](52-recuperar-conversa-get-ui-v050.md), tarefa50 e
[QA r2](../evidence/v050-qa-r2.md). Correção no escopo de recuperação já
aprovado, mesmos Developer → Reviewer → QA gpt-6-luna/high.

## Pré-condições

- R6 preservado. UI18553 e proxy18855 parados; API6932/18853 e fixtures26544/
  18854 preservados. Não chamar serviços reais na implementação.
- Payload sintético sanitizado em
  `.pytest_cache/v050-qa-real-runtime/recovery-get-r2-sanitized.json`, SHA256
  `c43c8e2d273570be2587c05c82adb2333284da92448913ab8580c85572168b7f`.
- Campanha existente33entradas/US$0,00532161, zero reservas abertas. Não abrir,
  resetar ou criar guarda/ledger, não executar inferência.

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
   Entregar passagem UI r4, parar escrita e retornar ao Reviewer no r7.

## Critérios de conclusão

- [x] GET no formato real recupera a resposta persistida correta na interface.
- [x] Fixture sintética mantém as chaves e roles observadas; o teste fixa explicitamente `merchant`/`assistant`.
- [x] Estado pendente, histórico anterior e erros GET continuam seguros nos testes de interface.
- [x] Atualização manual usa GET; AppTest verifica uma única POST original e nenhum reenvio em reruns/atualizações.
- [x] Suíte web completa e Ruff externo passaram; nenhum código backend, serviço real, guarda ou ledger foi alterado/acessado.

## Validação

Detalhes em [passagem Developer UI r4](../evidence/v050-developer-ui-r4.md).
Payload de referência confirmado sem imprimir seus textos: SHA-256
`c43c8e2d273570be2587c05c82adb2333284da92448913ab8580c85572168b7f`. A fixture
versionada no web contém valores sintéticos com o esquema completo da resposta
e mensagens `merchant`/`assistant`. A recuperação por cursor, erros GET,
histórico anterior, ausência de resposta, reruns e renderização são cobertos por
AppTest/MockTransport. Suite final: 20/20. `lint_and_tests.py --strict`
retornou código2: estrutura, pytest e skills passaram; o script não encontrou
Ruff no venv web. Ruff externo disponível no venv backend passou em
`app.py src tests tools`. Nenhum teste contactou API, provedor ou fixture live.

## Status

Concluída — [Reviewer UI r3](../evidence/v050-reviewer-ui-r3.md) apto e [QA r3](../evidence/v050-qa-r3.md) comprovou a recuperação no navegador; integrada na v0.5.0.
