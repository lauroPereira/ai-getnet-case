# Revisão independente da T66 — retomada

- **Candidato:** `70f8f14cf4bfaee2c1a43b3f5bded31f1557daff`, branch `codex/v0.7.0-identidade-hitl`; escopo: `c7affe5`, `7e4416c`, `48f7361` e `055f223`.
- **Papel:** Reviewer em contexto novo, sem passagem ou diagnóstico do Developer. O Supervisor executou algumas sondas preparadas pelo Reviewer em uma cópia isolada, por restrição de permissões do ambiente.
- **Parecer:** correções necessárias, dois P2. Complementa a revisão parcial em `docs/evidence/v070-reviewer.md`.

## Achados

1. **P2 — assinatura malformada:** `src/merchant_assistant/api/webhooks.py` usa `isdigit()` antes de `int()`, que lança `ValueError` para `t=²`; um `v1` não ASCII como `é` provoca `TypeError` em `hmac.compare_digest`. Ambos foram reproduzidos diretamente no verificador. Por inspeção, as rotas de integração e do receptor mock não tratam essas exceções, resultando em erro interno em vez de `401 invalid_signature`; a sonda HTTP específica não terminou no ambiente restrito. Corrigir parsing e testar pelas rotas sem enfraquecer HMAC.
2. **P2 — deduplicação concorrente:** em `src/merchant_assistant/api/integrations.py`, a consulta à inbox precede o efeito e a gravação sem reserva atômica. Sonda com dois pedidos autenticados e assinados, mesmo `event_id`, corpos para casos diferentes e sincronização após ambas as consultas retornou dois `200 accepted`; os dois casos foram reivindicados, mas a inbox ficou com uma linha. A correção deve preservar a repetição após `503 resume_failed` (D26).

Permanece o P3 da revisão parcial sobre a resposta a evento previamente recusado; os demais P3 dessa revisão continuam registrados na evidência original.

## Verificações

- Suíte focada em cópia isolada: 34 testes passaram, um pulado, código 0; inclui webhooks, integração em processo com o ticketing real, migração e identidade. O teste pulado exige diretório temporário sob `.pytest_cache` e não foi comprovado.
- Sonda adicional: falha reproduzida de deduplicação concorrente; ação antes de atribuição e atribuição tardia idempotente passaram.
- Banco sintético: `0008 → 0009 → 0008 → 0009`, caso e mensagem preservados; inbox e entregas criadas e removidas conforme a versão; `checkpoint_failed` aceito; verificações de integridade e chaves estrangeiras passaram.
- `docker compose config --quiet` com arquivo de ambiente vazio: código 0, sem leitura de `.env`.
- Mutação em cópias isoladas: 6 de 7 mortos, após conferência das asserções (assinatura, janela, retenção de 5xx, operador ativo, tentativas e D29). Sobreviveu a remoção da consulta à inbox. Rodadas que falharam antes das asserções foram descartadas.

Não foram executadas suíte completa, chamadas pagas ou de rede. A emissão de `handoff.created` por CLI e MCP não foi comprovada. O QA deve usar runtime e volume novos, pois a migração 0009 foi ampliada no lugar. Próximo passo: correção pelo Developer e nova revisão independente do candidato corrigido.
