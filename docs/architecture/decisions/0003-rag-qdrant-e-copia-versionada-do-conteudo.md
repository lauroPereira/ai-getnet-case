# 0003. RAG com Qdrant e cópia versionada do conteúdo coletado

## Título

Indexar fontes oficiais e a base fictícia no Qdrant com `text-embedding-3-small`, a partir de uma cópia versionada do conteúdo coletado.

## Status

```text
aceita
```

Aceita pelo responsável em 2026-10-26.

## Contexto

O desafio pede um pipeline RAG funcional que ingira as URLs indicadas e procure outras fontes. O site pode mudar ou ficar indisponível durante a avaliação, páginas dinâmicas podem gerar extração vazia e o avaliador precisa subir o sistema só com Docker. Os exemplos estão em inglês e boa parte do conteúdo brasileiro está em português. Cada fragmento precisa carregar origem e tipo de fonte para citação.

## Decisão

- A coleta salva o texto extraído de cada página em `data/snapshots/` com URL, título, data de coleta e hash. Essa cópia é versionada e é a entrada da indexação; atualizá-la é um comando explícito.
- A indexação fragmenta por seções, gera embeddings com `text-embedding-3-small` e grava no Qdrant (serviço no docker-compose; modo em memória nos testes) com metadados por fragmento.
- O índice é construído na primeira inicialização se estiver vazio. Modelo de embedding e configuração ficam registrados para reconstrução consistente.

## Alternativas consideradas

- **Coletar o site ao subir o container:** depende da rede e do estado do site na hora da avaliação.
- **Chroma ou FAISS em arquivo:** mais leve, porém com filtros de metadados e operação como serviço menos próximos de produção.
- **pgvector:** exigiria Postgres só para isso.
- **Modelo de embedding local:** evita custo, mas pesa a imagem Docker e a qualidade em português precisa ser provada.

## Consequências

Build e avaliação reproduzíveis e independentes do site. A primeira inicialização consome embeddings (custo pequeno e registrado). O repositório passa a conter texto público coletado, o que exige revisar o volume e manter só o necessário. A recuperação inglês → português precisa ser medida.

## Data

2026-10-26
