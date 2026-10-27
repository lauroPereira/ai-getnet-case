# Tarefa: tratar as pendências P3 da revisão v0.5.0 r2

## Objetivo

Corrigir os achados P3 do [parecer r2](../evidence/v050-reviewer-r2.md) sem
bloquear o QA real do candidato já apto. R2-06 foi decidido pelo responsável
(sidecar `<ledger>.limit` aceito) e não faz parte desta tarefa.

## Especificação relacionada

[Plano](../specs/base-versionada-v050-plano.md), [spec](../specs/base-versionada-v050.md),
[ADR0014](../architecture/decisions/0014-ciclo-kb-v050.md) e
[tarefa45](45-correcao-revisao-v050-r1.md).

## Pré-condições

- Executar depois do QA real do candidato apto, ou junto com defeitos que o QA
  devolver, para não invalidar a rodada em andamento.
- Developer Claude Sonnet 5.5 autorizado; sem chamada paga, commit ou push.
- Sem alterar contrato público, permissões, ledgers reais, coleções existentes
  ou o teto já gravado em qualquer `<ledger>.limit`.

## Arquivos prováveis

`src/merchant_assistant/orchestration/budget.py`, `rag/kb.py`,
`orchestration/graph.py`, `cli.py`, `main.py` e testes relacionados.

## Passos

1. R2-01: gravar o teto com representação exata (`repr`/`.17g`) ou comparar
   com tolerância; a primeira montagem nunca recusa o próprio valor.
2. R2-02: publicar o arquivo de teto de forma atômica (temporário no mesmo
   diretório e `os.link`/`os.replace`), sem sobrescrever teto existente.
3. R2-03: `readiness()` e captura usam caminho somente leitura quando o
   registro KB já existe; escrita só na primeira inicialização.
4. R2-04: verificar integridade no Qdrant antes do `BEGIN IMMEDIATE` e repetir
   dentro da transação só a conferência barata de estado — ou registrar o
   risco aceito se o QA não observar contenção.
5. R2-05: timeout explícito (30 s, como no runtime) no cliente OpenAI do CLI.
6. R2-07: remover `BudgetGuard.record`/`record_embedding` sem chamadores, ou
   restringi-los a uso interno documentado, ajustando o teste associado.
7. R2-08: testes de `max_retries == 0` nos três clientes reais (sem rede) e de
   ativação/retorno com manifesto sem `chunks`/`point_digest` e coleção vazia.
8. Validação estrita backend e passagem r3.

## Critérios de conclusão

- [ ] Cada item tem regressão sintética que falha antes e passa depois
  (ou risco aceito registrado, no caso de R2-04).
- [ ] Nenhum teto gravado é alterado; montagem concorrente não falha.
- [ ] `python tools/scripts/lint_and_tests.py --strict` passou; nenhuma chamada paga.
- [ ] Novo candidato e revisão focada antes de integrar.

## Validação

Pendente.

## Status

Aberta — aguarda o QA real do candidato apto.
