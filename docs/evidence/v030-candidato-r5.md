# Candidato: v0.3.0 local — rodada 5

## Resultado e critérios

Jornadas da v0.3.0, correções de isolamento e avaliação, e continuidade após handoff. Tarefas 21 a 26; história versão 1; critérios canônicos preservados. Cenários reservados inalterados.

## Identificação

- Branch `codex/v0.3.0-jornadas`; base/HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- [Manifesto](v030-candidato-r5.json): **48 arquivos**, fingerprint completo `8b15414ab90acfc576404ef45c23a71526eea333d0c4cdcf8d46d4f3e4741f97`.
- Fingerprint de runtime: `643609655b811641b497b96d5d4555b1dc6f2387016ac5e591ab79914622ab78`.
- API `sha256:71e97b5928e10bc5d3ba8cafedf95439295492c606b2a7ed139a9d90b9d61f1c`.
- Mocks `sha256:785653851bba24428b90552513bc0d6cc0947f64753071d44067eccd208a1cad`.

Delta desde r4: Router 5, anotações dos cenários dev, testes de avaliação e tarefa 26. Código Python do produto, schema e fontes de dados preservados. Imagens reconstruídas para incorporar o prompt; 126 insumos e scripts/dataset de validação identificados no JSON.

## Ambiente e dados

Stack completo em `127.0.0.1:18030`, API/Qdrant/mocks saudáveis, Router 5/Support 7, [prontidão](v030-ready-r5.json). Mesmo runtime sintético e ledger de validação: teto acumulado US$0,15, gasto antes da última revalidação US$0,13584893. Runtime anterior do responsável preservado.

QA tem ambiente HTTP sem credenciais em `127.0.0.1:18031`, com a mesma imagem, modelo programado e HTTP real ao serviço fictício. [Identificação do ambiente QA](v030-qa-environment-r5.json). O relógio/dados desse ambiente são fixos; a execução real usa relógio do sistema.

## História e verificações

- [Developer r5](v030-developer-r5.md): 181 testes, Ruff, estrutura e skills aprovados; 19 testes direcionados e 13/13 cenários programados.
- [R2 HTTP original](v030-real-http-r2.md): núcleo 27/27, todos os 40 casos com rotas/status/ferramentas/valores/fontes/grounding corretos; cinco falsos negativos de redação e 3/4 conversas. Relatório preservado.
- Preparado replay determinístico dos casos a partir de respostas e traces registrados, com checagem de que somente conteúdo/afirmações dos cenários dev são reavaliados. Zero chamada de API nessa operação. Custos/latências/notas originais serão identificados como históricos.
- Preparada nova execução real das quatro conversas via HTTP após revisão, dentro do saldo da mesma guarda. Não repetir casos gerais pagos para ajustes de redação.

## Pareceres e validade

Nova revisão independente pendente; QA ainda será acionado. Nenhum parecer anterior é declarado válido automaticamente para o delta. Métodos e candidatos de cada evidência devem ser distinguidos no [registro central](v030-resultado.md).

## Decisão e recuperação

Próximo: revisão, replay e revalidação das conversas, QA independente, decisão humana. Nenhum commit, push, merge, tag ou publicação autorizado. Recuperação por v0.2.0 e schema 0005 → 0004 em banco sintético isolado.
