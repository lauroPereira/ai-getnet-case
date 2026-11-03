# Tarefa: holdout de respostas da v0.8.0, escrito e lacrado antes de qualquer ajuste de prompt

## Objetivo

Criar `tests/scenarios/holdout_v080.jsonl` com pelo menos 20 casos novos (metade em português), rotulados contra os dados sintéticos e as fontes oficiais versionadas, e lacrá-lo por hash verificado na suíte.

## Especificação relacionada

[Spec 0.2](../specs/evolucao-pos-feedback.md) RF-92 e CA-50; [plano](../specs/evolucao-pos-feedback-plano.md) decisão técnica 15, risco "Holdout escrito pelo autor dos prompts" e seção "Sequência, dois times e estimativa" (72a, Time B, durante a v0.7.0).

## Pré-condições

- Worktree do Time B em `C:\workspace\ai-getnet-case-wt\time-b`, branch `codex/v0.8.0-avaliacao` (a partir da `main` com a v0.6.0), `.venv` próprio.
- Quem escreve o holdout não ajusta prompts: **não abra `prompts/`** nem traces ou respostas reais de modelo. As mensagens nascem de paráfrases das fontes oficiais versionadas (`data/sources/`, `data/knowledge-demo/`) e dos fatos dos dados sintéticos (`src/merchant_assistant/data/seed.py` e ferramentas em `src/merchant_assistant/tools/domain.py`), não dos prompts.
- Os JSONL existentes em `tests/scenarios/` servem só para o formato e para evitar duplicata: não copie nem reescreva de leve as mensagens deles.
- Sem chamada paga. Arquivos do Time A (`cli.py`, `evaluation/`, `orchestration/`, `api/`, `prompts/`) ficam intocados neste período.

## Arquivos prováveis

`tests/scenarios/holdout_v080.jsonl`, `tests/scenarios/holdout_v080.sha256`, `tests/unit/test_holdout_v080.py` (novos).

## Passos

1. Composição: ≥ 20 casos (sugestão 24: 12 pt, 12 en), `split: "holdout_v080"` (distinto do `holdout` antigo de `core_cases`, que foi usado no desenvolvimento). Cobrir as rotas na proporção do uso real: `knowledge`, `support` (recebíveis, liquidação, dispositivo, autorização, contrato, preço, cancelamento, habilitação), `knowledge_and_support`, `general_web`, `human_handoff` e uma recusa ou fora de escopo; ao menos três difíceis (paráfrase distante da página, duas intenções na mesma mensagem, pergunta em inglês sobre produto descrito só em português).
2. Rótulos no formato de `src/merchant_assistant/evaluation/runner.py` (`Case`): rotas aceitas, status, ferramentas esperadas, valores em centavos (`must_include_amounts`) e grupos de termos (`must_include_any`) tolerantes a sinônimos e às duas línguas quando couber; `must_not_include` para dado de outro lojista quando a pergunta tentar acessá-lo.
3. Derive cada valor das ferramentas sobre a seed em processo (banco sintético temporário, relógio fixo da seed), nunca de memória; anote em `docs/evidence/v080-holdout-derivacao.md` o comando e o resultado que sustentam cada valor e cada fonte (página e trecho curto).
4. Lacre: SHA-256 do conteúdo UTF-8 com quebras de linha normalizadas para `\n`, gravado em `holdout_v080.sha256`. Teste em `tests/unit/test_holdout_v080.py`: o hash confere; todos os casos carregam por `load_cases`; ≥ 20 casos e metade ou mais em pt; ids únicos e sem colisão com os outros JSONL; nenhuma mensagem igual às dos outros conjuntos.
5. Commit único da tarefa com a mensagem citando o hash.

## Critérios de conclusão

- [ ] ≥ 20 casos, ≥ 50% em pt, rotas cobertas como no passo 1, três difíceis marcados (campo `notes` ou id com sufixo `-HARD`).
- [ ] Cada valor e cada fonte tem derivação reproduzível no arquivo de evidência.
- [ ] Teste de lacre passa; alterar um byte do JSONL o faz falhar.
- [ ] Suíte estrita com código 0 no worktree; nenhuma chamada paga; `prompts/` não foi aberto (declarado na passagem).

## Validação

Developer, rodada 1 (2026-11-03), worktree do Time B, branch `codex/v0.8.0-avaliacao`, base `d7acaec`:

- `tests/scenarios/holdout_v080.jsonl`: 25 casos, 13 pt e 12 en, `split: "holdout_v080"`. Rotas: `knowledge` 6, `general_web` 2, `support` 10 (recebíveis, liquidação, dispositivo, autorização, contrato, preço ×2, cancelamento, habilitação, isolamento de outro lojista), `knowledge_and_support` 3, `human_handoff` 2, `out_of_scope` 2. Quatro difíceis com sufixo `-HARD` (o `Case` não tem campo `notes`): 2 em inglês sobre produto descrito só em português, 1 paráfrase distante e 1 com duas intenções.
- Lacre: SHA-256 `4002fdc9b9efd667d253c5fe9ae6b48d7cd03eac6c489a0119984d8139e1e626` (UTF-8, quebras normalizadas para `\n`) em `tests/scenarios/holdout_v080.sha256`.
- Derivação: [v080-holdout-derivacao.md](../evidence/v080-holdout-derivacao.md), com comando, saída das ferramentas sobre a seed (relógio `2026-10-26T10:00:00`, banco em `.pytest_cache/v080-b-holdout/`) e página e trecho de cada fonte oficial.
- `tests/unit/test_holdout_v080.py`: 6 testes (hash; CRLF não muda o hash e um byte alterado muda; carga por `load_cases` e composição; ids únicos e sem colisão; mensagens novas; valores dos casos com ferramenta saem das ferramentas sobre a seed). Com um byte do JSONL alterado, 2 testes falharam; com o arquivo restaurado, os 6 passaram.
- Suíte estrita: `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v080-b-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` terminou com código 0 e 355 testes aprovados; ruff sem achados. A primeira execução falhou só por um SIM300 (comparação invertida) no teste novo, corrigido antes da segunda.
- Nenhuma chamada paga; `prompts/` não foi aberto.

## Status

```text
Implementada pelo Developer (rodada 1); aguarda revisão independente.
```
