# QA D12 pré-holdout — v0.8.0 r4 (reteste dirigido)

Data: 2026-11-05 (UTC)  
Tarefa: [74](../tasks/74-correcao-qa-pre-holdout-v080.md). História: [orquestracao-avaliacao-v080.md](../historias/orquestracao-avaliacao-v080.md), versão 1, momentos 7 e 8 (e momentos 1 a 4 pela campanha).  
Resultado: **reprovado**. CA-51 não chega a 12/13 nas repetições 1 e 2, já contando só os casos com ambiente válido. Parte do bloco saudável ficou **inválida por ambiente** (seed sintética vencida, ver abaixo). CA-49 também não foi validado: `REPLAN-PROCEDURE` saiu inválido e `REPLAN-TOOL-DOWN` não rodou.

## Candidato

| Item | Valor |
|---|---|
| Branch | `codex/v0.8.0-replan` |
| Candidato fixado | `4c3c8a98ddfc4f7af7bba877177f3479152159b5` ([manifesto r4](v080-candidato-r4.json), fingerprint `b31be639…13f7`) |
| HEAD no início da rodada e do bloco `healthy` | `fe270bcaf8becdb2c9f92ac3e366560111735905` |
| HEAD no bloco `conversations` e no fim | `91e598d7781ee223bd749ff57e8ba3d2267ead41` (commit só de docs, avisado pelo Supervisor durante a rodada) |
| Diff candidato → HEAD em `src prompts tests data` | vazio nos dois HEADs. `fe270bc` traz os 6 arquivos de `documentation_only_after_pin`. `91e598d` acrescenta `docs/specs/evolucao-pos-feedback-plano.md` e `docs/specs/orquestracao-avaliacao-v080.md` (contingência de US$0,30) |
| Revisão | [v080-reviewer-t74-r2.md](v080-reviewer-t74-r2.md), apto em revisão estática |
| Holdout `holdout_v080` | não lido nem executado; SHA-256 LF conferido `91aa5158…4f1bac` |
| Não rastreados | `Claude outputs/`, `_tmp/`, `v/` preexistentes, intactos |

## Ambiente

- Pré-condição: `python tools/scripts/lint_and_tests.py --strict` (venv 3.13.3, `--basetemp=.pytest_cache/qa-r4-suite-basetemp`): **1097 passed** em 12m08s, ruff e skills ok, exit 0. Log SHA-256 `9bcfc598…5812`.
- Runtime da aplicação: `.pytest_cache/qa-v080-r1/runtime` (QA r1, migração 0011). Ledgers: `BUDGET_RUNTIME_DIR=data/runtime`; `BUDGET_LIMIT_USD=1.19504185` só no processo. Fixtures: `MOCK_SERVICES_DIR=data/mock-services`.
- Mock oficial de preços com a venv em `127.0.0.1:18765` (PID 21792). Saúde comprovada antes dos blocos: `/openapi.json` 200; `POST /pricing/simulations` (`sale_1988_0001`) 200, regra `pricing_mock_v1_debit`, taxa 194; `GET /charges/sale_1988_0001` 200. A saúde foi reconferida antes de cada bloco. O mock foi encerrado ao fim; nenhum processo Python ficou ativo.
- Juiz: DeepSeek `deepseek-flash`, `judge@3`, independência `different_provider`; agente OpenAI `gpt-6-luna`.
- Docker, navegador, `--judge-repeat`, smoke e holdout: não usados, como manda o despacho.

### Seletor de IDs (fora do repositório)

Usado `.pytest_cache/qa-v080-r1/qa-r4-selector.py`, com o original preservado em `qa-r4-selector.orig.py` (SHA-256 `62e177ad…5402`). O arquivo ajustado tem SHA-256 `4c5e970a…071a`. Dois ajustes, nenhuma guarda enfraquecida:

