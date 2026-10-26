<!-- Papel: registrar de qual versão do ai-dev-template este projeto foi criado, o que foi copiado, omitido e adaptado. -->

# Origem do template

| Campo | Valor |
| --- | --- |
| Template | ai-dev-template |
| Versão | 0.3.0 (tag `v0.3.0`) |
| Commit-base | `c85beee93c834f340d928f7da692b9cf6aea6c7d` |
| Estado da fonte | Sem alterações locais no momento da cópia (snapshot não modificado) |
| Data | 2026-10-26 |
| Skill usada | project-create, com destino previamente ocupado (ver abaixo) |
| Política de atualização | `explicit-review-required` |

## Destino

O diretório do projeto já continha o material de discovery do case. A pedido do responsável, esse material foi movido, sem alteração de conteúdo, para `discovery/` antes da cópia do template. Nenhum arquivo existente foi sobrescrito. `discovery/` é local e está no `.gitignore` porque contém contexto privado.

## Arquivos copiados (SHA-256 da fonte)

Somente os caminhos gerenciados do manifesto. Os quatro primeiros foram adaptados depois da cópia; o hash registrado é o da fonte.

```text
af558c0d53c60d3a5f27a3df1ec15153008a821bdd1764c456d717bac18221ea  .agent-template.json
d20e6e7cea99aad3b5f90ea0f4bb7446986d9a4a783ea1b3b9b566a368ee9052  .gitignore
8164ae87d4f93f98c472d26d72158776f60a949cd043e57938e331c4cd0364bd  AGENTS.md
bf226abfa6769e5b8243c9983006fba04b668b6a79ea01b1378ea68e38e1bf53  CLAUDE.md
935074cde24fcd0e586854fc1c323c7bf1dda45c4c62145aa91a8f68674564b2  docs/architecture/README.md
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  docs/architecture/decisions/.gitkeep
c5685c6bd2fdea05b654f7e36bb1e6c5447a034884617569c0d087e3967376b2  docs/evidence/README.md
58770288865b0cccbcb30ce2e764c925b105fd19c0c2d14790a4a6b2b5cf1868  docs/historias/README.md
27da88e719be6f7b6fc92bb66c8d06312208ea0ac010324ae28bc4ff2f16e16b  docs/specs/README.md
112e496f80a308b794fc5768bf1a5d295ff31d6d082b6a20ebe630991d0ec27b  docs/tasks/README.md
b809158a28cc95590be9389fc554341601fbb533f71a25c2f3cea8b7698b722e  docs/templates/candidato.md
cb0d9ef4d42c4f018664e9f73e4fb9cd88b99c8c7164fa70de2495494471a2a5  docs/templates/decision-record.md
d51c047e486de681bfbff777f9b16d8deccc20ddf25e5cc5148e3a4d62f31d34  docs/templates/historia-de-uso.md
14ab690e1d8829b84c5afd60dcf52e15fc8e32fe7cc925ec2bbfe4dabc63b2d8  docs/templates/modelo-analise-tarefa.md
678d2fbabc3806ce18a2c63919a36b249d3eec32c3cfa4c28ebe18a8d884b2ab  docs/templates/modelo-skill.md
fc05b58d6bad03bd520b51d239b50078d17d77c859c08ab12dfaec4b79d5eca0  docs/templates/modelo-workflow.md
8f2471c98892d9d36c5e9a3e6589e07d1868391dbd059938b5b05575adf5e10b  docs/templates/passagem-de-papel.md
992a3c0a2af8ef7762d4fa5cbb1e3740bd976f7c1365c10cfe994627fe88efd0  docs/templates/plan.md
7f93f1a0cb3c258563c74ca7824f0dcaf11385b3973bb766b3ee06a2d3466913  docs/templates/spec.md
8ec48a1ef137948a006451a6d87bb2e9a9b00c475f3e9891f4f998d99344a448  docs/templates/task.md
d6186801cc378121fd83b1455a1fa2f76ab66f160ca7c9b2b491271a86985c15  docs/wiki/agents/README.md
3c0f9a17ee16159210031a9b94b9f12e9a8f7daf58adab15feab011911630f90  docs/wiki/agents/atualizacao-do-fluxo.md
e39a4ae0fe41899c18f63cb46e5c8c71387db0ac5c0af212a765e6c386f89579  docs/wiki/agents/developer.md
16c65d3c358a11f6262ffbe60b34055df15c14e622576d49ae38dfe764abb138  docs/wiki/agents/perfil-develop.md
e6fe0c4a789285dca6faca87a35ebaa94cbead53664d6b00f28d1270499309e4  docs/wiki/agents/qa.md
2b8052036ac7b8f188bfa4f52c240e0a244eadd4fba6ebdc5edb0f57e4af2ee0  docs/wiki/agents/reviewer.md
36a739accdb1218d343236a956fee7f219962f6e4c1f2ed95a8175a0f5b4516d  docs/wiki/agents/supervisor.md
40bfdbf12fe95cbbdf250d8f70f0154dc2a5a8c197965c31ab6f86cda88609f8  docs/wiki/agents/workflow.json
86f473e22fd278e67fdd4b1389dbf06d7698823da1a8fba25b2dfa6c7734c8ca  evals/expected/01-correcao-minima.md
03ac138f4b29f05db470c06c172de24dae2252ebfd17a009ba9e49bd6e37150f  evals/expected/02-alteracao-contrato.md
7425a3d18e2b1d588f261d38fd28d44a1e42feaf4b9fac0a4e9a262c7bb97d7b  evals/expected/03-supervisor-entrada.md
67993262ace23c5886eb05aa8b30aa7d2d114de4d8af21f2b655adeea760ea2a  evals/expected/04-supervisor-continuidade.md
934e231be3007681916ea363db5cafc7e63b5e1867f9b18abd41847022548416  evals/tasks/01-correcao-minima.md
76a4599778820fba043fa25c10f46d549233087d2725fa6b06e6a4af8dec3bc1  evals/tasks/02-alteracao-contrato.md
9807bbc9041ffe9552c600133329e67e95f43ae5b56e34fc092b2361b8620438  evals/tasks/03-supervisor-entrada.md
06c3ec3d2b40fbabc77581599404f9845a3918af825af81f612a53f65d81dfa5  evals/tasks/04-supervisor-continuidade.md
911c388a031dc74697b7b3938a50ca9b724c777be32a9704c48b9b55c4b083ee  skills/developer/SKILL.md
5af31d557e2e9d25cffac7f9431aee532e0c79d0f577aa2239cfee731858dc8a  skills/project-bootstrap/SKILL.md
11ef247655ef07718da8eab8d33c1bfba9193c5bea8634d947a4a8e5f0e37fa0  skills/project-create/SKILL.md
8df61e84a9a60630bfa14faafc0ac9bfd81bf80fa0065663c202e617259b464c  skills/project-update/SKILL.md
99247d9caf97931a296ac841f5bb9cf8675eb76222d09b0a30ad5fb3dcd25a4b  skills/qa/SKILL.md
b6f42027e4c2cdea65e726bb31af942651f7f5866c565a4d3c9d724393ed8d9a  skills/repository-code-review/SKILL.md
9168bd5e06b9ab86d67b1f6ab997a7e48218970ee54f85930cc9692d189a001d  skills/reviewer/SKILL.md
27dc658f808092b5e65c351982a836f42a8891dcb86c11fab1a9d38d143eb0e8  skills/skill-creator/SKILL.md
ccd178dda8209c306c1e118a29cfc03ee2f2d966c0d69f77cc896fa54bdec2c1  skills/supervisor/SKILL.md
0886ff86cbb18169538e1b376c9349ff0936daf9e83ab75b88465c1ae1d62e56  tools/scripts/lint_and_tests.py
f4258c78d90cf5372af05cfa9a55049a830042a3ac23ec2c8b512a9f1b6f598f  tools/scripts/sync-skills.ps1
9eeba06f4783a527fc65499daeb16a23fc8b8a71f2c2ea2fe21f84edb2fa7fce  tools/scripts/validate-agent-flow.ps1
09e351be86938b107760a355f8045c128c098b7753a3632ec6db873b1a70891c  tools/scripts/validate-project.ps1
```

