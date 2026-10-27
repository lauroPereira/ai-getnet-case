# Candidato: v0.3.0 local — rodada 6

## Resultado e critérios

Mesmo produto e história da [rodada 5](v030-candidato-r5.md), com distinção explícita entre ban literal e afirmação semântica na avaliação. Tarefas 21 a 26; critérios canônicos e holdout preservados.

## Identificação

- Branch `codex/v0.3.0-jornadas`; base/HEAD `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.
- [Manifesto JSON](v030-candidato-r6.json): **49 arquivos**, fingerprint `f8efcec3918320c287b3b6c2faef2f38edca4847a02b19bcd781ed7e920a1af9`.
- Runtime `e58e5668172b992ebabf9777237686a2e0357cdccd5c7657436acbbc703b1cde`.
- API `sha256:f3181423b249dd14368e4b49bb09790c376371097cabc723fbaaba49b41e3699`.
- Mocks `sha256:89364d891ed4a596d6caf72712a00deaec4662359c2dc116fbe9dc6043aea64e`.

Delta desde r5: avaliador, anotações dos cenários dev e testes do avaliador. Router 5, Support 7, ferramentas, dados, contratos e código HTTP preservados. Imagens reconstruídas para conter o avaliador novo; 126 insumos identificados.

## Ambiente e dados

[API real pronta](v030-ready-r6.json) em `127.0.0.1:18030`; [API QA sem credenciais](v030-qa-environment-r6.json) em `127.0.0.1:18031`. As duas usam a mesma imagem exata, com modelos real/programado distintos e runtimes isolados. A guarda real acumulava US$0,13584893 antes das conversas; após revalidação, US$0,14123583 de US$0,15.

## História e verificações

- [Developer r6](v030-developer-r6.md): 191 testes/validação estrita, Ruff/estrutura/skills aprovados; 29 testes direcionados. Afirmações a rederivar pela revisão independente.
- `must_not_include` permanece bloqueio literal incondicional. `must_not_assert` é anotação opcional, com regras limitadas EN/PT para distinguir afirmação de incapacidade/dúvida, respeitando orações e contrastes; não é um avaliador universal de linguagem natural.
- Script de replay preserva respostas, latências/custos/notas históricos e exige igualdade dos checks não semânticos e de todo holdout. Só anotações dev de conteúdo/afirmações podem mudar; zero chamada de API.
- [Revalidação real das quatro conversas](v030-real-conversations-r3.md): 4/4 via HTTP no saldo do mesmo ledger. [QA independente](v030-qa-r6.md) apto funcionalmente, com limites explícitos.

## Pareceres e validade

[Revisão r6](v030-reviewer-r6.md) apta, [replay](v030-real-http-r2-replay.md) 40/40, conversas reais 4/4 e QA apto. Relatórios originais r1/r2 preservados. Após QA, somente estados/evidências das seis tarefas foram atualizados no [fechamento documental](v030-candidato-r6-docs1.md), com hashes próprios e runtime/insumos Docker idênticos. Este manifesto r6 permanece como identidade histórica da execução. Fonte/critério/ambiente relevantes que mudem invalidam o parecer no escopo afetado.

## Decisão e recuperação

Próximo: aceite humano para integração do candidato documental final. Não há autorização para commit, push, merge, tag ou publicação. Recuperação por v0.2.0 e schema 0005 → 0004 em banco sintético isolado.
