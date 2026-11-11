<!-- Papel: tarefa da etapa 0 da evolução para produção; adota no ai-getnet-case as práticas de fluxo do ampeli-sdd. -->

# Tarefa 62: preparação do fluxo (etapa 0)

## Objetivo

Adotar as práticas de execução do `ampeli-sdd` que reduzem a espera entre passagens, sem tocar no produto.

## Especificação relacionada

[evolucao-producao-v070-v0100.md](../specs/evolucao-producao-v070-v0100.md), seção "Eficiência de execução" (Q19); [plano](../specs/evolucao-producao-v070-v0100-plano.md), seção "Preparação do fluxo".

## Pré-condições

- Q19 aprovada pelo responsável em 2026-11-03 ("Aprovo, etapa 0"), o que inclui as alterações em AGENTS.md, CLAUDE.md e `.claude/`.
- Q20: `opus`/`high` nos três papéis, como na configuração da v0.6.0, registrado como reversível.

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
- [x] CI verde no GitHub depois do push.
- [x] Agentes visíveis numa sessão nova do Claude Code aberta na raiz (o carregamento só acontece no início da sessão).

## Resultado

Agentes nativos em `.claude/agents/`, CI `validate.yml` com a suíte estrita em PR e push na `main`, e `medir-agentes.py`, `checar-memoria.ps1` e `limpar-ambiente.ps1` adaptados ao projeto; `validate-agent-flow.ps1` passa sem parâmetro, de qualquer pasta. Suíte estrita: 349 testes, Ruff e skills aprovados.

## Status

```text
concluída (v0.7.0)
```
