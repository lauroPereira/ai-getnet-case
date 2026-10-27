# Integração da v0.3.0

## Aceite e escopo

Em 2026-10-27, o responsável autorizou explicitamente **“Autorizar integração
completa e tag v0.3.0”**: commit, push privado, PR para main, integração e tag,
conforme a [proposta](v030-integracao-proposta.md). A autorização não altera o
teto das APIs nem a visibilidade privada do repositório.

## Conferência antes do commit

- Branch `codex/v0.3.0-jornadas`; HEAD/base e main remota após fetch:
  `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- [Manifesto r6-docs1](v030-candidato-r6-docs1.json): 49/49 hashes; runtime
  31/31, insumos Docker 126/126 e ambos fingerprints conferidos.
- Identidade local `lauroPereira <lauro.s.pereira@gmail.com>` confere; conta
  GitHub conectada `lauroPereira`; repositório confirmado privado.
- Nenhum PR da branch ou tag v0.3.0 existente na conferência inicial.
- `git diff --check` aprovado. Critérios, história e conteúdo do candidato
  preservados; apenas evidências de aceite/integração atualizadas.

Depois do aceite, README e CHANGELOG foram alinhados ao estado validado/aprovado.
[Manifesto de release](v030-release.json), fingerprint
`3de3e863431e81740d014239bd88df093b48e9d37c9614993da59c826767c80a`:
delta restrito a dois documentos em relação ao r6-docs1; runtime idêntico e
único insumo Docker alterado README (descrição do pacote). As imagens/testes
r6 permanecem identificados, sem alegar novo build/teste do produto.

## Validação aplicável

[Resultado central](v030-resultado.md): 191 testes estritos, Reviewer e QA
independentes aptos; 40 respostas HTTP reais reavaliadas por replay e quatro
conversas reais repetidas no runtime final. Limitações e relatórios originais
permanecem preservados. Nenhuma nova chamada paga nesta integração.

## Integração e referência final

A execução segue commit → push da branch → PR → conferência de checks/base →
merge local → push de main → tag v0.3.0. A tag deve apontar para main contendo
o PR completo. A confirmação final é o estado do PR e os refs local/remoto;
não inferir conclusão somente da autorização ou deste documento preparatório.

Recuperação por commit de reversão; migração 0005→0004 comprovada somente em
bancos sintéticos isolados. A próxima versão parte de main atualizada após
esta integração, com plano e aprovações próprias para novos contratos e dados.
