# 0001. Python, FastAPI e Pydantic

## Título

Usar Python 3.13 com FastAPI e Pydantic v2 para a API e os contratos.

## Status

```text
aceita
```

Aceita pelo responsável em 2026-10-26.

## Contexto

O desafio pede um endpoint HTTP `POST` com resposta JSON e aceita qualquer linguagem. O ecossistema de agentes e RAG (SDKs de modelos, LangGraph, clientes de bancos vetoriais) é mais maduro em Python, e a experiência anterior do responsável está nessa linguagem. Os contratos de entrada, das saídas dos agentes e das ferramentas precisam de validação estrita.

## Decisão

Python 3.13, FastAPI servido por uvicorn, Pydantic v2 para todos os contratos e pydantic-settings para configuração por variáveis de ambiente.

## Alternativas consideradas

- **Node.js/TypeScript:** viável, mas com menos bibliotecas maduras para RAG e avaliação e sem experiência anterior aproveitável.
- **Flask:** exigiria validação e documentação OpenAPI manuais.
- **Python 3.12:** mais conservador, mas a máquina de desenvolvimento já usa 3.13 e as dependências previstas o suportam; volta a ser opção se alguma dependência falhar.

## Consequências

Validação e documentação interativa do contrato saem do framework. O mesmo modelo Pydantic serve à API, à saída estruturada dos modelos e aos testes. Fica-se preso à execução assíncrona do FastAPI, o que exige cuidado com chamadas bloqueantes ao banco local.

## Data

2026-10-26
