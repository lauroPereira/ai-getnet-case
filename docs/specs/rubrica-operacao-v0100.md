# Rubrica `judge.v4` e operação — v0.10.0

Versão 0.1 — 2026-11-05 — escrita pelo Supervisor; sequência **autorizada pelo responsável em 2026-11-05 ("A, C, B, E")**: C = rubrica, B = operação, E = leitura final do README. Deriva da [especificação 0.2](evolucao-pos-feedback.md) (RF-97, RF-104, RF-105), do [plano](evolucao-pos-feedback-plano.md) (v0.10.0, renumerada para 83 a 86) e do resultado da v0.9.0 ([ADR 0021](../architecture/decisions/0021-juiz-modelo-e-regua.md)). Vale a "Autorização por versão" do AGENTS.md. Prazo externo: 2026-11-06 às 08h; cada bloco só entra na `main` com QA apto e README e CHANGELOG coerentes, para a `main` ser entregável a qualquer hora.

## Problema

1. O experimento da v0.9.0 mostrou que nenhum dos dois juízes marca a frase genérica sem fonte que o humano marca, porque a rubrica `judge.v3` define afirmação sem suporte como "fato, valor, data, status ou promessa". A lacuna foi registrada como da rubrica; falta fechá-la e remedir.
2. Ressalvas do avaliador ainda abertas no bloco de maior potencial restante: a comparação de perfis roda numa thread do processo e um reinício a marca como `failed` (Memory, Production); métricas, alertas e painel só descritos (Observability).

## Resultado desejado

1. `judge.v4` acrescenta a frase genérica sem fonte à definição de afirmação sem suporte; as mesmas 24 respostas calibradas são rejulgadas com DeepSeek e com Opus sob a v4, e o relatório dos dois juízes mostra v3 × v4 contra as mesmas notas humanas (CA-57).
2. Uma comparação interrompida por reinício da API fica `interrupted` com as células concluídas preservadas e pode ser retomada pela API, continuando só as células que faltam, sem duplicar gasto (CA-58).
3. `GET /metrics` em texto Prometheus com contadores e somas por rota e por resultado (requisições, custo, chamadas de modelo, falhas de ferramenta, encaminhamentos, duração), e um arquivo versionado de regras de alerta sobre essas métricas (CA-59).

## Escopo

| Bloco | Conteúdo | Requisitos | Tarefa |
| --- | --- | --- | --- |
| C | `prompts/judge.v4.md` (arquivo novo), `RUBRIC_VERSION` selecionável (`--rubric v3\|v4`, padrão `v3` nesta versão até a remedição), rejulgamento das 24 com os dois juízes sob a v4, relatório v3 × v4 | RF-91, RF-108, CA-57 | 83 |
| B1 | Comparação retomável: estado `interrupted` no startup para `running` sem thread viva, `POST /v1/comparisons/{id}/resume` que continua só as células sem resultado, reuso dos resultados gravados | RF-104, CA-58 | 84 |
| B2 | `GET /metrics` (texto Prometheus, sem dependência nova) a partir de `traces.sqlite3` e do ledger, `alerts/rules.yml` versionado (orçamento perto do teto, taxa de falha de ferramenta, taxa de encaminhamento, latência p95), README | RF-97, CA-59 | 85 |
| Fechamento | Regressão, candidato, revisão, QA (rejulgamento real; reinício real da API no meio de uma comparação; `/metrics` ao vivo), ADR 0022, README, CHANGELOG | CA-57 a CA-59 | 86 |

Critérios novos (numerados aqui): **CA-57** relatório v3 × v4 dos dois juízes contra as mesmas 24 notas, com a condição (b) de D2 reavaliada (frases genéricas S01, S13, S16, S21) e a decisão do padrão da rubrica registrada; **CA-58** uma comparação iniciada, API reiniciada no meio, retomada pela API, termina `completed` com o mesmo número de células e sem célula paga duas vezes (ledger); **CA-59** `/metrics` responde em texto Prometheus válido com pelo menos `requests_total{route,status}`, `model_calls_total`, `cost_usd_total`, `tool_failures_total`, `handoffs_total`, `request_duration_seconds` (histograma ou sumário), e as regras de alerta referenciam só métricas que existem.

## Fora do escopo

