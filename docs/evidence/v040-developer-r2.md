# Passagem Developer r2 — correção P2 de orçamento

**Data:** 2026-10-27  
**Base:** candidata Developer r1 e parecer independente [v040-reviewer-r1.md](v040-reviewer-r1.md). Parecer e manifesto r1 foram preservados.  
**Escopo desta revisão:** resposta HTTP para `BudgetExceeded` em `POST /v1/router/compare`, regressões offline e documentação do erro. Nenhum arquivo do projeto web foi alterado.

## Delta

- O handler de comparação captura `BudgetExceeded` e responde HTTP `429` com código estável `request_budget_exceeded` ou `installation_budget_exceeded`. A mensagem informa que nenhuma comparação incompleta foi salva. O caminho não faz fallback nem inicia atendimento.
- O OpenAPI gerado declara `429` usando o corpo público `ErrorBody`.
- Quatro cenários paramétricos reproduzem limites por requisição e saldo global, antes do primeiro Router e antes do segundo.
- O contrato e a tarefa 33 documentam a semântica, resultados e estado pendente de nova revisão. A guarda, limites, reserva, liquidação e ledger não foram modificados.

## Validação

Teste focado (Windows; modelo, estimativa e liquidação programados; nenhum provedor chamado):

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_v1_api.py `
  -k budget_rejection `
  --basetemp=.pytest_cache/v040-budget-r2-target2-20261027
```

**Resultado:** exit 0; **4 passaram**. Nos casos antes do primeiro Router, não houve chamada ao modelo nem reserva contabilizada. Nos casos antes do segundo, a primeira chamada programada foi liquidada em US$0,03, a tentativa seguinte foi bloqueada antes de chamar o modelo e o ledger conservou exatamente essa liquidação. Os quatro casos retornaram `429` com o código correspondente; não houve linha em `router_comparisons`.

Validação strict completa:

```powershell
$env:PYTEST_ADDOPTS = '--basetemp=.pytest_cache/v040-strict-r2-budget-20261027'
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\Scripts\python.exe tools\scripts\lint_and_tests.py --strict
```

**Resultado:** exit 0; **206 testes passaram**; Ruff e validação de skills passaram. `git diff --check` também saiu com código 0. Os testes não fazem inferência paga nem acessam a API de provedor.

## Arquivos e hashes SHA-256

| Arquivo | SHA-256 |
| --- | --- |
| `src/merchant_assistant/api/v1.py` | `3ec7af0782f2c76e3807d150f326f4fb1a8b3215a90c2f0c4f7ab8906948dcd6` |
| `tests/integration/test_v1_api.py` | `87e1eaa15f4d811ce71e7704403958b8ae95372ce337dc2db7410aa2e4b8b5f3` |
| `docs/contracts/api-v040.md` | `f0dc166147699e1f82ab68296ee71e25d499353ae7b63ba859212bc263b134e1` |
| `docs/tasks/33-erro-orcamento-comparacao-v040.md` | `5388ec828e8951e03989e2e901077213c09d8acbb80ed1f002b3f50782423bda` |

## Estado

A correção cobre a falha P2 reproduzida sem custo. Aguarda congelamento e reavaliação pelo mesmo Reviewer. QA ainda não iniciou. CA-32 JEV real permanece pendente; nenhuma API paga foi chamada. Não houve commit, push, PR, tag, publicação nem alteração de ambiente ou ledger anterior.
