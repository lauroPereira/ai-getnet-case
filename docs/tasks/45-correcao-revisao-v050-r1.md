# Tarefa: embeddings sob guarda, coleções preservadas e liquidação única (v0.5.0)

## Objetivo

Corrigir seis pontos de orçamento, coleções, integridade, liquidação, estado publicado e teto antes de fixar novo candidato para a validação real.

## Especificação relacionada

[Plano aprovado](../specs/base-versionada-v050-plano.md) e
[história v1](../historias/base-versionada-v050.md).
São correções do escopo aprovado, sem ampliar API, permissões ou orçamento.

## Pré-condições

- Nenhuma chamada paga nesta tarefa.
- Nenhuma alteração em credenciais, arquivos protegidos, dados/ledgers reais,
  coleções existentes, limite nativo ou configuração global.

## Arquivos prováveis

`src/merchant_assistant/cli.py`, `config.py`, `orchestration/budget.py`,
`orchestration/graph.py`, `rag/embed.py`, `rag/index.py`, `rag/kb.py` e testes
relacionados. Web somente se correção comprovada exigir, dentro do plano.

## Passos

1. Fechar os caminhos pagos de embeddings do CLI. Toda chamada recebe
   guarda persistente antes da rede; embedding real sem guarda falha antes
   do provedor. Exercitar `index`, `bootstrap` e `eval-retrieval` com transporte
   falso, incluindo negação e uso desconhecido.
2. Impedir que CLI/bootstrap apaguem ou reconstruam coleções existentes,
   sobretudo ativa/anterior/referenciadas. Preferir reutilização segura ou
   recusa explícita; coleção nova nunca colide. Preservar bootstrap idempotente
   e não executar remoção fora de Qdrant exclusivamente em memória nos testes.
3. Conferir integridade da coleção contra o manifesto antes da troca
   do ponteiro (contagem, dimensão/modelo e pontos/digest esperados). Coleção
   vazia ou corrompida não permite ativação nem retorno; o ponteiro fica igual.
   Readiness deve observar a versão ativa atual sem chamada paga.
4. Tornar liquidação única e consistente. Repetição do mesmo valor pode
   ser idempotente; valor divergente ou liquidação de cancelada não reduz gasto.
   Validar concorrência e falha parcial do guard composto, preservando reserva
   conservadora quando o uso é desconhecido. Rejeitar valores monetários
   inválidos em vez de liberar saldo.
5. Teste de versão não rebaixa estado publicado. Restringir a candidatas
   ou persistir resultado sem modificar `active`/`retired`; proteger também
   contra corrida entre teste e transição.
6. Impor teto absoluto finito de US$5 na configuração e guarda, sem
   aumentar limite persistido. Cap adicional continua fixo em até US$0,25;
   limite nativo de US$1 e ledgers reais permanecem intocados.
7. Executar regressões sintéticas significativas e validação estrita do backend.

## Critérios de conclusão

- [x] Os seis casos reproduzidos têm regressão sintética que falha
  no comportamento anterior e passa após a correção.
- [x] Toda tentativa paga tem reserva anterior; não há SDK retry opaco.
- [x] Coleções publicadas e manifestos permanecem imutáveis; corrupção e corrida
  não produzem transição incoerente.
- [x] Nenhuma repetição/liquidação concorrente reduz custo já conhecido.
- [x] US$5 absoluto e cap persistente fixo não podem ser ampliados por remontagem.
- [x] `python tools/scripts/lint_and_tests.py` passou, com evidência objetiva;
  web foi revalidado se afetado. Nenhuma chamada paga foi executada.
- [x] Novo candidato fixado depois da correção e submetido a revisão independente.

## Resultado

Embeddings pagos do CLI sempre sob a guarda, coleções existentes preservadas, integridade conferida antes de trocar o ponteiro, liquidação única, estado publicado protegido no teste de versão e teto absoluto de US$5. Suíte estrita do backend: 293 testes (eram 221); nos quatro arquivos de regressão, 87 aprovados na árvore corrigida e 56 falhas numa cópia anterior à correção. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
