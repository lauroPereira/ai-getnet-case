# Passagem Developer r6 — seleção vinculada à comparação

**Data:** 2026-10-27  
**Branch backend:** `codex/v0.4.0-perfis-interface`  
**Base:** `bd549cc921ccffb37bd304a0959b8a4b690d6421`  
**Escopo:** resolver o achado funcional da QA r5 em que o rádio podia divergir da decisão vinculada ao `comparison_id`. A correção é somente no projeto web; API, backend e contrato permanecem inalterados.

## Alteração

Ao mudar o mecanismo selecionado com uma comparação ativa, a interface descarta imediatamente aquele resultado, esconde a ação de uso e informa que é necessária uma nova comparação. O formulário continua visível, mas comparar só acontece após novo clique explícito. Reruns não criam outro `comparison_id`; o botão de atendimento só aparece para uma comparação cuja escolha coincide com o rádio atual. O uso envia a decisão e o ID dessa comparação, uma única vez.

Essa regra preserva o vínculo imutável método/`comparison_id`: não altera o método de um ID existente e não faz comparação automática. Não foi necessário iniciar um backend para a correção web. O comportamento do backend ao reutilizar decisão JEV/LLM e registrar parâmetros efetivos permanece coberto pela integração sintética r5 em [passagem Developer r5](v040-developer-r5.md).

## Teste funcional

`test_changing_comparison_selection_invalidates_result_until_explicit_recompare` é parametrizado em ambas as direções: LLM→JEV e JEV→LLM. O AppTest confere que:

- a escolha, resumo e ação correspondem antes e depois da comparação;
- ao mudar a seleção, o resultado anterior é invalidado e a mensagem pede nova comparação;
- rerun depois da invalidação não chama `compare`;
- um novo `comparison_id` só é criado após clique explícito em comparar;
- o botão de uso envia uma única mensagem com o método escolhido e o novo `comparison_id`, sem chamar `compare` novamente.

## Validação executada

AppTest direcionado:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.venv-v040\Scripts\python.exe -m pytest -q `
  tests\test_interface.py::test_changing_comparison_selection_invalidates_result_until_explicit_recompare `
  --basetemp=.pytest_cache\v040-compare-selection-r6-target-20261027
```

**Resultado:** 2 passaram, uma por sequência.

Suíte web final e lint/format:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.venv-v040\Scripts\python.exe -m pytest -q `
  --basetemp=.pytest_cache\v040-compare-selection-r6-final-20261027
..\ai-getnet-case\.venv\Scripts\ruff.exe check --no-cache .
..\ai-getnet-case\.venv\Scripts\ruff.exe format --check --no-cache .
.venv-v040\Scripts\python.exe tools\scripts\lint_and_tests.py
```

**Resultado:** 14 testes passaram em 3,12 s; Ruff check passou; 72 arquivos estavam formatados. O script Python terminou exit 0 e validou a estrutura; também informou que lint não é executado em seu modo padrão. Os testes AppTest usam somente `SimulatedAPI`; nenhuma API de provedor ou backend real foi chamada. A interface web não foi validada contra um serviço HTTP novo nesta correção.

## Limites e estado

- Nenhum arquivo de backend, contrato público, OpenAPI ou cliente gerado foi alterado; o backend r5 pode ser reutilizado.
- Os testes comprovam comportamento de estado e chamadas do cliente simulado, não comportamento de provedor real. CA-32 continua pendente.
- Reviewer e QA da rodada r6 ainda não avaliaram o candidato. Esta passagem não declara aprovação nem release.
- Sem chamada paga, build, instalação, commit, push, tag, acesso remoto, publicação ou limpeza.

## SHA-256

| Projeto/arquivo | SHA-256 |
| --- | --- |
| web `app.py` | `B7911E93BB12CF5E341FDB6FA19EF27E2F50B0F477B8B625E52A9C2D37F7DDEF` |
| web `tests/test_interface.py` | `3148B6FDD03D61CBB0B531C0907A479BD35C25B6734E490DC6EB50802287999E` |
| web `README.md` | `216CBBBE7EBD742159FD9A3FF3A97DA7ADFEDC257D3CB0E7CF22588A606B4796` |
| backend `docs/tasks/38-selecao-comparacao-v040.md` | `2AD139BDDBF473E54691BFA8130E2868BF1DD5A57E904D6DB0A32CD0D24E7859` |
