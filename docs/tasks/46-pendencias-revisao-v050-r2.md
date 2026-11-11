# Tarefa: teto gravado exato, prontidão sem escrita e clientes reais sem retry

## Objetivo

Corrigir os pontos menores da revisão independente da v0.5.0 sem bloquear a validação real
do candidato já apto. O sidecar `<ledger>.limit` (R2-06) foi aceito pelo responsável
e não faz parte desta tarefa.

## Especificação relacionada

[Plano](../specs/base-versionada-v050-plano.md), [spec](../specs/base-versionada-v050.md),
[ADR 0014](../architecture/decisions/0014-ciclo-kb-v050.md) e
[tarefa 45](45-correcao-revisao-v050-r1.md).

## Pré-condições

- Executar depois da validação real do candidato apto, ou junto com defeitos que ela devolver.
- Sem chamada paga.
- Sem alterar contrato público, permissões, ledgers reais, coleções existentes
  ou o teto já gravado em qualquer `<ledger>.limit`.

## Arquivos prováveis

`src/merchant_assistant/orchestration/budget.py`, `rag/kb.py`,
`orchestration/graph.py`, `cli.py`, `main.py` e testes relacionados.

## Passos

1. Gravar o teto com representação exata (`repr`/`.17g`) ou comparar
   com tolerância; a primeira montagem nunca recusa o próprio valor.
2. Publicar o arquivo de teto de forma atômica (temporário no mesmo
   diretório e `os.link`/`os.replace`), sem sobrescrever teto existente.
3. `readiness()` e captura usam caminho somente leitura quando o
   registro KB já existe; escrita só na primeira inicialização.
4. Verificar integridade no Qdrant antes do `BEGIN IMMEDIATE` e repetir
   dentro da transação só a conferência barata de estado — ou registrar o
   risco aceito se a validação real não observar contenção.
5. Timeout explícito (30 s, como no runtime) no cliente OpenAI do CLI.
6. Remover `BudgetGuard.record`/`record_embedding` sem chamadores, ou
   restringi-los a uso interno documentado, ajustando o teste associado.
7. Testes de `max_retries == 0` nos três clientes reais (sem rede) e de
   ativação/retorno com manifesto sem `chunks`/`point_digest` e coleção vazia.
8. Validação estrita do backend.

## Critérios de conclusão

- [x] Cada item tem regressão sintética que falha antes e passa depois
  (ou risco aceito registrado, no caso da integridade no Qdrant).
- [x] Nenhum teto gravado é alterado; montagem concorrente não falha.
- [x] `python tools/scripts/lint_and_tests.py --strict` passou; nenhuma chamada paga.
- [x] Novo candidato e revisão focada antes de integrar.

## Resultado

Itens implementados e validados na [tarefa 54](54-estabilizacao-v060.md); a verificação de integridade no Qdrant dentro da transação de ativação ficou como risco aceito, sem contenção observada na validação real. Evidência: [resultado da v0.6.0](../evidence/v060-resultado.md).

## Status

```text
concluída (v0.6.0)
```
