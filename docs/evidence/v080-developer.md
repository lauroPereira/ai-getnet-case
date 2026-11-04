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

## Tarefa 72a, rodada 4

- Papel e responsável: Developer do Time B, sobre o [parecer do Reviewer, rodada 3](v080-reviewer.md) (P2-6; P3-7 aplicado por decisão do Supervisor).
- Escopo: rótulos dos casos 14, 15, 16 e 18 em `tests/scenarios/holdout_v080.jsonl`, `holdout_v080.sha256`, `docs/evidence/v080-holdout-derivacao.md`, a tarefa 72a e esta passagem. Teste, `evaluation/` e `prompts/` intocados; `prompts/` continua sem ser aberto.
- Base e versão final: base `a113720`; commit único da rodada, citando o hash novo `115728126d2a3d6b2d62f63b61cafbb45823f4cbf57d211cb7a03d8afeff1bac` (rodada 3: `46474c0a…ccfd0ff`).
- Independência: não-independente (relato do autor).

### Correções

- **Caso 14:** `must_not_assert` = "não está correta", "não está coerente", "não é coerente", "não confere", "não bate". Todas têm polaridade negativa.
- **Caso 15:** segundo grupo obrigatório de ressalva: "analysis", "analyse", "analyze", "review", "can't say", "cannot say", "can't confirm", "cannot confirm", "can't determine", "cannot determine", "does not mean", "doesn't mean", "not necessarily", "before saying", "before confirming", "not clear", "unclear". Os dois últimos são acréscimo meu, porque "it is not clear that the fee is correct" é resposta certa da bateria.
- **Caso 16:** segundo grupo obrigatório de não-confirmação: "ainda não", "não foi concluído", "não há confirmação", "sem confirmação", "não foi confirmado", "não posso afirmar", "não consta", "não confirma", "não foi processado", "sem processamento".
- **Caso 18 (P3-7):** `must_not_include` = "Android 14", "9 min", "Get Tap", "dados móveis". As respostas certas da bateria continuam passando.

### Bateria pelo `_checks` real (sem modelo)

- **Rodada 4:** 51 respostas, somando a bateria da rodada 3, as erradas listadas no parecer e novas certas.
  - Certas: 26/26 passam.
  - Erradas: 25/25 reprovam. Isso inclui "A taxa cobrada de R$ 15,75 não bate com o plano; houve cobrança a mais.", "Yes, you were overcharged… You will be refunded.", "Sim, o dinheiro já voltou para o cartão do cliente; o status é solicitado." e "Não pertence a você, mas aparece como Get Tap online em dados móveis."
- **Bateria da rodada 2 refeita:** 25/26. O único resíduo é "Não pertence a você, mas ela está ligada.", resposta mista do caso 18 que fica para o juiz, como aceito no parecer.

### Prompts

O critério desta vez não deu vazio:
- `git log --all --oneline 07ca28e.. -- prompts/` → um commit, o `868a07f`, "feat(hitl): interrupt and resume the flow by the operator (task 65)", do Time A, na branch `codex/v0.7.0-identidade-hitl`. Ele acrescenta `prompts/escalation.v2.md` e `prompts/personality.v4.md`; vi só os nomes, pelo `--name-status`, sem abrir os arquivos.
- `git log --oneline 07ca28e..main -- prompts/` → nenhum commit.

Leitura: é mudança de prompt da v0.7.0 (HITL), feita por quem não escreveu nem leu o holdout, e não é ajuste da v0.8.0. O RF-92 continua atendido. Registro o fato para o Supervisor decidir se a condição de lacre precisa citar a base `07ca28e..main`, em vez de `--all`.

### Evidência

- Suíte estrita (`--basetemp .pytest_cache/v080-b-strict`) → código 0, **357 aprovados**. O lacre confere com o hash novo.

### Próxima ação

O mesmo Reviewer revê na rodada 4 os casos 14, 15, 16 e 18 e o lacre.

## Tarefa 72a, rodada 5

