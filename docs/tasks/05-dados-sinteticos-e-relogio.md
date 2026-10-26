# Tarefa: Dados sintéticos e relógio

## Objetivo

Criar o banco SQLite com seed relativo a um relógio injetável, incluindo `cliente1988`, um segundo cliente e o glossário de status.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-18, RF-20, RF-21, CA-07. [Plano](../specs/assistente-multiagente-lojista-plano.md), seção Modelo de dados.

## Pré-condições

- Tarefa 03 concluída.
- [Decisão 0004](../architecture/decisions/0004-dados-sinteticos-sqlite-e-ferramentas-de-dominio.md) aceita.

## Arquivos prováveis

- `src/merchant_assistant/data/clock.py`, `db.py`, `seed.py`, `glossary.json`
- `tests/unit/data/test_clock.py`, `test_seed.py`

## Passos

1. Relógio com duas implementações (sistema e fixo), sempre no fuso `America/Sao_Paulo`, e presets de período (`yesterday`, `today`, `last_7_days`) resolvidos por ele.
2. Criar as tabelas do núcleo descritas no plano.
3. Seed de `cliente1988`: vendas em D-1 (à vista, débito e parcelada) com recebíveis previstos para D+1, status de origem `LOT_DONE` e repasse `SCHEDULED` sem crédito confirmado; uma maquininha sem conexão há algumas horas; uma transação negada no dia, com código sintético documentado; contrato com Pix, Link de Pagamento e maquininha.
4. Seed de `cliente_demo_002` com dados distintos, para isolamento.
5. Tabela sintética de códigos de negativa (código, categoria, chave de mensagem ao lojista).
6. Glossário de status: nome de origem preservado e conceito normalizado (ex.: `LOT_DONE` = lote processado, sem crédito confirmado).
7. Seed idempotente, recriado na inicialização.

## Critérios de conclusão

- [x] Com relógio fixo em 2026-10-26, todos os valores e datas são determinísticos.
- [x] Com o relógio do sistema, as vendas de `cliente1988` sempre caem no dia anterior.
- [x] Teste de virada de dia no fuso de São Paulo.
- [x] Nenhum dado real.

## Validação

2026-10-26: `tests/unit/data/` (15 testes) cobre fuso de São Paulo na virada do dia, períodos nomeados, dias úteis, seed determinístico com relógio fixo, vendas sempre em D-1 com o relógio do sistema, idempotência preservando encaminhamentos e isolamento entre clientes. Revisão não independente.

## Status

```text
concluída
```
