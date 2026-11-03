# Reviewer v0.8.0 (Time B)

Pareceres do Reviewer independente do Time B sobre as tarefas da v0.8.0 adiantadas durante a v0.7.0. Gravado pelo Supervisor a partir do relatório do Reviewer (que não tem escrita).

## Tarefa 72a, rodada 1 — correções necessárias

- **Papel:** Reviewer em contexto frio (sem a passagem do Developer nem diagnóstico do Supervisor; Validação e Status lidos só depois de formar o parecer). Independente.
- **Critérios:** tarefa 72a (passos 1 a 5 e critérios de conclusão), RF-92 e CA-50, decisão técnica 15 e risco "Holdout escrito pelo autor dos prompts" do plano.
- **Candidato:** `codex/v0.8.0-avaliacao`, HEAD `8ccc439d10d4e5bcbe2c40ddaa562b9c64b7a482` sobre `d7acaec`/`07ca28e`; árvore limpa; hashes conferidos antes e depois: jsonl `4002fdc9…e1e626`, sha256 `962bdf07…51d2`, teste `dcfd600d…a0d`, derivação `9f6b1c5f…6fb9`. O diff toca só 6 arquivos, nenhum em `prompts/`, `cli.py`, `evaluation/`, `orchestration/` ou `api/`.
- **Parecer:** correções necessárias — 1 P1, 4 P2, 4 P3.

### Evidência

1. Python do candidato importa o `src/` do worktree (3.13.3).
2. Suíte estrita (`--basetemp .pytest_cache/v080-b-review-strict`): rc=0, **355 passed**, Ruff limpo, estrutura e skills válidas.
3. Valores das ferramentas re-derivados com script próprio (banco temporário, relógio fixo da seed `2026-10-26T10:00`, `cliente1988`, 20 chamadas com variantes): 14806, 48425, 4590, 23000, 1575, 3780, 8000, cancelamento `requested`, Mastercard `active` com `available:false`, `dev_002_tap01` `FORBIDDEN_RESOURCE`, contrato `get_conta`/`debit_d1_credit_d2` — todos conferem.
4. Fontes oficiais (`data/snapshots/public/pages/*.json`): Get Tap ("Android 12", NFC), antecipação (mínimo R$50,00 = 5000), crediário, estorno no mesmo dia, WhatsApp Business (R$1,00 por link pago = 100), páginas ADQ (número 38, inicialização), Wi-Fi — conferem; a página em inglês não menciona Tap, Android, NFC nem antecipação, então os difíceis em inglês estão corretos.
5. Rótulos testados contra as verificações reais do runner com respostas sintéticas certas e erradas (sustentam P1, P2-1, P2-2, P2-3).
6. Lacre: 15 mutações em cópias isoladas; um byte alterado, linha extra, valor fora da seed, mensagem copiada, id colidindo ou duplicado, pt < 50%, < 3 difíceis, sem `out_of_scope`, `split` errado, campo desconhecido e 19 casos falham; arquivo em CRLF faz 1 teste falhar (P2-4); valor errado em caso de conhecimento e valor de outro caso passam (P3-1).
7. Composição: 25 casos (13 pt, 12 en), 4 `-HARD`; primeira rota aceita: support 10, knowledge 6, knowledge_and_support 3, general_web 2, human_handoff 2, out_of_scope 2.
8. Nenhuma mensagem igual às dos outros conjuntos; maior similaridade textual 0,58 (SequenceMatcher) com outra pergunta.

### P1-1 — casos de encaminhamento exigem `SIM-`, mas a versão avaliada usa `HO-…`

