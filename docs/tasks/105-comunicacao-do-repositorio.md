# Tarefa 105 — Reorganização da documentação e verificador de links

## Objetivo

Organizar a documentação versionada como a de um produto em evolução: o README conta as versões como roadmap e traz o que o operador precisa; `docs/evidence/` publica resultados com um índice; tarefas, histórias, specs e ADRs refletem o que foi entregue; um verificador de links relativos protege a navegação na suíte estrita.

## Especificação relacionada

Nenhuma. Regra de documentação do projeto (2026-11-06): a documentação versionada descreve o produto e suas decisões.

## Pré-condições

v0.10.0 integrada. Nenhuma chamada paga; código só em dois comentários e uma linha de configuração.

## Arquivos prováveis

`README.md`; `CHANGELOG.md` (seções de versões publicadas); `docs/architecture/decisions/*.md`; `docs/specs/*.md`; `docs/historias/*.md`; `docs/tasks/*.md`; `docs/contracts/*.md`; `docs/wiki/origem-template.md`; `docs/evidence/` e seu índice; `src/merchant_assistant/api/app.py` e `docker/entrypoint.sh` (um comentário cada); `.env.example` (uma linha); `tools/scripts/checar-links.py` (novo) e `tools/scripts/lint_and_tests.py`.

## Passos

1. **README.** Documento de produto: a tabela de versões conta a evolução como roadmap (o que cada versão trouxe e por quê, em termos de operação real); uma seção de operação com os fatos que o operador precisa (perfil do compose, credenciais de demonstração, snapshots datados, orçamento), uma frase cada; uma seção com as próximas versões (identidade por provedor externo, canal do operador no celular, múltiplos workers, OTLP, cancelamento com confirmação, resumo de conversas longas); cada tema em um lugar; links de evidência apontando para resultados.
2. **CHANGELOG** (versões publicadas): notas de configuração no lugar de listas de limites, com "superseded in vX" onde a versão seguinte fechou o item; correções em uma linha cada.
3. **ADRs.** Status atual em cada uma (0019 aceita; 0013 e 0015 com nota de supersessão); 0016 como reabertura do escopo para o roadmap de produção; alternativas como "não adotado", com o motivo.
4. **Specs.** As specs de evolução recebem nomes por versão (`evolucao-producao-v070-v0100.md`, `roadmap-v0110-v100.md` e seus planos); objetivos escritos como requisitos de produto; questões decididas fechadas; estado atual nas demais. Links atualizados em todo o repositório.
5. **Histórias e tarefas** com o estado real: histórias apontam a validação que as executou; tarefas entregues com Status final.
6. **Evidência.** `docs/evidence/` com resultados por versão, manifestos de candidato, execuções reais, calibração, holdouts, retrieval e relatórios finais de revisão independente; índice em `docs/evidence/README.md`; os originais completos ficam nas tags de versão.
7. **Contrato e wiki.** `docs/contracts/api-v1.md` com o contrato vigente (token, `interrupted`, URL do projeto web); `docs/wiki/origem-template.md` atualizado.
8. **Código.** Comentário do fallback de teste em `api/app.py`, linha do perfil de worker em `docker/entrypoint.sh` e comentário atualizado no `.env.example`.
9. **Verificação.** Verificador de links relativos `tools/scripts/checar-links.py` (links inline, imagens e referências fora de código; alvo rastreado pelo Git; âncoras pelo slug do GitHub) ligado ao `lint_and_tests.py` e ao `validate-project.ps1`; `checar-caminhos-pessoais.py`; suíte estrita.

## Critérios de conclusão

- README com seção de operação e de próximos passos; cada tema em um lugar.
- `docs/evidence/` com resultados e índice; nenhum link quebrado.
- Specs com nomes por versão; ADRs com status e voz corretos; histórias e tarefas com estado real.
- Verificador de links no `lint_and_tests.py`; suíte estrita verde; caminhos pessoais limpos.

## Resultado

Documentação reorganizada e `tools/scripts/checar-links.py` na suíte estrita, com 7 testes em `tests/unit/test_checar_links.py`.
`checar-links.py` sem alvo ausente em 322 arquivos Markdown; `checar-caminhos-pessoais.py` sem ocorrência em 634 arquivos; suíte estrita com 2.156 aprovados.
Evidência: [índice de evidências](../evidence/README.md).

## Status

```text
concluída (v0.11.0)
```