1. **Preflight de HEAD (pedido pelo Supervisor).** Aceita um HEAD diferente do candidato só se `git diff --name-only <candidato> <HEAD>` listar apenas `docs/`. A lista é impressa no stdout. As guardas de árvore suja, ledgers, cap, mock e revisão continuam iguais.
2. **Vazamento do filtro para a guarda da estimativa (defeito do seletor, achado nesta rodada).** Na primeira tentativa, a CLI recusou antes de qualquer chamada paga: `--campaign-estimate was altered or does not match the validated source projection`. Os ledgers não mudaram (log da tentativa: `healthy-attempt1-refused.*`). A substituição de `runner.load_cases` também valia para a revalidação da estimativa (`_build_v080_campaign_estimate`), que passava a projetar só os casos filtrados. Reproduzi offline: US$0,41145748 com o filtro e US$1,03174096 sem ele, valor igual ao do artefato. Ajuste: o filtro só vale quando quem chama é `cmd_eval`; os demais chamadores recebem o carregador original. Com isso, a guarda de estimativa revalida o conjunto completo, como na CLI pura. O mecanismo foi conferido offline antes da nova execução. A seleção exata aparece no stdout (`case_ids`) e em `config.cases = 21` no JSON (63 linhas).

## Blocos

| Bloco | IDs | Janela (UTC) | Exit | Situação |
|---|---|---|---|---|
| `healthy` | 21 IDs × 3 (63 respostas julgadas) | 03:43:14 – 03:54:51 | 0 | Executado; parte **inválida por ambiente** |
| `tool-down` | `REPLAN-TOOL-DOWN` × 3 | — | — | **Não executado**: a condição não pode ser produzida neste runtime (ver abaixo) |
| `conversations` | `FU01`–`FU04` (10 turnos) | 03:56:48 – 03:58:12 | 0 | Executado; válido |

### Condição de ambiente que invalidou parte do bloco `healthy`

A seed sintética usa o relógio do sistema como dia-base e só é recriada no `bootstrap`. O runtime de QA r1 foi semeado com o dia-base 2026-11-04: as vendas de "ontem" (`sale_1988_0001..0003`) ficaram com data 2026-11-03 (America/Sao_Paulo). O bloco rodou entre 00:43 e 00:54 de 2026-11-05 no horário de São Paulo. Nesse horário, "ontem" já era 2026-11-04 e não havia venda nessa data. Toda pergunta sobre "ontem" recebeu `simulate_pricing: NOT_FOUND`, ou recebíveis e cancelamentos vazios. O produto respondeu de forma coerente com os dados que tinha ("não encontrei venda de ontem"), mas a condição de teste não era a dos rótulos. A r3 rodou às 19:47 BRT de 04/11, com "ontem" = 03/11, por isso não viu o problema.

Ficam **inválidos por ambiente** os IDs cuja mensagem depende de "ontem": `V030-PRICE-CONSISTENT`, `V030-PRICE-CONDITIONS`, `V030-PRICE-DIVERGENCE`, `V030-SALE-CANCELLATION`, `V030-PT-PRICE-CONSISTENT`, `V030-PT-PRICE-CONDITIONS`, `V030-PT-PRICE-DIVERGENCE`, `V030-PT-SALE-CANCELLATION` e `REPLAN-PROCEDURE`. São 8 jornadas e 1 cenário, com 27 respostas. `REPLAN-TOOL-DOWN` pergunta pela "venda no débito de ontem". Com esta seed, a ferramenta falharia na busca local antes de tentar o mock recusado, então não foi executado. Rodar o bloco gastaria sem produzir a falha real de conexão que CA-49 exige.

Válidos: `EX04`, `EX08`, `NOEV`, `UC13`, `UC14`, `REPLAN-ACCOUNT`, `REPLAN-WEB`, `V030-PRICE-INSUFFICIENT`, `V030-PT-PRICE-INSUFFICIENT` ("latest", venda de 2026-11-02 presente), `V030-ENABLEMENT-PENDING`, `V030-PT-ENABLEMENT-PENDING`, `V030-CONTRACT-TERMINATION` e as quatro conversas.

## CA-51 — jornadas de negócio (rubrica determinística `passed`, a mesma da r3)

