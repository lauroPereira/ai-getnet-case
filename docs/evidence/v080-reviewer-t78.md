# Revisão independente da tarefa 78 (rótulos CA-51) — v0.8.0

Reviewer nativo (`opus`/`high`) em contexto frio, 2026-11-05; sem a passagem do Developer; tarefa lida só até "## Validação"; holdout só por blob e hash.

## Rodada 1 — candidato `2b62993cd6f09f806d735ad266c29e1ad1872a0c` (r8)

**Parecer: correções necessárias.** As 10 respostas da tarefa são corretas e passam; CA-51 recalculado na composição da r5 dá 13/13 nas três repetições; nenhuma resposta aprovada passa a reprovar. Quatro formas novas, porém, aceitam sozinhas respostas erradas e plausíveis que o r7 recusava, contra a D15 ("sem aceitar contradições").

### Candidato e suíte
Tree `7fd0b1a0…` e 99 blobs conferem; fingerprint `fbf79539…9a09` recalculado; holdout blob `22dfee8b…af9d` em `658c70a`, `2b62993` e HEAD; `src/`, `prompts/`, `data/`, `tools/` sem mudança. Suíte em cópia `git archive 2b62993`: 1.544 passed e 1 skipped em 742 s (skip isolado e passado: 1.545); Ruff e skills ok; exit 0.

### D15 caso a caso
| request_id | Jornada | Correta | Forma que cobre | Específica |
| --- | --- | --- | --- | --- |
| 531ac9146987 | PRICE-DIVERGENCE r1 | sim | `found a difference` | sim |
| b84c1106aea3 | PRICE-DIVERGENCE r2 | sim | `but the recorded charge is R$` | **não** (P2-4) |
| 9a0b07470114 | PRICE-DIVERGENCE r3 | sim | `shows a difference` | sim |
| 64b06f9b7f24 | PRICE-CONDITIONS r2 | sim | `different pricing plans` | **não** (P2-2) |
| 45e5804e758a | PT-PRICE-CONDITIONS r2 | sim | `diferença entre as condições` | **não** (P2-3) |
| 3180af09b4e0, b8354030edbd | PRICE-INSUFFICIENT r2, r3 | sim | `no expected fee or recorded charge` | sim |
| af77a604682c | PT-PRICE-INSUFFICIENT r1 | sim | `taxa esperada calculável nem uma cobrança registrada` | aceitável (P3-4) |
| 025b4ed82d6f | PT-PRICE-INSUFFICIENT r3 | sim | `não há evidências suficientes para comparar` | sim |
| 932e426373de | SALE-CANCELLATION r2 | sim | `request to cancel` + `not been processed` | **não** (P2-1) |

### Pontuação cruzada (`runner._checks`, rótulos `658c70a` × `2b62993`)
r5: 23 → 33 aprovadas, só as 10 `content_ok` mudam. r4: 14 → 14 (três `forbidden_ok` caem em respostas já reprovadas). r3: 39 → 39. CA-51 composição r5: arquivado 11/8/10, rótulos r7 11/8/10, rótulos r8 **13/13/13**.

### Achados
- **P2-1** `tests/scenarios/business_journeys.jsonl:6`: os grupos `request to cancel` + `not (been) processed` aceitam sozinhas "…was rejected/denied/declined, so it has not been processed", "status … is unknown", "There isn't a request to cancel…", "We have no record of a request to cancel…" (`rejected` e `unknown` são estados reais). Sugestão: proibir essas formas ou exigir "received" junto de "not processed".
- **P2-2** linha 2: `different pricing plans` aceita "No different pricing plans were used", "were not used", "wasn't made under different pricing plans", "There were no different pricing plans". Sugestão: forma afirmativa `used different pricing plans` ou proibições das negações.
- **P2-3** linha 9: `diferença entre as condições` aceita "Não encontrei/identifiquei/vejo diferença entre as condições", "Não foi encontrada diferença…". Sugestão: proibir essas negações ou restringir a forma.
- **P2-4** linha 3: `but the recorded charge is/was R$` é fragmento sem proposição: "shows a fee of R$ 0,75, but the recorded charge is R$ 0,75" passa todas as checagens. Sugestão: forma presa ao fato ou outra proposição geral.
- **P3-1** `test_t78_ca51_archived.py:130-143, 226-240`: mutante `n't show a difference` sobrevive; incluir as sondas dos P2 como regressão, sozinhas e coladas.
- **P3-2** linha 11 + `runner.py:108-124`: "Há evidências suficientes para comparar a taxa" colada a resposta aceita passa; lacuna estrutural (um "não" solto não é qualificador), já existente no r7; registrar para a decisão de rubrica da v0.9.0.
- **P3-3** lacunas de lista só com texto colado (mesma classe já existente no r7): "The same pricing plans were used", "Os planos foram os mesmos", "The cancellation is complete/done", "No cancellation was requested" (já passava).
- **P3-4** linha 11: forma presa à redação de uma resposta, negação fora da forma; sem contradição encontrada.
- **P3-5** `v080-candidato-r8.json`, `commits_since_previous`: assunto do commit diferente do real ("fix: accept correct CA-51 wordings in six journey labels") e quatro commits só de docs omitidos; sem impacto em código.