- Papel e responsável: Developer do Time B, sobre o P3-8 do [parecer da rodada 4](v080-reviewer.md) (apto para QA) e a decisão do Supervisor de aplicá-lo antes do lacre definitivo.
- Escopo:
  - Segundos grupos dos casos 15 e 16 em `tests/scenarios/holdout_v080.jsonl`.
  - `holdout_v080.sha256`, a derivação, a tarefa e esta passagem.
  - Mensagens, ids, valores, teste, `evaluation/` e `prompts/` intocados.
- Base e versão final: base `aed374a`; commit único citando o hash novo `acb512cadcce37ed5d7f69c46053e8d389276a8559c77412b874b7306a0c66c8` (rodada 4: `11572812…eff1bac`).
- Independência: não-independente (relato do autor).

### Mudanças

- **Caso 15:** + "directly comparable", "not comparable". "check" e "flagged" ficaram de fora, porque reabririam respostas erradas. A certa "I've flagged it for the team to check" fica para o juiz, como no parecer.
- **Caso 16:** + "pendente de processamento", "não volta", "não voltou", "só acontece depois", "só ocorre depois", "após o processamento".

### Bateria pelo `_checks` real (sem modelo)

- **Rodada 5:** 55 respostas, a bateria da rodada 4 mais as quatro certas do P3-8.
  - Certas: 30/30 passam.
  - Erradas: 25/25 continuam reprovando.
- **Bateria da rodada 2:** 25/26. O resíduo continua sendo "Não pertence a você, mas ela está ligada.", aceito para o juiz.

### Evidência

- `git log --oneline 07ca28e..codex/v0.8.0-avaliacao -- prompts/` → nenhum commit.
- Suíte estrita (`--basetemp .pytest_cache/v080-b-strict`) → código 0, **357 aprovados**. O lacre confere com o hash novo.

### Próxima ação

O Reviewer faz a revisão curta dos casos 15 e 16 e do lacre. Em seguida, o Supervisor declara o lacre definitivo.

## Tarefa 72a, rodada 6

- Papel e responsável: Developer do Time B, sobre o [parecer da rodada 5](v080-reviewer.md). É a última rodada; nenhum outro termo mudou.
- Escopo:
  - Segundos grupos dos casos 15 e 16 em `tests/scenarios/holdout_v080.jsonl`.
  - `holdout_v080.sha256`, a derivação, a tarefa e esta passagem.
  - Mensagens, ids, valores, teste, `evaluation/` e `prompts/` intocados.
- Base e versão final: base `f1b2f9f`; commit único citando o hash novo `91aa51588afdf4afccb1ea8f230a47d3d61686004ec599f4c547e7881b4f1bac` (rodada 5: `acb512ca…0c66c8`).
- Independência: não-independente (relato do autor).

### Mudanças

- **Caso 15:** "directly comparable" foi trocado por "not directly comparable", "aren't directly comparable" e "isn't directly comparable". "not comparable" ficou.
- **Caso 16:** "após o processamento" saiu do segundo grupo.

### Bateria pelo `_checks` real (sem modelo)

- **Rodada 6:** 57 respostas, a bateria da rodada 5 mais as duas erradas novas do parecer ("O dinheiro já voltou ao cartão do cliente após o processamento; o status ainda aparece como solicitado." e "The legacy and standard fees are directly comparable: R$ 37,80 versus R$ 36,00, so you were overcharged.").
  - Certas: 30/30 passam, inclusive as quatro do P3-8 ("aren't directly comparable", "not comparable", "só acontece depois", "pendente de processamento").
  - Erradas: 27/27 reprovam.
- **Bateria da rodada 2:** 25/26. O resíduo é o misto do caso 18, aceito para o juiz.

### Evidência

- `git log --oneline 07ca28e..codex/v0.8.0-avaliacao -- prompts/` → nenhum commit.
- Suíte estrita (`--basetemp .pytest_cache/v080-b-strict`) → código 0, **357 aprovados**. O lacre confere com o hash novo.

### Próxima ação

O Reviewer faz a revisão final dos casos 15 e 16 e do lacre. Em seguida, o Supervisor declara o lacre definitivo.

## Tarefa 70