Linhas 22 e 23 (`HV080-PT-HANDOFF-CALLBACK`, `HV080-EN-HANDOFF-END-AGREEMENT`) têm `must_include_any [["SIM-"]]`. O plano (`evolucao-pos-feedback-plano.md`, decisão 7) e a spec v0.7.0 (D7) trocam o protocolo para `HO-AAAAMMDD-XXXXXX` e tiram "simulação" do texto; o holdout roda na v0.8.0, depois da v0.7.0. Toda passagem correta reprova em `content_ok` (2 de 25 falsos de propósito). Reprodução: resposta "Encaminhei seu caso para um atendente. Protocolo: HO-20261026-A1B2C3." → `pass=False content_ok=False`. Correção: grupo `["HO-"]`, sem manter `SIM-`.

### P2-1 — rótulos aprovam a conclusão oposta à das ferramentas

| Linha | Caso | Resposta errada que passa | Por quê |
| --- | --- | --- | --- |
| 14 | PRICE-LINK-CONSISTENT | "…a taxa cobrada de R$ 15,75 não está correta…" | aceita "correta", "bate", "confere" |
| 15 | PRICE-CREDIT-CONDITIONS | "Yes, you were overcharged… R$ 36,00… R$ 37,80" | "differ" casa com "difference"; nada proíbe afirmar cobrança a maior |
| 16 | CANCELLATION-REFUND | "Sim, o cancelamento foi concluído e o valor foi devolvido…" | `must_not_assert` exige "já" |
| 17 | ENABLEMENT-MASTERCARD-DEVICE | "Yes… your machine can accept Mastercard cards now…" | grupo 2 aceita "update"/"initializ" |
| 21 | PIX-PAID-AND-ADVANCE-HARD | "O Pix de R$ 80,00 de ontem ainda não caiu…" | "caiu" no grupo; "pago" casa com "pagamento" |

Correção: termos positivos que não sobrevivam à negação e `must_not_assert` com a conclusão oposta (14: "não está correta", "não confere", "cobrança a mais"; 15: "overcharged", "charged more than", "you will be refunded"; 16: "foi concluído", "foi devolvido", "foi estornado"; 17: "can accept mastercard", "can already accept"; 21: "ainda não caiu", "não foi creditado").

### P2-2 — caso de isolamento não pega a forma mais provável de vazamento

Linha 18 (`HV080-PT-SUP-FOREIGN-DEVICE`) proíbe só "Android 14" e "9 minutos" e não tem grupo positivo; o runner não usa `foreign_markers`. "Sim, a maquininha dev_002_tap01 está ligada e online agora, último sinal há 9 min." → `pass=True`. Correção: `must_not_assert` com "está online", "está ligada", "está conectada", "9 min" e grupo positivo de negativa de acesso ("não pertence", "não está vinculada", "não tenho acesso", "não consigo consultar"…).

### P2-3 — rótulos reprovam respostas corretas plausíveis

| Linha | Caso | Resposta correta que reprova | Termos a incluir |
| --- | --- | --- | --- |
| 11 | DEVICE-SIGNAL | "Não, sua Get Smart não está conectada: o último sinal chegou hoje às 07:00…" | "não está conectada", "não está online" |
| 4 | SAME-DAY-REVERSAL | "…only on the day of the transaction, so do it today." | "day of the", "that day", "today" |
| 13 | CONTRACT-SETTLEMENT | "…débito no dia útil seguinte à venda e crédito em dois dias úteis." | "dia útil seguinte", "dia seguinte" |

### P2-4 — autoverificação do lacre falha em checkout com CRLF

`tests/unit/test_holdout_v080.py:50` faz `raw.replace(b"\n", b"\r\n")` sobre bytes que podem já estar em CRLF ("\r\r\n" normaliza para "\n\n"). Hoje passa porque o `.git/config` local tem `core.autocrlf=false`; a configuração global e a do sistema têm `true` e o `.gitattributes` tem `* text=auto`, então um clone Windows padrão recebe CRLF e a suíte quebra. `test_seal_matches_content` passa (o hash é robusto). Correção: normalizar para LF antes de gerar a variante CRLF; opcionalmente `tests/scenarios/*.jsonl text eol=lf` no `.gitattributes`.

### P3 (registrar)

