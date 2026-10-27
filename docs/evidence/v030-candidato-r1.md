# Candidato: v0.3.0 local — rodada 1

## Resultado e critérios

Jornadas de preço/contestação, bandeiras e consulta de cancelamento; tarefas 21 a 24. Critérios: CA-21, CA-22, CA-23, CA-28 e CA-31. Fontes: [plano](../specs/jornadas-v030-plano.md), especificações principal/complementar e [história versão 1](../historias/jornadas-v030.md).

## Identificação

- Branch: `codex/v0.3.0-jornadas`.
- Base e HEAD: `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4` (main atualizada antes da alteração).
- Alterações locais não commitadas: **42 arquivos**, hashes individuais no [manifesto JSON](v030-candidato-r1.json).
- Identidade do conjunto de arquivos: SHA-256 `ad1bfc9dc7c945453c0d3093cc1e8524a95f84185c8fecd50f79b4ff319c4284`.
- Imagem API: `sha256:4f05365ed614a52f04d3b77f6c4bad3bbf70110d28edca43f287aff0c14445db`.
- Imagem mocks: `sha256:eba11f0d2f7206697342e89c58d17a915b3c727ed1acc0b8cd62e05096b901c3`.
- Nenhum commit, PR, push, merge ou tag produzido nesta sessão.

Evidências e runtimes temporários ignorados não integram o fingerprint. Fontes, configuração de execução, fixtures, prompts, testes, critérios, história e documentação alterados estão identificados no manifesto. Alterar esses arquivos exige nova rodada no escopo afetado.

## Ambiente e dados

Windows, Python e versões locais no manifesto JSON; imagem Python 3.13.13; Docker Engine 29.8.0. Projeto de teste `getnet-v030-validation`, com serviço `mocks` interno sem porta publicada. Runtimes sintéticos novos e isolados; nenhuma migração aplicada ao runtime anterior do responsável. Nenhuma credencial em relatório.

## História e verificações

- História versão 1: hash no manifesto JSON.
- Validação estrita pelo Developer: 164 testes, Ruff, estrutura e skills aprovados; passagem em [v030-developer.md](v030-developer.md).
- [Avaliação programada final](2026-10-27-avaliacao-programada-v030-final.md): 13/13 casos novos, 4/4 conversas e verificações estruturais 40/40; conteúdo 25/40 no geral. Não comprova qualidade semântica com modelo real.
- Build corrigido r2 aprovado; [smoke r2](v030-docker-r2.json) entre contêineres: **17/17**, sem erros nas ferramentas, com modelo programado e zero chamadas pagas. O [smoke exploratório r1](v030-docker-r1.json) pertence à imagem anterior e não é evidência de aceite deste candidato.

## Pareceres e validade

Revisão técnica independente em andamento e QA pendente. Subagentes autorizados: `gpt-6-luna`, esforço `high`, explicitamente selecionados e com contexto novo. Rodada real autorizada e em execução (40 casos, quatro conversas, teto adicional US$0,15); não declarar liberação antes do resultado.

## Decisão e recuperação

Próximo: revisão independente e QA neste candidato, com correções devolvidas ao Developer se necessário. Integração/publicação dependem do responsável. Recuperação prevista: código v0.2.0 e retorno do esquema 0005 para 0004, validado somente em banco sintético isolado.