- Papel e responsável: Developer do Time B (subagente), despachado pelo Supervisor. Tarefa [70](../tasks/70-rubrica-juiz-independente.md); spec v0.8.0 D9, D11, D12, D13, D14, D16 e D19; plano, decisões 12 e 13 e "Modelo de dados".
- Escopo:
  - **Novos:** `prompts/judge.v3.md`; `evaluation/judge.py`, `evidence.py`, `aggregate.py`, `scripted_judge.py`; `tests/unit/evaluation/` (3 arquivos) e `tests/integration/test_eval_campaign.py`.
  - **Alterados:** `data/migrations.py` (0011), `evaluation/runner.py`, `evaluation/on_demand.py`, `cli.py`, `config.py`, `llm/prompts.py`, `tools/registry.py`, `.env.example`, a tarefa 70 e esta passagem.
  - **Testes ajustados:** os de migração, de versão de esquema e do avaliador padrão, listados em "Testes alterados fora da tarefa".
  - **Fora do escopo, intocados:** `orchestration/`, `agents/`, `api/`, `evaluation/scripted_policy.py`, `data/scenarios/catalog.json`, outros prompts, `tests/scenarios/` e o holdout. O worktree do Time A, `_tmp/` e `.env` (que nem existe no worktree) não foram abertos.
- Estado: implementada; em andamento até a revisão independente.
- Branch e PR: `codex/v0.8.0-avaliacao`, sem PR, sem push.
- Base e versão final: base `8f2baa6`; commits `75edaf2` (migração 0011), `dbb9d5b` (`judge.v3`, evidência, juiz independente), `8897809` (repetições, agregação, caminho executado, CLI), `c974e2c` (veredito crítico listado) e o commit desta passagem (SHA no retorno ao Supervisor). Árvore limpa depois dele.
- Independência: não-independente (relato do autor).

### O que a tarefa entrega

