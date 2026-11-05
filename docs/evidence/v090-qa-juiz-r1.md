# Passagem de papel: QA da v0.9.0, momentos 1 a 3 (experimento do juiz), rodada 1

- **Papel e responsável:** QA nativo, contexto novo; caixa-preta pela CLI (`merchant-assistant eval` e `eval-calibrate`). Sem Docker e sem navegador nesta fase, como pedido.
- **Objetivo e critérios:** CA-56 pelos momentos 1 a 3 de [juiz-retrieval-v090.md](../historias/juiz-retrieval-v090.md) (versão 1, 2026-11-05), com a spec [juiz-retrieval-v090.md](../specs/juiz-retrieval-v090.md) (D1, D2, D5, "Orçamento") e a regra operacional do P2-4 ([v090-reviewer-t79.md](v090-reviewer-t79.md), rodada 2; complemento de D1).
- **Escopo:** sonda de 3 julgamentos Opus, 72 (ou 24) julgamentos sobre as 24 respostas da calibração, relatório `eval-calibrate --judge` e regressão do relatório da v0.8.0.
- **Estado:** **bloqueado**. A credencial Anthropic é recusada pela API; momentos 2 e 3 não foram executados.
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, sem PR. Nada commitado pelo QA.
- **Base e versão final:** candidato [v090-candidato-r1.json](v090-candidato-r1.json) (head do manifesto `80a0853`, fingerprint `e3a8895f…81df`). HEAD no início: `97b8141` (só o manifesto sobre `80a0853`). Durante a suíte a branch avançou para `f8f7db4` (`docs/evidence/v090-developer.md` e `docs/tasks/80-retrieval-hibrido-bm25-rrf.md`, só documentação); a sonda rodou em `f8f7db4`, sem alteração no escopo do juiz.
- **Independência:** independente (não implementei nem revisei a tarefa 79).

## Pré-checagens (sem custo)

| Verificação | Resultado |
| --- | --- |
| `git rev-parse HEAD` | `97b81418…` no início, como pedido; `f8f7db4` depois (só docs, acima) |
| sha256 dos 17 arquivos do manifesto | os 17 conferem com o conteúdo dos blobs do commit. Na árvore de trabalho, 8 diferem só por CRLF (`.gitattributes` com `* text=auto`); normalizados para LF, os 17 conferem. Observação, sem efeito |
| `merchant-assistant eval --help` | mostra `--only-sample` e `--limit` (com a semântica de `--judge-repeat`) |
| `merchant-assistant eval-calibrate --help` | mostra `--judge` e `--judge-run` |
| `calibrations` no runtime de QA | 24 linhas, campanha `v080-all-r3`, rater `lauro` (única combinação) |
| sha256 de `.pytest_cache/qa-v080-r1/runtime/merchant.sqlite3` antes da primeira gravação | `ab3fc701…e3d6`, igual ao registrado pelo Reviewer; backup em `.pytest_cache/qa-v090-backup/merchant.sqlite3` com o mesmo hash |
| `data/runtime/anthropic` antes | não existia |
| Ledger do projeto `data/runtime/budget.sqlite3` antes | 3632 lançamentos (máx. id 3632), soma US$1,402518, 0 lançamentos `claude%`, teto 2.0 |
| `python tools/scripts/lint_and_tests.py --strict` (`PYTEST_ADDOPTS=--basetemp=.pytest_cache/qa-v090-suite-<ts>`) | **2050 passed** em 878 s, Ruff "All checks passed", skills válidas, caminhos pessoais: nenhuma ocorrência em 729 arquivos; exit 0. Começou em `97b8141` e terminou em `f8f7db4` (dois arquivos de documentação, fora dos testes); vale como pré-condição, não como número de revisão |

## Momento 1, sonda: bloqueado

Comando (sem valores de chave; as chaves vêm do `.env`):

```text
JUDGE_PROVIDER=anthropic JUDGE_MODEL=claude-opus-5-5 \
BUDGET_RUNTIME_DIR=data/runtime/anthropic BUDGET_LIMIT_USD=4.00 \
RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime \
merchant-assistant eval --judge-repeat 1 --answers-from docs/evidence/v080-all-r3.json \
  --only-sample docs/evidence/v080-calibracao-amostra.csv --limit 3 --name v090-juiz-opus-sonda
```

Início 2026-11-05T20:56:56Z, 12,7 s. Saída: "grading 3 of 44 recorded answers (24 request ids in v080-calibracao-amostra.csv), --limit 3", `judge_failed: 3`, "judgements stored in run_evaluations: 3 (execution v090-juiz-opus-sonda)", relatório em `docs/evidence/v090-juiz-opus-sonda.md` e `.json`.

| Julgamento | `request_id` | Estado | Erro exposto | `usage` | Débito no ledger Anthropic |
| --- | --- | --- | --- | --- | --- |
| `eval_4d08e08503e34d5d9d26` | `req_eval0c6f7493f669` | failed | `LLMError: judge: BadRequestError: Error code: 400 - invalid_request_error: 'This API key is not scoped to a workspace,...'` | ausente | US$0,050256 (`settled`) |
| `eval_6eacab7c27ff4680b961` | `req_evalda08fa632aaf` | failed | idem | ausente | US$0,046432 (`settled`) |
| `eval_149a7843622e4fd0ae99` | `req_eval4e3529ab6de2` | failed | idem | ausente | US$0,047440 (`settled`) |

Classificação: não é recusa, nem corte por `max_tokens`, nem falha de esquema. A API rejeitou a requisição (HTTP 400) pela configuração da chave: a chave do `.env` não está associada a um workspace. É ambiente e credencial, portanto **bloqueado**, e não defeito do candidato. Não há tokens nem custo real por julgamento a medir, nem projeção para 72. Por isso o momento 2 não foi iniciado: com essa chave, os 72 julgamentos falhariam e debitariam cerca de US$3,46 do cap só em reservas.

