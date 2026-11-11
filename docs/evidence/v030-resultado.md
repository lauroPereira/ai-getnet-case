# Resultado da v0.3.0

## Capacidades

- Um serviço interno `mocks`, sem porta pública, responde com regras sintéticas de preço e cobranças gravadas.
- O suporte compara taxas, consulta a habilitação de bandeiras e o cancelamento de vendas com ferramentas somente leitura, compartilhadas pelo domínio e pelo MCP.
- A migração 0005, reversível, guarda o contexto de preço do contrato, os pedidos de habilitação e os registros de cancelamento.
- Os prompts versionados de Router e Support filtram comparações de taxas identificáveis e o histórico recente de autorizações; as jornadas de negócio têm casos determinísticos.

## Validação

| Verificação | Resultado |
| --- | --- |
| Candidato | [Candidato de release](v030-release.md) r6: 49 arquivos, fingerprint `3de3e863431e81740d014239bd88df093b48e9d37c9614993da59c826767c80a`; runtime `e58e5668172b992ebabf9777237686a2e0357cdccd5c7657436acbbc703b1cde` |
| Suíte estrita | 191 testes; Ruff, estrutura e skills aprovados |
| Docker | API, Qdrant e mocks saudáveis; Router 5, Support 7, schema 5, índice de 145 trechos ([prontidão](v030-ready-r6.json)) |
| Revisão independente | Apto; isolamento, literal de privacidade e afirmações qualificadas e contraditórias verificados ([revisão](v030-reviewer-r6.md)) |
| Casos HTTP reais | 40/40 com a rubrica corrigida, reaplicada às mesmas respostas reais sem nova chamada ([replay](v030-real-http-r2-replay.md) das [respostas originais](v030-real-http-r2.md)) |
| Conversas HTTP reais | 4/4, incluindo a continuidade depois do encaminhamento, com o mesmo protocolo ([conversas](v030-real-conversations-r3.md)) |
| Validação independente | Apto: história por HTTP, MCP, falha controlada e isolamento, na mesma imagem com modelo programado ([validação](v030-qa-r6.md)) |
| Migração | 0005 → 0004 testada em banco sintético |

O replay reavaliou só o conteúdo dos cenários de desenvolvimento; as respostas reais, os 17 casos de holdout e as verificações de rota, status, idioma, ferramentas, valores e fontes ficaram como gravados.

## Gasto

US$0,14123583 na validação desta versão (duas execuções reais, índices, rubricas e as conversas repetidas), sob o teto persistente de US$0,15. Total registrado do projeto: US$0,59283583, com teto de US$5 na época ([registro](orcamento.md), [medição acumulada](v030-real-budget-r3.json)). O replay e a validação com modelo programado não fazem chamada paga.

## Decisão

Aprovada pelo responsável e integrada na `main` com a tag `v0.3.0` em 2026-10-27 ([PR #4](https://github.com/lauroPereira/ai-getnet-case/pull/4)). O retorno à v0.2.0 é pela migração 0005 → 0004.
