# Tarefa 105 — Comunicação do repositório: roadmap, notas operacionais e registros de processo

## Objetivo

Deixar a documentação versionada no tom de um produto em evolução: o README conta a história das versões como roadmap e traz só o que um operador precisa saber; registros de processo (relatórios de sessão, passagens, rodadas intermediárias de revisão e QA) saem do caminho do leitor; status de tarefas, histórias, specs e ADRs refletem o que já foi entregue.

## Especificação relacionada

Regra de comunicação do ciclo (responsável, 2026-11-06): documentação versionada descreve o produto e suas decisões; material de contexto fica em `discovery/`. Apoio local ao Developer: inventário no scratchpad da sessão (fornecido no despacho; nunca referenciado em arquivo versionado).

## Pré-condições

Worktree `ai-getnet-case-wt/pente-fino`, branch `docs/pente-fino` criada da `main` (`9d2587b`). Cópia local de `docs/relatorios/`, `docs/evidence/` e das specs de evolução já guardada pelo Supervisor em `discovery/process-archive/2026-11-06/`. Sem chamada paga; sem alteração de código além de dois comentários.

## Arquivos prováveis

`README.md`; `CHANGELOG.md` (só seções de versões já publicadas, nunca "Unreleased"); `docs/architecture/decisions/*.md`; `docs/specs/*.md`; `docs/historias/*.md`; `docs/tasks/*.md`; `docs/contracts/*.md`; `docs/wiki/origem-template.md`; `docs/relatorios/` (removido do versionamento); `docs/evidence/` (reduzido); `src/merchant_assistant/api/app.py` (um comentário); `docker/entrypoint.sh` (um comentário); `.env.example` (uma linha); `tools/scripts/` (verificador de links, se não existir).

## Passos

1. **README.** Reescrever como documento de produto: (a) remover a seção "Response to the evaluator's feedback", os parágrafos "History" e toda menção a feedback, avaliação, nota, ranking ou avaliador; (b) a tabela de versões conta a evolução como roadmap (o que cada versão trouxe e por quê, em termos de operação real); (c) "Limitations and next steps" vira **"Operating notes"**: só fatos que o operador precisa (perfil do compose, credenciais de demonstração, snapshots datados, orçamento), uma frase cada, sem a palavra limitação; (d) **"Roadmap"** com os itens das próximas versões como evolução planejada (identidade por provedor externo, canal de operador no celular, múltiplos workers, OTLP, cancelamento com confirmação, resumo de conversas longas), sem "falta" ou "não"; (e) cada tema aparece uma vez só; (f) links para evidência apontam só para resultados (QA final, calibração, holdouts, retrieval, candidatos, pareceres finais).
2. **CHANGELOG** (versões já publicadas): seções "Limitations" reduzidas a fatos de configuração ou removidas quando a versão seguinte fechou o item (acrescentar "superseded in vX" só onde ajudar o leitor); blocos "Fixed (task 54)", "Fixed (review r1, task 60)", "Fixed (QA r1, task 61)" condensados em uma linha cada; frases de processo (clean-clone smoke, replay, "does not claim", migração ampliada) removidas; nenhuma menção a feedback, nota ou avaliador. Não tocar em "Unreleased".
3. **ADRs.** 0016 reescrita como "Reabertura do escopo: roadmap de produção" (contexto em termos de operação real; sem nota, meta, ranking ou feedback); 0019 com status Aceita; 0013 e 0015 com nota de supersessão; em todas: "descartado" → "não adotado" com motivo, hipóteses e planos B removidos, frases desatualizadas reescritas no passado (lista por ADR no inventário).
4. **Specs.** `evolucao-pos-feedback.md` e `-plano.md` renomeados para `evolucao-producao-v070-v0100.md` e `-plano.md`; `evolucao-95.md` e `-plano.md` para `roadmap-v0110-v100.md` e `-plano.md`; seções "Problema" reescritas como objetivos de produto (o que uma operação real exige), tabelas de cobertura do feedback e de projeção removidas (ficam em `discovery/`), questões já decididas fechadas; `juiz-retrieval-v0110.md` com a meta de calibração como padrão do projeto; `rubrica-operacao-v0100.md`, `fechamento-v060-plano.md`, `api-kb-v050-proposta.md`, `juiz-retrieval-v090.md`, `incrementos-pos-nucleo.md` e `assistente-multiagente-lojista.md` (CA-25) com estado atual. Links atualizados em todo o repositório; AGENTS.md e CLAUDE.md **não** são editados: os nomes antigos entram como nota na passagem para PR separado do responsável.
5. **Histórias e tarefas.** Histórias com "pendente"/"ainda não executada" apontam o QA que as executou; tarefas entregues com checkboxes marcados e Status final; Status das 33 e 63 corrigidos.
6. **Registros de processo.** `git rm` de `docs/relatorios/` inteiro; em `docs/evidence/`, manter só resultados (`vXYZ-resultado*.md`, QA final de cada versão, candidatos, calibração, holdouts, retrieval, pareceres finais de revisão com estado apto) e remover passagens de Developer, rodadas intermediárias de revisão e QA, projeções de custo e triagens; `docs/evidence/README.md` reescrito como índice do que ficou. Links quebrados corrigidos ou removidos.
7. **Contrato e wiki.** `docs/contracts/api-v040.md` → `api-v1.md` com o contrato vigente (token, `interrupted`, sem `/v1/sessions`, URL do projeto web em vez de caminho local); `docs/wiki/origem-template.md` atualizado.
8. **Código (dois comentários e uma linha).** `api/app.py:60` (fallback de teste, não "until the graph is wired"); `docker/entrypoint.sh` com uma linha explicando o perfil de um worker; `.env.example:103` sem nome de branch.
9. **Verificação.** Verificador de links relativos em `tools/scripts/checar-links.py` (novo, se não existir) ligado ao `lint_and_tests.py`; `checar-caminhos-pessoais.py`; `grep -ri` por "feedback", "avaliador", "evaluator", "nota", "ranking", "benchmark", "minha falha", "erro do", "descartado" nos arquivos versionados com zero ocorrências fora de contexto legítimo (por exemplo, "feedback do lojista" numa tool); suíte estrita.

