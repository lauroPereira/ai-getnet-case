# Tarefa 106 — Imagem no GHCR e lockfile

## Objetivo

A cada tag, a CI publica a imagem da API no GitHub Container Registry; o compose usa a imagem publicada quando existe; dependências fixadas em `uv.lock`; a suíte estrita roda dentro da imagem sem PyPI.

## Especificação relacionada

[v1.0.0](../specs/leitura-acesso-v100.md): D1 a D4, CA-73. Plano: [decisão 20](../specs/roadmap-v0110-v100-plano.md).

## Pré-condições

Branch `codex/v1.0.0-final` (worktree `ai-getnet-case-wt/v100-final`), criada da `main` em `2bf3b59` (v0.13.0 integrada). Nenhuma chamada paga. Docker local autorizado pelo responsável para conferir o build, com RAM e disco monitorados (`tools/scripts/checar-memoria.ps1` antes e depois; `docker system prune` só das imagens criadas pela tarefa).

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

## Validação

Developer, rodada 1 (2026-11-10), branch `codex/v1.0.0-final`, base `main` em `2bf3b59`; código e testes em `acdd00e`. Sem chamada paga, sem Docker, sem download.

- **Base.** Os seis commits do preparo (`f34cde5..57dd51b`, feitos sobre `a1a4b19`) entraram por cherry-pick em ordem (`93595c6..340749d`). Um conflito, em `.env.example`: ficaram o bloco `API_WORKERS=2` da v0.13.0 e o `# APP_VERSION=latest` desta tarefa. O README juntou sem conflito e mantém o "Status" e a nota do Qdrant com dois workers da `main`. `git diff --stat 57dd51b HEAD` (antes do commit dos testes) tem os mesmos 19 arquivos e contagens de `git diff --stat a1a4b19 2bf3b59`: a diferença em relação ao preparo é só a correção final da v0.13.0.
- **Workflow.** `.github/workflows/validate.yml` é o de `57dd51b`, sem mudança. Os testes novos de D1 em `tests/integration/test_v100_image.py` conferem: `uv lock --check` antes da suíte estrita, com o uv da CI na mesma versão da imagem do `Dockerfile`; gatilho `push` em tags `v*`; `permissions` de topo só `contents: read`; job `image` só em `push` de tag `refs/tags/v`, depois de `validate`, com `contents: read` e `packages: write`; login no GHCR com `GITHUB_TOKEN` e nenhum outro segredo no arquivo; tags `:<tag>` e `:latest`; rótulos OCI de origem e versão; build do alvo `runtime` com push.
- **Lockfile.** `uv 0.13.7` (`lock --check --offline`, cache novo no scratchpad, sem download de Python): `Resolved 111 packages`, exit 0. `uv.lock` traz `merchant-assistant` 1.0.0 com `provides-extras = ["ingest", "otel", "dev"]`, como o `pyproject.toml`.
- **Versão.** 1.0.0 em `pyproject.toml`, `__init__.__version__` (servido por `/health` e em `versions.app` do `/ready`) e nos testes de versão. CHANGELOG com a seção `[1.0.0] — not released`.
- **Testes focados** (`.venv` do repositório principal, `PYTHONPATH` = `src` deste worktree + extra `otel` local, sem chaves de provedor, `--basetemp` e `cache_dir` novos no scratchpad): `tests/integration/test_v100_image.py`, `tests/unit/data/test_seed.py`, `test_use_cases.py`, `test_v0130_otel.py`, `test_v070_closing.py`, `test_v070_story.py`, `test_v080_story.py`, `tests/unit/evaluation/test_t87_web_evidence.py`: **155 passed** em 106 s, exit 0; `test_v100_image.py` sozinho: 11 passed. `ruff check --no-cache .`: `All checks passed!`. `checar-links.py`: nenhum alvo ausente em 362 arquivos Markdown. `checar-caminhos-pessoais.py`: nenhuma ocorrência em 718 arquivos.
- **Ficam para o Supervisor:** a suíte estrita completa; o build local (`docker build --target test`, `docker run --rm --network none`) e o `docker compose config`/subida pela imagem, que fecham CA-73 junto com a publicação pela CI na tag.

## Status

```text
pronta para revisão (Developer, rodada 1); suíte estrita e build Docker com o Supervisor
```
