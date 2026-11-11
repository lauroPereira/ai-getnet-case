# Revisão independente do ajuste do `judge.v5` para a iteração 3 da D6(a) (v0.11.0)

**Parecer final: apto**, no candidato `9d96661` ([v0110-candidato-r3.json](v0110-candidato-r3.json)), 2026-11-07, sem achado bloqueante. Revisão em contexto independente; o resultado do ajuste está em [v0110-v5-ajuste.md](v0110-v5-ajuste.md).

- **Candidato:** `9d9666143f307f0f87664979e91e6ac208316eed` (escopo `e2de0b1..9d96661`). Blobs: `prompts/judge.v5.md` `5430b33` (SHA-256 `5dca658e…b33048`), `docs/templates/instrucao-rotulagem-calibracao.md` `e185ef3` (SHA-256 `7bdb7db3…269256`).
- **Suíte estrita** num clone limpo: **2391 passed, 1 skipped**; depois da última correção, nos módulos do juiz e da calibração: 260 passed; links verdes.

## Re-derivado

- **Regras novas, gerais e iguais nos dois documentos:** lacuna declarada das fontes ("não informa", inclusive dito da Getnet) é `supported` salvo item que mostre ou informe a coisa; fato negativo sobre a Getnet ou um produto ("não oferece, não aceita, não cobra, não permite, não tem") e "não há mais nada" seguem a regra do `not_found`; data do dia da resposta, ou do dia anterior ou seguinte, é `partial` salvo outra data no item ou na mensagem.
- **Uma régua só:** 28 pares em `SAME_RULES`, marcas por regra iguais e na mesma ordem e a mesma contagem de frases nas seis regras após o cabeçalho; frase acrescentada a um só lado faz o teste falhar.
- **Método da iteração 3:** uma repetição, como nas iterações anteriores e no momento 8; `--judge-majority` disponível como ferramenta, fora do critério.
- **Congelamento da D6:** o `judge.v5` não julgou as 36 seladas; `judge_claims.v1` inalterado desde o selo.
- **S04:** a evidência registra as duas leituras das afirmações 2 e 3 (passage de taxas e evidência truncada); a adjudicação é do responsável.

## Mutação

Rodada 1: 22 mutantes, 17 mortos. Rodada 2: 18, 16 mortos. Rodada 3: 13, 12 mortos; o sobrevivente fica na agregação por maioria, fora do critério.