| Repetição | Aprovadas (13) | Válidas aprovadas / válidas (5) | Máximo possível se as 8 inválidas passassem | r3 | Falhas com ambiente válido |
|---:|---:|---:|---:|---:|---|
| 1 | 3/13 | 3/5 | **11/13** | 9/13 | `V030-PRICE-INSUFFICIENT` (`content_ok`, `req_evalbccfe360ff22`); `V030-CONTRACT-TERMINATION` (rota inicial `clarify`, status `needs_clarification`, `req_eval35a095aa8794`) |
| 2 | 3/13 | 3/5 | **11/13** | 11/13 | `V030-PRICE-INSUFFICIENT` (`content_ok`, `req_evaldf38c4d80b5e`); `V030-PT-PRICE-INSUFFICIENT` (`content_ok`, `req_evale8ee4429374a`) |
| 3 | 4/13 | 4/5 | 12/13 | 10/13 | `V030-PT-PRICE-INSUFFICIENT` (`content_ok`, `req_eval51b2a1d763e0`) |

**CA-51 reprovado** nas repetições 1 e 2, sem depender da seed vencida. A repetição 3 fica inconclusiva. `ENABLEMENT-PENDING` passou 3/3 nos dois idiomas. `CONTRACT-TERMINATION` passou 2/3; nas repetições 2 e 3, o protocolo `HO-` saiu sem `unsupported_claim`.

Leitura das falhas válidas:

- **`PRICE-INSUFFICIENT` (EN e PT):** as respostas mantêm a proposição esperada, ou seja, não há regra aplicável nem cobrança registrada, logo não dá para comparar. O juiz deu 5/5/5/5 (ou usefulness 4), sem afirmação sem suporte. O rótulo literal recusa redações equivalentes, como "no fee rule or recorded charge was available to compare" e "não havia uma regra de preço aplicável nem uma cobrança registrada". É a mesma classe de falso negativo da triagem r4, ainda não coberta pelos rótulos dev. Tarefa [75](../tasks/75-rotulo-literal-price-insufficient-v080.md).
- **`CONTRACT-TERMINATION` r1:** o Router pediu esclarecimento ("encerrar o contrato todo ou um serviço?") em vez de encaminhar a um humano; a rota aceita é só `human_handoff`. Tarefa [76](../tasks/76-encerramento-contrato-pede-esclarecimento-v080.md).

## CA-49 — replanejamento (rota pelo plano inicial, D16; caminho executado à parte)

| ID | Rep. | `request_id` | Rota inicial | `executed_path` / decisões `replan` (next, origin, hops) | `plan_hops` | Check |
|---|---:|---|---|---|---:|---|
| `REPLAN-ACCOUNT` | 1 | `req_eval3dd86be708a7` | knowledge | support (`model`, 1) → web (`model`, 2) → finish (`rule:gap_declared`) | 2 | passa |
| `REPLAN-ACCOUNT` | 2 | `req_eval7bd24748ff20` | knowledge | idem | 2 | passa |
| `REPLAN-ACCOUNT` | 3 | `req_evaldd20496c84f3` | knowledge | idem | 2 | passa |
| `REPLAN-WEB` | 1 | `req_eval982a8d0d8f87` | knowledge | web (`rule:evidence_insufficient_web`, 1) → finish (`rule:gap_declared`) | 1 | passa |
| `REPLAN-WEB` | 2 | `req_eval4cac27bc4e28` | knowledge | idem | 1 | passa |
| `REPLAN-WEB` | 3 | `req_evale71386414772` | knowledge | web (`rule:evidence_insufficient_web`, 1) → finish (`rule:complete`) | 1 | passa |
| `REPLAN-PROCEDURE` | 1–3 | `req_evalafab8e116e5d`, `req_eval1b3204944857`, `req_evala4e0c37fb21d` | knowledge_and_support | support (`rule:plan_pending`, 0) → finish | 0 | **inválido por ambiente** ("vendas de ontem" sem recebíveis em 04/11); falhou tools/amounts/content |
| `REPLAN-TOOL-DOWN` | — | — | — | não executado | — | **não validado** |

