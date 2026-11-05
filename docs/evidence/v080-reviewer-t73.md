# Revisão independente da T73 — v0.8.0

## Rodada 1 — correções necessárias

- **Candidato e base** `60ef1ebe0935de83a7aa88865f257961b94e313c` sobre `01e56d0963fe30b74b7fee76c9ed45aceb27c883`, em `codex/v0.8.0-t73`. O worktree ficou limpo. O Reviewer usou `gpt-6-luna/xhigh` em contexto independente.
- **P1. Ledger primário e teto seguem o runtime.** Com `runtime_dir=C:/qa/new-runtime`, o banco, Qdrant, `budget.sqlite3` e `budget-v080-qa.sqlite3` ficaram todos sob o runtime novo. A campanha perde o saldo histórico do ledger primário e pode montar um novo teto ao trocar de runtime. A prova inspecionou os caminhos passados aos construtores, sem escrever nos ledgers.
- **P1. Conversas de acompanhamento fora da projeção.** `eval --split all` roda quatro conversas e registra seus custos fora de `cases`. A amostra e o estimador da rodada 1 cobrem só os casos. Um teto escolhido pela projeção pode interromper o QA antes das últimas etapas.
- **P2. Amostra programada pode recomendar teto para QA real.** O CLI aceitou o relatório `scripted` de cinco casos com custo zero e marcou a estimativa dentro do teto. O fluxo pago deve exigir medição real e concluída.
- **Validação** com 31 testes focados aprovados em 54,96 s, Ruff limpo e checagem da versão `0.8.0`. O Git sinalizou CRLF preexistente no arquivo da guarda sob a regra padrão de whitespace. Nenhuma execução de Docker, holdout ou chamada paga.
- **Próxima ação** Developer corrige os três achados e devolve novo candidato para revisão antes do QA pago.

## Rodada 2 — correções necessárias

- **Candidato e base** `9deca612f32becd1e3477bc7638d457a66b14269` sobre `60ef1eb`. Contexto independente com `gpt-6-luna/xhigh`, HEAD fixo e worktree limpo.
- **Bloqueante. O teto excepcional aceita um escalar sem medição.** `--campaign-cap-usd 1.00` verifica apenas que `estimated_cost_usd` está entre US$0,50 e US$1,00. O teste monta o teto com um JSON contendo só `estimated_cost_usd: 0.75`. A decisão deve depender da evidência válida de uma amostra real e de sua projeção.
- **Verificações estáticas** confirmaram o caminho persistente dos dois ledgers, a recusa antes de iniciar o juiz, a cobertura das conversas e o cálculo D12. Parse AST e `git diff --check` passaram. O Reviewer evitou pytest, SQLite e Docker enquanto a suíte estrita do Supervisor rodava.

## Rodada 3 — apta

- **Candidato e base** `9057aaac36eddbe309393089115175b6fc98b5bd` sobre `9deca61`. Reviewer `gpt-6-luna/xhigh` em contexto novo verificou os 105 hashes de um pacote que contém o delta, o código, os testes pertinentes e as fontes normativas.
- **Parecer apto.** A CLI valida a referência local da amostra real, recalcula a projeção e confere o artefato antes de montar o teto de US$1,00. A pré-validação de juiz ocorre antes de abrir ledgers. A construção do cliente e do orquestrador ocorre depois da guarda. A revisão conferiu também D12, as conversas sem juiz, o runtime persistente, a versão `0.8.0`, o schema 11 e o Dockerfile.
- **Validação independente** por inspeção estática, sem pytest, SQLite, Docker, rede ou chamada paga. A suíte estrita fica registrada pelo Supervisor.
- **Ocorrência** uma primeira passagem r3 foi interrompida após uma busca ampla exibir duas linhas do holdout da v0.8.0. A passagem foi descartada para aceite. O parecer acima usa outro contexto e um pacote sem o arquivo de holdout. Nenhum conteúdo lacrado foi usado para alterar o produto.
