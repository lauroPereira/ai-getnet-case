# 0011. Serviços fictícios de pricing e cobrança como app HTTP separada

## Título

Implementar o PRaaS fictício e a fonte de cobrança como uma app HTTP separada (`mocks`) no docker-compose, consumida pelo backend por clientes com timeout.

## Status

```text
proposta
```

## Contexto

A jornada de preço exige que o PRaaS fictício seja a autoridade do preço esperado e que a cobrança venha de fonte independente, para que uma divergência não desapareça por recalcular as duas com a mesma função. O discovery previu um backend local de mocks com rotas separadas e chamada HTTP real para exercitar contrato, timeout e erros.

## Decisão

- App FastAPI `mocks` com `POST /pricing/simulations` e `GET /charges/{transaction_id}`, dados próprios e política sintética versionada (`pricing_mock_v1`).
- O backend usa `PricingClient` e `ChargesClient` com timeout e erros estruturados; as ferramentas `simulate_pricing` e `get_fee_breakdown` chamam esses clientes.
- O comparador determinístico fica no backend e trabalha só com centavos retornados; o modelo nunca calcula valores.
- O serviço fica só na rede interna do compose.

## Alternativas consideradas

- **Funções no mesmo processo:** mais simples, mas não exercita contrato HTTP nem falhas de rede, e facilita misturar dados das duas fontes.
- **Um serviço por fonte:** mais realista, sem ganho proporcional para o case.

## Consequências

Três serviços no compose. Divergências são reproduzíveis com fixtures independentes. Testes usam o app `mocks` em processo.

## Data

2026-10-26
