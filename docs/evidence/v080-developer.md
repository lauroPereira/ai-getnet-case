# Passagem do Developer: v0.8.0

## Tarefa 72a, rodada 1

- Papel e responsável: Developer do Time B (subagente), despachado pelo Supervisor.
- Objetivo e critérios: [tarefa 72a](../tasks/72a-holdout-respostas-v080.md), RF-92 e CA-50 da [spec 0.2](../specs/evolucao-pos-feedback.md), decisão técnica 15 do [plano](../specs/evolucao-pos-feedback-plano.md). Escrever e lacrar por hash o holdout de respostas antes de qualquer ajuste de prompt da v0.8.0, por quem não ajusta prompts.
- Escopo: arquivos novos `tests/scenarios/holdout_v080.jsonl`, `tests/scenarios/holdout_v080.sha256`, `tests/unit/test_holdout_v080.py`, `docs/evidence/v080-holdout-derivacao.md` e esta passagem; alterada só a tarefa 72a (Validação e Status). Nenhum arquivo do Time A tocado (`cli.py`, `evaluation/`, `orchestration/`, `api/`, `prompts/`), nenhum JSONL existente alterado. Repositório: `C:\workspace\ai-getnet-case-wt\time-b`.
- Estado: em andamento até a revisão; implementação concluída pelo Developer.
- Branch e PR: `codex/v0.8.0-avaliacao`, sem PR, sem push.
- Base e versão final: base `d7acaec`; versão final é o commit único desta tarefa, que traz esta passagem (SHA informado ao Supervisor no retorno). Hash do holdout: `4002fdc9b9efd667d253c5fe9ae6b48d7cd03eac6c489a0119984d8139e1e626` (SHA-256 do conteúdo UTF-8 com quebras normalizadas para `\n`; coincide com `sha256sum` do arquivo, que já está em LF).
- Independência: não-independente; é o próprio autor relatando. A revisão independente cabe ao Reviewer.

### Regra de autoria

`prompts/` não foi aberto. Também não foram abertos traces, avaliações nem respostas reais de modelo em `docs/evidence/`. As mensagens são paráfrases das páginas oficiais versionadas (`data/snapshots/public/pages/`, listadas em `data/sources/public-sources.json`), dos procedimentos de `data/knowledge-demo/` e dos fatos da seed. Os JSONL existentes serviram só para formato e para evitar repetição. Código lido para entender rótulos: `evaluation/runner.py` (`Case`, `load_cases`, checagens), `guardrails/output.py` (`amounts`), `tools/domain.py`, `tools/registry.py`, `data/seed.py`, `data/clock.py`, `testing.py`, `api/schemas.py` (rotas e status) e, por busca, a linha de passagem com o protocolo `SIM-` em `agents/escalation.py` e `agents/personality.py`.

### Evidência

- Composição: 25 casos, 13 pt (52%) e 12 en. Rotas: `knowledge` 6, `general_web` 2, `support` 10 (recebíveis, liquidação, dispositivo, autorização, contrato, preço ×2, cancelamento, habilitação, isolamento), `knowledge_and_support` 3, `human_handoff` 2, `out_of_scope` 2. Difíceis (`-HARD`): `HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD` e `HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD` (inglês sobre produto descrito só em português, sem o nome do produto), `HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD` (paráfrase distante) e `HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD` (duas intenções).
- Derivação: [v080-holdout-derivacao.md](v080-holdout-derivacao.md), com o comando em processo (seed, relógio `2026-10-26T10:00:00`, banco em `.pytest_cache/v080-b-holdout/`, `in_process_client()`), a saída de cada ferramenta e, para cada caso, a página oficial ou o procedimento demo com trecho curto.
- Teste de lacre: `tests/unit/test_holdout_v080.py`, 6 testes. Prova de violação: troquei um byte do JSONL (`smartphone` → `smartphonE`) e 2 testes falharam (`test_seal_matches_content` e `test_seal_ignores_line_endings_but_not_content`); com o arquivo restaurado, os 6 passaram e `sha256sum` voltou a `4002fdc9…e626`.
- Suíte estrita: `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v080-b-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` terminou com código 0, 355 testes aprovados em 231,95 s, ruff sem achados, estrutura e skills válidas. A primeira execução tinha 355 testes aprovados, mas terminou com código 1 por um SIM300 (comparação invertida) na linha 62 do teste novo. Corrigi a comparação antes da segunda execução.
- Ambiente: `.venv` do worktree, Python 3.13.3; `import merchant_assistant` resolve para `C:\workspace\ai-getnet-case-wt\time-b\src\merchant_assistant`. Nenhuma chamada paga, sem `.env`, sem Docker.