`.claude/skills/` e `.agents/skills/` foram gerados no destino por `tools/scripts/sync-skills.ps1` a partir de `skills/`.

## Omissões

| Item da fonte | Motivo |
| --- | --- |
| `.git` | Snapshot independente; Git do projeto ainda não inicializado |
| `README.md` do template | O projeto tem README próprio |
| `.claude/settings.json` | Fora dos caminhos gerenciados; preferências e permissões não são herdadas |
| `.github/` (workflow e CODEOWNERS) | Fora dos caminhos gerenciados; CI do projeto será definido quando houver repositório |
| `.obsidian/` | Configuração pessoal de editor |
| `docs/raw/` | Nunca copiado por regra do template |
| `docs/evidence/2026-09-30-template-flow-validation.md` | Evidência real do template, não do projeto |
| `docs/wiki/checklist-inicial.md`, `docs/wiki/politica-de-permissoes.md` | Fora dos caminhos gerenciados |

## Adaptações

| Arquivo | Adaptação |
| --- | --- |
| `AGENTS.md` | Seção "Sobre este projeto": objetivo, stack, idioma, fluxo SDD, discovery local, privacidade, orçamento e estado do Git |
| `CLAUDE.md` | Indicação para ler "Sobre este projeto" e tratar `discovery/` como local |
| `.agent-template.json` | `project_name`, descrição do projeto, caminhos próprios do projeto e `enabled_optional_components: ["sdd"]` |
| `.gitignore` | `discovery/`, artefatos de build Python e dados gerados em execução |
