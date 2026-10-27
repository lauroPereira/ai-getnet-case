# Passagem Developer r1 — v0.5.0 base versionada

- **Papel:** Developer r1, contexto independente, modelo/esforço autorizados pelo responsável.
- **Objetivo:** implementar tarefas39–44 conforme spec, plano, API, história v1 e ADR0014 aprovados.
- **Estado:** implementação local concluída; aptidão técnica cabe ao Reviewer. QA real não executado.
- **Repositórios e branches:** backend `codex/v0.5.0-base-versionada`, base `ea2355b5ba8fa8dcff66200f34461ae063183250`; web `codex/v0.5.0-base-versionada`, base `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`. Sem commit/push; o Supervisor fixará o manifesto/hash do candidato após esta passagem.
- **Trabalho pré-existente:** preservadas as mudanças de preparação/fechamento v0.4 e os registros da supervisão. Nenhum arquivo protegido foi alterado.

## Implementação

- Backend: migração aditiva/reversível `0007_kb_versions`; registro dos snapshots público/fictício; rascunho com revisão otimista e diff; estimativa/hash; coleção nova por candidata; estados `building`, `testing`, `ready`, `active`, `retired`, `failed`; erro saneado; ativação/retorno CAS e eventos; índice/versão capturados antes de cada run e persistidos em trace/snapshot.
- Orçamento: `OpenAIEmbedder` reserva antes de cada lote e liquida uma vez, conservando a reserva se uso for desconhecido. OpenAI/DeepSeek usam `max_retries=0`; JEV é chamada HTTP única. `CombinedBudgetGuard`, `FixedBudgetGuard` e `build_orchestrator(..., budget=...)` permitem ao QA combinar o ledger existente com cap persistente de até US$0,25. O cap registra valor e ID uma vez, recusa mudança de valor e cancela somente uma reserva ainda não enviada quando o guard primário nega.
- Web: editor/diff/estimativa/build/teste/ativação/retorno via API autenticada; OpenAPI e cliente gerados de montagem sintética sem segredos, com Qdrant em memória.
- Dados/runtime: validações usaram SQLite temporário e coleções em memória. A montagem OpenAPI criou runtime sintético novo sob `.pytest_cache`; não iniciou `create_application`, não leu `.env`, não abriu `data/runtime/budget.sqlite3`, não migrou banco real, nem iniciou portas. Os dados persistentes de produto continuam no `merchant.sqlite3` e no caminho `runtime/qdrant` já existente; não é necessário diretório de runtime adicional para a operação normal.

## Validações observadas

- Backend: `.venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`, com `PYTHONDONTWRITEBYTECODE=1` e basetemp novo. Resultado: **221 passed**, Ruff aprovado, estrutura e skills aprovadas.
- Web: `.venv-v040/Scripts/python.exe -m pytest` com basetemp novo: **15 passed**. Ruff em todos os arquivos Python web via ambiente que já inclui Ruff: aprovado. `tools/scripts/lint_and_tests.py`: estrutura aprovada; o próprio venv web não contém o módulo Ruff.
- Testes direcionados cobrem migração `0006→0007→0006` em SQLite sintético; documento oficial imutável; demo sem escrita; revisão obsoleta; diff; build/hash; negação de orçamento antes do transporte; settle único; colisão sem substituir coleção; teste/ativação/retorno; versão capturada durante ativação; cap de campanha persistente e cancelamento pré-envio.
- Contrato web: OpenAPI 3.1 `info.version=0.5.0`, 22 operações `/v1`; `tools/generate_client.py` gerou 22 aliases a partir do snapshot.
- `git diff --check` padrão sinaliza `CR` das linhas adicionadas nos arquivos originalmente CRLF. Conferência com `-c core.whitespace=cr-at-eol` é a apropriada para distinguir fim de linha Windows de whitespace excedente; não foi alterada configuração Git.

## QA real: preparado, não executado

O próximo QA pode criar runtime NOVO explícito e injetar a guarda antes de bootstrap, embedding ou primeiro atendimento:

```python
from merchant_assistant.config import Settings
from merchant_assistant.main import build_orchestrator
from merchant_assistant.orchestration.budget import (
    BudgetGuard, CombinedBudgetGuard, FixedBudgetGuard,
)

settings = Settings(_env_file=None, runtime_dir=qa_runtime_novo)
base = BudgetGuard(ledger_existente, limit_usd=1.00)
cap = FixedBudgetGuard(cap_persistente, 0.25, cap_id="v050-qa")
guard = CombinedBudgetGuard(base, cap)
orchestrator = build_orchestrator(settings, budget=guard)
```

`qa_runtime_novo` isola SQLite/Qdrant/trace; `ledger_existente` mantém os registros e o limite nativos; `cap_persistente` é o mesmo caminho em todas as tentativas QA. Recriar o runtime de atendimento não recria esse cap. Não renomear o ID, não limpar o sidecar nem fornecer outro valor para o mesmo ID. Os segredos entram somente por configuração segura em memória; não são copiados para arquivo ou frontend. O SDK não tenta novamente chamadas pagas sem nova reserva. QA deve fixar esse cap apenas uma vez, validar preços/modelos primeiro e nunca chamar se custo/preço for desconhecido.

## Limites e próxima passagem

- Nenhuma inferência, embedding ou judge real foi disparado pelo Developer; pytest/fakes são determinísticos.
- A jornada paga fim a fim, JEV real/modelos pendentes da v0.4 e custo final continuam sem evidência até QA autorizado.
- Nenhum Reviewer/QA foi iniciado aqui; não há parecer próprio nem decisão de release. Próximo responsável: Reviewer independente; após correções, Supervisor fixa o candidato e despacha QA real autorizado.
- Commit, push, publicação, migração de banco do responsável, limpeza de coleções e alterações de credenciais não foram executados.
