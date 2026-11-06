# Passagem de papel: revisão da tarefa 83 (rubrica `judge.v4` e remedição), rodada 1

- **Papel e responsável:** Reviewer (subagente, contexto frio), 2026-11-05.
- **Objetivo e critérios:** tarefa 83, lida só até "## Validação"; spec `rubrica-operacao-v0100.md` D1, D2 e CA-57; história `rubrica-operacao-v0100.md`, momentos 1 a 3; ADR 0021.
- **Escopo:** `1655e80` (`prompts/judge.v4.md`, `evaluation/judge.py`, `evaluation/scripted_judge.py`) e `9e66d20` (`evaluation/calibration.py`, `cli.py` nos blocos `eval` e `eval-calibrate`). Testes: `tests/unit/evaluation/test_judge_v4.py` (novo), `tests/integration/test_v0100_rubric.py` (novo) e `tests/unit/evaluation/test_judge_v3.py` (ajustado).
- **Estado:** **correções necessárias**. Nenhum P1, 2 P2 (lacunas de teste, uma delas com fonte duplicada do padrão da rubrica) e 4 P3.
- **Branch e PR:** `codex/v0.10.0-rubrica-operacao`, sem PR.
- **Base e versão final:** base `0266652`; candidato `9e66d20`, revisado sobre o export de `f4dfb97` (árvore `0d40239`). `3b180ff` e `f4dfb97` só mexem em documentação: `git diff 9e66d20 f4dfb97 -- src tests prompts` sai vazio. Não há manifesto `v0100-candidato-*.json`, então fixei o candidato pelos blobs: `judge.v3.md 7375786`, `judge.v4.md 2c0f2c9`, `cli.py b78866a`, `calibration.py 67404f7`, `judge.py 9b48a14`, `scripted_judge.py 73105e2`, `test_v0100_rubric.py 758fcb5`, `test_judge_v4.py e88ecd0` e `test_judge_v3.py 70f22bd`. Durante a revisão, o HEAD da branch avançou de `f4dfb97` para `023dc61` com os commits da tarefa 84 (`4b6891b`, `b6f7e19`, `ee7774a`, `023dc61`). `git diff --stat f4dfb97 023dc61` restrito a `prompts`, `evaluation/`, `cli.py`, `tests/unit/evaluation` e `test_v0100_rubric.py` sai vazio, então este parecer continua valendo para o candidato. O export ficou igual a `f4dfb97` no fim (`diff -rq` contra um novo `git archive`, desconsiderando só caches).
- **Independência:** independente. Não implementei nada e não li `v0100-developer.md` nem a Validação ou o Status da tarefa 83.

## Comandos e números

Rodei tudo em cópias de leitura em `<scratchpad da sessão>`: `git archive f4dfb97` (candidato), `git archive 0266652` (base) e uma terceira cópia para mutação. Usei o Python do `.venv` do projeto (3.13.3) com `PYTHONPATH` no `src/` da cópia, e conferi o módulo carregado (o `.venv` tem instalação editável apontando para a árvore de trabalho, que está sendo alterada pela tarefa 84). Não houve chamada paga, rede, Docker nem Git de escrita. Não toquei em `data/runtime/` nem em `.env`. O banco `.pytest_cache/qa-v080-r1/runtime/merchant.sqlite3` foi só copiado: sha256 `18968e43…881c87` antes e depois.

| Verificação | Resultado |
| --- | --- |
| `pytest` (export de `f4dfb97`, basetemp novo dentro do `.pytest_cache` da cópia) | **2116 passed, 0 skipped, 0 failed**, 942 s, exit 0 |
| `ruff check` (os 164 arquivos que `lint_and_tests.py` lista) | All checks passed |
| `validate_structure` e `validate_skills` (cópia) | válidas |
| `checar-caminhos-pessoais.py` (os 765 arquivos rastreados de `f4dfb97`, passados em lotes) | rc 0, nenhuma ocorrência |

As quatro etapas do `lint_and_tests.py --strict` rodaram separadamente, porque a cópia não tem `.git` e o verificador de caminhos depende de `git ls-files`. Observação: `ruff format --check` reformataria 4 dos arquivos tocados, mas isso não está no CI nem no `--strict`, e a base também falha nele. Não conta como achado.

## O que re-derivei e como

