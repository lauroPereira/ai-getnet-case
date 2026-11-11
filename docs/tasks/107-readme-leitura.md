# Tarefa 107 — README de leitura rápida e evidência

## Objetivo

Quem abre o repositório entende em minutos o que o assistente faz, como rodar e onde está a evidência de cada número.

## Especificação relacionada

[v1.0.0](../specs/leitura-acesso-v100.md): D5, CA-74. Plano: decisão 22. RF-129.

## Pré-condições

Tarefas 106 e 108 concluídas. Resultados das versões v0.12.0 e v0.13.0 em `docs/evidence/` (`v0120-resultado.md` e `v0130-resultado.md`). Nenhuma chamada paga.

## Arquivos prováveis

`README.md`, `CHANGELOG.md`, `docs/evidence/README.md` (índice), capturas em `docs/apresentacao/` (ou pasta já usada pelo README), README da interface web se a trilha depender dele.

## Passos

1. Topo do README: o que é, para quem, em três frases; status v1.0.0; como rodar em dois caminhos (imagem publicada e build local).
2. Trilha de 10 minutos: subir, perguntar como lojista, encaminhar a humano, responder como operador (aba Operador e ticketing), avaliar uma resposta; cada passo com comando ou clique e o resultado esperado.
3. Tabela antes × depois por área (atendimento, avaliação/juiz, retrieval, memória, identidade, operação): número da v0.10.0, número atual, link da evidência em `docs/evidence/`; só números já registrados em evidência versionada.
4. Capturas com dados sintéticos: aba Operador, ticketing e login por redirecionamento; Telegram só com captura sem nome nem identificador do grupo.
5. `docs/evidence/README.md` como índice com links válidos; CHANGELOG 1.0.0; notas de operação atualizadas (dois workers, túnel, imagem).
6. Texto de produto, sem processo interno; caminhos pessoais e dados reais proibidos.

## Critérios de conclusão

- Links relativos válidos (`checar-links.py`), caminhos pessoais limpos, suíte estrita verde.
- A trilha é executável como escrita.

## Resultado

Topo do README com o que é, para quem e dois caminhos para rodar; trilha de 10 minutos pela interface com login por redirecionamento; tabela antes × depois por área só com números de evidência versionada; índice de `docs/evidence/` e CHANGELOG 1.0.0.
`checar-links.py` sem alvo ausente em 367 arquivos Markdown e caminhos pessoais limpos; capturas com dados sintéticos em `docs/images/`.
Trilha percorrida com modelo real, com notas 5, 5 e 5 na avaliação por IA da resposta. Evidência: [resultado da v1.0.0](../evidence/v100-resultado.md).

## Status

```text
concluída (v1.0.0)
```