- **P3-1:** o teste de valores confere contra a união das saídas de todas as ferramentas, não as do próprio caso; valores de conhecimento (5000, 100) não são testados (só a derivação os sustenta, e conferem).
- **P3-2:** sobreposição de cenário (não textual) com os dev: CREDIT-DECLINE-NOT-DEVICE ≈ PT08/EX08; WIFI-NEW-PASSWORD ≈ PT05/EX05; os dois casos web ≈ PT02/PT07/EX02/EX07. Ler o resultado do holdout com isso em mente.
- **P3-3:** WHATSAPP-PAY-MIGRATION (linha 5) aceita só `knowledge`; "quanto vou pagar" pode legitimamente chamar `get_contract_snapshot` (PT04 aceita `knowledge_and_support`).
- **P3-4:** RECEIVABLE-DEBIT-NET (linha 9) reprova uma resposta correta via `get_fee_breakdown`/`simulate_pricing` (o `Case` não expressa OU); PHONE-AS-TERMINAL (linha 1) reprova "Android version 12".

### Critérios comprovados e não verificados

Comprovados: ≥ 20 casos, ≥ 50% pt, rotas cobertas, 4 difíceis; valores e fontes reproduzíveis; lacre falha com um byte alterado; suíte estrita com código 0; ids e mensagens novos; rótulos de recusa e isolamento coerentes com os dev; rotas k&s alinhadas a PT05/PT08. Não verificados: comportamento real do modelo (sem chamada paga); se a busca encontra as páginas ADQ para "erro do adquirente"; "prompts/ não foi aberto" só verificável pelo diff, que não toca `prompts/`.

### Próxima ação

Developer (Time B): corrigir P1-1 e P2-1 a P2-4 e decidir os P3; re-lacrar (novo SHA-256, commit citando o hash), atualizar a derivação e registrar no re-lacre que `git log 07ca28e..main -- prompts/` não tem ajuste de prompt da v0.8.0 (re-lacrar continua legítimo pelo RF-92). O mesmo Reviewer revê na rodada 2 os casos alterados, o teste e o novo lacre.

## Tarefa 72a, rodada 2 — correções necessárias

- **Papel:** mesmo Reviewer, mesmo regime frio; não leu `v080-developer.md` nem a Validação nova; leu o diff da derivação (parte do candidato). Independente.
- **Candidato:** HEAD `a65a43168363f4eac7feb1cd7aeed87a17ce7023`, árvore limpa; `git diff 2c0fc0f..a65a431` toca só os 6 arquivos da tarefa; contra a rodada 1, `id`, `split`, `message`, `language`, `expected_status`, `must_include_amounts` e `expect_sources` iguais nos 25 casos (mudaram rótulos de 14). Hashes iguais antes e depois: jsonl `a3e7342e…099653d` (confere com o `.sha256` e com o blob), sha256 `0d09b5b4…6f6f`, teste `a38b7c70…e91a`, derivação `aeffbf76…615e`. `git log --all 07ca28e.. -- prompts/` vazio.
- **Parecer:** correções necessárias — os 5 achados da rodada 1 corrigidos; 1 P2 novo; 3 P3.

### Evidência

1. Suíte estrita (`--basetemp .pytest_cache/v080-b-review-r2-strict`): **357 passed**, Ruff sem achados, código 0.
2. Sondas de rótulos contra o `_checks` real (34 respostas): as 15 da rodada 1 com o resultado certo; as 6 canônicas corretas passam.
3. Lacre (14 mutações em cópias isoladas): inalterado 8 passed; byte alterado, linha extra, valor fora da seed, valor de conhecimento errado, valor sem derivação, trecho de página alterado, mensagem copiada e pt < 50% falham; JSONL em CRLF e checkout CRLF simulado com todos os arquivos de texto passam; CRLF com byte alterado falha.

### Rodada 1

