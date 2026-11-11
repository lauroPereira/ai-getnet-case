# Tarefa 111 — Disponibilidade de motor e perfis

## Objetivo

Quem roda o backend só com a chave da OpenAI não consegue escolher, na interface, o JEV nem perfis cujo provedor não tem chave; a interface diz qual chave falta.

## Especificação relacionada

[v1.1.0](../specs/tickets-retomada-v110.md): D3, CA-78, RF-132.

## Pré-condições

Tarefa 110 concluída no backend e na interface. Nenhuma chamada paga.

## Arquivos prováveis

Backend: `src/merchant_assistant/api/v1.py` (`GET /v1/profiles`), `profiles.py`, `docs/contracts/api-v1.md`, testes. Web: `app.py`, `README.md`, testes.

## Passos

1. `GET /v1/profiles`: cada perfil ganha `available` (verdadeiro quando o provedor de cada agente do perfil tem chave configurada no backend) e `missing_providers` (nomes dos provedores sem chave; vazio quando disponível); a resposta ganha `router_mechanisms` (`{"llm": true, "jev": <TYPESAFE_API_KEY configurada>}`). Nenhum valor de chave. A regra de chave por provedor é a mesma usada para construir os clientes de modelo.
2. Contrato `api-v1.md` atualizado.
3. Web: perfil indisponível aparece marcado como indisponível neste backend e não é enviado; o JEV indisponível fica desabilitado no atendimento, na comparação só dos Routers e na comparação de perfis, com uma frase que nomeia a chave que falta no backend (`TYPESAFE_API_KEY`, `DEEPSEEK_API_KEY`); o padrão cai para um perfil e um motor disponíveis (o perfil Híbrido deixa de puxar o JEV quando ele está indisponível). Backend antigo sem os campos novos: comportamento atual.
4. README da web e do backend (uma frase onde as chaves opcionais são descritas) e testes.

## Critérios de conclusão

- Testes da API: com e sem `TYPESAFE_API_KEY` e `DEEPSEEK_API_KEY`, os campos refletem as chaves e nenhum valor de chave aparece na resposta.
- Testes da interface: sem as chaves, JEV e perfis dependentes não são enviáveis e a frase nomeia a chave; com as chaves, tudo como antes; backend sem os campos novos mantém o comportamento atual.
- Suítes estritas do backend e da web verdes.

## Resultado

`GET /v1/profiles` com `available`, `missing_providers` e `router_mechanisms`, pela mesma regra de chave da fábrica de modelos e sem valor de chave; a interface desabilita o JEV e os perfis sem chave e nomeia a variável que falta.
`test_v111_profile_availability.py` com 12 testes no backend e `test_v111_availability.py` com 11 na interface; suítes estritas com 3.039 aprovados no backend e 195 na interface.
Com modelo real: disponibilidade com o nome da chave e o JEV com a chave configurada. Evidência: [resultado da v1.1.0](../evidence/v110-resultado.md).

## Status

```text
concluída (v1.1.0)
```
