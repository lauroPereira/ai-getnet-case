# Tarefa 87 — Resumo da busca no trace e páginas citadas como evidência

## Objetivo

Fazer o juiz ver a evidência das respostas de busca web: o passo de busca grava o que a busca devolveu, e a avaliação busca o texto das páginas citadas e o entrega ao juiz como evidência de página.

## Especificação relacionada

[Juiz por afirmação, evidência da web e retrieval — v0.11.0](../specs/juiz-retrieval-v0110.md): D1, D2, CA-60. Plano do ciclo: [decisões 1 e 2](../specs/roadmap-v0110-v100-plano.md#decisões-técnicas). Base: `agents/knowledge.py` (`_web`, `run_web`, `evidence_texts`), `evaluation/evidence.py` (`passage_items`, `WEB_NOTE`, `judge_input`, `fit_items`), `rag/collect.py` (`extract_text`), `guardrails/` (máscara), `observability/traces.py` (`detail` por passo).

## Pré-condições

A avaliação consome os campos `web_summary` e `web_urls`; a busca de páginas ocorre apenas na avaliação, nunca durante o atendimento.

## Arquivos prováveis

`agents/knowledge.py` (gravar `web_summary` e `web_urls` em `ctx.step_notes` nos dois passos), `evaluation/evidence.py` (itens `web_page` e `web_summary`, buscador com cache, três formas da nota), `evaluation/web_pages.py` (novo: busca, limites, cache), `config.py` (`WEB_EVIDENCE=on|off`, `WEB_EVIDENCE_TIMEOUT_SECONDS`, `WEB_EVIDENCE_MAX_BYTES`), `prompts/judge.v3.md` e `judge.v4.md` **não mudam** (a descrição dos itens novos vai no `judge_input`, campo `evidence_notes`, não no prompt), `cli.py` (`eval --judge-repeat --only-route` se ainda não existir), testes em `tests/unit/evaluation/` e `tests/integration/`.

## Passos

1. **Trace.** Em `_web` e em `run_web`, gravar em `ctx.step_notes["web_summary"]` o texto da busca mascarado (teto 4 000 caracteres; `web_summary_truncated: true` quando cortado) e `ctx.step_notes["web_urls"]` (lista de `{title, url}`). Conferir que o `detail` do passo persiste no trace e aparece em `GET /v1/runs/{id}` sem expor nada não mascarado.
2. **Buscador.** `evaluation/web_pages.py`: `fetch(url) -> PageText | Unavailable`: só `https`, timeout configurável (padrão 10 s), limite de bytes (padrão 2 MB), sem seguir redirecionamento para outro domínio, `User-Agent` do projeto; `extract_text` do `rag/collect.py`; máscara; cache em `runtime/web_evidence/<sha256(url)>.json` com `fetched_at`, `status`, `text`, `truncated`. Cache lido antes de buscar. Nenhuma busca no caminho de resposta ao lojista.
3. **Evidência.** `evidence.py`: para passos `knowledge` (modo `web`) e `web` com `web_urls`, um item `{"kind": "web_page", "title", "url", "text"}` por URL buscada, dentro do teto comum de `fit_items`; URL indisponível → um item `{"kind": "web_summary", "text": <web_summary>}` e nota "page unavailable; the search summary written by the assistant is given instead, it is not a page"; sem `web_urls` → nota atual. `WEB_EVIDENCE=off` → comportamento atual. As notas ficam em `evidence_notes` como hoje; o relatório do `eval` conta respostas por forma da nota.
4. **Rejulgar por rota.** `eval --judge-repeat N --answers-from <relatório.json> --only-route general_web` seleciona as respostas da rota com evidência web.
5. **Testes sem rede:** servidor HTTP em processo com três páginas (uma com texto, uma 500, uma que redireciona para outro domínio); item `web_page` montado e cortado no teto; fallback no resumo; cache usado na segunda chamada; `WEB_EVIDENCE=off`; `web_summary` gravado e mascarado nos dois passos com modelo programado; `GET /v1/runs/{id}` mostra o campo mascarado; nenhuma busca durante `POST /messages` (teste que falha se o buscador for chamado no turno).

## Critérios de conclusão

- `web_summary`/`web_urls` nos traces dos dois passos, mascarados e limitados.
- Itens `web_page` no `judge_input` quando a página foi buscada; fallback e nota nos outros casos; cache funcionando.
- `judge.v3.md` e `judge.v4.md` intocados (hash conferido em teste).
- Os testes do buscador usam servidor em processo; o endpoint de atendimento não acessa páginas web.
