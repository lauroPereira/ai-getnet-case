# Tarefa: Verificar fontes oficiais e imagem do enunciado

## Objetivo

Confirmar as páginas oficiais que fundamentam os exemplos de conhecimento e se o texto delas é extraível, e conferir a imagem incorporada ao enunciado.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RF-09, RF-12, UC-01, UC-04, UC-06, UC-09, UC-10, questão Q5.

## Pré-condições

- Autorização do responsável para acesso à rede.
- Lista inicial de fontes públicas, mantida localmente.

## Arquivos prováveis

- `data/sources/public-sources.json` (novo)
- `docs/evidence/2026-10-verificacao-de-fontes.md` (novo)

## Passos

1. Partir da lista inicial de fontes e de `https://www.getnet.net/en`, exigida pelo enunciado.
2. Navegar pelo site oficial e localizar páginas sobre maquininhas (Get Smart, Get Clássica ou equivalentes), Pix, crediário, antecipação de recebíveis e Link de Pagamento. Registrar somente URLs efetivamente visitadas; não deduzir endereços.
3. Para cada página, comparar o texto visível no navegador com o texto obtido por requisição HTTP simples e classificar a extração como `static`, `dynamic` ou `empty`.
4. Registrar os produtos citados nos exemplos que não têm página oficial; eles viram casos de "sem evidência" no conjunto rotulado.
5. Abrir a imagem do enunciado e registrar o que ela mostra e se altera algum requisito.
6. Criar `data/sources/public-sources.json` com `url`, `market`, `topic`, `product`, `extraction` e `verified_at`.

## Critérios de conclusão

- [x] Cada exemplo de conhecimento (UC-01, 04, 06, 09, 10) tem fonte verificada ou ausência registrada.
- [x] Toda página da lista tem classificação de extração.
- [x] Imagem do enunciado verificada, ou impossibilidade registrada.
- [x] Evidência gravada com data e método.

## Resultado

32 URLs verificadas em 2026-10-26 no navegador e por cliente HTTP, todas com `robots.txt` permitido: 30 com extração estática e 2 dinâmicas, capturadas renderizadas. A imagem do enunciado revelou a etapa Personality, incorporada como RF-37. Evidência: [verificação de fontes](../evidence/2026-10-26-verificacao-de-fontes.md).

## Status

```text
concluída (v0.1.0)
```
