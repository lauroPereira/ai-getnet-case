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

## Rodada 2 — candidato `663ce0982b4648736196e99de2a3216601e6bb09` (r6)

**Parecer: apto para QA.** Os dois P2 da rodada 1 corrigidos, sem regressão; nenhum P1 ou P2 novo; quatro P3 registrados. Contexto frio mantido (sem `v080-developer.md`; tarefas só até "## Validação"; holdout só por blob e hash).

### Candidato e hashes
HEAD `eee8348`; diferença para `663ce09` só em `documentation_only_after_pin`. Tree `eedbb12e…6aff`, 97 blobs e fingerprint `6e3d6c20…9c42` conferem antes e depois. Holdout blob `22dfee8b…af9d` em `94bf7b3`, `663ce09` e HEAD. Sem mudança em `tests/scenarios/*.jsonl`, `prompts/`, `data/` e `cli.py`.

### Suíte
`lint_and_tests.py --strict` em cópia `git archive 663ce09`: 1.340 passed e 1 skipped em 781 s (o skip exige basetemp dentro de `.pytest_cache`; isolado, passou: total 1.341, igual ao manifesto); Ruff e skills ok; exit 0. Uma execução com basetemp POSIX foi descartada (erros de ambiente).

### Achados da rodada 1
| Achado | Situação | Re-derivação |
| --- | --- | --- |
| P2-75 | corrigido | 22 ressalvas honestas EN/PT (U+2019, U+2018, U+02BC; "does not mean/establish", "não significa que", "não há como saber se", "não é possível afirmar que", "no evidence that") dão `forbidden_ok=True` (21 falhavam no runner antigo); 29 contradições continuam recusadas, inclusive ressalva seguida de afirmação. |
| Re-pontuação | sem mudança | 195 respostas (`v080-healthy-r4.json`, `v080-all-r3.json`) com `_checks` de `94bf7b3` e `663ce09`: 0 checagens mudam; 80 U+2019 e 10 travessões exercitados. |
| P2-76 | corrigido | 16 frases mantêm a decisão do modelo ("fechar contrato com a Getnet", "close the contract", "Finalize o contrato", "How do I close my contract?"…); 12 vão a `human_handoff`/`contract` (possessivos EN/PT, "end the contract", "Rescindir o contrato"). O código antigo errava 12/16. |
| P3-76 | corrigido | `router.py:96-97`: nota `rule` só quando a regra muda a rota. |
| P3-77b | corrigido | Blob LF `570ac505…e607` = `procedure_sha256` gravado a partir da cópia CRLF. |
| P3-77d | corrigido | Sem a conferência de `:263-265`, o teste novo falha. |
| P3-75, P3-77a, P3-77c, P3-77e | abertos | fora do delta. |

Ensaio da transição em ledgers sintéticos no scratchpad: dry-run sem escrita; `--apply` eleva 1,70→2,00 e 1,10→1,40, entradas, comprometidos e reservas inalterados, SHA-256 lógico igual, bytes do primário idênticos, `already_applied` na repetição. Diff do script restrito a `_source_sha256` e sua chamada.

### Achados novos
- **P3-R2a.** As janelas `[^.!?;,]{0,100}$` de `runner.py:53`, `:56`, `:73` e `:82` passaram a valer para mais formas: uma afirmação posterior na mesma oração ligada por "e/and/porque/senão que" vira ressalva. Reprodução (aceitas no novo, recusadas no antigo): "Não é possível afirmar que houve erro e a taxa está correta."; "Não posso afirmar outra coisa senão que a taxa está correta."; "Não podemos dizer que houve falha porque a taxa está correta."; "It is not possible to establish that there was a problem and the fee is correct."; "It is unclear whether you saw it and the fee is correct.". Construção improvável, juiz cobre, mas um `passed` determinístico falso pode inflar CA-51. Sugestão: exigir adjacência (`que\s+$` / `that\s+$`), como em "não significa que". De preferência antes do holdout.
- **P3-R2b.** Sem teste: travessão em `_CLAUSE_BOUNDARIES` (`:44`) e "don't/doesn't know whether".
- **P3-R2c.** `translate` dos termos de `must_include_any`/`must_not_include` sem teste; efeito colateral aceitável ("status `solicitado`" com crase satisfaz `'solicitado'`). Efeito no holdout não verificado (exigiria abrir o conteúdo).
- **P3-R2d.** Troca de `_source_sha256` por `_file_sha256` só é detectada em checkout CRLF.

### Mutações
24 em cópias separadas: 18 detectadas; sobreviventes cobertos pelos P3 acima.

### Próxima ação
Supervisor aplica a transição da tarefa 77 e segue para o QA; P3-R2a antes do holdout.

## Rodada 3 — candidato `658c70adc69cb956c931737b8a1caf38ed638dd5` (r7)

**Parecer: apto para QA.** P3-R2a e P3-R2b corrigidos, sem regressão; nenhum P1 ou P2 novo; três P3 menores. Contexto frio mantido.

- **Hashes:** HEAD `3e7b09d`; diferença para `658c70a` só o manifesto r7. Tree `a5a2cd66…af9`, 97 blobs e fingerprint `3316002e…d2` conferem antes e depois. Holdout blob `22dfee8b…af9d` em `663ce09`, `658c70a` e HEAD. Delta restrito a `runner.py`, teste da tarefa 75, tarefa e docs.
- **Suíte** em cópia `git archive 658c70a`: 1.378 passed e 1 skipped em 695 s (skip isolado e passado: total 1.379, igual ao manifesto); Ruff e skills ok; exit 0.
- **P3-R2a corrigido:** 28 sondas de contradição (as cinco do parecer, variantes com "and/e/because", travessões U+2013/U+2014) todas recusadas no r7; o r6 aceitava 17. 35 ressalvas honestas adjacentes (três apóstrofos, "does not mean/establish that", "don't know whether", "unclear whether", "não significa que", "não há como saber se", "não é possível afirmar que", maiúsculas) continuam aceitas. As janelas de 100 caracteres remanescentes são exatamente as de `4c3c8a9` (`runner.py:57`, `:66`, `:69`, `:79`, `:88`, `:90`).
- **P3-R2b corrigido:** travessão como fronteira e "don't/doesn't know whether" testados nas listas positiva e negativa.
- **Re-pontuação:** 195 respostas (`v080-healthy-r4.json`, `v080-all-r3.json`), 0 de 1.755 checagens mudam.
- **Mutações:** 14 em cópia separada, 14 detectadas (adjacência `that\s+$`/`que\s+$`, lookaheads de say/dizer, travessões, formas novas).
- **Achados novos:** P3-R3a, ressalva com palavra intercalada ("not possible to confirm that indeed the fee is correct") agora recusada: erra na direção conservadora, sem efeito nas respostas arquivadas (`runner.py:62`, `:67`, `:85`). P3-R3b, comentário em `runner.py:50-54` impreciso ("not sure that" também passou a exigir adjacência). P3-R3c, "I can't say anything and the fee is correct." segue aceita pela janela antiga de say/dizer (`:69`, `:90`), como em `4c3c8a9`; o juiz cobre. Seguem abertos e fora do delta: P3-75, P3-77a, P3-77c, P3-77e, P3-R2c, P3-R2d.

### Próxima ação
Supervisor aplica a transição da tarefa 77 e despacha o QA r5 com o candidato r7.