Resumo rolante de conversas longas (RF-105; fica em próximos passos salvo tempo sobrando); OTLP; painel; provedor Anthropic nos agentes; mudança de `RETRIEVAL_MODE` ou `RERANK`; novo holdout.

## Decisões

| ID | Decisão | Motivo | Como reverter |
| --- | --- | --- | --- |
| D1 | `judge.v4` difere da v3 em uma frase: afirmação sem suporte inclui "a general claim stated as fact with no source in the evidence (for example 'rates vary by contract' when no passage says so)"; o resto é idêntico. `RUBRIC_VERSION` continua `judge.v3` por padrão até o resultado da remedição; a troca do padrão é decisão registrada na tarefa 86 com os números | Mudar uma variável por vez; comparabilidade com a v0.8.0 | Voltar o padrão |
| D2 | Regra de decisão do padrão da rubrica, escrita antes de rodar: v4 vira padrão se, com o DeepSeek, a concordância do veredito com o humano não cair e pelo menos 2 das 4 genéricas forem marcadas, sem que a concordância ±1 dos critérios piore em mais de 0,05 em qualquer um. O Opus sob v4 é reportado, não decide | Mesma disciplina da v0.9.0 | — |
| D3 | Comparação: no startup, toda linha `running` sem thread viva vira `interrupted` (estado novo, sem migração: a coluna `state` aceita o valor por `CHECK`? se o `CHECK` impedir, migração 0012 reversível que amplia o `CHECK`); `resume` lê `cells`, pula as com `request_id`, executa as demais com a mesma `config` e o mesmo `estimate`, reserva só o que falta; `read` mostra `interrupted` em vez de `failed` | Ressalva literal do avaliador | — |
| D4 | `/metrics` é calculado sob demanda a partir de `traces.sqlite3` (`requests` e `steps`) e do ledger, com cache de 5 s; sem biblioteca Prometheus; formato de exposição texto 0.0.4; sem rótulo com texto de mensagem ou id de lojista | Zero dependência, zero dado pessoal | Trocar por cliente oficial |
| D5 | `alerts/rules.yml` no formato de regras do Prometheus (grupo `merchant-assistant`), com 4 regras e `runbook` apontando para o README; validado por teste que confere que cada métrica citada existe em `/metrics` | "Regras de alerta versionadas" é a ressalva literal | — |
| D6 | QA real da B1 com modelo real: comparação de 2 perfis × 3 cenários (≈ US$0,05), API morta no meio por `taskkill`, reiniciada, `resume`; seed ressemeada se passar da meia-noite | CA-58 exige reinício real | — |

## Orçamento

Projeto: ledger em US$1,419 de US$2,00; previsto nesta versão: rejulgamento DeepSeek das 24 × 3 (≈ US$0,03), comparação do QA (≈ US$0,05 a US$0,10), smoke; teto da versão US$0,25. Anthropic: 24 × 3 no Opus sob v4 (≈ US$1,30) dentro dos US$2,52 restantes do cap de US$4,00 já autorizado.

## Riscos

| Risco | Mitigação |
| --- | --- |
| v4 piora os critérios 1 a 5 ao tornar o juiz mais severo | Regra D2 com tolerância de 0,05 e os dois resultados publicados |
| `CHECK` da tabela `comparisons` impede `interrupted` | Migração 0012 reversível, testada nos dois sentidos |
| Reinício real da API no QA derruba o Qdrant embutido | Runtime isolado; Qdrant embutido reabre; é exatamente o cenário medido |
| Meia-noite | Nada pago entre 23h50 e 00h10; `bootstrap` antes de qualquer fase real depois |
| Prazo | Ordem C → B1 → B2; se B2 não couber, a versão fecha com C e B1 e `/metrics` fica em próximos passos |

## Tarefas

83. [Rubrica `judge.v4` e remedição dos dois juízes](../tasks/83-rubrica-judge-v4-remedicao.md).
84. [Comparação retomável após reinício](../tasks/84-comparacao-retomavel.md).
85. [`/metrics` e regras de alerta versionadas](../tasks/85-metrics-e-alertas.md).
86. [Fechamento da v0.10.0](../tasks/86-fechamento-v0100.md).

História de uso: [rubrica-operacao-v0100.md](../historias/rubrica-operacao-v0100.md).
