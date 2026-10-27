# 0007. Interface Streamlit em projeto separado, consumindo só a API

## Título

Construir a interface em Streamlit, num projeto separado (`ai-getnet-case-web`), que acessa o backend apenas pela API `/v1` com papéis demo e admin verificados no backend.

## Status

```text
proposta
```

## Contexto

O responsável pediu Streamlit e um projeto separado. A interface precisa de chat, perfis, toggle LLM/JEV, editor de documentos, avaliações e gráficos, e será exposta a um recrutador. O backend continua dono de regras, dados, índices, versões e orçamento.

## Decisão

- Projeto próprio em `C:\workspace\ai-getnet-case-web`, com Streamlit e um cliente HTTP gerado a partir do OpenAPI do backend.
- Nenhum acesso direto a arquivos, SQLite ou Qdrant; nenhuma regra de negócio na interface.
- API `/v1` versionada; `POST /v1/sessions` emite token de papel `demo` ou `admin`; o backend verifica o papel em cada rota.
- Modo de respostas simuladas na interface para desenvolver as telas sem o backend.
- Toda chamada paga só por ação explícita do usuário; resultados gravados são reaproveitados nos reruns.

## Alternativas consideradas

- **Streamlit no mesmo repositório e processo:** mais simples, mas mistura responsabilidades e expõe o backend junto com a interface.
- **Frontend web (React):** mais flexível, mas contraria o pedido e aumenta o escopo.

## Consequências

Contratos explícitos e testáveis; a API segue útil sozinha. Exige manter versão de contrato e um segundo projeto (repositório e template a decidir, Q9).

## Data

2026-10-26