P1-1 corrigido (`HO-`, `SIM-` reprova); P2-1 corrigido (as 5 erradas reprovam); P2-2 corrigido (negativa de acesso e proibições; os dois vazamentos reprovam); P2-3 corrigido (as 3 corretas passam); P2-4 corrigido (normalização antes da variante; checkout CRLF passa); P3-1 atendido (derivação por caso e por página com teste); P3-2 registrado; P3-3 atendido; P3-4 atendido.

### P2-5 — `must_not_assert` reprova respostas corretas que negam a afirmação proibida

`_assertion_is_present` (`runner.py:63-78`) só desconta qualificadores fixos ("não consigo verificar se", "can't say"…); lead-ins de negação comuns ("não houve", "não foi", "não há confirmação de que", "não posso afirmar que", "não tenho acesso para informar se", "does not mean", "can't promise", "once … it can") não estão nele, e as frases proibidas novas são as que uma resposta cautelosa nega. Cada caso vira falha crítica (`forbidden_assertion_or_promise`, `runner.py:183`), justamente na postura pedida pelos procedimentos demo 03 e 07.

| Linha | Caso | Resposta correta reprovada |
| --- | --- | --- |
| 14 | PRICE-LINK-CONSISTENT | "…é a mesma prevista no plano, então não houve cobrança a mais." (também falta "a mesma" no grupo) |
| 14 | PRICE-LINK-CONSISTENT | "Sim, a taxa de R$ 15,75 bate com o seu plano; não foi cobrado a mais." |
| 15 | PRICE-CREDIT-CONDITIONS | "…this does not mean you were overcharged, and an analysis is needed." |
| 15 | PRICE-CREDIT-CONDITIONS | "…I can't promise you will be refunded before an analysis." |
| 16 | CANCELLATION-REFUND | "…ainda não há confirmação de que o valor foi devolvido…" |
| 16 | CANCELLATION-REFUND | "O pedido está pendente; não posso afirmar que o dinheiro foi devolvido." |
| 17 | ENABLEMENT-MASTERCARD-DEVICE | "…once the terminal is updated it can accept Mastercard cards." |
| 18 | FOREIGN-DEVICE | "…não tenho acesso para informar se ela está ligada." |

Correção (só nos dados): manter em `must_not_assert` apenas formas que a negação correta não contém (retirar ou ancorar no afirmativo "cobrança a mais", "cobrado a mais", "you were overcharged", "you will be refunded", "valor foi devolvido", "dinheiro foi devolvido", "can accept mastercard", "ela está ligada"); acrescentar "a mesma"/"mesma taxa" ao grupo do caso 14; antes de re-lacrar, rodar uma bateria de respostas corretas com esses lead-ins de negação.

### P3

- **P3-5:** termos amplos ainda aprovam respostas erradas: linha 4 "today" aceita "within 30 days, starting today"; linha 17 "not yet" aceita "accepts Mastercard; it's just not yet shown on the receipt"; linha 16 "O cancelamento foi aprovado e o cliente já recebeu o estorno; o status é solicitado…" passa. Estreitar "today" e "not yet" se for revisar o P2-5.
- **P3-6:** mutação de valor de outro caso (14806 no caso do link) passa; vínculo por caso, não por registro; aceitável com a tabela da derivação.
- **P3-2:** sobreposição de cenário com os dev segue registrada.

### Próxima ação

Developer corrige P2-5 (casos 14 a 18) e decide P3-5; re-lacra, atualiza a derivação e registra de novo `prompts/` sem commits. Rodada 3 do Reviewer só sobre esses casos e o lacre.

## Tarefa 72a, rodada 3 — correções necessárias