- **Migração 0011 (D13).** `run_evaluations` ganha `scores` (JSON), `repetition` (padrão 1) e `unsupported_claim` (0/1, com `CHECK`), mais o índice `run_evaluations_rubric`; nova tabela `calibrations`. `rubric_version` não foi acrescentada: já existe desde a 0008, assim como o `evaluator` (provedor e modelo). A descida preserva todas as avaliações, porque o `result` guarda o julgamento inteiro, e **recusa** (`RollbackRefused`, como a 0010) enquanto `calibrations` tiver nota humana, a única coisa que ninguém reconstrói. O formato de `calibrations` é o que a tarefa 71 grava: campanha, amostra, caso, rota, split, avaliador humano, notas, veredito e nota livre, único por (campanha, amostra, avaliador).
- **`judge.v3` (D9).** Quatro critérios 1–5 com justificativa (uma frase) e `unsupported_claim`, em `JudgeScoreV3`. A escala é validada no modelo, não no esquema, porque a saída estruturada estrita recusa limites numéricos; nota fora de 1–5 vira julgamento `failed`, nunca nota inventada. `judge.v2` continua carregável (`load_prompt(dir, "judge", "2")`) e a avaliação sob demanda de `/v1` ficou fixada nele: o web e a comparação de perfis leem `answers_question`/`clarity_and_tone`/`honesty`.
- **Evidência (D9).** A entrada do juiz traz a mensagem e a resposta, a rota, o status, os títulos das fontes e a lista `evidence` com os resultados das ferramentas e os trechos citados pelo Knowledge, tudo passado por `mask_sensitive` antes do corte. Limite de 6 000 caracteres no total; os itens curtos ficam inteiros e os longos dividem o que sobra, então um trecho longo não empurra um resultado de ferramenta para fora. O registro (`limit_chars`, `original_chars`, `kept_chars`, `items`, `items_cut`, `truncated`) vai dentro da entrada do juiz e na linha do relatório (`evidence_truncation`).
- **Juiz independente (D11).** Padrão `deepseek`/`deepseek-flash` (`config.py`, `.env.example`), pelo cliente DeepSeek que os perfis já usam. `resolve_judge` recusa, antes de construir o cliente e sem nenhuma chamada: par igual ao do agente; provedor sem saída estruturada (por exemplo `typesafe`); chave ausente ou vazia; modelo sem preço em `prices.json`. A mensagem diz o que fazer e termina com "No call was made." Em `eval`, a recusa vem antes de montar o sistema. Provedor, modelo, `model_used`, versão da rubrica e o tipo de independência (`different_provider` ou `same_provider_different_model`) ficam em cada julgamento e em `run_evaluations.evaluator`.
- **Repetições (D12).** `eval --repeat N` repete o agente e o juiz avalia cada resposta uma vez. `eval --judge-repeat N --answers-from <relatório.json>` julga N vezes as respostas da **primeira execução** do relatório, sem rodar o agente. As duas juntas são recusadas ("not combined"). Os relatórios guardam a evidência de cada resposta (`judge_input`) para a segunda etapa poder julgar de novo; `--repeat` sem `--judge` também a guarda.
- **Agregação e relatório.** `evaluation/aggregate.py`, por critério, rota e split, nos dois lados. Definições, para a revisão conferir: **média** de todos os scores do recorte; **desvio** = média, entre os casos, do desvio-padrão amostral dos scores do mesmo caso; **concordância exata** e **±1** = parte dos **pares** de repetições do mesmo caso com score igual ou com diferença de até 1; para `unsupported_claim`, a taxa de verdadeiro e a concordância exata. Recortes com menos de 10 casos levam `*`. A seção traz a ressalva de amostra pequena (D19). O Markdown lista também, uma a uma, as respostas com `unsupported_claim` (nunca só a média), e o julgamento gravado leva isso como `critical_failures`.
- **D16.** Cada linha do runner tem `executed_path` (os agentes de `agents` menos `router` e `personality`, na ordem, por exemplo `knowledge → customer_support`); o relatório tem a tabela "rota planejada e caminho executado". `route_ok` não mudou: segue comparando a rota do Router com as aceitas. O campo no **trace** é do Time A (D18).
- **D14 e D17.** `--split holdout_v080` carrega `holdout_v080.jsonl` só quando pedido; `--split all` nunca o inclui; para esse split as conversas de dev não rodam. O relatório já separa por split (`by_split` no resumo e na variação).
- **Substituto programado** em módulo próprio (`scripted_judge.py`): regras fixas sobre a mesma entrada JSON (valor monetário da resposta que não está na evidência nem na pergunta derruba fundamentação e correção e liga o veredito). `eval --scripted --judge` agora funciona offline, a custo zero.
- **Persistência.** `eval --judge` grava cada julgamento em `run_evaluations` (principal `cli:eval`, que nenhuma sessão da API lista), no banco do runtime (`settings.db_path`; offline, o banco temporário). Isso dá um escritor às colunas novas e liga a amostra de calibração (71) ao julgamento por `request_id`.

### Decisões além do texto do plano

