# Tarefa 106 — Imagem no GHCR e lockfile

## Objetivo

A cada tag, a CI publica a imagem da API no GitHub Container Registry; o compose usa a imagem publicada quando existe; dependências fixadas em `uv.lock`; a suíte estrita roda dentro da imagem sem PyPI.

## Especificação relacionada

[v1.0.0](../specs/leitura-acesso-v100.md): D1 a D4, CA-73. Plano: [decisão 20](../specs/roadmap-v0110-v100-plano.md).

## Pré-condições

v0.13.0 integrada. Nenhuma chamada paga. Docker local para conferir o build.

## Arquivos prováveis

`.github/workflows/validate.yml`, `Dockerfile`, `uv.lock` (novo), `pyproject.toml`, `docker-compose.yml`, `README.md`, testes de configuração.

## Passos

1. Gerar `uv.lock` a partir do `pyproject.toml` com os extras usados na imagem e na CI; Dockerfile instalando pelo lockfile (`--frozen`).
2. CI: passo que falha se o lockfile estiver desatualizado; job `image` só em tag `v*`, com `permissions: packages: write`, login no GHCR com `GITHUB_TOKEN`, build e push de `:<tag>` e `:latest` e rótulos OCI.
3. Compose: `image:` com `${APP_VERSION:-latest}` e `build:` no mesmo serviço, `pull_policy: missing`.
4. README: "Run the tests inside the image" (contêiner sem rede, suíte estrita).
5. Testes: workflow com o job só em tag e permissões mínimas; compose com `image:` e `build:`; Dockerfile usando o lockfile.

## Critérios de conclusão

- CA-73 coberto por testes de configuração e por um build local dentro da imagem com a suíte estrita sem rede; suíte estrita verde.

## Resultado

`uv.lock` com 111 pacotes e `uv lock --check` na CI antes da suíte estrita; job `image` só em tag `v*`, com `packages: write` e login no GHCR por `GITHUB_TOKEN`; compose com `image:` e `build:` no mesmo serviço; versão 1.0.0 no pacote.
Testes de configuração em `test_v100_image.py`; suíte estrita com 2.982 aprovados no host e dentro da imagem sem rede (`docker run --network none`).
Evidência: [resultado da v1.0.0](../evidence/v100-resultado.md).

## Status

```text
concluída (v1.0.0)
```
