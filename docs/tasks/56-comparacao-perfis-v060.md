# Tarefa: comparação pequena de perfis com dois gráficos

## Objetivo

Comparar dois ou três perfis publicados sobre poucos cenários explícitos, com dois gráficos e uma tabela rastreáveis até as execuções.

## Especificação relacionada

[Spec v0.6.0, bloco C](../specs/fechamento-v060.md), RF-78, CA-48 e [plano](../specs/fechamento-v060-plano.md) (decisões 4 e 5).

## Pré-condições

Tarefa 55 concluída (cenários, verificações e avaliação). Sem chamada paga.

## Arquivos prováveis

Backend: `api/v1.py`, `data/migrations.py` (`comparisons`), orquestração da comparação, testes. Web: `app.py`, cliente, snapshot OpenAPI, fixtures e testes.

## Passos

1. Tabela `comparisons` na migração 0008.
2. `POST /v1/comparisons/estimate`: células, reusos de execuções compatíveis, novas execuções, fatores fixos, marcação exploratória quando houver mais de uma mudança entre perfis e estimativa.
3. `POST /v1/comparisons` com estimativa confirmada: execução fora da requisição no processo da API, uma versão da base para toda a comparação, efeitos de domínio numa cópia temporária do banco sintético, traces e snapshots marcados com `purpose=comparison`; negação de orçamento interrompe o restante e fica registrada.
4. `GET /v1/comparisons/{id}`: estado, configuração, células, falhas e agregados.
5. Resultados: gráfico custo × qualidade por perfil (duração média e tamanho da amostra), gráfico de custo por agente/modelo com seleção que abre as execuções, tabela cenário/perfil/resultado/duração/custo; Router-only em seção própria; "não avaliado" em vez de zero.
6. Testes de limites, reuso, falha parcial, isolamento (contagens do domínio original inalteradas) e ausência de POST em rerun ou seleção de gráfico.

## Critérios de conclusão

- [x] Nenhuma conversa, caso, tentativa ou encaminhamento criado no atendimento original.
- [x] Configurações, versões, repetições, amostra e falhas registradas e exibidas.
- [x] Qualidade só com os mesmos rótulos e rubrica; sem nota fictícia.
- [x] Validação estrita backend e web com código 0; nenhuma chamada paga.

## Resultado

Comparação de dois ou três perfis em até 18 células, executada fora da requisição sobre cópia do domínio, com dois gráficos e uma tabela que abrem as execuções; contagens do domínio original inalteradas e negação de orçamento registrada. Suíte estrita: backend 326 testes, web 30. Evidência: [resultado da v0.6.0](../evidence/v060-resultado.md).

## Status

```text
concluída (v0.6.0)
```
