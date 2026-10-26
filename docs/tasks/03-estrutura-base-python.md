# Tarefa: Estrutura base do projeto Python

## Objetivo

Criar o pacote `merchant_assistant` com configuração, lint, testes e uma aplicação FastAPI mínima com verificações de vida e prontidão.

## Especificação relacionada

[Plano](../specs/assistente-multiagente-lojista-plano.md), seção Componentes afetados; RF-03, RNF-05, RNF-08.

## Pré-condições

- [Decisão 0001](../architecture/decisions/0001-python-fastapi-pydantic.md) aceita.

## Arquivos prováveis

- `pyproject.toml`, `.env.example`
- `src/merchant_assistant/__init__.py`, `config.py`, `api/app.py`
- `tests/unit/test_health.py`

## Passos

1. Criar `pyproject.toml` com dependências mínimas (fastapi, uvicorn, pydantic, pydantic-settings) e de desenvolvimento (pytest, ruff, httpx).
2. Criar o layout `src/` previsto no plano, só com os módulos que esta tarefa usa.
3. Configuração por variáveis de ambiente: `OPENAI_API_KEY` opcional (os testes rodam sem chave), `APP_ENV`, `DEMO_MODE` desligado por padrão e `TIMEZONE=America/Sao_Paulo`.
4. Implementar `GET /health` e `GET /ready`.
5. Testar com o cliente de testes do FastAPI.
6. Criar `.env.example` sem valores secretos.

## Critérios de conclusão

- [ ] `pytest` e `ruff check` passam.
- [ ] `python tools/scripts/lint_and_tests.py --strict` passa.
- [ ] Nenhum segredo nos arquivos.

## Validação

A preencher na execução.

## Status

```text
pendente
```
