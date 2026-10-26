<!-- Papel: porta de entrada do projeto enquanto ele está em preparação; será substituído pelo README final em inglês (tarefa 13 e fatia 4). -->

# ai-getnet-case

Sistema multiagente de suporte ao lojista para o desafio **Getnet AI Hardcore Engineer — Multi-Agent Support System**. Uma API recebe `message` e `user_id` e resolve a demanda com quatro agentes: Router, Knowledge (RAG sobre fontes oficiais e busca web), Customer Support (ferramentas sobre dados sintéticos) e Escalation (encaminhamento humano simulado).

## Estado

Preparação concluída; implementação não iniciada. Não há código, Docker nem índice RAG ainda.

| Item | Situação |
| --- | --- |
| Especificação | [Aprovada](docs/specs/assistente-multiagente-lojista.md) |
| Plano técnico | [Aprovado](docs/specs/assistente-multiagente-lojista-plano.md) |
| Decisões de arquitetura | [0001 a 0005 aceitas](docs/architecture/decisions/) |
| Tarefas | [01 a 14 (fatias 0 e 1) pendentes](docs/tasks/) |
| Git e repositório remoto | `lauroPereira/ai-getnet-case` (privado) |

## Tecnologia

Python, FastAPI, LangGraph, Qdrant, SQLite, pytest e ruff, conforme as decisões aceitas. Modelos: OpenAI como baseline, Jev opcional no Router. Teto de US$5 em chamadas pagas.

## Como trabalhar

Base criada a partir do **ai-dev-template 0.3.0** ([origem](docs/wiki/origem-template.md)), com SDD ativo:

```text
spec → plan → tasks → implementação → validação
```

- Diga "Supervisor" para conduzir o fluxo; Developer, Reviewer e QA seguem o [protocolo dos papéis](docs/wiki/agents/README.md).
- Instruções para agentes: [AGENTS.md](AGENTS.md) (ver "Sobre este projeto") e [CLAUDE.md](CLAUDE.md).

## Discovery

O material de discovery (enunciado, discovery, escopo inicial, base fictícia e a [revisão com objeções](discovery/revisao-discovery.md)) fica em `discovery/`. A pasta é local e está no `.gitignore` porque contém contexto privado; os arquivos versionados usam só a síntese incorporada à especificação.

## Validação da base

```powershell
.\tools\scripts\validate-project.ps1
.\tools\scripts\validate-agent-flow.ps1
python tools/scripts/lint_and_tests.py
```

Depois de alterar uma skill em `skills/`, regenere as cópias com `.\tools\scripts\sync-skills.ps1`.