1. **Escopo do diff.** `git diff 0266652..9e66d20 --stat` mostra 8 arquivos, exatamente os esperados. Não mudam `tests/scenarios`, `evals`, `data`, `config.py`, a guarda de orçamento nem os rótulos, cenários e holdout. `prompts/judge.v3.md` tem sha256 `45d59f0c…75152bd` em `0266652` e em `9e66d20`, e o diff dele é vazio.
2. **`judge.v4.md` contra v3** (`git diff --no-index`). A v4 muda `version: 3` para `version: 4` e acrescenta a frase da D1 ("or a general claim stated as fact with no source in the evidence", com os dois exemplos) na definição de `unsupported_claim`. As linhas foram requebradas, mas o texto achatado é idêntico fora da frase, como o próprio teste confere. `JudgeScoreV3` não muda. O padrão continua v3: `RUBRIC_VERSION = "3"`, `validate_judge` e `scripted_judge` carregam `load_prompt(..., rubric_version(rubric))`, e `rubric_version(None)` devolve "3". `on_demand.py` continua fixado na `judge.v2`. Não há outro carregador de `judge` sem versão fixada (busquei `load_prompt(` em `src`); o único caminho que pega "a mais nova" é `prompt_versions()` (P3-1).
3. **Gravação por rubrica, pela CLI real** (`cli.main([...])`, com o DeepSeek programado atrás da fábrica real e uma chave sintética, sobre uma cópia do banco de QA):
   - `eval --judge-repeat 3 --rubric v4 --name probe-ds-v4` grava 72 julgamentos, `rubric_version` 4 e `evaluator.prompt` `judge@4`, e o modelo recebeu 72 prompts v4 e nenhum v3.
   - O mesmo comando sem `--rubric` (`probe-ds-v3`) grava 72 julgamentos `judge@3`, com 72 prompts v3 recebidos.
   - `eval --scripted --judge-repeat 1 --rubric v4` e `eval --scripted --judge --rubric v4 --limit 2` registram `judge_config` com `prompt: judge@4`.
   - `eval --scripted --rubric v4` sem juiz avisa que "--rubric is ignored".
4. **Relatório multi-bloco**, pela CLI real, com flags repetidas:
   - P1: três `--judge` (DeepSeek v4, Opus v3 `v090-juiz-opus-r3` real e DeepSeek v3) produzem os blocos O, A, B e C. A tabela das frases genéricas sai na ordem S01, S13, S16, S21 com a linha "Marcadas" (O 0 de 4, A 2 de 4, B 1 de 4, C 0 de 4). B reproduz o 1 de 4 do Opus na ADR 0021. A linha D2 sai para A contra O: (a) 0,917 contra 0,667, (b) 2 de 4, (c) ±1 sem piora, "Três condições atendidas: sim", sem decidir.
   - P2: o mesmo juiz com rubricas diferentes gera os blocos A v3 e B v4.
   - P9: um juiz só, `--rubric v4` e sem `--judge-run` escolhe a única execução v4.
5. **Recusas** (todas sem arquivo de saída e sem calibração gravada):
   - `--judge` repetido sem `--judge-run`: "2 --judge need 2 --judge-run".
   - `--rubric v5`: o argparse recusa com "invalid choice".
   - Execução nomeada com a rubrica errada: "gravou julgamentos judge.v4, não judge.v3: confira --rubric".
   - Pareamento fora de ordem, nos runs ou nas rubricas: recusado pela checagem de execução e de rubrica.
   - `--rubric` sem `--judge`: recusado.
   - Juiz sem nenhum julgamento v4 e sem `--judge-run`: "não há julgamento ... sob a rubrica judge.v4".
6. **Regressão da v0.9.0, com o código de `0266652` e o de `9e66d20`**, cada um sobre uma cópia própria do banco de QA:
   - `import_filled` com `now` fixo, no modo Opus (`--judge anthropic/claude-opus-5-5 --judge-run v090-juiz-opus-r3 --campaign v090-juiz-opus`) e no modo v0.8.0 sem juiz: os relatórios saem **byte a byte idênticos** (sha256 `82e6a216…` e `f0662ea2…` nas duas versões).
   - Pela CLI real (`eval-calibrate --import docs/evidence/v080-calibracao-amostra.csv --rater lauro --judge ... --judge-run ... --campaign v090-juiz-opus`): base e candidato saem idênticos, fora a linha "Gerado em".
   - Contra o `docs/evidence/v090-juiz-opus.md` publicado, a única diferença é a seção "Decisão pela regra D2 (Supervisor, 2026-11-05)", que foi acrescentada à mão.
7. **Mutação manual** (cópia própria, testes da tarefa mais `test_judge_v3`, `test_calibration_flow` e `test_v090_judge`). Foram **21 mutantes: 16 mortos, 2 equivalentes e 3 sobreviventes reais**. Antes de começar, o subconjunto passava: 119 passed.

