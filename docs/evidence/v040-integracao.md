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

Autorização registrada e preparação em andamento. URLs, SHAs e resultado
efetivo serão conferidos antes de declarar integração concluída. A v0.5.0
partirá das mains integradas/atualizadas, com plano e aprovações próprias de
APIs e migração antes de alterar produto.
