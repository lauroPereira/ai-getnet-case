# Passagem de papel: QA v0.9.0, modo híbrido pela API (complemento do momento 4), rodada 1

- **Papel e responsável:** QA (subagente, contexto novo), 2026-11-05, de 23:24 a 23:40 UTC.
- **Objetivo e critérios:** confirmar pela API, com o padrão novo (`RETRIEVAL_MODE=hybrid`, `RERANK=off`), que o Knowledge se comporta bem fora do caminho feliz. São três perguntas reais, cada uma numa conversa nova: (1) sem evidência nas páginas, (2) fora de domínio com uma palavra comum ("taxa") e (3) termo exato de `dev`. A rodada fecha a segunda metade do momento 4 da história [juiz-retrieval-v090.md](../historias/juiz-retrieval-v090.md), que ficou "não verificada" em [v090-qa-retrieval-r1.md](v090-qa-retrieval-r1.md). Ela também vive a limitação do [ADR 0020](../architecture/decisions/0020-retrieval-hibrido-holdout.md): no híbrido, o atalho "sem evidência" só dispara quando o BM25 também não acha nada.
- **Escopo:** `POST /messages` e `GET /traces/{request_id}` de uma API local (uvicorn, Qdrant embutido), com o token do lojista sintético `cliente1988`. Ficaram fora desta rodada Docker, navegador, chamadas Anthropic e `eval --judge`.
- **Estado:** **apto**, com as observações e limitações abaixo.
- **Branch e PR:** `codex/v0.9.0-juiz-retrieval`, sem PR. Nada foi commitado.
- **Base e versão final:** o briefing fixou `195bc46`. Às 20:24:27 (-03:00), antes do primeiro passo desta rodada, o Supervisor commitou `1035cfe`, que só traz docs (`docs/relatorios/2026-11-05-noite-v090.md` e o índice). Todos os passos rodaram sobre `1035cfe`, com a árvore estável. `git diff d7775ff 1035cfe -- src tests prompts pyproject.toml .env.example` mostra só `config.py` (padrão `hybrid`), `.env.example` e dois testes, como descrito no commit `3746bcc`. `git status` mostra só os não rastreados de sempre.
- **Independência:** independente. O contexto era novo e eu não escrevi nem revisei o código.

## Ambiente e orçamento

| Item | Valor |
| --- | --- |
| Runtime isolado | `.pytest_cache/qa-v090-hybrid/runtime`, novo. Fica mantido para auditoria |
| Bootstrap | `merchant-assistant bootstrap` às 20:25 (-03:00), no mesmo dia local das perguntas: dados sintéticos semeados e índice de 145 chunks de 40 documentos a partir dos snapshots (`corpus_hash d7ed966b…`, `bm25_corpus_hash ca4109c8…25a98`, o mesmo da medição r1) |
| API | `uvicorn --factory merchant_assistant.main:create_application --host 127.0.0.1 --port 8765` com o `.env` atual. `RETRIEVAL_MODE` e `RERANK` não foram definidos e valeram os padrões (`hybrid`/`off`). `DEMO_MODE=true` foi passado só para habilitar `GET /traces`. `/ready`: 145 chunks, `gpt-6-luna`, prompts `knowledge_rag@1`, `knowledge_web@2`, `replan@2`, `router@6` |
| Token | `merchant-assistant auth token --url http://127.0.0.1:8765` (padrão `DEMO_USER_PASSWORDS` do `.env`), guardado num arquivo temporário e apagado no fim. Nenhum valor foi copiado |
| Variáveis de orçamento | `BUDGET_RUNTIME_DIR=data/runtime`. `BUDGET_LIMIT_USD=1.55` no bootstrap e `0.13` na API (ver "Premissa do briefing") |

### Premissa do briefing: onde a API e o bootstrap lançam o custo

O briefing esperava que os lançamentos fossem para o ledger do projeto (`BUDGET_RUNTIME_DIR=data/runtime`). Na prática, o `bootstrap` e a API lançaram em **`RUNTIME_DIR/budget.sqlite3`**, um ledger novo no runtime isolado, e não em `data/runtime/budget.sqlite3`. Pelo código, `build_orchestrator` (main.py:88) e o guard da CLI fora da avaliação (cli.py:24) usam `settings.runtime_path`; só `eval` usa `budget_runtime_path`.