### Mutações
14 pontos em cópia separada: 13 mortos; sobrevivente `n't show a difference` (P3-1).

### Próxima ação
Developer corrige P2-1 a P2-4 com P3-1 como regressão; novo candidato e revisão curta antes do reteste pago das seis jornadas.

## Rodada 2 — candidato `481eebd48c02306f6d2680438f51bf6ddc8ffd2f` (r9)

**Parecer: correções necessárias.** P2-1 a P2-4 e P3-1 fechados; as 10 respostas passam; pontuação cruzada `2b62993` × `481eebd` em 111 respostas: 0 mudanças (r3 39/39, r4 14/14, r5 33/33); CA-51 na composição da r5: 13/13 ×3. Dois P2 novos introduzidos pelas proibições.

- **Hashes:** tree `f86a5333…`, 99 blobs e fingerprint `83c7ee74…dcb0e` conferem; holdout blob `22dfee8b…af9d` em `658c70a`, `2b62993`, `481eebd` e HEAD; `src/`, `prompts/`, `data/`, `tools/` sem mudança.
- **Suíte** em cópia `git archive 481eebd`: 1.682 passed e 1 skipped em 671 s (skip isolado e passado: 1.683); Ruff e skills ok; exit 0.
- **Rodada 1:** todas as sondas reprovam agora, sozinhas e coladas; "Rejected:…", "There were no different pricing plans", "Não foram encontradas diferenças…", "R$ 0,75, but the recorded charge was R$ 0,75" reprovam; mutante `n't show a difference` morre.

### Achados novos
- **P2-5** `business_journeys.jsonl:6`: proibições nuas `rejected`, `declined`, `denied`, `refused`, `unknown`, `no record(s) of` recusam redações corretas de pendência que o r7/r8 aceitavam: "…was requested and has not been processed or rejected yet", "…there is no record of it being completed", "…is still pending: it has not been processed or rejected yet", "…hasn't been approved or declined yet". Correção: prender a afirmações ("was/been/is rejected", "status: rejected", "as rejected", "no record of a/the/your request") e incluir essas redações corretas como regressão (`test_t78_ca51_archived.py:374`).
- **P2-6** `business_journeys.jsonl:2`: "The charge … haven't/hasn't used different pricing plans" passa (contração de "have not used"); acrescentar `n't used different`.
- **P3-6** linhas 9 e 2: `não há diferença`, `sem diferença`, `nenhuma diferença`, `no different` recusam respostas corretas que citam atributos iguais ("Não há diferença no número de parcelas nem no canal", "The installments and channel were no different"); prender a "entre as condições/planos".
- **P3-7** falsas recusas pelo estreitamento (erro conservador, o r7 também recusava): "Há uma diferença entre as condições", "Different pricing plans were used", "made under different pricing plans", "R$ 0.00 … R$ 0.75", "R$0,00", espaço não separável. O QA deve conferir cada `content_ok` falho no reteste.
- **P3-8** 2 de 18 mutantes sobrevivem: devolver a linha 2 a `different pricing plans` e a linha 9 a `diferença entre as condições` mantém o teste verde; sondas que prendem: "Different pricing plans were never applied.", "Não detectamos diferença entre as condições.".
- **P3-9** estrutural (extensão do P3-2, para a decisão de rubrica da v0.9.0): paráfrases erradas ainda aceitas ("…not been processed and won't be", "cannot be processed", "was not approved/accepted", "Neither…", "It is not true that…", "Essa diferença entre as condições não existe", "…R$ 0,75, which is expected and correct"). Com o P2-5, `was not approved`, `was not accepted`, `will not be/won't be processed`, `cannot be processed` são acréscimos baratos.

### Mutações
18 em cópia separada: 16 mortas; sobreviventes as duas do P3-8.

### Próxima ação
Developer corrige P2-5 e P2-6, de preferência com P3-6 e P3-8 na mesma passada e as sondas como regressão; nova revisão curta antes do reteste pago.