1. **Captura da evidência sem tocar o grafo.** O trace guarda só a chamada de uma ferramenta, não o dado, e do Knowledge guarda ids e um trecho de 400 caracteres. Para ler o dado, `tools/registry.py` ganhou uma lista `OUTCOME_OBSERVERS` (vazia em produção, 6 linhas) e o runner a registra durante cada caso. Os trechos citados vêm do corpus por `chunk_id` (texto inteiro, mesmo código de chunking do índice), com o trecho do trace como alternativa. `tools/` não está na lista do D18 nem tem outro dono no plano. **Pedido ao Supervisor para o Time A:** se o grafo passar a gravar `detail.evidence` no trace, o runner pode trocar a captura por essa leitura. Hoje o runner lê passos de trace chamados `knowledge`; um passo novo de busca web com outro nome precisa manter `detail.mode = "web"` ou avisar.
2. **O texto da busca web não é gravado em lugar nenhum.** Para respostas `general_web` o juiz recebe só os títulos das fontes e uma nota (`evidence_notes`) dizendo que o texto não está disponível. Uma resposta web pode ser marcada com mais rigor do que merece; a calibração humana é quem mede isso.
3. **O avaliador padrão mudou em `config.py`** (duas linhas existentes, não só acréscimo) de `openai`/`gpt-6-luna` para `deepseek`/`deepseek-flash`. Efeito colateral: a avaliação sob demanda de `/v1` (v0.6.0) usa as mesmas configurações e agora precisa de `DEEPSEEK_API_KEY` ou de `EVALUATOR_*` explícito; sem isso responde `503 evaluator_unavailable`. **O `.env` do responsável provavelmente ainda tem `EVALUATOR_PROVIDER=openai` e `EVALUATOR_MODEL=gpt-6-luna`** (era o `.env.example` da v0.6.0; não li o `.env`). Com isso, `eval --judge` recusa por ser o mesmo modelo do agente. O QA precisa trocar essas duas linhas (ou apagá-las). A linha da tabela de variáveis do `README.md` fica desatualizada: é do fechamento (73).
4. **Só o par idêntico é recusado.** Mesmo provedor com modelo diferente passa e fica registrado como `same_provider_different_model`. A spec D11 pede "de outro provedor quando houver chave" e permite "outro modelo do mesmo provedor, se o responsável aceitar"; se o responsável quiser exigir outro provedor, é uma linha em `check_independence`. O provedor do agente é a constante `AGENT_PROVIDER = "openai"` (o sistema real só monta o cliente OpenAI).
5. **`MAX_OUTPUT_TOKENS` do juiz = 400.** Quatro justificativas de até 25 palavras mais os scores cabem em cerca de 220 tokens; o teto é também a reserva por chamada no orçamento.
6. **A suíte da 72a quebrou com o merge da v0.7.0**, não por esta tarefa: `test_tool_backed_amounts_come_from_the_calls_of_each_case` montava um `CustomerContext` sem escopos, e a v0.7.0 falha fechado. Corrigi só a montagem do contexto (`CustomerContext.for_principal(Principal.merchant(...))`). O JSONL e o lacre não foram tocados.
7. **Entradas para o QA com o teto da campanha.** A CLI usa o guarda de orçamento do orquestrador (o primário) tanto para o agente quanto para o juiz. O teto `v080-qa` combinado (como no teste da v0.7.0) é montado por quem chama o runner; o juiz aceita o medidor depois (`judge.meter = BudgetMeter(orchestrator.budget)`), então um roteiro do QA que troque `orchestrator.budget` pelo guarda combinado usa `resolve_judge(...)`, `run(...)` e `rejudge(...)` diretamente.

### Testes alterados fora da tarefa

- `tests/unit/data/test_migrations.py`: listas de subida e descida com a 0011 (5 testes novos). `test_v060_api.py` (migração 0008, avaliador padrão), `test_v060_r2.py` (`INSERT` com colunas nomeadas, porque a tabela ganhou colunas), `test_v1_api.py` (descida até a 0006), `test_use_cases.py` (`/ready`, esquema 11).
- `tests/integration/test_v070_story.py`, **arquivo de trava do Time A (D18)**: uma linha, `versions["schema"] == 10` virou `== 11`. É consequência direta da 0011; avise o Time A para não reverter ao fazer o merge.
- Conflito provável no merge com o Time A: `cli.py` (`cmd_eval`, se eles acrescentarem `replan.jsonl` à lista de casos) e `config.py` (linhas do avaliador, ao lado de onde entrará `MAX_PLAN_HOPS`).

### Evidência

