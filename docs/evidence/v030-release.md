# Candidato de release v0.3.0

## Identificação

[Manifesto de release](v030-release.json), fingerprint
`3de3e863431e81740d014239bd88df093b48e9d37c9614993da59c826767c80a`,
branch `codex/v0.3.0-jornadas`, base `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.

Após o [r6-docs1](v030-candidato-r6-docs1.md), somente README e CHANGELOG
foram alinhados ao aceite humano para release. Os outros 47 arquivos são
idênticos; código, dados, critérios, história, testes e 31 arquivos de runtime
permanecem os mesmos. [Passagem Developer](v030-developer-release-docs.md).

## Escopo da evidência

Os testes e imagens identificados são os do runtime r6 validado. Dos 126
insumos Docker, somente README mudou, como descrição incluída no pacote;
nenhum novo build ou teste do produto é declarado neste fechamento editorial.
O manifesto preserva as imagens r6 e explicita esse delta. A mudança não
acrescenta funcionalidade nem modifica comportamento.

191 testes estritos, revisão e QA independentes aptos; 40 respostas HTTP
reais preservadas reavaliadas por replay, separadas das quatro conversas
reais repetidas no r6. [Resultado central e limitações](v030-resultado.md).

## Aceite e integração

O responsável autorizou integração completa e tag v0.3.0 em 2026-10-27.
[Registro de integração](v030-integracao.md). [Reviewer](v030-reviewer-release-docs.md)
e [QA](v030-qa-release-docs.md) confirmaram este delta documental, em sequência,
antes do commit, sem novas execuções ou APIs. Os efeitos Git devem ser
confirmados pelos refs e pelo estado real do PR.