## Momentos 2 e 3

- **Momento 2** (`--judge-repeat 3 --name v090-juiz-opus-r3`): não executado; depende da sonda. Não existem `v090-juiz-opus-r3.*` nem `v090-juiz-opus.md`.
- **Momento 3, comparação com `--judge`:** não executado; sem julgamentos Opus completos não há o que comparar.
- **Momento 3, regressão sem `--judge` (sem custo), executada:**

  ```text
  RUNTIME_DIR=.pytest_cache/qa-v080-r1/runtime BUDGET_RUNTIME_DIR=data/runtime/anthropic BUDGET_LIMIT_USD=4.00 \
  merchant-assistant eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv --rater lauro \
    --out .pytest_cache/qa-v090-control/v080-calibracao-regressao.md
  ```

  Saída: "calibrations: 0 stored, 24 updated, 0 skipped (campaign v080-all-r3, rater lauro)". Contra `docs/evidence/v080-calibracao.md`, o `diff` só mostra a linha "Gerado em" (data) e o parágrafo de disclosure escrito à mão. Fica **idêntico**, como esperado. Em `calibrations` mudou só `created_at` nas 24 linhas (de `2026-11-05T16:12:14+00:00` para `2026-11-05T20:57:44+00:00`). Notas, vereditos, notas de texto e `evaluation_id` ficaram iguais (comparação coluna a coluna contra o backup). O valor original de `created_at` está no backup.

## Regra D2

Não aplicável nesta rodada: não há julgamento Opus completo. As condições (a) ±1 por critério, (b) `unsupported_claim` > 0,667 com ≥ 2 de S01, S13, S16 e S21 marcadas e (c) consistência exata ≥ 0,70 ficam **não verificadas**.

## Ledgers e custos

| Ledger | Antes | Depois | Delta |
| --- | --- | --- | --- |
| Anthropic `data/runtime/anthropic/budget.sqlite3` | não existia | 3 lançamentos `judge`/`claude-opus-5-5`, `settled`, total US$0,144128; `.limit` = 4.0 | +US$0,144128 (só a sonda; o `eval-calibrate` não lança) |
| Projeto `data/runtime/budget.sqlite3` | 3632 lançamentos, US$1,402518, 0 `claude%` | idem | 0 |

Tokens totais: 0 registrados (os 3 julgamentos falharam sem `usage`). O débito de US$0,144128 é a reserva conservadora do julgamento sem `usage` (P3-1 da rodada 1 do Reviewer), lançada como `actual_usd` = `reserved_usd`. Um 400 de requisição inválida normalmente não é cobrado pela Anthropic. O responsável pode confirmar no console. Em todo caso, o cap gravado ao lado do ledger já conta esse valor: sobram US$3,855872 para a próxima tentativa.

## Achados e limitações

- **Bloqueio (ambiente/credencial):** a chave Anthropic do `.env` é recusada com 400 "not scoped to a workspace". Corrigir a credencial cabe ao responsável (AGENTS.md, "Autorização por versão"). O QA não leu nem alterou a chave.
- **Observação (atrito para o operador):** a mensagem de erro chega truncada ("…") no relatório e no banco, então a causa completa da API não aparece na CLI. O trecho visível bastou para classificar.
- **Observação:** o JSON da sonda traz `passed: 1.0` e `cost_usd: 0` no resumo, com `judge_failed: 3`. O Markdown diz "3 julgamentos falharam e ficaram fora das médias". O custo exibido (0) difere do débito no ledger (US$0,144128), pela mesma razão do P3-1.
- **Observação:** rodar `eval-calibrate --import` sem `--judge` regrava `created_at` das notas humanas. É inofensivo para o relatório, mas a data original só fica no backup.
- **Evidência gerada:** `docs/evidence/v090-juiz-opus-sonda.json` e `.md` (3 falhas). Os 3 julgamentos falhos ficam no banco sob a execução `v090-juiz-opus-sonda`. Eles não entram no `eval-calibrate --judge-run v090-juiz-opus-r3`, mas repetir a sonda com o mesmo nome sobrescreveria o relatório e fundiria as execuções (P2-4).
- Nenhum arquivo de evidência contém caminho pessoal (conferido nos dois arquivos da sonda e neste).

## Como terminou

O responsável queria ver o Opus julgar as mesmas 24 respostas que ele já avaliou. Na primeira tentativa, a Anthropic recusou a chave antes de qualquer julgamento: nenhuma nota foi produzida e nenhuma foi inventada. Os três julgamentos aparecem como falhos no relatório da sonda. As 24 notas humanas e os julgamentos DeepSeek continuam intactos, e o relatório da v0.8.0 sai igual. O experimento ainda não começou de fato.

## Próxima ação e responsável

1. **Responsável:** emitir ou ajustar a chave Anthropic para que ela pertença a um workspace com crédito (console Anthropic) e atualizar o `.env`. Alterar credenciais exige decisão humana.
2. **Supervisor:** decidir o nome da nova sonda. Pela regra do P2-4, o QA copia `v090-juiz-opus-sonda.*` para `-original` antes de reutilizar o nome, ou usa um nome novo (por exemplo `v090-juiz-opus-sonda2`). Também decide se a margem de US$3,60 para 3 repetições continua valendo, já que o cap restante é US$3,855872. Depois disso, o QA retoma pelo momento 1 com o mesmo ledger (`BUDGET_RUNTIME_DIR=data/runtime/anthropic`, sem elevar o teto).

## Decisão humana pendente

Credencial Anthropic (item 1), porque credenciais estão fora da autorização por versão.
