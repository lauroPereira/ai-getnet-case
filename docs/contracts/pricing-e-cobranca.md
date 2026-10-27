# Contrato interno de pricing e cobrança (v0.3.0)

Os endpoints abaixo pertencem ao serviço FastAPI interno `mocks`, na porta 8001 da rede Compose. Não há porta publicada. Os dados são fixtures sintéticas, mantidas em arquivos independentes por fonte.

## POST /pricing/simulations

Entrada validada: `customer_id`, `transaction_id`, `operation` (`sale_fee`), `gross_amount_minor` (inteiro positivo), `currency`, `conditions` (`payment_type`, `installments`, `channel`, `pricing_plan`) e `pricing_version`.

Resposta: `customer_id`, `transaction_id`, `rule_id`, `rule_version`, `applicable`, as `conditions` aplicadas, `currency`, `components` (`name`, `amount_minor`), `installments` (`number`, `gross_minor`, `fee_minor`, `net_minor`) e `expected_fee_minor` (nulo quando não aplicável). A resposta é uma versão de regra fictícia; não representa preço ou fórmula Getnet.

## GET /charges/{transaction_id}?customer_id=...

A cobrança é lida somente de `charges-v1.json`, separado dos dados de pricing. Resposta: `customer_id`, `transaction_id`, `recorded`, `conditions`, `currency`, `components`, `installments` e `charged_fee_minor` (nulo quando não registrado).

Ambas as rotas confirmam que a chave pertence ao `customer_id` confiável informado pelo backend. `404` representa evidência ausente; `403` representa vínculo diferente; respostas inesperadas são convertidas em erro controlado pelo cliente HTTP.

## Ferramentas do assistente

Nenhuma ferramenta recebe `customer_id` nem exige que o lojista informe identificadores de venda. `simulate_pricing` e `get_fee_breakdown` aceitam filtros opcionais `period`, `payment_type`, `installments` e `sale_date`; a aplicação seleciona uma venda pertencente ao lojista autenticado. Se o filtro resultar em várias vendas, pede refinamento. `simulate_pricing` solicita pricing e cobrança de forma independente e compara apenas `expected_fee_minor` com `charged_fee_minor`, em centavos, se as condições e aplicabilidade forem compatíveis.

Resultados: `consistent`, `different_conditions`, `divergence` ou `insufficient_evidence`. Só `divergence` inclui diferença aritmética. Nenhuma ferramenta executa ajuste, reembolso, habilitação, cancelamento ou encerramento de contrato.