Consequência prática: com `BUDGET_LIMIT_USD=1.55`, o ledger isolado gravou o teto 1,55 no sidecar e partiu do zero. Isso daria à API uma folga de US$1,55 fora do ledger do projeto, e não os ~US$0,13 que o briefing pretendia. Por isso subi a API com `BUDGET_LIMIT_USD=0.13`. O valor fica abaixo do sidecar 1,55 e é aceito pela guarda (`/ready` mostrou `budget_remaining_usd 0.1293`). Ele reproduz a folga pretendida: 1,41870799 + 0,13 ≈ 1,55 no total do projeto. Não é defeito desta versão: o comportamento é anterior à v0.9.0 e o README só fala do ledger da avaliação. Fica como pergunta ao Supervisor (ver "Achados").

## Pré-condição

`python tools/scripts/lint_and_tests.py --strict` sobre `1035cfe`: **2107 passed, 1 skipped** em 722 s, ruff sem achados, estrutura e skills válidas, verificador de caminhos pessoais sem ocorrência (754 arquivos), exit 0. A suíte começou às 20:25 (-03:00) e correu em paralelo com o bootstrap e as três perguntas. Desvio de ordem: as perguntas não esperaram o fim da pré-condição. O código era idêntico ao do candidato que o Reviewer validou, mais `3746bcc`, e a suíte passou.

## Momento a momento

Cada pergunta foi feita numa conversa nova, com `POST /messages` só com `message` e em seguida `GET /traces/{request_id}` com o mesmo token. As respostas e os traces completos ficaram em `<scratchpad da sessão>`.

### 1. Sem evidência nas páginas (NOEV)

- **Pergunta:** "A Getnet oferece seguro contra roubo da maquininha com cobertura internacional?"
- **Execução:** `request_id` `req_7bddaa267cc84d8ba2b6`, conversa `conv_99a7c0c074b24875ade7`. HTTP 200 em 12,6 s.
- **Resultado:** rota `knowledge`, status `answered`, `resolution.state` `awaiting_customer`, `plan_hops` 1. Agentes `router`, `knowledge`, `web` e `personality`; 4 chamadas de modelo, 0 ferramentas.
- **Resposta (completa):** "Não encontrei confirmação nas informações oficiais consultadas sobre a Getnet oferecer seguro contra roubo da maquininha ou cobertura internacional."
- `sources` e `citations` vazios.
- **Knowledge (`rag`, `knowledge_rag@1`), 6 hits:**
  - `todas-as-maquininhas#3`, score 0,030
  - `como-fazer-uma-venda-na-maquininha-getnet#1`, 0,030
  - `duvidas#39`, 0,029
  - `conta-digital#0`, 0,029
  - `get-tap#4`, 0,027
  - `todas-as-maquininhas#6`, 0,016
  
  Todos os documentos são `pub:` (páginas públicas oficiais). Os scores estão na escala RRF.
- **Replan:**
  1. `next=web`, `origin=rule:evidence_insufficient_web`, `evidence_sufficient=false`. O `knowledge_gap` do modelo diz que as passagens não informam seguro nem cobertura internacional.
  2. Depois do passo `web` (`knowledge_web@2`), `next=finish`, `origin=rule:gap_declared`, com o gap `web_gap_unconfirmed`.
- **Custo (ledger):** US$0,0115025 + US$0,00000036 de embedding da consulta. Quase tudo veio da busca web: o passo `knowledge` web lançou US$0,0109604.
- **Avaliação:** **conforme.** O assistente declarou a lacuna, tentou a web pelo replanejamento e não inventou valor, prazo nem condição. O `status answered` é coerente com uma resposta que diz o que não pôde confirmar. Isso confirma a limitação do ADR 0020: o BM25 achou tokens comuns ("maquininha"), então o atalho "sem evidência" não disparou e o modelo leu 6 passagens irrelevantes. Mesmo assim, ele declarou `evidence_sufficient=false` corretamente. O custo da limitação foi uma chamada de síntese a mais (US$0,0002234), sem efeito na resposta.

### 2. Fora de domínio com palavra comum

- **Pergunta:** "Qual a taxa de câmbio do dólar hoje?"
- **Execução:** `request_id` `req_25dfeff0da424f019fa5`, conversa `conv_05d3e1a1e9bd43e5b75a`. HTTP 200 em 8,4 s.
- **Resultado:** rota **`general_web`**, status `answered`, `plan_hops` 0. Agentes `router`, `knowledge` e `personality`; 3 chamadas de modelo.
- **Resposta:** "Hoje, 5 de novembro de 2026, a cotação PTAX do Banco Central é R$ 5,4615 para compra e R$ 5,4621 para venda por dólar."
- `sources`: 1 fonte `web` (`ptax.bcb.gov.br`).
- **Knowledge:** modo `web` (`knowledge_web@2`), **sem hits do índice**: nenhuma passagem da Getnet foi consultada.
- **Replan:** `next=finish`, `origin=rule:complete`, `evidence_sufficient=true`.
- **Custo (ledger):** US$0,01105897.
- **Avaliação:** **conforme.** O Router mandou a pergunta para a web geral e a palavra "taxa" não puxou as passagens de taxas da Getnet. Não conferi o valor da cotação, que fica fora do escopo do produto.

