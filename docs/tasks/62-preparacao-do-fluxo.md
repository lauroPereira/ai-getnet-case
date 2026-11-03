<!-- Papel: tarefa da etapa 0 da evolução pós-feedback; adota no ai-getnet-case as práticas de fluxo do ampeli-sdd. -->

# Tarefa 62: preparação do fluxo (etapa 0)

## Objetivo

Adotar as práticas de execução do `ampeli-sdd` que reduzem a espera entre passagens, sem tocar no produto.

## Especificação relacionada

[evolucao-pos-feedback.md](../specs/evolucao-pos-feedback.md), seção "Eficiência de execução" (Q19); [plano](../specs/evolucao-pos-feedback-plano.md), seção "Preparação do fluxo".

## Pré-condições

- Q19 aprovada pelo responsável em 2026-11-03 ("Aprovo, etapa 0"), o que inclui as alterações em AGENTS.md, CLAUDE.md e `.claude/`.
- Q20 sem escolha explícita: o Supervisor adotou `opus`/`high` nos três papéis por padrão (configuração da v0.6.0), registrada como reversível.

## Arquivos prováveis

`AGENTS.md`, `CLAUDE.md`, `.claude/agents/{developer,reviewer,qa}.md`, `.github/workflows/validate.yml`, `tools/scripts/{medir-agentes.py,checar-memoria.ps1,limpar-ambiente.ps1}`, `docs/templates/relatorio-do-supervisor.md`, `docs/relatorios/README.md`, `docs/wiki/agents/README.md`.

## Passos

1. AGENTS.md: delegação por agentes nativos, autorização por versão e ritmo (despertador, um agente pesado por vez, limpeza depois do QA, corpo de PR por arquivo).
2. CLAUDE.md: agentes nativos existem; remeter à autorização por versão.
3. `.claude/agents/`: Developer, Reviewer (sem Edit/Write) e QA (com navegador), com os limites deste projeto (nenhuma chamada paga fora da campanha do QA; sem `data/runtime/`, `.env`, `discovery/`; sem push).
4. CI: `validate.yml` com `lint_and_tests.py --strict` em PR e push na `main`.
5. Portar e adaptar `medir-agentes.py`, `checar-memoria.ps1` e `limpar-ambiente.ps1`.
6. Modelo de relatório, pasta `docs/relatorios/` e matriz de modelo por papel no protocolo.

## Critérios de conclusão

- [x] Os três agentes aparecem em `.claude/agents/` com `name`, `description`, `tools`, `model` e `effort`.
- [x] `medir-agentes.py` roda sem erro neste projeto e reconhece `tarefa 63`, `T64` e `65-assunto`.
- [x] `checar-memoria.ps1` devolve veredito; `limpar-ambiente.ps1` roda em simulação sem listar processos de outros projetos e sem tocar em `data/runtime/` nem nos controles de campanha.
- [x] Validação estrita local passa.
- [ ] CI verde no GitHub depois do push (depende do push, que é do responsável).
- [ ] Agentes visíveis numa sessão nova do Claude Code aberta na raiz (o carregamento só acontece no início da sessão).

## Validação

2026-11-03, sessão do Supervisor, Windows, Python 3.13 do `.venv`:

- `python -I tools/scripts/medir-agentes.py`: código 0; 0 passagens (nenhum subagente nativo despachado ainda); regex testada com `Developer tarefa 63 identidade` → `T63`, `T64 fila` → `T64`, `docs/tasks/65-interrupcao.md` → `T65`.
- `checar-memoria.ps1`: "VEREDITO: cabe um agente pesado."
- `limpar-ambiente.ps1` (simulação): 278 MB identificados (scratchpads e `__pycache__`); worktree `_tmp/qa-pr7-20261028` mantida por estar fora do scratchpad; nenhum processo listado depois do filtro por `ai-getnet-case`.
- `lint_and_tests.py --strict`: primeira execução reprovada por 5 achados do Ruff no `medir-agentes.py` copiado (linhas longas, `zip` sem `strict`, alias de UTC); corrigidos. Segunda execução: código 0, **349 passed** em 249 s, Ruff "All checks passed!", skills válidas.
- `validate-agent-flow.ps1`: falhava no PowerShell 5.1 sem `-ProjectRoot` porque `$PSScriptRoot` chega vazio no valor padrão (defeito anterior). Corrigido com autorização do responsável: a raiz é calculada no corpo do script. Passa sem parâmetro, a partir da raiz e de outra pasta. Registrado em `locally_modified_managed_paths` do `.agent-template.json`, com AGENTS.md e CLAUDE.md.
- Pré-condição dos agentes nativos acrescentada ao plano (v0.7.0): sessão nova aberta na raiz e conferência dos três tipos antes do primeiro despacho.
- `validate.yml`: YAML válido (um job, `validate`); execução real depende do push.

## Status

```text
em andamento
```

Implementado; falta o commit (pedido ao responsável), o push e a confirmação do CI e dos agentes numa sessão nova.
