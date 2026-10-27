# Revisão restrita — documentos de release v0.3.0

## Confirmação

**Confirmado para o delta documental analisado.** O README e o CHANGELOG refletem a validação e a aprovação para release sem afirmar que integração, PR, merge ou tag já ocorreram. Os pareceres r6 e os resultados de produto permanecem os mesmos; esta conferência não é nova validação do produto nem operação Git.

## Identidade e escopo

- Manifesto `v030-release.json`: candidato `v0.3.0-release`, branch `codex/v0.3.0-jornadas`, base/HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- Recalculei o fingerprint `3de3e863431e81740d014239bd88df093b48e9d37c9614993da59c826767c80a` e os 49 hashes do manifesto; todos coincidem.
- Comparado a `v030-candidato-r6-docs1.json`, somente `README.md` e `CHANGELOG.md` diferem. Os outros 47 arquivos permanecem idênticos; os 31 hashes de runtime e fingerprint runtime `e58e5668172b992ebabf9777237686a2e0357cdccd5c7657436acbbc703b1cde` são os mesmos.
- Entre os 126 insumos Docker, apenas `README.md` mudou. O manifesto mantém as imagens r6 (`f3181423b249dd14368e4b49bb09790c376371097cabc723fbaaba49b41e3699` da API e `89364d891ed4a596d6caf72712a00deaec4662359c2dc116fbe9dc6043aea64e` dos mocks). Os documentos não afirmam que houve rebuild.

## Fatos de release conferidos

- Os **191 testes** são a validação estrita registrada pelo Developer r6. Reviewer r6 e QA r6 têm pareceres aptos; a avaliação não atribui a esses documentos uma execução adicional.
- Os **40 resultados HTTP** são respostas originais r2 reavaliadas por replay determinístico, sem novas chamadas. O relatório preserva os 17 holdouts e informa que latências, custos e notas permanecem históricos.
- As **quatro conversas ao vivo**, incluindo FU02 com o protocolo mantido após handoff, são uma validação separada, executada via HTTP no candidato r6. O relatório registra custo de US$0,00538690 nessa rodada e gasto acumulado de US$0,14123583 sob o teto de US$0,15.
- README e CHANGELOG dizem que v0.3.0 foi validada e aprovada pelo responsável **para release**. O CHANGELOG explicita que não afirma PR, merge ou tag concluídos; o README encaminha integração e tag ao registro central. O registro central atual informa autorização e instrui confirmar os efeitos reais antes de avançar. Não encontrei declaração de que operações Git já ocorreram.

## Limite

Não repeti testes nem fiz chamadas de API; nenhuma necessidade nova de validação surgiu, pois o delta não altera código ou critérios. A aprovação deste relatório confirma somente README/CHANGELOG em relação ao manifesto r6-docs1 e não executa nem substitui a integração e a tag autorizadas.