### 3. Termo exato de `dev` (R-EXACT-D30-en)

- **Pergunta**, copiada de `tests/scenarios/retrieval.jsonl`: "Which rates apply when I receive in D30?". Escolhi esta porque o denso real a deixava fora do top 6 na r1.
- **Execução:** `request_id` `req_eef1936eed5a414ea456`, conversa `conv_0d7a0ccee44d44e4a336`. HTTP 200 em 10,1 s.
- **Resultado:** rota `knowledge`, status `answered`, `plan_hops` 0. Agentes `router`, `knowledge` e `personality`; 3 chamadas de modelo.
- **Resposta:** "With receipt in D30, the public offer lists these rates: Getnet card machine: Debit 1,90%; credit 3,50%; installments from 6,09% for 2x to 16,59% for 12x. Get Tap: Debit 0,99%; credit 2,98%; installments from 5,98% for 2x to 15,88% for 12x. Your own rates depend on your contract."
- `sources`: 1 fonte `official`, `https://site.getnet.com.br/todas-as-maquininhas/`.
- **Citação construída:** `pub:site-getnet-com-br-todas-as-maquininhas#2-26b0638746ce857b`. É o **primeiro hit** e pertence ao documento esperado (`todas-as-maquininhas`).
- **Knowledge (`rag`), 6 hits:**
  - `todas-as-maquininhas#2`, **0,031**
  - `duvidas#41`, 0,016
  - `receba-ja-plano-de-recebimento-reduzido#3`, 0,016
  - `todas-as-maquininhas#1`, 0,016
  - `duvidas#40`, 0,016
  - `receba-ja-plano-de-recebimento-reduzido#0`, 0,016
  
  Todos `pub:`.
- **Replan:** `next=finish`, `origin=rule:complete`, `evidence_sufficient=true`.
- **Custo (ledger):** US$0,00073917 + US$0,0000002 de embedding.
- **Fundamentação conferida:** os 7 percentuais da resposta e a nota "*Taxas mediante recebimento em D30" estão no snapshot oficial `data/snapshots/public/pages/site-getnet-com-br-todas-as-maquininhas.json`. O excerto do hit 1 traz o bloco do Get Tap e a nota D30. O rótulo "Getnet card machine" para o bloco 1,90%/3,50% é uma leitura plausível da página: o bloco aparece na seção "Leve sua maquininha… pague apenas a taxa de transação", ao lado do link de pagamento.
- **Avaliação:** **conforme.** A resposta saiu da passagem certa, com citação, fonte oficial e `evidence_sufficient` verdadeiro.
- **Origem dos hits:** o trace não expõe `origin`. Pela escala RRF (k=60), um score de 0,031 só é possível com o item nas duas listas, ou seja, `both`; 0,016 ≈ 1/61 corresponde a uma lista só. Isso é inferência minha, coerente com a r1 (R-EXACT-D30-en, posição 1, `both`).

## Custo (somente leitura antes e depois)

| Ledger | Antes | Depois | Delta |
| --- | --- | --- | --- |
| Projeto `data/runtime/budget.sqlite3` | `max(id)` 3826, US$1,41870799, tudo `settled`, 0 `claude%` | idêntico | **US$0** |
| Isolado `.pytest_cache/qa-v090-hybrid/runtime/budget.sqlite3` (sidecar 1,55) | não existia | `max(id)` 15, US$0,02404412, 15 `settled`, 0 `claude%` | **US$0,02404412** |

Detalhe do delta do ledger isolado:

| Origem | Valor |
| --- | --- |
| Bootstrap (3 lotes de embeddings) | US$0,00074292 |
| Pergunta 1 | US$0,0115025 |
| Pergunta 2 | US$0,01105897 |
| Pergunta 3 | US$0,00073917 |
| Embeddings das consultas | US$0,00000056 |

- **Total da rodada:** US$0,02404412, abaixo dos US$0,05 esperados. Somado ao ledger do projeto, o gasto equivale a US$1,44275211, abaixo dos US$1,55 do briefing e do teto persistido de US$2,00.
- O ledger Anthropic (`data/runtime/anthropic`) não foi tocado.

