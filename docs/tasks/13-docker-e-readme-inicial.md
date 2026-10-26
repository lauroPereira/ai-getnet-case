# Tarefa: Docker e README inicial

## Objetivo

Empacotar API e Qdrant com docker-compose, inicialização automática do seed e do índice, e um README inicial em inglês para build, execução e testes.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RNF-01, CA-13, CA-16 (parcial).

## Pré-condições

- Tarefas 07 a 12 concluídas.

## Arquivos prováveis

- `Dockerfile`, `docker-compose.yml`, `.env.example`, `.dockerignore`
- `README.md` (seção de uso do produto)
- Comando de smoke no CLI

## Passos

1. Dockerfile em estágios, imagem `python:3.13-slim`, usuário sem privilégios.
2. Compose com API e Qdrant (imagem com versão fixa), volumes e healthchecks.
3. Comando de inicialização que cria o seed e o índice (se vazio) antes de subir a API.
4. README com pré-requisitos, configuração, `docker compose up --build`, exemplos com `curl`, testes e avisos de custo.
5. Smoke que envia os 10 exemplos e confere status HTTP e rota.

## Critérios de conclusão

- [ ] Em ambiente limpo, sem volumes nem cache, `docker compose up --build` e o smoke passam com apenas `OPENAI_API_KEY`.
- [ ] Tempo e custo da primeira inicialização registrados.

## Validação

A preencher na execução.

## Status

```text
pendente
```
