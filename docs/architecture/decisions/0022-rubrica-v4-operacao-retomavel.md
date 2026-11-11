# 0022. Rubrica `judge.v4` medida e não promovida; comparação retomável após reinício; métricas e alertas versionados

## Título

Fechar a lacuna da rubrica com uma frase nova (`judge.v4`), medi-la com os dois juízes contra as mesmas notas humanas e manter `judge.v3` como padrão pela regra escrita antes; tornar a comparação de perfis retomável após reinício da API; expor `/metrics` em texto Prometheus a partir dos traces e do ledger, com regras de alerta versionadas.

## Status

Aceita (v0.10.0, 2026-11-06). Superada em parte pelas ADRs [0023](0023-juiz-por-afirmacao-evidencia-web.md) (`judge.v5` padrão, v0.11.0) e [0025](0025-identidade-e-operacao.md) (lease entre workers e painel, v0.13.0). Complementa as ADRs 0019 e 0021. Spec: [rubrica-operacao-v0100.md](../../specs/rubrica-operacao-v0100.md); validação real do juiz em [v0100-qa-juiz-r1.md](../../evidence/v0100-qa-juiz-r1.md).

## Contexto

1. A v0.9.0 mostrou (ADR 0021) que nenhum dos dois juízes marca a frase genérica sem fonte que o humano marca, e atribuiu a lacuna à rubrica, que define afirmação sem suporte como "fato, valor, data, status ou promessa". Faltava testar essa atribuição.
2. A comparação de perfis rodava numa thread do processo e um reinício a marcava como `failed`; métricas, alertas e painel estavam só descritos.

## Decisão

**Rubrica.**
- `prompts/judge.v4.md` é a v3 mais uma frase: afirmação sem suporte inclui "a general claim stated as fact with no source in the evidence". Nada mais muda; `judge.v3.md` fica intocado (hash conferido em teste).
- `--rubric v3|v4` em `eval --judge-repeat` e em `eval-calibrate --import`, com uma única resolução (`--rubric` > `judge.RUBRIC_VERSION` > v3); cada julgamento grava a rubrica usada; `eval-calibrate` compara qualquer lista de (juiz, execução, rubrica) contra as mesmas notas humanas, com a tabela das frases genéricas e a linha da regra.
- **Regra escrita antes (D2):** a v4 vira padrão se, com o DeepSeek, o veredito não cair, pelo menos 2 das 4 genéricas forem marcadas e nenhum critério piorar mais de 0,05 em ±1. **Resultado:** DeepSeek v4 × v3: veredito 0,792 contra 0,667 (sim), genéricas 0 de 4 (não), critérios dentro de 0,05 (sim). Opus v4 × v3 (reportado): 0,917 contra 0,875, 2 de 4 (S01, S21), dentro de 0,05. **`judge.v3` continua o padrão**; v4 disponível por configuração.
- Leitura: a frase funciona quando o modelo consegue aplicá-la; o juiz padrão não a aplica. A lacuna é de rubrica e de modelo juntos; fechá-la exige trocar os dois, o que a regra de custo da ADR 0021 (54×) não autoriza sozinha. A v0.11.0 trocou a rubrica pela avaliação por afirmação (`judge.v5`, [ADR 0023](0023-juiz-por-afirmacao-evidencia-web.md)).

**Comparação retomável.**
- Migração 0012 (reversível) amplia o `CHECK` de `comparisons.state` com `interrupted`; o downgrade converte em `failed`.
- No startup e em qualquer leitura, uma comparação `running` sem thread viva vira `interrupted`, com as células concluídas preservadas e a tentativa em curso registrada em `interrupted_attempts` com o custo lido do ledger (somado uma vez).
- `POST /v1/comparisons/{id}/resume[?retry_failed=true]` executa só as células sem resultado, reserva só o que falta, acumula `cost_usd` e responde `409` com código próprio para `running`, `completed`, nada a retomar e fatores fixos alterados. O registro da thread acontece antes de `running` ficar visível e cada thread libera só a própria entrada; dois `resume` concorrentes executam cada célula uma vez.
- Na v0.10.0 o registro de threads era por processo, com um worker, e a reivindicação comparava só o estado (janela ABA teórica); superado na v0.13.0 (RF-123). **Atualização da v0.13.0** ([tarefa 99](../../tasks/99-workers-webhooks-orfaos.md)): o registro em memória deu lugar a uma lease no banco (`worker_id`, `heartbeat_at`, renovada a cada 5 s, vencida depois de 20 s); a retomada lê a linha, confere e grava a nova lease na mesma transação `BEGIN IMMEDIATE`, então a janela ABA deixou de existir. Toda escrita da execução exige a lease, célula a célula: um dono que a perdeu termina a célula em curso, nada dela é gravado em `comparisons` e ele não começa outra; a célula roda de novo sob o novo dono, e o custo da tentativa encerrada fica em `interrupted_attempts`. A retomada é o `POST .../resume` do dono, atendido por qualquer worker. A API roda com dois workers.

