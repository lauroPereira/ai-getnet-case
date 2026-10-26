# Tarefa: Pipeline de ingestão RAG

## Objetivo

Coletar as fontes, gravar a cópia versionada, fragmentar, indexar e recuperar, para fontes oficiais e base fictícia, com Recall@k medido.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-09, RF-10, RF-11, RF-14, CA-04. [Decisão 0003](../architecture/decisions/0003-rag-qdrant-e-copia-versionada-do-conteudo.md).

## Pré-condições

- Tarefas 01 e 03 concluídas; tarefa 02 concluída para a etapa com embeddings reais.
- Autorização de acesso à rede para a coleta.

## Arquivos prováveis

- `src/merchant_assistant/rag/` (fontes, coleta, extração, fragmentação, embeddings, índice, recuperação)
- `src/merchant_assistant/cli.py` (comandos `ingest` e `index`)
- `data/snapshots/public/`, `data/knowledge-demo/`
- `tests/unit/rag/`, `tests/integration/test_retrieval.py`, `tests/scenarios/retrieval.jsonl`

## Passos

1. Promover a base fictícia de `discovery/base-conhecimento-ficticia/` para `data/knowledge-demo/`, retirando do README as menções à pesquisa exploratória e acrescentando a tabela de códigos de negativa sintéticos da tarefa 05.
2. Coletor HTTP identificado, com respeito a `robots.txt` e intervalo entre requisições; extração do conteúdo principal, sem navegação repetida.
3. Gravar uma cópia por página com `url`, `title`, `collected_at`, `content_hash` e texto.
4. Falhar com relatório quando o texto extraído de uma página estiver vazio ou curto demais.
5. Fragmentar por seções, com tamanho e sobreposição configuráveis, mantendo metadados por fragmento.
6. Embeddings OpenAI e um embedder falso determinístico para testes; Qdrant como serviço ou em memória; nome de coleção versionado.
7. Recuperação top-k com filtro por tipo de fonte.
8. Conjunto rotulado inicial (pergunta → fragmentos esperados) para os exemplos de conhecimento em inglês e português; medir Recall@k com embeddings reais dentro da reserva.

## Critérios de conclusão

- [ ] `ingest` gera a cópia versionada; `index` reconstrói o índice só a partir dela.
- [ ] Testes rodam sem rede.
- [ ] Recall@k em inglês e em português registrado em `docs/evidence/`, com amostra e custo.

## Validação

A preencher na execução.

## Status

```text
pendente
```