## Regressão

- **Suíte estrita** (pré-condição acima): 2107 passed, 1 skipped, exit 0.
- **Árvore durante a suíte:** `src/`, `tests/` e `prompts/` não mudaram. O rascunho deste arquivo ficou cerca de 40 s em `docs/evidence/` (20:33 a 20:34, -03:00) e foi retirado até o fim da suíte. Nenhum teste varre `docs/evidence/`: os que citam evidência abrem arquivos nomeados. O verificador de caminhos rodou no início. Por isso a execução vale.
- **Fumaça de produto:** as três perguntas acima, com o padrão `hybrid`/`off`.

## Critérios comprovados e não verificados

- **Comprovados:**
  - Com o padrão novo (`hybrid`/`off`), sem evidência, o assistente declara a lacuna e passa pela web via replan (`rule:evidence_insufficient_web` → `rule:gap_declared`), sem inventar nada.
  - A pergunta fora de domínio com "taxa" vai para `general_web`, sem passagens da Getnet.
  - O termo exato `D30` é respondido a partir da passagem certa, com citação construída, fonte oficial e `evidence_sufficient=true`.
  - O momento 4 da história está fechado pela API.
- **Não verificados:**
  - A origem `dense`/`bm25`/`both` por hit, que o trace não expõe (inferida pelo score).
  - `source_kind` por hit: o trace só traz o prefixo `pub:` no `doc`.
  - O valor da cotação do dólar.
  - Variação entre execuções: uma execução por pergunta.

## Achados e limitações

- **Pergunta ao Supervisor (premissa do briefing).** O ledger usado pela API e pelo `bootstrap` local segue `RUNTIME_DIR`, não `BUDGET_RUNTIME_DIR`. Num QA pela API em runtime isolado, o custo não aparece em `data/runtime/budget.sqlite3`, e `BUDGET_LIMIT_USD` vira o teto de um ledger novo, sem somar o gasto do projeto. A linha do README sobre `BUDGET_RUNTIME_DIR` ("keep this pointed at the project budget volume when `RUNTIME_DIR` is isolated for a QA run") pode levar a crer que a API também o respeita. Contornei com `BUDGET_LIMIT_USD=0.13`. Cabe ao Supervisor decidir se isso é um registro no README ou uma tarefa futura. Não abri tarefa de defeito: o comportamento é anterior à versão, não impede o uso e o briefing é que presumia outro.
- **Observação 1.** Os hits do passo `knowledge` no trace trazem `doc`, `score`, `chunk_id` e `excerpt`, sem `origin` nem `source_kind`. Quem audita o híbrido pelo trace não vê se o hit veio do denso, do BM25 ou dos dois. O `eval-retrieval` mostra isso, mas a API não.
- **Observação 2.** `/health` e `/ready` informam `version 0.8.0` (`pyproject.toml` também está em 0.8.0), enquanto o CHANGELOG já tem `[0.9.0]`. Cabe ao Supervisor alinhar no fechamento.
- **Observação 3.** No trace da pergunta 2, `detail.citations` vem como `[null]` (rota `general_web`, sem passagem). É inofensivo, mas é um valor nulo dentro de uma lista.
- **Observação 4.** Na pergunta 1, o custo veio quase todo da busca web (US$0,011). A limitação do ADR 0020 (atalho que não dispara no híbrido) só acrescentou uma chamada de síntese barata.
- **Limitações:**
  - São 3 perguntas, uma execução cada.
  - A origem dos hits foi inferida pela escala do score.
  - O replanejamento para a web depende do conteúdo da web no momento.

Tarefas de defeito: nenhuma.

## Como terminou

O lojista perguntou por um seguro contra roubo com cobertura internacional. O assistente procurou nas páginas oficiais, não achou, tentou a web e respondeu com franqueza que não encontrou confirmação, sem inventar condições. Depois o lojista perguntou a cotação do dólar, e o assistente buscou a cotação do dia na web, sem confundir "taxa de câmbio" com as taxas da maquininha. Por fim, o lojista perguntou quais taxas valem no recebimento em D30. O assistente respondeu com os percentuais da página oficial de maquininhas, citou a página e lembrou que as taxas do contrato podem ser outras. As três conversas custaram cerca de 2,4 centavos de dólar.

## Próxima ação e responsável

O Supervisor decide o tratamento da pergunta sobre o ledger da API em runtime isolado e das observações 1 a 3. Depois, roda `tools/scripts/limpar-ambiente.ps1`. O runtime isolado fica mantido para auditoria.

## Decisão humana pendente

Nenhuma do QA.