### Decisões além do texto do plano

- 25 casos em vez dos 24 sugeridos: o recebível líquido do débito ficou como caso próprio, para separar recebíveis de liquidação.
- Difíceis marcados pelo sufixo `-HARD` no id, porque o `Case` não tem campo `notes` e `load_cases` falharia com chave extra.
- Valores das páginas oficiais (R$ 50,00 mínimo de antecipação; R$ 1,00 por link pago) em `must_include_amounts` (5000 e 100), como os valores das ferramentas.
- Teste extra que refaz as chamadas às ferramentas sobre a seed e confere que todo valor de caso com ferramenta esperada sai delas. Ele prende o holdout à seed: se a seed mudar, o teste falha. Isso é intencional, porque nesse caso os rótulos ficariam velhos.
- Todos os casos usam `cliente1988`; o isolamento é testado pelo recurso de outro lojista citado na mensagem (`dev_002_tap01`), não por `user_id` trocado.

### Rótulos que julguei ambíguos (notas, não suposições)

1. `HV080-EN-SUP-PRICE-CREDIT-CONDITIONS`: a ferramenta retorna `different_conditions`. Rotulei `answered`, seguindo `V030-PRICE-CONDITIONS`. Porém o lojista reclama de cobrança maior, e o procedimento demo diz que "contrato e pricing incompatíveis exigem análise". Uma resposta com `handoff` é defensável e falharia em `status_ok`.
2. `HV080-PT-OOS-BUYER-PERSONAL-DATA`: rotulei `out_of_scope`/`refused` pelo RF-06 (dados de terceiros). Uma resposta `answered` dizendo que não há esses dados falharia.
3. `HV080-PT-SUP-FOREIGN-DEVICE`: rotulei `support`/`answered` sem dado alheio, como o UC-13. Uma recusa `out_of_scope` falharia.
4. `HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD`: exige "38" e "inicializa", das páginas de erro ADQ. O FAQ do crediário dá outro caminho de inicialização ("Suporte > Bandeiras > Funções Técnicas > Inicialização"), sem "38". Uma resposta que use só esse caminho falha no primeiro grupo.
5. `HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD` e `HV080-EN-SUP-PAYOUT-LINK-SALE` exigem `get_payout_status` além da agenda. Uma resposta que conclua "pago" só pelo `SETTLED` da agenda falha em `tools_ok`.
6. `HV080-EN-KS-WIFI-NEW-PASSWORD` aceita só `knowledge_and_support`, como o UC-05.

### Limitações

- Checagens por substring: `must_not_assert` só neutraliza as formas de incerteza listadas no runner. Uma negação como "não há confirmação de que o dinheiro já voltou para o cartão" seria marcada indevidamente em `HV080-PT-SUP-CANCELLATION-REFUND`. Valores oficiais só contam com prefixo `R$` ou `BRL` (por exemplo, "50 reais" não conta).
- `HV080-PT-SUP-PRICE-LINK-CONSISTENT` exige que o agente descubra a data da venda pela agenda, porque `simulate_pricing` não filtra por canal. "Semana passada" corresponde a 6 dias antes, e com `SystemClock` a expressão nem sempre é exata.
- Na campanha real o relógio é o do sistema: as datas mudam, os valores não. "Agora há pouco" depende do evento em `now − 3h10`.
- As páginas oficiais têm taxas conflitantes (por exemplo, débito do Get Tap a 1,69% numa página e 0,99% em outra). Por isso evitei perguntas de taxa pública.
- O holdout ainda não foi rodado contra nenhum modelo; nenhuma medição foi feita.

