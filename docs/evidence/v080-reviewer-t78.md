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
