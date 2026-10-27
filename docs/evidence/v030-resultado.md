# Resultado da validação da v0.3.0

## Estado da entrega

**v0.3.0 integrada na main e tag enviada em 2026-10-27**: [PR #4](https://github.com/lauroPereira/ai-getnet-case/pull/4) concluído, merge `bd549cc921ccffb37bd304a0959b8a4b690d6421`, tag anotada `v0.3.0` no mesmo commit local/remoto. Jornadas de preço, bandeiras e consulta de cancelamento implementadas; revisão técnica, revalidações e QA independente concluídos. [Conferência da integração](v030-integracao.md).

[Candidato de release](v030-release.md): 49 arquivos, fingerprint `3de3e863431e81740d014239bd88df093b48e9d37c9614993da59c826767c80a`; runtime `e58e5668172b992ebabf9777237686a2e0357cdccd5c7657436acbbc703b1cde`. O [r6-docs1](v030-candidato-r6-docs1.md) fechou estados/evidências das seis tarefas 21–26; após o aceite humano, somente README/CHANGELOG foram alinhados ao release. História, critérios, contratos, código, cenários e runtime são idênticos ao [r6 original preservado](v030-candidato-r6.md). Imagens validadas continuam r6; único insumo Docker alterado é o README como descrição do pacote, sem novo build declarado.

## Processo e independência

Supervisor na sessão principal; exatamente três subagentes autorizados e acionados, todos explicitamente `gpt-6-luna` com esforço `high`: Developer (`/root/developer_v030`), Reviewer (`/root/reviewer_v030`) e QA (`/root/qa_v030`). Correções retornaram ao mesmo Developer; Reviewer e QA receberam contextos novos separados do implementador.

## Evidências e candidatos

| Verificação | Resultado registrado | Validade |
| --- | --- | --- |
| Validação estrita final | **191 testes**, Ruff, estrutura e skills aprovados | [Developer r6](v030-developer-r6.md) e manifesto r6 |
| Stack Docker completo | API, Qdrant e mocks saudáveis; Router 5/Support 7, schema 5, índice de 145 trechos | [Prontidão r6](v030-ready-r6.json); imagens identificadas no manifesto |
| Revisão técnica independente | **Apto para revalidação e QA**; isolamento, literal de privacidade e afirmações qualificadas/contraditórias verificados | [Reviewer r6](v030-reviewer-r6.md) |
| Casos HTTP reais | **40/40** após replay determinístico da rubrica corrigida | [Replay](v030-real-http-r2-replay.md) das mesmas [respostas originais r2](v030-real-http-r2.md); sem nova API |
| Conversas HTTP reais | **4/4**, incluindo continuidade após handoff com mesmo protocolo | [Revalidação r3](v030-real-conversations-r3.md), executada no candidato r6 |
| QA independente | **Apto funcionalmente**, com limitações explícitas; história por HTTP, MCP, falha controlada e isolamento | [QA r6](v030-qa-r6.md); [ambiente sem credenciais](v030-qa-environment-r6.json), mesma imagem com modelo programado |
| Fechamento SDD | Tarefas 21–26 concluídas e validadas; integração ainda depende do responsável | [Manifesto documental](v030-candidato-r6-docs1.json), [Reviewer](v030-reviewer-fechamento.md) e [QA](v030-qa-fechamento.md) do fechamento |

A primeira rodada real encontrou defeitos de consulta/roteamento/apresentação financeira. A segunda confirmou os 27 casos do núcleo e as verificações de rota, status, idioma, ferramentas, valores, fontes e grounding dos 40 casos, mas apresentou cinco falsos negativos da rubrica e uma falha de continuidade em FU02. Os relatórios originais permanecem preservados.

O replay reavaliou somente conteúdo/afirmações dos cenários dev, preservando as respostas reais, os 17 holdouts e todos os checks não semânticos. Sua tabela de custo/latência e as notas do juiz são históricas, não uma nova medição. A continuidade foi corrigida e repetida ao vivo via `POST /messages`: FU02 termina em suporte/`handoff`, com caso e protocolo preservados. A média do juiz não substitui essas verificações.

O QA não encontrou defeito funcional reproduzível. A falha de dependência foi injetada em endpoint HTTP isolado com modelo programado; sua redação com modelo real não foi repetida. O MCP foi validado por cliente stdio no contêiner Linux, após limitação do loop local Windows. O ruído de recuperação em uma repetição programada de Visa não foi tratado como evidência da qualidade do modelo real. Essas limitações permanecem no parecer para o aceite humano.

## Orçamento

Validação desta entrega: **US$0,14123583**, incluindo duas rodadas, índices, rubricas e revalidação das conversas, sob o mesmo teto persistente **US$0,15**. Saldo desse teto: US$0,00876417. Total registrado do projeto: **US$0,59283583 de US$5**. O replay e o QA com modelo programado não fazem chamadas pagas. Conferir [registro de orçamento](orcamento.md) e [medição acumulada](v030-real-budget-r3.json).

## Próxima ação e recuperação

O responsável autorizou integralmente a [integração proposta](v030-integracao-proposta.md): commit na branch, push ao repositório privado, PR para main, merge e tag v0.3.0. Conferir seu efeito real no registro de integração e nos refs Git antes de avançar. Recuperação por commit de reversão e migração de 0005 para 0004, já testada em banco sintético. A próxima versão (v0.4.0) deve partir de main atualizada contendo esta entrega. Runtimes de teste isolados e dados anteriores do responsável preservados.

[PR #4](https://github.com/lauroPereira/ai-getnet-case/pull/4) criado e branch
enviada, commit de produto `1baff5324458e909bb23be1f89fa7fa6a1f8f2d9`.
O provedor não apresenta checks/status/jobs de CI; os 191 testes e pareceres
registrados são validações locais. Confirmar merge e tag nos refs após a execução.

**Conferência final concluída:** PR integrado; refs local/remoto de main/tag
iguais ao merge acima. [Hashes canônicos Git](v030-git-integracao.json)
reproduzem os blobs versionados, separadamente dos hashes locais históricos
anteriores à normalização de finais de linha do Git. A próxima versão foi
iniciada somente em planejamento, na branch `codex/v0.4.0-perfis-interface`.