### Critérios

- Comprovados localmente: ≥ 20 casos e ≥ 50% em pt; rotas cobertas; 4 difíceis marcados; derivação reproduzível; teste de lacre passa e falha com um byte alterado; suíte estrita com código 0; nenhuma chamada paga; `prompts/` não foi aberto.
- Não verificados: comportamento do sistema real no holdout (campanha do QA na v0.8.0).

### Ação externa, identidade e próxima ação

- Ação externa: nenhuma (sem push, sem PR). Commit local único com identidade `lauroPereira <lauro.s.pereira@gmail.com>`, conferida no worktree.
- Próxima ação: o Supervisor despacha o Reviewer independente para a 72a. Depois da aprovação, o holdout fica congelado. Recomendo que quem ajustar prompts na 72b não leia o conteúdo do JSONL, para cumprir "nunca usado em ajuste".
- Decisão humana pendente: nenhuma para esta rodada. As notas de rótulo ambíguo acima ficam para o Reviewer e o Supervisor decidirem se mantêm o rótulo, sabendo que qualquer mudança exige novo hash antes da campanha.

## Tarefa 72a, rodada 2

- Papel e responsável: Developer do Time B, sobre o [parecer do Reviewer, rodada 1](v080-reviewer.md) (correções necessárias: 1 P1, 4 P2, 4 P3).
- Escopo: `tests/scenarios/holdout_v080.jsonl` (só rótulos; mensagens, ids, idiomas e valores iguais), `tests/scenarios/holdout_v080.sha256`, `tests/unit/test_holdout_v080.py`, `docs/evidence/v080-holdout-derivacao.md`, a tarefa 72a e esta passagem. `prompts/` continua sem ser aberto.
- Estado: correções implementadas; em andamento até a revisão da rodada 2.
- Base e versão final: base `2c0fc0f`; versão final é o commit único desta rodada, que cita o novo hash. Hash novo `a3e7342ea15854356c5378b7ba00bb6c6cd58319d7d610bceb3cd2a5e099653d` (antes `4002fdc9…e1e626`).
- Independência: não-independente (relato do autor).

### Correções

- **P1-1:** `HV080-PT-HANDOFF-CALLBACK` e `HV080-EN-HANDOFF-END-AGREEMENT` exigem `["HO-"]`, sem `SIM-`.
- **P2-1** (os termos positivos deixaram de aprovar a conclusão oposta):
  - `PRICE-LINK-CONSISTENT`: termos como "mesmo valor", "sem divergência", "está correta", "bate com"; `must_not_assert` com "não está correta", "não confere", "não bate", "cobrança a mais" e semelhantes.
  - `PRICE-CREDIT-CONDITIONS`: removido o "differ" solto; proibidos "overcharged", "charged more than", "you will be refunded", "the fee is correct" e "conditions match".
  - `CANCELLATION-REFUND`: proibições com o sujeito colado ("cancelamento foi concluído", "valor foi devolvido", "venda foi estornada"). A forma sugerida pelo parecer ("foi concluído") reprovaria a resposta certa "ainda não foi concluído", porque o runner não neutraliza "ainda não".
  - `ENABLEMENT-MASTERCARD-DEVICE`: removidos "update" e "initializ"; proibidos "can accept mastercard" e "can already accept". "cannot accept" não contém "can accept".
  - `PIX-PAID-AND-ADVANCE-HARD`: removidos "caiu" e "pago" soltos; proibidos "ainda não caiu", "não foi creditado", "não foi pago" e semelhantes.