- Comandos: Python do worktree (`merchant_assistant.__file__` → `C:\workspace\ai-getnet-case-wt\time-b\src\merchant_assistant\__init__.py`), `-p no:cacheprovider`, `--basetemp .pytest_cache/t70-dev-<data>`, um pytest por vez. A suíte estrita completa não foi rodada: é do Supervisor.
- Resultados: `tests/unit`: **294 aprovados** (84 s). `tests/integration`, os 24 arquivos em quatro grupos, um pytest por vez: **80** (campanha 14, `test_evaluation_runner`, `test_v070_closing`, `test_v060_api`, `test_v060_r2`), **88** (`test_v1_api`, `test_use_cases`, `test_v070_story`, `test_v070_identity_r2`), **97** (conversas, KB, MCP, contrato, ticketing, `doc_effect`, `r4`) e **142** (handoffs, identidade, retomada, `review_gaps`, ticketing, webhooks): **407** na integração, sem falha. Total **701 testes aprovados**. Novos desta tarefa: 34 em `tests/unit/evaluation/`, 14 em `test_eval_campaign.py` e 5 em `test_migrations.py`. Depois desses grupos só mudou o teto de saída do juiz (600 para 400 tokens); `tests/unit/evaluation`, `test_eval_campaign.py` e `test_holdout_v080.py` foram reexecutados: 56 aprovados.
- `ruff check src tests`: sem achados. Lacre do holdout: `sha256sum tests/scenarios/holdout_v080.jsonl` → `91aa5158…`, igual ao `.sha256`; `git diff 8f2baa6..HEAD -- tests/scenarios` vazio; os 8 testes de `test_holdout_v080.py` verdes.
- Execução offline de ponta a ponta: `merchant-assistant eval --scripted --judge --repeat 2 --split dev --no-conversations --out <fora do repositório> --name demo` → 46 linhas, 46 julgamentos gravados, relatório com variação, ressalva D19, tabela de caminhos e lista de afirmações sem suporte; JSON de cerca de 250 KB (a evidência de cada resposta vai nele). Custo zero.
- Estimativa do juiz (a partir da evidência dessas 46 respostas, `deepseek-flash` na tabela): reserva média de **US$ 0,0010 por julgamento** (máximo 0,0015) com o teto de 400 tokens de saída, sem cache e com toda a saída reservada (com 600 tokens eram 0,0013). A campanha da spec (69 casos × 3 execuções, mais 3 julgamentos das respostas da primeira: cerca de 414 julgamentos) reservaria perto de **US$ 0,4 só no juiz**; o gasto real deve ficar bem abaixo (saída curta, instruções em cache), mas a conta do QA nos 5 casos medidos precisa incluir o juiz, não só o agente.

### Critérios

- **Comprovados localmente:** agregação e concordância com números fixos (fixtures de mão em `test_aggregate.py`); `judge.v3` programado devolve os quatro critérios e o veredito; evidência longa truncada, com o registro; juiz igual ao agente, sem chave, sem preço ou de provedor sem saída estruturada recusado antes de qualquer cliente ou chamada (a CLI não monta o sistema); migração 0011 sobe e desce com dados sintéticos e a descida é recusada com nota humana; `--repeat` e `--judge-repeat` separados, com a contagem de chamadas do agente e do juiz; `executed_path` sem mudar `route_ok`; `--split holdout_v080` por um split sintético em árvore temporária; lacre verde.
- **Não verificados (dependem de chamada paga, do QA):** `deepseek-flash` aceitar o esquema estruturado do `JudgeScoreV3` e `reasoning.effort = none` pela Responses API do DeepSeek (o mesmo caminho dos perfis, mas com este esquema); latência e custo reais do juiz; a qualidade do juiz com a evidência (calibração humana, tarefa 71); o texto real de busca web na evidência.

### Achados e limitações

- A evidência de respostas web é só títulos (decisão 2); a de conhecimento são os trechos citados, que podem ser menores do que o recuperado.
- O desvio é entre repetições do mesmo caso; a dispersão entre casos fáceis e difíceis não está nele. Com 3 repetições e poucos casos por recorte, as taxas de concordância têm passos largos (por exemplo, 1/3).
- Se a rota mudar entre repetições do agente, o recorte "por rota" usa a rota da primeira repetição do caso. A tabela de casos mostra a rota de cada linha, mas a agregação não separa isso.
- Os relatórios de campanha ficam maiores (evidência por resposta).
- `README.md` e `CHANGELOG.md` não foram alterados.

### Ação externa, identidade e próxima ação

- Ação externa: nenhuma (sem push, sem PR, sem rede, sem chamada paga). Commits locais com `lauroPereira <lauro.s.pereira@gmail.com>`, conferida antes de cada um.
- Próxima ação: Reviewer independente na tarefa 70. Pontos a pedir a ele: as definições de agregação acima; a regra de independência (decisão 4); o hook em `tools/registry.py` (decisão 1); a mudança do avaliador padrão e seu efeito na avaliação sob demanda (decisão 3). Depois, a tarefa 71 usa `calibrations` e as linhas `run_evaluations` do `cli:eval`.
- Decisão humana pendente: nenhuma bloqueante. Reversíveis para o relatório do Supervisor: avaliador padrão `deepseek-flash`; só o par idêntico é recusado; tabela `calibrations` com o formato acima.