## Critérios de conclusão

- README sem menção a feedback, nota ou avaliador; "Operating notes" e "Roadmap" no lugar de "Limitations and next steps"; cada tema em um lugar.
- `docs/relatorios/` fora do versionamento; `docs/evidence/` só com resultados e índice; nenhum link quebrado.
- Specs renomeadas e neutras; ADRs com status e voz corretos; histórias e tarefas com estado real.
- Verificador de links no `lint_and_tests.py`; suíte estrita verde; caminhos pessoais limpos.

## Validação

Developer, rodada 1 (2026-11-06), branch `docs/pente-fino`, base `0c8bd1b`, código e testes da suíte em `d00aba2`. Sem chamada paga.

- **Remoções e renomeações.** `docs/relatorios/` (11 arquivos) e 146 arquivos de `docs/evidence/` saíram do versionamento; ficam 152 (resultado consolidado, QA final, pareceres finais aptos, manifestos `*-candidato-r*.json`, execuções reais, calibração, holdouts, retrieval, `orcamento.md`) e o índice [docs/evidence/README.md](../evidence/README.md). Links para arquivos removidos em tarefas e evidências viraram texto; referências a linha de código usam `#L<n>`. `git mv`: as quatro specs do passo 4, `docs/contracts/api-v040.md` → `api-v1.md` e a ADR 0016 → `0016-reabertura-roadmap-producao.md`.
- **Verificador de links.** `tools/scripts/checar-links.py` (novo; links inline, imagens e referências fora de código; alvo dentro do repositório; âncoras pelo slug do GitHub) ligado ao `lint_and_tests.py` e ao `validate-project.ps1`; `tests/unit/test_checar_links.py` (4 testes). O link de AGENTS.md para o nome antigo do plano fica como aviso (`PENDING_PROTECTED`) até o PR do responsável. `lint_and_tests.py` repassa argumentos desconhecidos ao pytest no modo estrito.
- `python tools/scripts/checar-links.py`: nenhum alvo ausente em 322 arquivos Markdown; 1 aviso pendente (AGENTS.md:18).
- `python tools/scripts/checar-caminhos-pessoais.py`: nenhuma ocorrência em 633 arquivos.
- `git grep -i -E "feedback|avaliador|evaluator|ranking|benchmark|minha falha|erro do reviewer|descartad"`: as ocorrências restantes são de contexto legítimo: o avaliador sob demanda do produto (`EVALUATOR_*`, `run_evaluations.evaluator`, "avaliador fixo", "comentário do avaliador por IA"), o rotulador humano da calibração ("avaliador humano", colunas do avaliador), o feedback do lojista no acompanhamento técnico, ranking de retrieval, "resposta descartada" pelo proxy e caches descartados, nomes antigos dentro dos manifestos JSON de candidatos (registro com hashes), o modelo `docs/templates/decision-record.md`, esta tarefa, e AGENTS.md e CLAUDE.md (não editados).
- `python tools/scripts/lint_and_tests.py --strict --basetemp=<scratchpad da sessão>/... -p no:cacheprovider -rs` (`.venv` do worktree, árvore limpa em `d00aba2`, sem mudança durante a execução): **2153 passed, 1 skipped** em 1103 s; Ruff `All checks passed!`; estrutura, skills, caminhos e links válidos; exit 0. O skip é de ambiente (`test_v070_identity_r2.py:277`, só roda com basetemp sob `.pytest_cache`).