Nos 63 traces do bloco, o maior `plan_hops` foi 2 (limite 3); cada decisão registra `origin`. Os controles de fallback web `EX04` e `NOEV` seguiram `web` por `rule:evidence_insufficient_web` com `plan_hops` = 1 e passaram 3/3. `REPLAN-WEB` corrigido: 3/3, contra 2/3 na r3. Os passos `replan` foram capturados do `traces.sqlite3` por `request_id` logo depois de cada bloco ([traces healthy](v080-healthy-traces-r4.json)). **CA-49 não validado** nesta rodada: falta `REPLAN-PROCEDURE` com ambiente válido e `REPLAN-TOOL-DOWN` com conexão recusada.

## Controles e conversas

| Controle | Rep. 1 | Rep. 2 | Rep. 3 | r3 |
|---|---|---|---|---|
| `EX04` | passa | passa | passa | passava |
| `EX08` | passa | passa | passa | falhou conteúdo na rep. 1 |
| `NOEV` | passa | passa | passa | falhou conteúdo nas 3 |
| `UC13` | passa | passa | passa | falhou status na rep. 3 |
| `UC14` | passa | passa | passa | passava |

Conversas **4/4** (r3: 3/4). **`FU01` corrigido:** o turno 2 ("Deu certo, voltou a funcionar!") teve rota inicial `acknowledgement`, `answered`, caso `resolved` com evidência `customer_confirmed` (`req_evalfu759a4b59da`); o turno 1 foi `req_evalfu4e1a01e5e8`. `FU02`–`FU04` passaram todos os turnos; os `request_id` estão em [traces das conversas](v080-conversations-traces-r4.json).

Ruído observado: `V030-PT-PRICE-DIVERGENCE` rep. 3 (`req_eval9a688ad14ac0`) teve `router: APIConnectionError` transitório. O caso já estava inválido por ambiente.

## Juiz (bloco `healthy`; as conversas não são julgadas)

`judge_failed = 0` em 63 julgamentos; `unsupported_claim_rate` = **0/63** (r3: 19/132); `judge_web_note` = **0/12** respostas com nota web (r3: 9/24). Médias: groundedness 4,92; factual_correctness 4,87; relevance 4,76; usefulness 4,56. As respostas com protocolo de escalada (`UC14`, `CONTRACT-TERMINATION` rep. 2 e 3) não foram marcadas, o que é coerente com a evidência do protocolo agora entregue ao juiz. Em parte das 27 respostas inválidas, o juiz avaliou respostas honestas sobre dados ausentes; essas médias não valem como medida das jornadas datadas.

## Custo e ledgers (somente leitura, antes e depois de cada bloco)

| Ponto | Primário `data/runtime/budget.sqlite3` (ID, comprometido) | Campanha `budget-v080-qa.sqlite3` (ID, comprometido) | Reservas |
|---|---|---|---|
| Antes | 2346, US$0,94504185 | 730, US$0,38283761 | 0 / 0 |
| Tentativa recusada pela guarda | sem mudança | sem mudança | 0 / 0 |
| Depois de `healthy` | 2691, US$1,13814171 | 1075, US$0,57593747 | 0 / 0 |
| Depois de `conversations` (final) | 2733, US$1,14385079 | 1117, US$0,58164655 | 0 / 0 |

| Bloco | Lançamentos | Delta (iguais nos dois ledgers) | Por modelo |
|---|---:|---:|---|
| `healthy` | 345 | US$0,19309986 | gpt-6-luna US$0,16561876; deepseek-flash US$0,02747534; embeddings US$0,00000576 |
| `conversations` | 42 | US$0,00570908 | gpt-6-luna US$0,00570750; embeddings US$0,00000158 |
| **Total r4** | 387 | **US$0,19880894** | — |

Gate da rodada: US$0,25; usados US$0,19880894; sobram **US$0,05119106** do gate. Cap fixo `v080-qa` US$1,10: comprometidos US$0,58164655, restam **US$0,51835345**. Primário (teto 1,70): restam US$0,55614921. Folga depois da reserva de juiz e holdout (US$0,43772873): US$0,08062472. Nenhum gasto ficou fora da guarda; a campanha não foi remontada.