**Métricas e alertas.**
- `GET /metrics` em texto de exposição 0.0.4, calculado sob demanda de `traces.sqlite3` e do ledger, com cache de 5 s, sem dependência nova: `requests_total{route,status}`, `model_calls_total{agent}`, `tool_calls_total{tool,outcome}`, `tool_failures_total{tool}`, `handoffs_total`, `replan_total{origin}`, `request_duration_seconds` (histograma), `cost_usd_total{provider}`, `budget_remaining_usd`, `budget_limit_usd`.
- Todo rótulo vem de um conjunto fechado do código (rotas, status, agentes, regras do replanejador, ferramentas, provedores); qualquer outro valor vira `other`; um teste de deriva prende os conjuntos ao código. Nenhum rótulo carrega texto, `request_id`, lojista ou operador.
- Banco vazio, corrompido ou travado nunca dá 500: o coletor serve a última leitura completa (zerado só antes da primeira). `/metrics` é público como `/ready` (só contagens); em produção, restringir por rede ou token.
- `alerts/rules.yml` (formato Prometheus, grupo `merchant-assistant`): orçamento abaixo de 10% do teto, falha de ferramenta acima de 5% em 15 min, encaminhamento acima de 30% em 1 h, p95 acima de 20 s em 15 min; cada regra com `runbook_url` para a seção Observability do README; um teste confere que toda métrica citada existe.

## Alternativas consideradas

- **Promover a v4 porque melhora o veredito:** ignoraria a regra escrita antes e a condição que mede o que importa (as genéricas); não adotado, reversível pelo responsável.
- **Trocar juiz e rubrica de uma vez (Opus + v4):** custo 54× por julgamento; fica como opção explícita, não como padrão.
- **Reexecutar a comparação do zero após reinício:** pagaria de novo as células concluídas; não adotado.
- **Cliente Prometheus oficial em processo:** dependência e estado em memória que se perde no reinício; o cálculo sob demanda sobre o que já é gravado é suficiente para 145 chunks e uma instância.
- **Painel versionado:** não adotado nesta versão; entregue na v0.13.0 ([ADR 0025](0025-identidade-e-operacao.md)).

## Consequências

- Positivas: a hipótese da v0.9.0 fica testada com número; a comparação sobrevive a reinício sem pagar duas vezes; há métricas e alertas que um Prometheus local consome em duas linhas de `scrape_config`.
- Custos assumidos: `/metrics` recalcula a cada 5 s a partir do SQLite; `human_reply` e retomadas entram nos denominadores das taxas. A rubrica padrão passou ao `judge.v5` na v0.11.0 e a API roda com dois workers desde a v0.13.0.
- Resultado da validação operacional (CA-58, CA-59, [registro](../../evidence/v0100-qa-ops-r1.md)): comparação real de 2 perfis × 3 cenários morta com `taskkill` após 1 de 6 células; após o reinício, `interrupted` com a célula concluída intacta e a tentativa em curso registrada com o custo reservado; `resume` → `202 {resumed_cells: 5}` → `completed` em 46 s, uma linha de ledger por célula, `cost_usd` igual à soma; segundo `resume` → `409`. `/metrics` igual aos traces e ao ledger; nenhum rótulo com identificador. Custo US$0,006 em ledger isolado.

## Data

2026-11-06.
