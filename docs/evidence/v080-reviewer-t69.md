# Revisão independente das tarefas 69 e 68b — rodada 1

- **Candidato:** `e1cbffbe0a96e9dcd29120af7e9aca4ad4be9ea2`, branch `codex/v0.8.0-replan`, base `5134eff`; worktree destacado `review-a2`, HEAD e status iguais antes e depois. Diff de 21 arquivos.
- **Independência:** subagente `reviewer` (sonnet/xhigh) em contexto frio; leu as tarefas até "Validação"; leu a ADR 0019 só depois de formar opinião; não leu a passagem do Developer. Gravado pelo Supervisor a partir do relatório do Reviewer.
- **Parecer:** **correções necessárias** — 1 P2.

## Achado

**P2-1 — na rota `general_web`, a guarda de repetição (D5) e o orçamento (D6) podem ser furados.** O nó `knowledge` é a busca web nessa rota e grava `ran = "web"` (`orchestration/graph.py:151,175`); `allowed_next` e `_guard` (`agents/replanner.py:312-316,373`) não reconhecem `knowledge` como já executado, então o modelo pode escolher `knowledge` de novo, o que refaz a busca web e sobrescreve o resultado; com `escalate` isento do orçamento, os saltos chegam a 4. Reproduzido com Support devolvendo seleção e escalada e o planejador escolhendo `knowledge`, `knowledge`, `escalate`: três buscas web e `plan_hops = 4`. Só no caminho do modelo, estreito mas determinístico; a enumeração dos estados alcançáveis dá máximo 4 com o alias e 3 sem ele.

## P3

1. `finish` do modelo com `review=incomplete` não grava a lacuna (`replanner.py:348-350,395-410`); a Personality ainda vê `missing` e a nota, mas "concluir exige revisão completa" só vale de fato no caminho das regras.
2. Rótulos dos cenários soltos: `REPLAN-WEB` passa com "não encontrei"; `REPLAN-PROCEDURE` aceita fontes do próprio Support; `REPLAN-TOOL-DOWN` passa sem replanejamento. Os caminhos só ficam presos nas asserções de `agents` e decisões dos testes; com modelo real, os rótulos sozinhos não provam o replanejamento.
3. O nome `executed_path` não existe no Time A; o caminho está em `agents` e no trace. O runner do Time B (tarefa 70) deriva o campo de `agents` (D16).
4. A regra `complete` fecha com `review=complete` quando o Knowledge diz evidência suficiente e lista `missing` (fixado de propósito por teste); rótulo otimista no trace.
5. A prova da lacuna honesta para na entrega à Personality: a política programada ignora `unconfirmed`, o `personality.v4` não cita a chave e o fallback determinístico omite a lacuna. Só a campanha real prova o texto.
6. 68b: o comportamento já existia (`integrations.py:229-231`); o teste novo passa na base e mata 5 mutantes. A observação O-8 do QA no Docker não foi reexplicada pelo teste.
7. Falha do Support depois de queda de ferramenta: duas regras discordam e o modelo é chamado (resposta controlada com protocolo); raro, não é regressão.
8. `hops` conta `escalate` (documentado na ADR; a D6 fala em "outro especialista"); `replan` não está em `profiles.AGENTS` e cai no modelo base.

## Comprovado por execução

- **Regras antes do modelo:** eval programado com 123 chamadas de modelo na base e no candidato e 0 chamadas ao `replan`; pergunta simples com 3 chamadas; ambiguidade construída com exatamente 2. Enumeração de 380 032 estados: o modelo só é consultado em conflito de regras ou sem regra. Nenhuma regra manda à web o que deveria escalar.
- **D5/D6 nas rotas `knowledge` e `support`:** nenhum especialista repetido, laço forçado em ≤ 3 saltos, limites de chamadas e custo respeitados, lacuna entregue no limite.
- **D7/D16:** passo `replan` com `next`, `reason`, `review`, `hops`, `origin`, `observed`; `route` é o plano inicial; `agents` na ordem real.
- **CA-49 programado:** os quatro cenários passam com `agents` e decisões exatos.
- **Regressão × base:** 40 casos (25/40, `route_ok` 1,0, custo 0) e 4 conversas idênticos campo a campo, normalizado o sufixo do protocolo `HO-`.
- **D3/D18:** grafo de retomada, `human_review` e `escalation.py` intactos; nenhum `test_v070_*` alterado; 9 arquivos da v0.7.0 → **128 passed**.
- **Mutação:** 27 mutantes, 26 mortos; o sobrevivente (M02) é equivalente em resultado.
- **Suíte estrita** (Supervisor, neste candidato): **704 passed**, código 0.

## Não comprovado

`replan.v1` com modelo real; texto real da lacuna; cenários com modelo real; O-8 no Docker.
