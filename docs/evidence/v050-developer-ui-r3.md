# Passagem Developer — reconfirmação de teto KB v0.5 (UI r3)

**Estado:** correção local concluída; revisão independente do delta r6 pendente. Não é autoaprovação nem aceite de QA.

## Escopo e candidato-base

- Tarefa: `docs/tasks/51-reconfirmar-teto-kb-v050.md`; achado `WUI-R1-01` do parecer independente UI r1.
- Candidato r5 preservado: `docs/evidence/v050-candidato-r5.json`; fingerprint combinado da fonte `71818710468cd1ad63a83c49e8eec61e5db28bf5d824381b0e0e3d509e40d76c`.
- Web: branch `codex/v0.5.0-base-versionada`, HEAD base `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`.
- Mudanças de produto limitadas a `app.py`; regressão atualizada em `tests/test_interface.py`. Bytes r5 foram preservados em `.pytest_cache/v050-r6-confirmation-originals/`.
- Recuperação manual do chat não foi alterada. Backend/runtime, API, OpenAPI, guardas, credenciais e orçamento permaneceram intactos.

## Correção

O contexto de confirmação de build agora inclui o teto numérico efetivamente retornado pelo widget, junto ao digest, ativa e revisões. O contexto de teste inclui o teto junto à candidata e versão ativa. Em cada rerun, qualquer mudança de teto altera o contexto e desmarca a confirmação antes de renderizar o checkbox. O valor permanece no estado do próprio `number_input`; não há callback de envio nem POST até nova confirmação e clique explícito.

## Validação

Fakes e AppTest apenas; nenhuma API real ou chamada paga:

- Teste focado `tests/test_interface.py -k kb_confirmation_controls_enable_once_without_form_submission --basetemp=.pytest_cache/v050-r6-target -q` — **1 passou, 19 filtrados**. Para build e teste, elevou e reduziu o teto depois da confirmação; em cada mudança o checkbox ficou desmarcado, o botão desabilitado e o valor digitado permaneceu. Os contadores de build/teste ficaram em zero até reconfirmar e clicar. Depois do clique, o cliente falso recebeu uma chamada com o teto reconfirmado (`0.125` no build; `0.11` no teste).
- `tools/scripts/lint_and_tests.py --strict`, `.venv-v040`: **20/20 testes passaram**; estrutura e skills passaram. O script retornou **código 2** porque Ruff não está instalado nesse venv.
- Ruff externo no conjunto web: `python -m ruff check app.py src tests tools` — **All checks passed!** Nenhum pacote foi instalado.
- A suíte completa mantém regressões da recuperação manual GET, do tratamento de transporte e dos outros controles da KB. Backend não foi retestado nem alterado.

## Próxima passagem

Supervisor fixa r6 após esta passagem; o mesmo Reviewer valida a alteração de contexto; depois o mesmo QA revalida no candidato r6 e na mesma campanha já existente. Nenhuma operação real, limpeza, commit, push ou publicação foi feita.
