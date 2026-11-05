# 0021. Juiz da avaliação: modelo padrão escolhido por experimento pré-registrado contra notas humanas, e a régua literal como piso

## Título

Manter `deepseek/deepseek-flash` como juiz padrão depois de medir `claude-opus-5-5` sobre a mesma amostra calibrada por humano; tratar a régua literal das jornadas como piso determinístico e o juiz calibrado como a checagem de conteúdo.

## Status

**Aceita** (v0.9.0, 2026-11-05; experimento da tarefa 79, QA r2; decisão D2 da [spec](../../specs/juiz-retrieval-v090.md) confirmada pelo responsável). Complementa a ADR 0019 e as decisões D9 a D11 da v0.8.0.

## Contexto

A v0.8.0 introduziu o `judge.v3` (groundedness, factual_correctness, relevance, usefulness, afirmação sem suporte) com juiz independente do agente (DeepSeek sobre agente OpenAI) e uma calibração humana de 24 respostas. A calibração mostrou um juiz consistente consigo mesmo e mais severo que o humano, mas que nunca marcava as mesmas afirmações sem suporte: o humano apontou frases genéricas sem fonte em quatro respostas; o juiz, respostas web sem texto gravado. Ficou a dúvida se a lacuna era do modelo (o DeepSeek é o mais fraco do portfólio) ou da rubrica. Em paralelo, a régua literal das jornadas de negócio (frases obrigatórias e proibidas) recusava paráfrases corretas e deixava passar paráfrases erradas fora da lista registrada (tarefa 78 da v0.8.0).

## Decisão

- **Experimento pré-registrado.** As mesmas 24 respostas, o mesmo `judge_input`, o mesmo prompt `judge.v3` e as mesmas notas humanas; só o modelo do juiz muda (`claude-opus-5-5`, parâmetros padrão, 3 repetições). A regra de decisão foi escrita na spec antes de rodar: o Opus vira padrão se (a) a concordância ±1 não piorar em nenhum critério, (b) a concordância do veredito passar de 0,667 com pelo menos 2 das 4 frases genéricas marcadas, e (c) a consistência exata ≥ 0,70.
- **Resultado.** 72/72 julgamentos válidos, US$1,34 em ledger Anthropic separado. (a) atendida: ±1 de 0,958 / 0,958 / 1,000 / 0,958 contra 0,833 / 0,833 / 1,000 / 0,917. (c) atendida: 0,81 a 1,00. (b) não atendida: veredito 0,875 (kappa 0,357) contra 0,667 (−0,200), mas só 1 das 4 frases genéricas marcada. Custo por julgamento 54 vezes maior (US$0,0178 contra US$0,00033).
- **Juiz padrão:** continua `deepseek/deepseek-flash`. Pela regra, o caso é lacuna da rubrica: o modelo mais forte concorda mais com o humano em tudo o que a rubrica pede e ainda não marca o que ela não pede. O Opus fica disponível por configuração (`JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5`), com adaptador próprio, preços com cache e ledger por diretório.
- **Rubrica:** na próxima versão, `judge.v4` acrescenta à definição de afirmação sem suporte a frase genérica sem fonte; o texto da busca web passa a ser gravado para o juiz. Mudança de prompt é arquivo novo, nunca edição do `judge.v3`.
- **Régua do CA-51:** a régua literal decide o que é binário (rota, status, ferramentas, valores, fontes, afirmações proibidas registradas) e funciona como piso; o juiz calibrado é a checagem de conteúdo. Nesta versão isso é documentação; a troca do critério de aceite no código fica para a próxima campanha de jornadas, com o juiz escolhido por esta ADR.
- **Rastreabilidade:** cada julgamento grava provedor, modelo, nome da execução e tokens (entrada, saída, cache); `eval-calibrate --judge --judge-run` compara qualquer juiz com as mesmas notas humanas sem nova avaliação.

## Alternativas consideradas

- **Trocar para o Opus porque concorda mais:** ignoraria a regra escrita antes e a lacuna demonstrada; custo 54× sem fechar a lacuna; descartado (reversível pelo responsável).
- **Juiz do mesmo provedor do agente:** viola a independência (D11); descartado.
- **Régua literal como único critério:** quatro rodadas de revisão na v0.8.0 mostraram que substring não expressa negação; descartado como critério de conteúdo.
- **Só juiz, sem régua:** o juiz tem lacuna própria (frases genéricas, web sem texto); descartado; a combinação fica.

## Consequências

- Positivas: decisão com número e regra prévia, reprodutível para qualquer outro modelo; o experimento custou US$1,34 e levou meia hora de QA; a evidência da dimensão de avaliação deixa de depender de um único juiz.
- Negativas: a rubrica continua sem a linha de frase genérica até o `judge.v4`; a amostra de 24 é pequena (D19) e o kappa dos critérios 1 a 5 é pouco informativo por efeito de teto; julgar com o Opus custa 54× mais quando for escolhido.

## Data

2026-11-05.