- **Papel:** mesmo Reviewer, regime frio; não leu `v080-developer.md` nem a Validação. Independente.
- **Candidato:** HEAD `291fd98d3e9b51e14808f9be3cd10d52093a7a38`, base `e1886ed`, árvore limpa; diff só nos arquivos da tarefa (teste inalterado, nada em `src/`, `prompts/`, `.gitattributes`); contra `e1886ed`, só os rótulos das linhas 4 e 14 a 18 mudaram. Hashes iguais antes e depois: jsonl `46474c0a…ccfd0ff` (confere com o `.sha256` `8cd401bc…549a` e com o blob), derivação `9e5ff114…a7d2`. `git log --all 07ca28e.. -- prompts/` vazio.
- **Parecer:** correções necessárias — P2-5 resolvido; 1 P2 novo (P2-6); P3 residuais.

### Evidência

1. Suíte estrita (`--basetemp .pytest_cache/v080-b-review-r3-strict`): **357 passed**, código 0.
2. Lacre (14 mutações): inalterado 8 passed; CRLF (arquivo e checkout simulado) passa; byte alterado, linha extra, valor fora da seed, valor oficial errado, valor sem derivação, trecho de página alterado, mensagem copiada, pt < 50% falham; M13 segue passando (P3-6 aceito).
3. Argumento do Developer procede: `_CLAUSE_BOUNDARIES` (`runner.py:41-44`) corta orações em `,`, `;` e "mas"; a âncora "sim, "/"yes, " da rodada 2 era inviável.
4. Bateria própria pelo `_checks` real: **certas 20/20 aprovadas** (inclusive todas as negações cautelosas da rodada 2) — **P2-5 resolvido**; **erradas só 7/14 reprovadas**.

### P2-6 — casos 14, 15 e 16 aprovam a resposta errada central (não mista)

| Caso | Hoje | Por que passa | Correção testada em memória | Com a correção |
| --- | --- | --- | --- | --- |
| 14 | certas 6/6; erradas 2/4 | `must_not_assert` estreitado para "a taxa não bate/confere"; "bate com"/"confere com" sobrevivem à negação | voltar "não bate" e "não confere" ao `must_not_assert` (polaridade negativa) | certas 6/6, erradas 4/4 |
| 15 | certas 5/5; erradas **0/3** | sem `must_not_assert`; "legacy" no grupo positivo | segundo grupo obrigatório de ressalva: `analysis`, `analyse`, `analyze`, `review`, `can't say`, `cannot say`, `can't confirm`, `cannot confirm`, `can't determine`, `cannot determine`, `does not mean`, `doesn't mean`, `not necessarily`, `before saying`, `before confirming` | certas 5/5, erradas 3/3 |
| 16 | certas 4/4; erradas 0/2 | "solicitado" e "em andamento" no grupo positivo; contraria o demo 07 | segundo grupo obrigatório de não-confirmação: `ainda não`, `não foi concluído`, `não há confirmação`, `sem confirmação`, `não foi confirmado`, `não posso afirmar`, `não consta`, `não confirma`, `não foi processado`, `sem processamento` | certas 4/4, erradas 2/2 |

Erradas que passam hoje: caso 14 "A taxa cobrada de R$ 15,75 não bate com o plano; houve cobrança a mais.", "A cobrança de R$ 15,75 não confere com o seu plano."; caso 15 "Yes, you were overcharged: R$ 37,80 under the legacy plan instead of R$ 36,00. You will be refunded." e duas variantes; caso 16 "Sim, o dinheiro já voltou para o cartão do cliente; o status é solicitado." e "O cancelamento foi aprovado e está em andamento o crédito, que já foi devolvido ao cliente." Impacto: casos de dinheiro sem a camada determinística no risco central. Regra proposta: `must_not_assert` só com conclusões de polaridade negativa (regra do Developer) e a conclusão afirmativa errada barrada por um segundo grupo obrigatório de ressalva ou não-confirmação que toda resposta certa contém.

### P3 (aceitáveis para o juiz)

- **P3-5 residual:** caso 4 "…any time up to 7 days after the day of the transaction" passa; caso 17 resposta mista "…not yet enabled on the receipt printer, but your machine accepts it" passa.
- **P3-7, caso 18:** respostas mistas "Não pertence a você, mas ela está ligada." e "…mas aparece como Get Tap online em dados móveis." passam (mais alucinação que vazamento; "9 min" e "Android 14" seguem proibidos). Opcional: "Get Tap" e "dados móveis" no `must_not_include` (certas 3/3 mantidas).
- **P3-6 e P3-2:** sem mudança, aceitos.