| Mutante | Resultado |
| --- | --- |
| M01 frase da v4 removida | morto (`test_v4_is_v3_plus_the_one_sentence…`) |
| M02 `--rubric` ignorado em `_eval_rubric`; M03 em `validate_judge`; M04 em `scripted_judge` | mortos |
| M05 runs pareados em ordem inversa; M06b rubricas rotacionadas | mortos |
| M06 rubricas em ordem inversa | equivalente: a lista do teste `v4, v3, v4` é um palíndromo |
| M07 tolerância 0,05 para 0,10; M08 para 0,04; M09 veredito `>=` para `>`; M10 mínimo 2 para 3; M11 S21 trocado por S22 | mortos |
| M12 `judgement_for` ignora a rubrica | **sobreviveu** (P2-2) |
| M13 `_judge_rows` ignora a rubrica; M14 sem a checagem de execução sob outra rubrica; M15 sem a recusa de bloco repetido; M16 blocos sempre ligados, o que muda o relatório da v0.9.0; M18 análise de A trocada pela de O | mortos |
| M17 `_baseline` pega o último bloco v3 do mesmo juiz | sobreviveu, equivalente no teste e no comando planejado do QA (P3-4) |
| M19 padrão do parser de `eval --rubric` trocado de `v3` para `v4` | **sobreviveu** (P2-1) |
| M20 `eval-calibrate --judge` sem `action="append"` | **sobreviveu** (P2-1) |

Uma primeira passada caiu no M13 por codificação do console. Encerrei o processo e restaurei a cópia de mutação a partir do export, conferindo com `diff -rq`. Os mutantes M13 a M20 foram refeitos do zero; os resultados de M01 a M12 são da passada limpa, anterior à interrupção.

## Achados

### P1

Nenhum.

### P2

- **P2-1. O padrão da rubrica tem uma segunda fonte no parser, e nenhum teste passa pelo argparse de `--rubric` ou de `--judge` repetido.**
  - Condição: `cli.py:1345-1347` declara `eval --rubric` com `default="v3"`, e `cli.py:602` compara com `"v3"` literal. A D1 diz que o padrão é `RUBRIC_VERSION`, mas o parser não lê essa constante. Todos os testes de `--rubric` e de blocos montam `argparse.Namespace` à mão, e nenhum chama `cli.main([...])` com `--rubric` nem com `--judge` repetido.
  - Impacto: se a tarefa 86 trocar `RUBRIC_VERSION` para "4", `eval --judge` e `eval --judge-repeat` sem `--rubric` continuam enviando `v3`. Já `eval-calibrate` sem `--rubric` passa a ler v4, porque `_rubric(None)` devolve `RUBRIC_VERSION`. Os dois comandos ficariam com padrões diferentes, e o erro apareceria numa campanha paga. Uma regressão no parser também passa calada: M19 (padrão `v4`) sobrevive aos 6 arquivos pertinentes. M20 (sem `append`) também sobrevive, e nesse caso `--judge A --judge B` sem `--judge-run` usaria só B sem avisar.
  - Reprodução: mutantes M19 e M20 (tabela acima).
  - Correção sugerida: `default=None` no `eval --rubric`, deixando a resolução para `rubric_version(None)`, e o aviso comparando com `None` ou com `RUBRIC_VERSION`. Mais um teste no nível de `cli.main([...])` que confira `rubric_version` gravado sem `--rubric` (igual a `RUBRIC_VERSION`) e com `--rubric v4`, e que rode `eval-calibrate` com `--judge`, `--judge-run` e `--rubric` repetidos.
- **P2-2. A única guarda contra rotular julgamentos v3 como v4 no caminho "juiz sem `--judge-run`" não tem teste.**
  - Condição: quando o juiz pedido não tem julgamento na rubrica pedida, `choose_run` devolve `None`, e só o filtro de `judgement_for` (`evaluation/calibration.py:505`) impede a ligação com julgamentos de outra rubrica. O mutante M12, que remove esse filtro, sobrevive.
  - Impacto: com M12 aplicado numa cópia, `eval-calibrate --import … --judge anthropic/claude-opus-5-5 --rubric v4 --campaign probe-m12` sobre o banco de QA (sem nenhum julgamento Opus v4) termina com rc 0. Grava 24 calibrações e publica um bloco "A `anthropic/claude-opus-5-5` judge.v4" com os números do Opus v3 da v0.9.0 (groundedness 0,625 / 0,958). É exatamente o dado do CA-57, e o passo 5 da tarefa pede ligação inválida recusada. O código atual recusa corretamente (item 5 acima); a falta é de teste.
  - Correção sugerida: um teste com um juiz que só tem julgamentos v3, `--rubric v4` e sem `--judge-run`, que espere a recusa e nenhuma linha em `calibrations`.

### P3

