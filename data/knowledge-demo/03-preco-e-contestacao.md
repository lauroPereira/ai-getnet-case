---
id: KB-DEMO-PRICING-001
version: 0.1.1
source_kind: simulated_internal
environment: demo
domain: pricing
---

# Conferência de preço e contestação

Documento operacional fictício, válido somente na demonstração. A fórmula real de qualquer produto comercial fica fora desta referência.

> Disponibilidade nesta versão: as consultas especializadas deste procedimento ainda não estão habilitadas no assistente. Explique o conceito com fontes oficiais e ofereça encaminhamento para análise.

## Evidências necessárias

O fluxo usa get_contract_snapshot para identificar a condição aplicável, get_fee_breakdown para localizar a cobrança e seu contexto e simulate_pricing para consultar o preço esperado no PRaaS fictício. Se o contexto já estiver disponível e validado, a consulta correspondente pode ser reaproveitada.

Os registros identificam cliente, operação, produto, canal, vigência, parcelas, dias_float e contexto de precificação. A simulação devolve simulation_id, rule_version, aplicabilidade, componentes, descontos por parcela e totais. O pricing responde pelo resultado esperado; a cobrança informa o registrado.

## Procedimento

Após histórico e healthcheck, identificar a venda e as evidências ainda ausentes. Consultar somente recursos do cliente permitido. Validar correspondência dos contextos antes de comparar valores. O comparador da aplicação confere parcelas, componentes, moeda e totais em centavos; o agente explica os resultados das ferramentas.

Uma simulação atual ou hipotética não comprova o preço de uma venda histórica. Se a versão aplicável estiver ausente ou o pricing falhar, o atendimento registra evidência insuficiente, sem reconstruir a fórmula.

## Conclusão e encaminhamento

Cobrança compatível: apresentar composição e, quando pertinente, o efeito do horizonte de antecipação de cada parcela. Confirmar se a dúvida foi esclarecida. Divergência: preparar análise com condição, cobrança, simulação, referências, diferença e questão pendente. Contrato e pricing incompatíveis exigem análise antes de afirmar qual cobrança seria devida.

Uma contestação não é resolvida apenas pela criação do protocolo. Negociação exige uma oferta autorizada e identificada; esta versão permite explicar condições, sem alterar taxa, contrato ou executar ressarcimento. Sem eventos de integração, não se atribui a causa a falha de sincronização.