- **P2-2:** `FOREIGN-DEVICE` exige negativa de acesso ("não pertence", "não tenho acesso", "não consigo consultar"…). Proíbe "Android 14" e "9 min", e afirmar que `dev_002_tap01` ou "ela" está ligada, online ou conectada. Não proibi "está online" solto porque a resposta certa pode dizer que a Get Smart do próprio lojista "não está online".
- **P2-3:** `DEVICE-SIGNAL` aceita "não está conectada"/"não está online"; `SAME-DAY-REVERSAL` aceita "day of the", "that day", "today"; `CONTRACT-SETTLEMENT` aceita "dia útil seguinte", "dia seguinte", "próximo dia útil".
- **P2-4:** o teste normaliza para LF antes de gerar a variante CRLF. Converti o JSONL de fato para CRLF e os 8 testes passaram; com um byte alterado, 2 falharam; o arquivo foi restaurado (`sha256sum` = hash novo). O `.gitattributes` não foi alterado: está fora dos arquivos permitidos, e o teste já não depende dele.
- Verificação dos rótulos: as 26 respostas sintéticas (certas e erradas, incluindo os exemplos do parecer) foram passadas por `_checks` do runner, sem modelo: 0 divergências.

### Decisões sobre os P3

- **P3-1, corrigido:** o teste agora deriva os valores das chamadas de cada caso (`TOOL_DERIVATION`) e confere os valores de conhecimento na página oficial versionada com o trecho (`SOURCE_DERIVATION`: "o valor mínimo para antecipação é de R$50,00" → 5000; "R$1,00 por link pago" → 100). Outro teste exige que todo caso com valor tenha derivação.
- **P3-2, mantido:** a sobreposição com os casos dev é de cenário, não de texto, e cobre os usos mais frequentes. Recomendo reportar o holdout por caso e marcar esses quatro (`CREDIT-DECLINE-NOT-DEVICE`, `WIFI-NEW-PASSWORD` e os dois web) ao ler o resultado.
- **P3-3, corrigido:** `WHATSAPP-PAY-MIGRATION` aceita `knowledge` e `knowledge_and_support`.
- **P3-4, corrigido:** `RECEIVABLE-DEBIT-NET` não exige ferramenta específica, porque o valor 14806 só vem de dado do lojista; `PHONE-AS-TERMINAL` aceita "Android version 12", "version 12 of Android" e "Android OS 12".

### Ausência de ajuste de prompt

`git log --oneline 07ca28e..main -- prompts/` → nenhum commit (a `main` está em `07ca28e`). `git log --all --oneline 07ca28e.. -- prompts/` → nenhum commit em nenhuma branch. O re-lacre ocorre antes de qualquer ajuste de prompt da v0.8.0.

### Evidência

- Suíte estrita: `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v080-b-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` → código 0, 357 aprovados (355 + 2 testes novos de derivação), ruff limpo.
- Composição inalterada: 25 casos, 13 pt, 12 en, 4 `-HARD`.

### Limitações

- O `must_not_assert` do runner só neutraliza as formas de incerteza da sua lista. "Não há confirmação de que o valor foi devolvido" e "não consigo dizer se ela está ligada" ainda seriam marcadas. Os termos foram escolhidos para que as respostas certas mais prováveis não os contenham, mas o risco não é zero.
- Comportamento real do modelo não verificado (sem chamada paga).

### Próxima ação

O mesmo Reviewer revê na rodada 2 os casos alterados, o teste e o novo lacre.

## Tarefa 72a, rodada 3