- **P3-1. `prompt_versions()` passa a reportar `judge` "4" com o padrão em v3.**
  - Condição: `llm/prompts.py:25-28` lê o arquivo mais novo, e o resultado aparece em três lugares:
    - em `/ready` (`versions.prompts.judge`, via `orchestration/graph.py:820`);
    - no `prompt_set` de cada `run_snapshots`, gravado em cada atendimento (`api/v1.py:1065`);
    - no contexto de reaproveitamento das comparações (`comparisons.py:117` e `comparisons.py:76`).
  - Efeito: o formato do contrato não muda e nenhum teste fixa o valor. No `/ready` e nos snapshots, a informação fica imprecisa. A imprecisão já existia: antes o campo dizia "3" enquanto a avaliação sob demanda usa a v2. Nas comparações, as execuções gravadas antes do candidato deixam de ser reaproveitadas, porque o `prompt_set` mudou, e as células correspondentes rodam (e são pagas) de novo. Essa invalidação acontece uma vez só, sempre que um arquivo de prompt novo entra, e o juiz nem participa do atendimento. Continua sob as guardas de orçamento.
  - Encaminhamento: registrar na ADR 0022 e no README da tarefa 86. Fica a decisão de se `prompt_set` do atendimento deve incluir os prompts de avaliação. Reprodução: `prompt_versions(Path('prompts'))` dá `judge: '3'` na base e `judge: '4'` no candidato.
- **P3-2. O relatório do `eval` cita `judge.v3` fixo mesmo sob a v4.**
  - Condição: `evaluation/runner.py:527` escreve "o `judge.v3` não rebaixa o que não pode conferir". No relatório de `eval --scripted --judge-repeat 1 --rubric v4`, essa frase aparece na linha 21, enquanto a linha 3 do mesmo relatório traz `judge@4`.
  - Impacto: o relatório do momento 1, que vai para `docs/evidence/`, sai com o nome errado da rubrica.
- **P3-3. A conversão de nome de rubrica existe duas vezes.** `judge.rubric_version` (`evaluation/judge.py:45`) e `calibration._rubric` (`evaluation/calibration.py:1454`) fazem a mesma conversão com exceções diferentes. Uma das duas pode chamar a outra.
- **P3-4. A escolha da base da D2 entre vários blocos v3 do mesmo juiz não tem teste.**
  - Condição: `_baseline` (`evaluation/calibration.py:1270`) pega o primeiro bloco v3 do mesmo juiz, o que dá O quando o juiz é o original. Sem teste para isso, o M17 sobrevive, mas é equivalente no teste e no comando planejado do momento 3, que tem um bloco v3 por juiz.
  - Observação: para o DeepSeek, a base da D2 é a execução `legado` da v0.8.0, e não uma reexecução v3. A comparação v3 × v4 mistura, assim, a mudança da rubrica com a variação entre execuções. Isso é coerente com a D2, que fala da concordância atual de 0,667, mas o relatório só diz "o bloco `judge.v3` do mesmo juiz", sem dizer qual quando há mais de um. Vale uma frase no relatório e um teste.

## Critérios

| Critério | Situação |
| --- | --- |
| `judge.v3.md` intocado; `judge.v4.md` difere em uma frase | **comprovado** (sha256 e diff) |
| Esquema `JudgeScoreV3` inalterado; padrão v3; `rubric_version` e o prompt gravados certos | **comprovado** (CLI real, 72 + 72 julgamentos) |
| `--rubric` nos dois comandos; blocos pareados pela ordem; rubrica errada recusada | **comprovado** (sondas P1 a P9). Lacuna de teste no parser (P2-1) |
| Relatório multi-bloco com a tabela S01/S13/S16/S21 e a linha D2 sem decidir | **comprovado** |
| Sem `--rubric`, o relatório da v0.9.0 sai byte a byte igual | **comprovado** contra o código de `0266652` sobre o banco real de QA |
| Ligações inválidas recusadas | **comprovado** em execução; lacuna de teste no caminho sem `--judge-run` (P2-2) |
| Suíte estrita verde; caminhos limpos | **comprovado** (2116 passed; ruff, estrutura, skills, caminhos) |
| Momentos 1 a 3 com modelos reais (CA-57) | **não verificado**: é do QA, com chamada paga |

## Parecer e próxima ação

**Correções necessárias** para o candidato `9e66d20` (export `f4dfb97`), em revisão independente. O comportamento central está correto e foi re-derivado em execução: v4, gravação, multi-bloco, D2, recusas e regressão byte a byte da v0.9.0. Os dois P2 são de teste. O P2-1 inclui uma mudança pequena no parser, para que o padrão tenha uma fonte só antes da decisão da tarefa 86.

Próximo: o **Developer** corrige P2-1 e P2-2 (os P3 ficam a critério, com P3-1 e P3-4 registrados na tarefa 86). Depois, uma rodada 2 do Reviewer, restrita a `cli.py` e aos testes novos, com a reaplicação dos mutantes M12, M19 e M20. Não há decisão humana pendente nesta revisão.

Nenhum efeito no repositório além deste arquivo. Os processos em segundo plano (suíte e mutantes) terminaram antes deste relato.
