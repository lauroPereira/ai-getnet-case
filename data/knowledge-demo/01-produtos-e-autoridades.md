---
id: KB-DEMO-CONCEPTS-001
version: 0.1.0
source_kind: simulated_internal
environment: demo
domain: concepts
---

# Produtos e autoridade das evidências

Documento operacional fictício, válido somente na demonstração.

## Conceitos de demonstração

Uma venda possui um ou mais recebíveis. O plano de recebimento, as condições de precificação e a situação do pagamento são fatos distintos. mdr_negociado, taxa_servico e dias_float preservam os nomes dos atributos da simulação, com unidade, base e versão informadas pelo pricing.

O plano reduzido e a antecipação automática têm identificadores próprios. A presença de um produto não implica que o outro esteja contratado. O canal de captura e a data da operação integram o contexto de consulta.

Habilitação de bandeira solicitada, habilitação ativa no cadastro e disponibilidade no equipamento são estados distintos. A passagem entre eles depende dos registros retornados pelas ferramentas.

## Responsabilidade por campo

| Fonte sintética | Responsabilidade |
| --- | --- |
| PricingMock, referido como PRaaS fictício | Preço esperado, parâmetros, parcelas e versão da simulação |
| ContractsMock | Condições aceitas, vigência, produtos e dados cadastrais |
| ChargesMock | Descontos e valores registrados na cobrança |
| OnboardingMock | Workflow das habilitações e credenciamentos solicitados |
| DevicesMock | Cadastro, configuração e sinais disponíveis do equipamento |
| AuthorizationsMock | Eventos e respostas de autorização da transação |
| SalesMock | Status e elegibilidade de cancelamento de venda |
| SupportHistoryMock | Casos anteriores, tentativas, protocolos e assuntos pendentes |

## Uso das evidências

A simulação de preço precisa corresponder ao contexto contratado da operação. Divergência entre referências de contrato e pricing exige análise; confiança do modelo não escolhe uma versão vencedora. O healthcheck agrega sinais e não redefine o valor esperado de preço, o aceite do contrato ou a resposta da autorização.

Uma mensagem do lojista ajuda a identificar a demanda, mas não comprova uma mudança de contrato, uma aprovação ou uma correção. Dados individuais são obtidos por ferramentas vinculadas ao cliente da sessão.