## Artefatos (SHA-256)

| Arquivo | SHA-256 |
|---|---|
| [v080-healthy-r4.json](v080-healthy-r4.json) | `41a3b4d5736101e77a739bc04fbfb8c90d32d782159ced4f4e08410eba7fa230` |
| [v080-healthy-r4.md](v080-healthy-r4.md) | `3fae43fb500e1e8d676a6dc26fa3313929aabf60fe13ff36a9ae1abe791adbe4` |
| [v080-conversations-r4.json](v080-conversations-r4.json) | `c4da45ae3c6d808547fb6a829f8d8b1ea1ad9655f817e9e664d21bf1fe379ece` |
| [v080-conversations-r4.md](v080-conversations-r4.md) | `7f8733881772ab30a8960cd40e19bbd508ccb8b710f421f04c67a7e0b85bf1d1` |
| [v080-healthy-traces-r4.json](v080-healthy-traces-r4.json) | `6d5d35099008c91cf5608e2f33754286340240289ff5900e2dcb84a8b1839b18` |
| [v080-conversations-traces-r4.json](v080-conversations-traces-r4.json) | `f156b0dedbddebfb91ad595d480cc4ba2617a872ef4afcc083dd792d6c2b2d01` |
| `.pytest_cache/qa-v080-r1/qa-r4-results/healthy.stdout.log` | `7ebe26448eb33e7c8af4bb8bfd4dcd288028cca0c7c258820bdc07442a90311a` (stderr vazio) |
| `.pytest_cache/qa-v080-r1/qa-r4-results/conversations.stdout.log` | `2dab2a99d6c55d39ba4d326b5d7ec29fbf9a39c4e2aafa30f9199e761126da99` (stderr vazio) |
| `.pytest_cache/qa-v080-r1/qa-r4-results/healthy-attempt1-refused.stdout.log` / `.stderr.log` | `f418bd62…eadd` / `cf3caac3…0b` |
| `.pytest_cache/qa-v080-r1/qa-r4-results/suite-strict.log` | `9bcfc598dc8bf52cecea5a7548fc08be93bee8c5974c6e5dd1f6aa39699d5812` |

## Limitações

- 27 das 63 respostas do bloco `healthy` estão inválidas por ambiente; os números agregados do relatório (`passed` 0,492) misturam válidas e inválidas e não medem o candidato.
- CA-49 sem `REPLAN-PROCEDURE` válido e sem `REPLAN-TOOL-DOWN`.
- A repetição 3 de CA-51 é inconclusiva (no máximo 12/13).
- O seletor é um harness fora do repositório, com dois ajustes registrados acima.

## O que a história ensinou sobre o próprio roteiro

As jornadas dizem "ontem", e a seed sintética é relativa ao dia em que foi gerada. Um runtime preservado de um dia para outro deixa de corresponder aos rótulos sem nenhum aviso. Isso vale também para o holdout (D17) e para o smoke, se reaproveitarem runtime. Antes de qualquer bloco pago, a rodada precisa confirmar que o dia-base da seed é o dia corrente no fuso da aplicação, ou ressemear o runtime isolado. Ressemear é uma decisão do Supervisor: a seed recria as tabelas sintéticas e preserva handoffs e auditoria.

## Como terminou

O lojista que perguntou sobre a antecipação no próprio plano, sobre aproximação numa maquininha inexistente, sobre a conexão da maquininha e sobre o status da habilitação recebeu respostas honestas e úteis. O lojista que confirmou "deu certo" viu o caso encerrado como resolvido. Quem perguntou pelas vendas de "ontem" ouviu que não havia venda nesse dia, o que era verdade para os dados daquele runtime, mas não era a situação que a jornada queria testar. Em respostas corretas sobre falta de evidência de taxa, a régua literal ainda marcou falha. Um pedido de encerramento de contrato recebeu pergunta de esclarecimento em vez de ir para um atendente. A rodada termina reprovada para o pré-holdout, com o mock desligado, os ledgers conferidos e o holdout intacto.
