# Revisão independente do candidato r5 da v0.8.0 (tarefas 75 a 77)

Reviewer nativo do Claude Code (`opus`/`high`) em contexto frio, 2026-11-05. Não leu a passagem do Developer; leu as tarefas só até "## Validação"; do holdout usou apenas hash e `git rev-parse`.

## Rodada 1 — candidato `94bf7b3b6e0ac44167878fad5bb12765726a51f8`

**Parecer: correções necessárias.** Nenhum P1; dois P2 (tarefas 75 e 76). A tarefa 77 está apta.

### Candidato e hashes
Tree `1b1b7310…554e` confere com o manifesto `v080-candidato-r5.json`; 97 arquivos de `files_sha256` conferem com os blobs; fingerprint recalculado `80527de4…b778` confere, antes e depois da revisão. Holdout: blob `22dfee8b…af9d`, igual em `9057aaa`, `94bf7b3` e HEAD; SHA-256 LF `91aa5158…4f1bac`. `prompts/` e `data/` sem mudança no delta.

### Comandos e números
- Suíte estrita em cópia `git archive 94bf7b3`, basetemp novo: **1.247 passed** em 644 s; Ruff e skills ok; exit 0.
- Travas de D18 na mesma cópia: 470 testes, todos verdes (história, webhooks, retomada e encaminhamentos da v0.7.0; outbox; jornadas, replanejamento e história da v0.8.0; regras do replanner; T76; orçamento e router).
- Ledgers reais (`data/runtime/budget*`) com SHA-256 idêntico antes e depois; árvore versionada limpa.

### Tarefa 75 — rótulos `PRICE-INSUFFICIENT`
Re-derivação: 146 respostas arquivadas pontuadas com `runner._checks` nos rótulos de `4c3c8a9` e de `94bf7b3`; mudam exatamente as quatro `request_id` da tarefa, só em `content_ok`; nenhum `forbidden_ok` muda; as 12 respostas desses IDs passam. As quatro respostas foram lidas e julgadas corretas (D15 cumprido). Catálogo sem `V030-*`: não há espelho. 25 sondas de contradição recusadas; ressalvas legítimas passam.

- **P2-75.** As asserções novas de `must_not_assert` ("the fee is incorrect", "the fee was charged correctly", "the fee is wrong", "a taxa está incorreta", "a taxa cobrada está correta", "há divergência na taxa"; `tests/scenarios/business_journeys.jsonl:4` e `:11`) transformam ressalvas honestas em falha crítica (`forbidden_ok`). Os prefixos qualificadores em `src/merchant_assistant/evaluation/runner.py:47-62` só reconhecem apóstrofo reto e não cobrem "does not mean/establish that", "não significa que", "não há como saber se", "não é possível afirmar que". Reprodução: "…so I couldn’t confirm whether the fee was charged correctly." (U+2019) passa a `forbidden_ok=False`; idem "This does not mean the fee is incorrect.", "Isso não significa que a taxa está incorreta.", "…não é possível afirmar que há divergência na taxa.". Correção sugerida: normalizar U+2019 e cobrir as formas negativas em `_assertion_is_present`, ou trocar as asserções ambíguas; testes com ressalvas tipográficas e negativas. `runner.py` também pontua o holdout.
- **P3-75.** Lacunas literais preexistentes: "…the fee matches the plan." e "…mas a taxa confere com o plano." passam como corretas; o juiz cobre.

### Tarefa 76 — Router e encerramento de contrato
Re-derivação: regra em `router.py:22-34` e `:46-47`; `router.v6` intacto; 37 sondas (positivos EN/PT vão a `human_handoff`; perguntas, menção a serviço/produto, negações, pedidos mistos, conversa com histórico e `safety` mantêm o comportamento anterior); ponta a ponta com Router programado devolve `handoff` com `HO-`.

- **P2-76.** A regex (`router.py:26`, `:31-32`) aceita `fechar|feche|finalizar|finalize` sem possessivo e "close the contract": "Quero fechar contrato com a Getnet.", "Gostaria de fechar contrato.", "Quero finalizar o contrato.", "I want to close the contract." viram `human_handoff` com protocolo, sobrepondo uma decisão correta do modelo (`contract_signup`). Contraria a decisão do Supervisor ("pedido explícito de encerramento"). Correção sugerida: tirar essas formas sem possessivo ou exigir `meu`/`nosso`; avaliar "close the contract" sem my/our; acrescentar aos `NOT_EXPLICIT`.
- **P3-76.** O trace não registra quando a regra atua (`router.py:106-114`); sugestão `step_notes["rule"] = "contract_termination"`. Nota: `safety == "none"` em `:46` é redundante (mutante equivalente), não é defeito.

### Tarefa 77 — teto de contingência
0,50/1,00/1,10 inalterados; 1,40 exige estimativa revalidada em (1,00; 1,10], cap persistido e primário cobrindo; nunca monta campanha nova; guardas de `27add60` e `f8daab0` preservadas. Ensaio da CLI sobre cópias dos ledgers reais: 13 casos, todos com o resultado esperado (recusa com cap em 1,10 apontando a transição; recusa sem cap; recusa com primário 1,70; aceita 1,40 após transição com folga 0,81835345; recusa 1,10, 1,00, sem estimativa, estimativa r2, estimativa fora da faixa). Ensaio da transição em `.pytest_cache/rev-t77-rehearsal-20261105/`: dry-run não escreve; `--apply` eleva primário 1,70 → 2,00 (sidecar LF preservado) e campanha 1,10 → 1,40 (sidecar CRLF preservado, registro `v080-qa`), 2.733 e 1.117 entradas inalteradas, comprometidos 1,14385079 e 0,58164655 inalterados, 0 reservas, SHA-256 lógico igual (`845ee88e…6181`, `9fae30f5…e100`); nova execução `already_applied`; recusa com reserva aberta, processo ativo ou mesmo arquivo nos dois papéis; bytes do primário idênticos; no `iterdump` da campanha só a linha do cap muda.

- **P3-77a.** A checagem prévia lê o sidecar primário e ignora `BUDGET_LIMIT_USD`; o QA define o limite por processo conforme a fase.
- **P3-77b.** `procedure_sha256` em `prepared.json` registra os bytes CRLF da árvore (`366e4f2c…4e14`); o blob LF é `ecefa4e5…51c9`. Normalizar ou anotar.
- **P3-77c.** A folga do primário só é conferida depois da escrita.
- **P3-77d.** A conferência lógica dos backups não tem teste (mutação M17 sobrevive).
- **P3-77e.** Cap 0,50 após a transição termina com `ValueError` em vez de `SystemExit` (preexistente).

### Mutações manuais
17 mutações em cópia separada: 15 detectadas (M2–M16), 2 sobreviventes (M1 equivalente; M17 sem teste).

### Próxima ação
Developer corrige P2-75 e P2-76 com testes novos; P3 a critério. Revisão curta só do que mudar (runner e rótulos, regex do Router) e suíte estrita. A transição da tarefa 77 pode ser aplicada pelo Supervisor com o candidato corrigido aprovado.
