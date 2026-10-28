# Tarefa: efeito da documentação no comportamento

## Objetivo

Preparar, sem custo, a demonstração V1 → edição fictícia → candidata → teste → ativação → mudança observável → retorno, com a diferença esperada fixada antes da edição.

## Especificação relacionada

[Spec v0.6.0, bloco D](../specs/fechamento-v060.md), RF-63–66, RF-79, CA-49 e [plano](../specs/fechamento-v060-plano.md) (decisão 6).

## Pré-condições

Tarefa 55 concluída (catálogo e Resultados). Documento fictício de dispositivos (`KB-DEMO-DEVICES-001`) disponível no registro da base. Sem chamada paga.

## Arquivos prováveis

`data/scenarios/` (cenário de D), fixture com o texto da V2, testes de integração com política programada, e o roteiro operacional em `docs/evidence/v060-qa-preparacao.md`.

## Passos

1. Escrever a pergunta segura e pertinente, com rota esperada `knowledge_and_support`, no catálogo.
2. Registrar a diferença esperada antes da edição: na V2, o procedimento exige `get_contract_snapshot` antes de oferecer Link de Pagamento como alternativa, e a resposta só oferece a alternativa se o produto constar nos fatos.
3. Preparar o texto da V2 como edição de rascunho do documento fictício, sem prazo oficial, regra financeira ou concessão de ferramenta.
4. Teste de integração sem custo: mesma pergunta, cenário, perfil, prompts e ferramentas em conversas independentes; V1 sem a consulta, V2 com a consulta, V1 restaurada sem ela; trecho, versão, fatos e ferramentas visíveis em Resultados.
5. Roteiro do QA real: executar a V1 primeiro; se a diferença já ocorrer, redefinir e registrar outra antes de editar; repetição pequena por versão.

## Critérios de conclusão

- [ ] Diferença esperada registrada antes de qualquer edição real.
- [ ] Teste sem custo mostra a mudança e o retorno por ferramenta e fato, não só por redação.
- [ ] Nenhuma ferramenta nova, prazo oficial ou regra financeira vinda do texto.

## Validação

- Diferença esperada registrada antes de qualquer edição real em [v060-qa-preparacao.md](../evidence/v060-qa-preparacao.md); pergunta `SC-DOC-EFFECT` no catálogo; V2 em `data/scenarios/kb-demo-devices-v2.md` (só acrescenta a seção "Alternativa de venda com a maquininha sem conexão").
- `test_document_edit_changes_tool_use_and_rollback_restores_it`: V1 sem `get_contract_snapshot`; rascunho V2 com diff só de adição; build, teste e ativação; V2 com o trecho novo nos `hits`, `get_device_status` → `get_contract_snapshot`, fonte do contrato e oferta condicionada ao fato; retorno a `kb_initial` restaura o comportamento; três conversas independentes com o mesmo cenário, perfil, digest, Router e conjunto de prompts.
- `test_v2_text_adds_no_deadline_amount_or_new_tool`: a seção nova não tem dígitos (prazo, valor, taxa) e só cita a ferramenta já autorizada.
- Limite: a política programada aplica o procedimento recuperado; o comportamento do modelo real fica para o QA, com o roteiro na preparação.

Validação estrita backend (`PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v060-dev-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`): **326 passed**, Ruff "All checks passed!", estrutura e skills válidas, código 0. Web (`.venv-v040/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`): **30 passed**, Ruff sem achados, código 0. Nenhuma chamada paga, chave de provedor ou build Docker. Passagem: [v060-developer.md](../evidence/v060-developer.md).

## Status

```text
concluída
```

Revisada (Reviewer, rodadas 1–5) e validada no QA real da v0.6.0 (rodada 2, candidato r5); ver [resultado](../evidence/v060-resultado.md).