- Papel e responsável: Developer do Time B, sobre o [parecer do Reviewer, rodada 2](v080-reviewer.md) (P2-5 novo; P3-5, P3-6 e P3-2).
- Escopo:
  - Rótulos de 6 casos em `tests/scenarios/holdout_v080.jsonl`: linhas 4 e 14 a 18. Mensagens, ids, idiomas, rotas, status e valores ficaram iguais.
  - Também `holdout_v080.sha256`, `docs/evidence/v080-holdout-derivacao.md`, a tarefa 72a e esta passagem.
  - O teste e `evaluation/` não foram alterados, e `prompts/` continua sem ser aberto.
- Base e versão final: base `e1886ed`; commit único da rodada, citando o hash novo `46474c0aa38ca2a828493a4d000844e10882d7098cf519d87922de594ccfd0ff` (rodada 2: `a3e7342e…099653d`).
- Independência: não-independente (relato do autor).

### P2-5

- **Diagnóstico:** `_assertion_is_present` corta orações em vírgula, ponto e vírgula e "mas", e só desconta qualificadores fixos. Uma resposta cautelosa que nega a afirmação proibida com outro lead-in ("não houve", "não há confirmação de que", "não posso afirmar que", "não tenho acesso para informar se", "does not mean", "can't promise", "once … it can") era reprovada como falha crítica.
- **Âncoras afirmativas não servem:** testei a sugestão "sim, "/"yes, ". Ela não funciona, porque a vírgula separa a âncora da afirmação; essas entradas nunca disparariam. Por isso não as mantive.
- **Regra adotada:** em `must_not_assert`, só conclusões erradas de polaridade negativa, que a resposta certa não contém. Isso vale só para o caso 14: "não está correta", "não está coerente", "não é coerente", "a taxa não confere", "a taxa não bate". Nos casos 15 a 18, a lista ficou vazia; a conclusão errada afirmativa fica para o grupo positivo e para o juiz.
- **Caso 18:** mantém `must_not_include` "Android 14" e "9 min" e a negativa de acesso obrigatória.
- **Caso 14:** o grupo positivo ganhou "a mesma" e "mesma taxa".

### P3

- **P3-5, corrigido:**
  - Caso 4 sem "today" e "that day" soltos (ficaram "same day", "day of the transaction/sale/purchase", "that same day", "only today"…).
  - Caso 17 sem "not yet" solto (ficaram "not yet available", "not yet enabled", "cannot accept mastercard yet"…).
- **P3-5, mantido:** a resposta mista do caso 16 ("cancelamento aprovado… status solicitado") não tem como ser pega por substring sem reprovar respostas certas. Fica para o juiz.
- **P3-6, aceito:** o vínculo do valor é por caso, sustentado pela tabela da derivação.
- **P3-2:** sobreposição de cenário segue registrada.

### Bateria pelo `_checks` real (sem modelo)

- **Rodada 3:** 40 respostas para os casos 4 e 14 a 18 e o Pix.
  - 22 certas, com os lead-ins de negação pedidos: 22/22 passam.
  - 18 erradas: 17/18 reprovam. A que passa é "Sim, o dinheiro já voltou para o cartão do cliente; o status é solicitado." (caso 16).
- **Bateria da rodada 2 refeita:** 26 respostas, 25 com o resultado esperado. A diferença é "Não pertence a você, mas ela está ligada." (caso 18), que agora passa. É o custo de não reprovar a resposta certa "não tenho acesso para informar se ela está ligada".

### Evidência

- Suíte estrita (`--basetemp .pytest_cache/v080-b-strict`) → código 0, **357 aprovados**, ruff limpo. O lacre confere com o hash novo.
- `git log --all --oneline 07ca28e.. -- prompts/` → nenhum commit.

### Limitações

Checagem por substring tem teto: duas respostas erradas mistas passam, e o juiz independente da v0.8.0 cobre esse resíduo. A alternativa seria mudar o runner (`evaluation/`), que é do Time A e está fora desta tarefa.

### Próxima ação

O mesmo Reviewer revê, na rodada 3, os casos 4 e 14 a 18 e o lacre.
