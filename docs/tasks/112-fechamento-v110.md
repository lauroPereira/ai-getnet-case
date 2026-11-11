# Tarefa 112 — Fechamento da v1.1.0

## Objetivo

O repositório descreve a v1.1.0 como entregue: versão, CHANGELOG, README e contrato coerentes com o que as tarefas 109 a 111 fizeram.

## Especificação relacionada

[v1.1.0](../specs/tickets-retomada-v110.md): CA-76 a CA-78.

## Pré-condições

Tarefas 109 a 111 concluídas nas duas branches da versão. Nenhuma chamada paga.

## Arquivos prováveis

`pyproject.toml`, `uv.lock`, `src/merchant_assistant/__init__.py`, testes que fixam a versão, `CHANGELOG.md`, `README.md`, `docs/contracts/api-v1.md`; na web, `pyproject.toml` e `README.md` se a versão da interface for declarada.

## Passos

1. Versão 1.1.0 no pacote, no lockfile (`uv lock`) e nos testes que a fixam; `/health` e `/ready` informam 1.1.0.
2. CHANGELOG `[1.1.0] — not released`: Added (ferramenta de tickets, rota de conversas, retomada na interface, disponibilidade de motor e perfis), Changed (prompt do suporte v11 e, se houver, do Router), Contract and data (rota nova, campos novos em `/v1/profiles`, nenhuma migração).
3. README: status v1.1.0, linha da v1.1.0 em "Beyond the challenge", ferramenta nova onde as ferramentas do suporte são listadas, uma frase na trilha de 10 minutos sobre recarregar a página (a conversa volta) e sobre perguntar pelo ticket; roadmap.
4. Links, caminhos pessoais e suíte estrita.

## Critérios de conclusão

- Nenhuma menção a 1.0.0 como versão atual; números e textos batem com as tarefas.
- Suíte estrita verde; links e caminhos limpos.

## Validação

Developer, rodada 1 (2026-11-10). Branch `codex/v1.1.0-tickets-retomada`, base `66a4454` (tarefa 111). Sem chamada paga.

- **Versão.** `pyproject.toml` e `__version__` em `1.1.0`; `uv.lock` regenerado com `uv lock` do uv 0.13.7 (a versão do `Dockerfile`, cache novo em `<scratchpad da sessão>`): "Resolved 111 packages", "Updated merchant-assistant v1.0.0 -> v1.1.0", só essa linha muda no lockfile; `uv lock --check --offline` com exit 0. Os quatro testes que fixam a versão (`test_use_cases`, `test_v070_story` para `/ready`; `test_v070_closing`, `test_v080_story` para o pacote) esperam `1.1.0`. Os títulos `version="1.0.0"` dos apps de `mocks` e `ticketing` são versões próprias desses serviços desde que foram criados e não mudam.
- **CHANGELOG.** Entrada `[1.1.0] — not released`: Added (ferramenta `get_handoff_cases`, rota `GET /v1/conversations`, retomada na interface, disponibilidade de perfis e motores), Changed (`support.v11`; `router.v7` sem mudança; chave vazia conta como ausente para todos os provedores, regra comum da fábrica de modelos e de `GET /v1/profiles`), Contract and data (rota e campos aditivos, versão `1.1.0` em `/health` e `/ready`, nenhuma migração, esquema 16).
- **README.** Status v1.1.0 no topo; `APP_VERSION=v1.1.0` no exemplo de tag; trilha de 10 minutos, passo 6, com a frase sobre recarregar a página (a conversa volta, **Conversa retomada**) e sobre "Tenho algum ticket aberto?" depois de **Nova conversa**; tabela de componentes com 11 ferramentas do suporte; "eleven tools" e a linha de `get_handoff_cases` na tabela de ferramentas; item "Latest conversations (v1.1.0)" em "Conversations and case follow-up"; linha da v1.1.0 em "Beyond the challenge"; no roadmap, v1.0.0 como "Built" e a linha da v1.1.0 "In progress", com a spec. Nenhum número além dos das tarefas 109 a 111 (limite de 5 casos, `limit` 1 a 20 com padrão 5, 4 caracteres do filtro).
- **Contrato.** `docs/contracts/api-v1.md` já tem as linhas da tabela de rotas e as duas seções "Acréscimos da v1.1.0" (tarefas 110 e 111); sem mudança aqui.
- **Web.** A versão da interface (`pyproject.toml` da web, `0.6.0`) não acompanha a do backend desde a v0.6.0, e o README da web já descreve a v1.1.0 (tarefas 110 e 111); nenhuma mudança no worktree da web.
- **Comandos e números.** `.venv` do repositório principal com `PYTHONPATH=src` deste worktree, `-p no:cacheprovider` e `--basetemp` novo em `<scratchpad da sessão>` (pelo `PYTEST_ADDOPTS` na suíte estrita).

  | Comando | Resultado |
  | --- | --- |
  | `pytest` de `test_v070_closing`, `test_v080_story`, `test_use_cases`, `test_v070_story`, `test_v100_image`, `test_v100_tunnel`, `test_evaluator_settings`, `test_v0100_metrics` | **123 passed** (contagem pela barra de progresso) |
  | `uv lock --check --offline` (uv 0.13.7) | "Resolved 111 packages", exit 0 |
  | `python tools/scripts/lint_and_tests.py --strict` | **3039 passed, 1 skipped** em 17 min 50 s, `ruff` "All checks passed!", skills válidas, exit 0. O skip é `test_v0130_otel.py:436` (o venv não tem o extra `otel`) |
  | `checar-caminhos-pessoais.py` | nenhuma ocorrência em 741 arquivos |
  | `checar-links.py` | nenhum alvo ausente em 374 arquivos Markdown |

## Status

```text
pronta para revisão (rodada 1)
```
