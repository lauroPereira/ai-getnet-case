# Integração v0.4.0 — autorização e candidato

## Autorização humana

Em 2026-10-27, após receber o resultado r6 e suas limitações, o responsável
autorizou criar PR, fazer merge e começar a próxima versão. Confirmou criar
`lauroPereira/ai-getnet-case-web` **privado**, integrar ambos os projetos e usar
no web a identidade local `lauroPereira <lauro.s.pereira@gmail.com>` sem alterar
a configuração global da máquina.

A autorização de QA pago começa na **v0.5.0**, sob o teto total de US$5 e a
guarda persistente. Ela não transforma os testes v0.4.0 em inferência real;
CA-32/JEV e disponibilidade autenticada dos modelos continuam abertos e devem
ser revalidados pela próxima rodada. Testes determinísticos permanecem úteis
para contratos, erros e regressões, separados da aceitação real do QA.

## Base validada

- [Candidato r6](v040-candidato-r6.json), fonte
  `d54fbd3799cecfefd0c467be217eb841e59d4ae9c89f607dc1a64967ae4d9367`.
- Backend216/web14; [Reviewer r6](v040-reviewer-r6.md),
  [QA r6](v040-qa-r6.md) e positivos [QA r5](v040-qa-r5.md).
- [Auditoria pós-QA](v040-verificacao-final-r6.json): mapas51/84/127/128,
  protegidos e 124 arquivos instalados íntegros. Nenhuma API paga v0.4.0;
  acumulado do projeto US$0,59283583.
- Backend privado, main remota conferida em
  `bd549cc921ccffb37bd304a0959b8a4b690d6421`, identidade local confere.
- Web inicializado com 70 arquivos inalterados da base aprovada, commit
  `2cf57ba7ee9c128c0467fe6ddc738197bf40a2d3`; main publicada e atualizada
  antes da branch de trabalho. Não foi criado commit vazio.

## Ajustes para integração

Somente README/changelog e estados documentais das tarefas são alinhados ao
aceite e às evidências finais. Código, contrato, dados, prompts, histórias,
catálogo e testes do r6 não mudam. Os hashes locais anteriores são preservados;
Git pode normalizar finais de linha, portanto a integração também registra
hashes dos blobs canônicos do índice/commit.

O candidato inclui o fechamento documental histórico da integração v0.3.0,
sem modificar aquela tag. Excluir `.env`, discovery, dados de runtime,
credenciais e ambientes/cache. Somente fontes públicas e dados sintéticos.

## Operação e recuperação

Commit/push das branches, um PR por projeto, conferência de checks e merge
local com a identidade do projeto, seguido de push da main. Confirmar que
cada PR foi integrado e a árvore promovida contém seu head. Não tornar os
repositórios públicos. Recuperação por reversão de commits; migração0006→0005
foi testada apenas em bancos sintéticos. Não remover dados nem reiniciar ledgers.

## Estado

PRs abertos e branches enviadas:

- Backend [PR #5](https://github.com/lauroPereira/ai-getnet-case/pull/5),
  implementação `be86c5c2b0961c3b47dd760f0b4eee318a2162fa`.
- Web [PR #1](https://github.com/lauroPereira/ai-getnet-case-web/pull/1),
  implementação `b76d415dbbc611cc767c7a5be43d00cf28232a68`.
- [Manifesto canônico Git](v040-git-integracao.json): 160 blobs backend e
  84 de fonte web conferidos, sem divergências; fonte canônica combinada
  `0e20fff42cf4ec982961a8adf688b365eb69ae27ff0dae0e9f531fc71952dac9`.

Checks e resultado efetivo do merge serão reconferidos antes de declarar
integração concluída. O fechamento pós-merge fica no início da v0.5.0, evitando
auto-referência de SHA no próprio commit. A próxima versão parte das mains
integradas/atualizadas, com plano e aprovações específicas de APIs/migração.

## Confirmação pós-merge — registrada na branch v0.5

Os dois PRs estão `closed/merged`. Main local/remota backend:
`ea2355b5ba8fa8dcff66200f34461ae063183250`; web:
`40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`. Autor/committer conferem; árvores
iguais às pontas dos PRs e ancestralidade confirmada. Ambos permanecem privados.
O GitHub apresenta estado limpo e nenhum check/status/job de CI; testes e
pareceres acima são evidências locais. [Confirmação estruturada](v040-integracao-confirmada.json).

Após os merges, mains atualizadas e branches `codex/v0.5.0-base-versionada`
criadas em ambos. O plano da próxima versão fica local aguardando aprovação
específica; nenhum gasto pago ou produto v0.5 foi executado na preparação.
