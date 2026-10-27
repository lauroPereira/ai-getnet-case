# Confirmação QA dos documentos de release — v0.3.0

## Parecer

**Confirmado para o delta documental de release.** README e CHANGELOG mantêm corretos o resumo de validação e seus limites em relação ao candidato r6 já avaliado. Esta confirmação não repete validação de produto nem executa operações Git.

## Candidato e delta

- Candidato `v0.3.0-release`, branch `codex/v0.3.0-jornadas`, base/HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- Fingerprint recalculado `3de3e863431e81740d014239bd88df093b48e9d37c9614993da59c826767c80a`; os 49 hashes de produto conferem.
- Em relação a `v030-candidato-r6-docs1.json`, somente `README.md` e `CHANGELOG.md` diferem; os outros 47 arquivos são idênticos.
- Runtime: 31/31 hashes e fingerprint `e58e5668172b992ebabf9777237686a2e0357cdccd5c7657436acbbc703b1cde` idênticos. Entre os 126 insumos Docker, apenas `README.md` mudou como descrição do pacote. As imagens permanecem API `sha256:f3181423b249dd14368e4b49bb09790c376371097cabc723fbaaba49b41e3699` e mocks `sha256:89364d891ed4a596d6caf72712a00deaec4662359c2dc116fbe9dc6043aea64e`; os documentos não alegam novo build.

## Conferência dos fatos e limites

- Os **191 testes** são atribuídos à validação estrita registrada pelo Developer r6.
- Os **40/40 casos HTTP** estão identificados como replay determinístico das respostas originais r2, sem novas chamadas; os **17 holdouts** e as métricas históricas são descritos separadamente.
- As **quatro conversas ao vivo (4/4)** são registradas como rodada HTTP r3 distinta, repetida no candidato r6; o custo de US$0,00538690 e o acumulado de US$0,14123583/US$0,15 estão no resultado central.
- README e CHANGELOG encaminham os detalhes às passagens Developer, Reviewer e QA e aos relatórios do replay/conversas. O resultado central preserva as limitações do QA: a resposta scripted não foi tratada como qualidade do modelo real, a falha de dependência não teve nova execução com modelo real, e o MCP foi validado no container Linux após bloqueio do runtime Windows.
- Os documentos dizem que a entrega foi aprovada para release, sem alegar que PR, merge ou tag já foram concluídos. A integração e a tag autorizadas permanecem fora deste escopo e sob execução/verificação do Supervisor.

Nenhum teste, execução de produto ou chamada de API foi realizada nesta confirmação.