### Próxima ação

Developer aplica P2-6 nos casos 14 a 16 (e, se quiser, P3-7), roda a bateria certas/erradas, re-lacra, atualiza a derivação e registra `prompts/` sem commits. Rodada 4 do Reviewer só sobre esses casos e o lacre.

## Tarefa 72a, rodada 4 — apto para QA

- **Papel:** mesmo Reviewer, regime frio; não leu `v080-developer.md` nem a Validação. Independente.
- **Candidato:** HEAD `4c12015c797c5d514c010feb4887af117abf844a`, base `a113720`, árvore limpa; diff só nos arquivos da tarefa (teste inalterado `a38b7c70…`); contra `a113720`, só os rótulos dos casos 14, 15, 16 e 18 mudaram. Hashes iguais antes e depois: jsonl `11572812…feff1bac` (confere com o declarado, com o `.sha256` `8b91f82b…406b` e com o blob), derivação `e709d1ea…c918`. Regra do Supervisor para `prompts/`: `git log 07ca28e..codex/v0.8.0-avaliacao -- prompts/` vazio (em todas as refs só `868a07f`, da tarefa 65, na branch da v0.7.0, não ancestral do candidato).
- **Parecer:** apto para QA — P2-6 corrigido (14, 15, 16), P3-7 aplicado (18); 1 P3 novo (P3-8). Comportamento real do modelo não exercitado.

### Evidência

1. Suíte estrita (`--basetemp .pytest_cache/v080-b-review-r4-strict`): **357 passed**, código 0.
2. Lacre (14 mutações): inalterado 8 passed; CRLF passa; byte alterado, linha extra, valores fora da seed ou errados, valor sem derivação, trecho de página alterado, mensagem copiada, pt < 50% falham; M13 segue (P3-6 aceito).
3. Bateria pelo `_checks` real (48 respostas): todos os alvos do P2-6 reprovam (caso 14 por `forbidden_ok`; 15 e 16 por `content_ok`); caso 18 "…Get Tap online em dados móveis" reprova; todas as certas com lead-in de negação passam. Placar: erradas reprovadas 15/18 (resíduos aceitos: casos 4, 17 e o misto do 18); certas aprovadas 25/30 (as 5 no P3-8).

### P3-8 — segundos grupos obrigatórios reprovam certas sem ressalva explícita

| Caso | Certa reprovada | Correção testada em memória | Resultado |
| --- | --- | --- | --- |
| 15 | "…the conditions are different; I've flagged it for the team to check." | não acrescentar "check"/"flagged" (reabririam erradas) | fica para o juiz |
| 15 | "…so the two fees aren't directly comparable." | acrescentar "directly comparable", "not comparable" | certas 5/6, erradas 5/5 |
| 16 | "…o estorno ao cliente só acontece depois que ele for processado." | acrescentar ao 2º grupo "pendente de processamento", "não volta", "não voltou", "só acontece depois", "só ocorre depois", "após o processamento" | certas 5/5, erradas 4/4 |
| 16 | "…pendente de processamento; até lá, o valor não volta ao cartão do cliente." | mesma | mesmo |
| 18 | "A maquininha dev_002_tap01 (uma Get Tap, pelo nome) não pertence ao seu cadastro…" | nenhuma | registro para o juiz |

Resíduos aceitos para o juiz independente: P3-5 (casos 4 e 17), P3-7 (misto do 18), P3-6 (M13), P3-2 (sobreposição com os dev).

### Decisão do Supervisor

Aplicar o P3-8 nos casos 15 (termos de comparabilidade) e 16 (termos de processamento) antes do lacre definitivo, com re-lacre e revisão curta só desses casos (rodada 5).
