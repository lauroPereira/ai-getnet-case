# Revisão independente da T70 — rodada 1

- **Candidato:** `f3872d669f1c821e7c2dd9fdde3f2e8c7ebb423d`, branch `codex/v0.8.0-avaliacao`, base `8f2baa6`; worktree destacado `review-a`, HEAD e status iguais antes e depois.
- **Independência:** subagente `reviewer` (sonnet/xhigh) em contexto frio; leu a tarefa até "Validação", a spec e o plano; não leu as passagens do Developer; não abriu o conteúdo do holdout (blob idêntico entre base e candidato, lacre verde). Gravado pelo Supervisor a partir do relatório do Reviewer.
- **Parecer:** **correções necessárias** — 1 P2, 10 P3.
- **Decisão do Supervisor sobre o P2:** opção (a): o `/v1` volta a usar `EVALUATOR_PROVIDER`/`EVALUATOR_MODEL` como antes, e o juiz da campanha ganha variáveis próprias (`JUDGE_PROVIDER`/`JUDGE_MODEL`, padrão DeepSeek). Também evita que o `.env` antigo do responsável faça o `eval --judge` recusar.

## Achado

**P2-01 — o avaliador padrão novo derruba a avaliação sob demanda do `/v1` sem `DEEPSEEK_API_KEY`.** `config.py:79-80` passou o padrão de `openai/gpt-6-luna` para `deepseek/deepseek-flash`, e a rota do `/v1` usa o mesmo `Settings` (`evaluation/on_demand.py:154-156`). Numa instalação só com `OPENAI_API_KEY`, como pede o README, a estimativa responde 200 e a confirmação `503 evaluator_unavailable` (falha segura, nada gravado). Reproduzido com a fábrica real de modelos; o teste existente usa o modelo programado e não pega.

## P3

1. A descida da 0011 perde `repetition` (o `result` não a guarda) e a subida não reconstrói `scores` e `unsupported_claim`; o comentário da migração e o teste dizem "nothing is lost".
2. `OUTCOME_OBSERVERS` (`tools/registry.py:176,226`) é lista global: duas gravações simultâneas se contaminam (reproduzido com duas threads; o gravador de A recebeu o resultado de B) e a exceção de um observador atravessa `execute()`. Hoje só a CLI sequencial usa.
3. A independência compara só textos: aceitou `deepseek/gpt-6-luna` e `openai/text-embedding-3-small`; `prices.json` tem o provedor de cada modelo.
4. Erro cru do provedor gravado em `run_evaluations.error` e no relatório (`judge.py:112`).
5. Lacunas de teste: máscara das passagens e da mensagem do lojista, custo do agente zerado no relatório do juiz, `--repeat` sem juiz seguido de `--judge-repeat`, argumentos da ferramenta na evidência (mutantes M11, M12, M28, M32, M34 sobrevivem; o código está correto).
6. Respostas de web vão ao juiz sem evidência, e o `judge.v3` não cita as notas de evidência: tendem a ser marcadas como afirmação sem suporte.
7. Relatório e CLI: truncamento não resumido no Markdown; justificativa sem escape na tabela; `--name` padrão faria o holdout sobrescrever o relatório de desenvolvimento; `--split` ignorado em silêncio com `--judge-repeat`; caso atribuído à rota da 1ª repetição.
8. `prompt_versions` passa a listar `judge: 3`, o que muda o `prompt_set` usado no reaproveitamento das comparações, enquanto a avaliação sob demanda usa o v2.
9. A avaliação sob demanda não tem marca de independência (já não tinha).
10. O plano diz que a 0011 acrescenta `rubric_version`, que já existe desde a 0008.

## Comprovado por execução

- **Migração 0011:** subida com avaliações da 0008 preservadas; descida recusada (10, 9 e 0) com nota humana em `calibrations`, sem alterar nada; liberada com a tabela vazia; integridade e chaves estrangeiras ok.
- **`judge.v3`:** quatro critérios e veredito; nota fora da escala vira `failed`; truncamento exato em 6 000 caracteres (fuzz de 20 000 casos sem violação); máscara do resultado de ferramenta antes do corte; token, chave, CPF, cartão e e-mail chegam mascarados; evidência de um lojista nunca cita outro; `judge.v2` carregável e a sob demanda do `/v1` fixada nele.
- **Independência:** recusa antes de qualquer chamada para par igual ao agente, sem chave, sem preço e provedor sem saída estruturada; provedor, modelo e tipo de independência gravados.
- **Repetições:** `--repeat` repete só o agente; `--judge-repeat` só o juiz sobre a 1ª execução; as duas juntas recusadas. Média, desvio, concordância exata e ±1 conferidas à mão e em 3 000 tentativas aleatórias contra implementação independente, sem divergência; definições razoáveis, com as ressalvas da D19.
- **D16, D14/D17, D18:** `executed_path` de `agents` sem `router` e `personality`, `route_ok` inalterado; holdout só lido com `--split holdout_v080`, nunca em `all`; diff fora dos arquivos do Time A.
- **Testes:** 78 passed nos arquivos pertinentes; eval programado com juiz e repetições coerente com a base. Mutação: 36 mutantes, 30 mortos. Suíte estrita (Supervisor, neste candidato): **701 passed**, código 0.

## Não comprovado

Chamada real à DeepSeek com saída estruturada e teto de 400 tokens; campanha real; cliente web diante do `503`; tratamento real do juiz para respostas de web.