Developer, rodada 2 (2026-11-06), sobre a revisão independente da rodada 1; código e testes da suíte em `2555631`. Sem chamada paga.

- **P2-1:** a v0.4.0 aparece como validada com modelos programados: status do README ("independent review; QA uses real models … from v0.5.0 on"), tarefas 27 a 34, história `perfis-interface-v040.md` por momento (CA-33 por testes e revisão; CA-28 e RF-53 por regressão automatizada) e nota em "Notes" da 0.4.0 no CHANGELOG.
- **P2-2:** regras de operação voltaram ao imperativo no CHANGELOG (holdouts marcados como vistos, `bootstrap` no mesmo dia) e no README (captura no navegador, `bootstrap` antes da execução paga); a ADR 0020 voltou a citar o relacre após a revisão dos rótulos e a contagem por arquivo de relatório.
- **P2-3:** linhas de comportamento nas ADRs 0018 (`503` repetível após 5 s; bloqueios exercitados no Windows), 0019 (rota `knowledge_and_support` sem replanejamento) e 0022 (reivindicação compara o estado; registro por processo; lease no roadmap).
- **P2-4:** nota do worker único no README como regra de operação.
- **P2-5:** `docs/relatorios/` no `.gitignore`; o modelo de relatório aponta para `discovery/relatorios/`.
- **P2-6:** as transições de teto da v0.8.0 (primário 1,00 → 1,70 em 2026-11-04 e 1,70 → 2,00 em 2026-11-05; cap 1,10 → 1,40) estão consolidadas em [orcamento.md](../evidence/orcamento.md); `v080-custo-estimativa-r3.json` voltou.
- **P3:** `lint_and_tests.py` recusa argumento desconhecido sem `--strict`; `checar-links.py` resolve alvos contra `git ls-files`, com testes de alvo fora da raiz, título repetido e arquivo não rastreado (7 testes); o índice de evidências diz que os originais estão nas tags; as menções em texto a registros removidos citam a tag da versão; R2-04 voltou a "risco aceito"; "limitação" e "pós-feedback" saíram dos quatro pontos apontados.
- `checar-links.py`: nenhum alvo ausente em 322 arquivos Markdown; 1 aviso pendente (AGENTS.md:18). `checar-caminhos-pessoais.py`: nenhuma ocorrência em 634 arquivos.
- `python tools/scripts/lint_and_tests.py --strict --basetemp=<scratchpad da sessão>/... -rs` (`.venv` do worktree, árvore limpa em `2555631`): **2156 passed, 1 skipped** em 974 s; Ruff `All checks passed!`; estrutura, skills, caminhos e links válidos; exit 0. O skip é o mesmo de ambiente da rodada 1.

Developer, rodada 3 (2026-11-06): a ADR 0022 voltou a registrar a janela teórica (ABA) da reivindicação do `resume`, apontada na revisão da tarefa 84 e tratada no roadmap pela lease (v0.13.0). Só um `.md` mudou; `checar-links.py` sem alvo ausente e grep de vocabulário sem ocorrência nova.

## Status

```text
pronta para revisão (Developer, rodada 3)
```

Aberta pelo Supervisor em 2026-11-06.
