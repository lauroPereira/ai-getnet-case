# 0009. Versões da base de conhecimento com coleção por versão

## Título

Criar uma coleção Qdrant por versão da base e manter um ponteiro para a versão ativa, com o ciclo build → teste → ativação → retorno.

## Status

```text
aceita
```

Aceita pelo responsável em 2026-10-26.

## Contexto

O responsável quer editar a documentação fictícia pela interface. Uma versão incompleta não pode substituir a ativa, cada execução deve consultar uma versão consistente e é preciso voltar à anterior. Fontes oficiais coletadas não podem ser sobrescritas.

## Decisão

- `kb_versions` com estados `building`, `testing`, `ready`, `active` e `retired`; cada versão aponta para uma coleção própria (`getnet_kb_vN`) e um manifesto (documentos, hashes, modelo de embedding).
- Rascunhos editam só documentos `simulated_internal`; documentos `public_official` são somente leitura.
- Ativação troca o ponteiro de forma atômica; execuções em andamento terminam na versão que começaram.
- Mantêm-se a ativa, a candidata e a anterior; as demais são removidas.
- Trocar o modelo de embedding também cria uma nova versão.

## Alternativas consideradas

- **Atualizar a coleção ativa no lugar:** risco de base inconsistente durante a atualização e sem retorno.
- **Índice por documento:** mais granular, mas a consulta deixa de ter uma versão única identificável.

## Consequências

Cada resposta identifica a versão da base usada; retorno instantâneo. Custo de reindexar a base inteira por versão (cerca de US$0,001 hoje).

## Data

2026-10-26
