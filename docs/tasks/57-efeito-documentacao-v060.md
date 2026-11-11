# Tarefa: efeito da documentação no comportamento

## Objetivo

Preparar, sem custo, a demonstração V1 → edição fictícia → candidata → teste → ativação → mudança observável → retorno, com a diferença esperada fixada antes da edição.

## Especificação relacionada

[Spec v0.6.0, bloco D](../specs/fechamento-v060.md), RF-63–66, RF-79, CA-49 e [plano](../specs/fechamento-v060-plano.md) (decisão 6).

## Pré-condições

Tarefa 55 concluída (catálogo e Resultados). Documento fictício de dispositivos (`KB-DEMO-DEVICES-001`) disponível no registro da base. Sem chamada paga.

## Arquivos prováveis

`data/scenarios/` (cenário de D), fixture com o texto da V2, testes de integração com política programada, e o roteiro operacional da validação real (na tag `v0.6.0`).

## Passos

1. Escrever a pergunta segura e pertinente, com rota esperada `knowledge_and_support`, no catálogo.
2. Registrar a diferença esperada antes da edição: na V2, o procedimento exige `get_contract_snapshot` antes de oferecer Link de Pagamento como alternativa, e a resposta só oferece a alternativa se o produto constar nos fatos.
3. Preparar o texto da V2 como edição de rascunho do documento fictício, sem prazo oficial, regra financeira ou concessão de ferramenta.
4. Teste de integração sem custo: mesma pergunta, cenário, perfil, prompts e ferramentas em conversas independentes; V1 sem a consulta, V2 com a consulta, V1 restaurada sem ela; trecho, versão, fatos e ferramentas visíveis em Resultados.
5. Roteiro da validação real: executar a V1 primeiro; se a diferença já ocorrer, redefinir e registrar outra antes de editar; repetição pequena por versão.

## Critérios de conclusão

- [x] Diferença esperada registrada antes de qualquer edição real.
- [x] Teste sem custo mostra a mudança e o retorno por ferramenta e fato, não só por redação.
- [x] Nenhuma ferramenta nova, prazo oficial ou regra financeira vinda do texto.

## Resultado

Diferença esperada registrada antes da edição; a V2 só acrescenta a seção de alternativa de venda. O teste sem custo mostra a V1 sem `get_contract_snapshot`, a V2 com o trecho novo e a ferramenta e a V1 restaurada sem ela. Na validação real, o trecho novo veio em primeiro (0,758) e a V1 restaurada voltou sem a ferramenta. Suíte estrita: backend 326 testes, web 30. Evidência: [resultado da v0.6.0](../evidence/v060-resultado.md).

## Status

```text
concluída (v0.6.0)
```
