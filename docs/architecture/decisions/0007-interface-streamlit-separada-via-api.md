# 0007. Interface Streamlit em projeto separado, consumindo só a API

## Título

Construir a interface em Streamlit, num projeto separado (`ai-getnet-case-web`), que acessa o backend apenas pela API `/v1` com papéis demo e admin verificados no backend.

## Status

Aceita (2026-10-26); entregue na v0.4.0. A sessão opaca foi substituída por JWT na v0.7.0 ([ADR 0017](0017-identidade-principal-escopos.md)).

## Contexto

Streamlit e um projeto separado são escolha do responsável. A interface precisa de chat, perfis, toggle LLM/JEV, editor de documentos, avaliações e gráficos, e é exposta a visitantes. O backend continua dono de regras, dados, índices, versões e orçamento.

## Decisão

- Projeto próprio, [ai-getnet-case-web](https://github.com/lauroPereira/ai-getnet-case-web), com repositório próprio no GitHub, criado a partir do ai-dev-template (decisão do responsável em 2026-10-26), com Streamlit e um cliente HTTP gerado a partir do OpenAPI do backend.
- Nenhum acesso direto a arquivos, SQLite ou Qdrant; nenhuma regra de negócio na interface.
- API `/v1` versionada; `POST /v1/sessions` emite token de papel `demo` ou `admin`; o backend verifica o papel em cada rota. Na v0.7.0 a sessão deu lugar a `POST /v1/auth/token` com JWT ([decisão 0017](0017-identidade-principal-escopos.md)).
- Modo com respostas sintéticas na interface para desenvolver as telas sem o backend.
- Toda chamada paga só por ação explícita do usuário; resultados gravados são reaproveitados nos reruns.

## Alternativas consideradas

- **Streamlit no mesmo repositório e processo:** não adotado: mais simples, mas mistura responsabilidades e expõe o backend junto com a interface.
- **Frontend web (React):** não adotado: mais flexível, mas aumenta o escopo sem ganho para as telas pedidas.

## Consequências

Contratos explícitos e testáveis; a API segue útil sozinha. Exige manter versão de contrato e um segundo repositório, com seu próprio fluxo SDD.

## Data

2026-10-26
