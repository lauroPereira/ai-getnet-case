# Tarefa: Regressão e candidato dos dois projetos

## Objetivo

Fixar e validar o candidato backend/web com revisão e QA independentes.

## Especificação relacionada

CA-28, CA-32–37, CA-44 e RNF-13; [plano v0.4.0](../specs/perfis-interface-v040-plano.md).

## Pré-condições

Tarefas 27–31 completas no escopo aprovado, autorizações de delegação/rede e gasto real separadas.

## Arquivos prováveis

Testes, histórias, manifestos Git/hashes, README/changelog e evidências dos dois projetos.

## Passos

1. Executar validação estrita Python, AppTest, núcleo/jornadas/conversas sem custo e Docker/MCP proporcionais.
2. Fixar candidato dos dois projetos, história, contratos, catálogo, fixtures e ambiente; usar hashes Git ou bytes com algoritmo explícito.
3. Despachar Reviewer em contexto novo; correções retornam ao Developer e geram candidato revisado.
4. Após revisão apta, despachar QA pela história; preparar estimativa real por provedor e pedir autorização antes de chamadas pagas.
5. Relatar critérios comprovados/lacunas/retorno; commits, pushes, remotos e tags exigem aceite humano específico da entrega.

## Critérios de conclusão

- [x] Regressão do núcleo e v0.3.0 preservada, com custos/modos separados. *Regressão real do núcleo na v0.6.0.*
- [x] Reviewer e QA independentes identificam o mesmo candidato backend/web.
- [x] Nenhum requisito real concluído somente por testes programados; lacunas explícitas.
- [x] APIs dentro de US$5 e autorização adicional própria; nenhum ledger reiniciado.
- [x] Integração/publicação somente após autorização correspondente.

## Validação

Backend `.venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`, com `PYTHONDONTWRITEBYTECODE=1` e `PYTEST_ADDOPTS=--basetemp=.pytest_cache/v040-strict-r4-final-20261027`: **214 passed**, Ruff e skills passaram. Web `.venv-v040/Scripts/python.exe -m pytest -q --basetemp=.pytest_cache/v040-web-r4-final-20261027`: **12 passed**; Ruff check/format passou. AppTest Real e fluxo API HTTP sintéticos cobrem login, perfil, conversa, comparação, uso único, administração, catálogo/parâmetro, trace, logout e 401 na mesma conexão após 204 vazio. Ver passagem Developer r4. CA-32 não executado; sem chamadas pagas. Reviewer e QA da rodada r4 ainda não aprovaram o candidato.

## Status

```text
concluída (v0.4.0)
```

Revisão independente e QA real aptos ([resultado](../evidence/v040-resultado.md)). A chamada real ao JEV (CA-32) foi feita na v0.5.0 e a regressão real do núcleo na v0.6.0.
