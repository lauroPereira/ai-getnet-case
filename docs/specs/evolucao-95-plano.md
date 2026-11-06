<!-- Papel: plano técnico do ciclo "caminho para 9,5" (v0.11.0 a v1.0.0), derivado de evolucao-95.md. -->

# Plano: caminho para 9,5 (v0.11.0 a v1.0.0)

## Especificação relacionada

[evolucao-95.md](evolucao-95.md), versão 0.1 (proposta, 2026-11-06). Base: `main` em `5fd59b2` (v0.10.0 mais correções de documentação). Cada versão segue o ciclo das anteriores: spec complementar curta → tarefas → Developer → Reviewer independente → candidato selado por hash → QA real com teto fixo → `docs/evidence/vXYZ-resultado.md` → merge local com a identidade do projeto → tag. A autorização por versão do AGENTS.md vale; o responsável entra no teto (Q21), na calibração (Q22), nas tags e no push.

Numeração reservada: tarefas **87 a 104**; migrações **0013 a 0015**; ADRs **0023 a 0025**; prompts novos `judge.v5`, `summary.v1`, `support.v8` (cancelamento), `knowledge_web.v3` (se o resumo da busca precisar de marcação).

## Decisões técnicas

### v0.11.0 — Juiz e retrieval

1. **Resumo da busca no trace** (RF-109). `agents/knowledge.py` já guarda o texto da busca em `evidence_texts` para a guarda de saída; o passo `knowledge` (modo `web`) e o passo `web` passam a gravar em `detail` o texto mascarado (teto de 4 000 caracteres, truncamento anotado) e as URLs. Nome do campo: `web_summary`, para o leitor nunca confundir com página.
2. **Páginas citadas como evidência** (RF-110). `evaluation/evidence.py` ganha um buscador de páginas: para cada URL de `web_summary`, `GET` com timeout curto, só `https`, sem seguir redirecionamento para outro domínio, extração de texto (HTML para texto com o mesmo extrator dos snapshots), máscara, teto igual ao das demais evidências, cache em `runtime/web_evidence/<sha256 da URL>.json` com data. A nota `WEB_NOTE` passa a ter três formas: página buscada, página indisponível (fallback no resumo), sem URL. O juiz recebe cada página como item de evidência com título e URL. Nos testes, um servidor HTTP em processo serve páginas fixas; nenhum teste sai para a rede.
3. **`judge.v5` em duas etapas** (RF-111). Duas chamadas por julgamento: `judge_claims.v1` (lista de afirmações, saída estruturada: `claims[]` com `text`, `kind ∈ {fact, value, date, status, promise, guidance, standard}`) e `judge.v5` (recebe as afirmações numeradas e a evidência; devolve por afirmação `verdict ∈ {supported, partial, generic, not_found}` e `support` com o trecho; devolve os quatro critérios como na v3). `unsupported_claim` é calculado em código: verdadeiro se alguma afirmação de tipo diferente de `standard` tiver `generic` ou `not_found`. `--rubric v5` nas mesmas resoluções da v4; cada julgamento grava as duas saídas. O custo por julgamento dobra em chamadas; a sonda de 5 casos mede antes da campanha.
4. **Calibração por afirmação** (RF-112). `eval-calibrate --sample` gera, além do CSV atual, um pacote por resposta em Markdown (`<id>.md`: pergunta, resposta, evidência completa por item, lista de afirmações numeradas com caixas para marcar) e um CSV de afirmações (`sample-claims.csv`: resposta, número, texto, marca em branco, campo para afirmação acrescentada). `--import` aceita `--rater <nome> <csv>` duas vezes; calcula o veredito humano por rotulador a partir das marcas; concordância humano × humano; `--adjudication <csv>` com o rótulo ouro e o motivo nas divergências; `--judge`/`--judge-run`/`--rubric` como hoje, agora contra o ouro. Kappa por afirmação (n = número de afirmações) ao lado do kappa por resposta.
5. **Amostra selada** (RF-113). `eval-calibrate --sample 36 --from <campanha v0.11.0> --exclude <amostra v0.8.0> --enrich knowledge,knowledge_and_support --seed <registrado>`; hash do pacote em `tests/scenarios/calibration_v0110.sha256` antes de qualquer julgamento humano ou por `judge.v5`. As respostas `general_web` da amostra vêm da campanha nova (com `web_summary`), não da v0.8.0.
6. **Candidatos e regra** (RF-113). Ordem fixa: (a) rejulgar as 24 da v0.8.0 sob `judge.v5` com DeepSeek para ajuste do prompt de afirmações (critério de parada escrito na tarefa: ≥ 3 das 4 genéricas marcadas, ≤ 1 falso positivo); (b) selar as 36; (c) rotulagem humana; (d) juiz 3× nas 60 com DeepSeek; (e) sonda Sonnet 5.5 em 5 casos; se couber no teto, Sonnet 3× nas 60; (f) ensemble calculado a partir de (d) e (e) sem chamada nova; (g) decisão pela regra da spec, registrada na ADR 0023. Nenhuma edição de prompt depois de (b).
7. **Retrieval** (RF-114). `eval-retrieval --mode hybrid@36` devolve os 36 da fusão sem reordenação por modelo, cortados em 6, como controle; `RETRIEVAL_BM25_MIN_SCORE` (padrão desligado) descarta hits só de BM25 abaixo do piso antes da fusão; tabela nos dois splits; `RERANK` decidido pela regra da ADR 0020.
8. **Régua combinada** (RF-115). `evaluation/scripted_policy.py` e o relatório de jornadas separam `deterministic` (como hoje) de `content` (juiz padrão: piso 4 em correção e relevância, `unsupported_claim` falso); `passed = deterministic and content`; o README mostra as duas colunas.

### v0.12.0 — Orquestração, memória e escrita

9. **Resumo rolante** (RF-116). `conversations.summary`, `conversations.summary_until_message_id`; `ConversationStore.history()` devolve `{"summary": str | None, "recent": [...]}`; o resumo é gerado por `summary.v1` (esforço mínimo, ≤ 200 tokens, mascarado) só quando há mensagem nova fora da janela; prompts de Router, Support e Personality recebem o resumo como bloco de dados "Earlier in this conversation (summary)". Cacheado por id: uma chamada por avanço da janela.
10. **Registro de fatos** (RF-116). Tabela `conversation_facts(conversation_id, kind, value, source_tool, source_message_id, created_at)`, preenchida em `orchestration/graph.py` ao final do turno a partir de `ctx.outcomes` (valores, datas, protocolos, status, produtos) e de `cases.py` (protocolo `HO-`, pedido de cancelamento); nunca a partir de texto do modelo. A guarda de saída (`personality.py`) une `evidence_texts` com os valores do registro. O resumo nunca entra na guarda.
11. **Ablação** (RF-117). `Settings.replan = on|off`; com `off`, o grafo liga cada especialista diretamente a `personality` como antes da v0.8.0 (o plano inicial do Router continua). `eval --replan off` grava `replan=off` na configuração da campanha; `eval-compare --a <rel> --b <rel>` (sem chamada) gera o relatório pareado por caso, critério e rota, com bootstrap da diferença, e a seção "decisões de origem `model`" lida dos traces.
12. **ADR 0024** (RF-118). Documento; sem código. Inclui o diagrama dos dois desenhos e a condição de revisão (por exemplo, ablação mostrando ganho só nas decisões do modelo).
13. **Cancelamento com confirmação** (RF-119). Tabela `sale_cancellation_requests(request_id, customer_id, sale_id, amount, sale_date, state ∈ {pending_confirmation, confirmed, declined, expired}, protocol, created_at, confirmed_at, idempotency_key)`; ferramenta `request_sale_cancellation(sale_id)` com escopo `support:write`, que cria `pending_confirmation` e devolve o resumo; `confirm_sale_cancellation(request_id)` executada **por código**, não por function calling, quando o turno seguinte do lojista é uma confirmação explícita (classificação pelo Router: rótulo `confirmation` com `yes|no|other`); `no` ou 2 turnos sem confirmação → `declined`/`expired`. `support.v8` instrui a mostrar o resumo e pedir confirmação. Auditoria com o escopo de escrita. Jornada `V0120-CANCEL-CONFIRM` (3 turnos) no catálogo.

### v0.13.0 — Segurança e operação

14. **Emissor próprio** (RF-120). `api/identity.py`: `GET /v1/auth/authorize` (parâmetros `client_id`, `redirect_uri` registrado, `code_challenge` S256, `state`), página de login mínima do emissor (HTML servido pela API, sem framework), `POST /v1/auth/token` com `grant_type=authorization_code` (+ `code_verifier`) e `refresh_token` (rotativo: o anterior é revogado ao usar; família revogada se um token já usado reaparecer). Tabelas `auth_codes` e `refresh_tokens`. A interface Streamlit usa o redirecionamento; `password` fica marcado "demo" no `/docs`.
15. **Emissor externo** (RF-121). **Dex** (CNCF, Go, ~20 MB) no compose, perfil `oidc`, com usuários sintéticos estáticos; `OIDC_ISSUERS` (lista) com descoberta e JWKS cacheado; mapeamento de claims (`groups` → papel, escopos por papel) em `identity.py`; `iss` desconhecido → `401 invalid_issuer`. Keycloak só se o avaliador pedir (Q24).
16. **Telegram** (RF-122). Módulo `integrations/telegram.py`: serviço pequeno no compose (perfil `telegram`), recebe `handoff.created` como destino de webhook assinado, envia ao `TELEGRAM_OPERATOR_CHAT_ID` via Bot API, faz long polling dos comandos, chama `/v1/handoffs/{id}/claim|actions` com token de operador (`client_credentials` de um principal `operator` de serviço). Testes com Bot API falsa em processo. Desligado sem `TELEGRAM_BOT_TOKEN`.
17. **Lease multi-worker** (RF-123). `comparisons.worker_id`, `comparisons.heartbeat_at`; a thread renova a cada 5 s; órfã = heartbeat há mais de 20 s; `resume` reivindica em `BEGIN IMMEDIATE`; `_ACTIVE` sai; `_CASE_LOCKS` de `handoffs.py` sai onde `BEGIN IMMEDIATE` já serializa; `PRAGMA journal_mode=WAL` confirmado na abertura; `uvicorn --workers 2` no compose; teste de integração com dois processos reais e `taskkill` no dono.
18. **Webhooks e caso órfão** (RF-124, RF-125). Estado `exhausted` em `webhook_outbox`; `POST /v1/webhooks/deliveries/{id}/resend` (escopo `handoff:operate`); na subida, `exhausted` com idade > 1 h reentra uma vez; `handoffs.py` ganha `recover_orphans()` na subida: `open` sem evento de ticketing e sem intenção no outbox → intenção recriada.
19. **OTLP e dashboard** (RF-126). `opentelemetry-sdk` + exportador OTLP como dependência opcional (`[otel]`); spans por passo do trace já existente; coletor `otel/opentelemetry-collector` por perfil `otel`; `observability/grafana/assistant.json` com painéis sobre as métricas de `/metrics` (mistura de rotas, p95, custo por provedor, orçamento, encaminhamentos, origens do replan).

### v1.0.0 — Leitura e acesso

20. **Imagem e lockfile** (RF-127). `validate.yml` ganha o job `image` em tag: build e push para `ghcr.io/<owner>/ai-getnet-case:<tag>`; `docker-compose.yml` com `image:` e `build:` (a imagem publicada vence quando existe); `uv.lock` versionado; README "Run the tests inside the image".
21. **`docs/process/`** (RF-128). `git mv` de `docs/relatorios/`, `docs/tasks/`, passagens e JSONs de evidência não citados pelo README para `docs/process/` com índice; verificador de links relativos em `tools/scripts/` e no `lint_and_tests.py`; AGENTS.md e CLAUDE.md citam os caminhos antigos: a mudança desses dois arquivos vai por PR separado para aprovação do responsável.
22. **README** (RF-129, RF-98). Tabela antes × depois por critério; trilha de 10 minutos; capturas (aba Operador, ticketing, Telegram); túnel testado com evidência.

## Componentes afetados

| Área | v0.11.0 | v0.12.0 | v0.13.0 | v1.0.0 |
| --- | --- | --- | --- | --- |
| `agents/` | `knowledge.py` (`web_summary`) | `replanner.py` (liga/desliga), `support.py` (cancelamento), `personality.py` (guarda com fatos), `router.py` (rótulo de confirmação) | — | — |
| `evaluation/` | `evidence.py` (páginas), `judge.py` (v5, duas etapas), `calibration.py` (afirmações, dois rotuladores, adjudicação), `scripted_policy.py` (régua combinada), `retrieval.py` (`hybrid@36`, piso) | `runner.py` (`--replan`), `compare.py` novo | — | — |
| `orchestration/` | — | `graph.py` (fatos, `replan=off`), `state.py` | — | — |
| `conversations.py`, `cases.py` | — | resumo, fatos, pedido de cancelamento | `recover_orphans` | — |
| `tools/` | — | `domain.py` (`request_sale_cancellation`, `confirm_sale_cancellation`), `registry.py` (escopo de escrita) | — | — |
| `api/` | — | — | `identity.py` (authorize, code, refresh, emissores externos), `v1.py` (resend), `webhooks.py` (`exhausted`) | — |
| `integrations/` | — | — | `telegram.py` novo | — |
| `comparisons.py`, `handoffs.py` | — | — | lease; locks removidos | — |
| `observability/` | — | — | `otel.py` novo, `grafana/assistant.json` | — |
| `rag/` | `index.py` (piso BM25, `hybrid@36`) | — | — | — |
| `data/migrations.py` | — | 0013 | 0014, 0015 | — |
| `prompts/` | `judge_claims.v1`, `judge.v5` | `summary.v1`, `support.v8`, `router.v7` | — | — |
| `cli.py` | `eval-calibrate` (pacotes, `--rater`, `--adjudication`), `eval-retrieval --mode hybrid@36`, `--rubric v5` | `eval --replan`, `eval-compare` | — | — |
| `tests/` | páginas em processo, v5, calibração a dois, piso, régua combinada | resumo, fatos, ablação, cancelamento, jornada | PKCE, refresh rotativo, emissor externo, Telegram falso, dois processos, resend, órfãos, OTLP | links, imagem |
| `docker-compose.yml`, `.env.example` | — | — | perfis `oidc`, `telegram`, `otel`; `--workers 2` | `image:` |
| `.github/workflows/` | — | — | — | job `image` |
| Projeto web | — | — | login por redirecionamento | capturas |
| `docs/` | spec complementar, tarefas 87–91, ADR 0023 | tarefas 92–96, ADR 0024 | tarefas 97–101, ADR 0025 | tarefas 102–104, `docs/process/` |

Não alterar: `judge.v3`, `judge.v4`, holdouts selados da v0.8.0 e v0.9.0, snapshots públicos, regras financeiras das ferramentas, ledger. AGENTS.md, CLAUDE.md e `.claude/` só por PR aprovado.

## Modelo de dados

**Migração 0013 (v0.12.0), reversível.** `conversations.summary TEXT`, `conversations.summary_until_message_id INTEGER`; `conversation_facts(fact_id, conversation_id, kind, value, source_tool, source_message_id, created_at)`; `sale_cancellation_requests` (campos na decisão 13); `run_evaluations.claims` (JSON) para os julgamentos v5.

**Migração 0014 (v0.13.0), reversível.** `auth_codes(code_hash, principal_id, client_id, redirect_uri, code_challenge, expires_at, used_at)`; `refresh_tokens(token_hash, family_id, principal_id, issued_at, expires_at, used_at, revoked_at)`; `api_principals.issuer` (padrão: emissor próprio).

**Migração 0015 (v0.13.0), reversível.** `comparisons.worker_id`, `comparisons.heartbeat_at`; `webhook_outbox.state` aceita `exhausted`; `webhook_outbox.resend_count`.

Cache de páginas da web em `runtime/web_evidence/`, fora das migrações. Checkpoints e BM25 como hoje.

## APIs ou interfaces

| Rota ou comando | Versão | Mudança |
| --- | --- | --- |
| `eval-calibrate --sample N --from --exclude --enrich --seed`; `--import --rater nome csv ×2 --adjudication csv --rubric v5` | v0.11.0 | Pacotes por afirmação; dois rotuladores; ouro |
| `eval --rubric v5`, `eval-rejudge --rubric v5` | v0.11.0 | Juiz em duas etapas |
| `eval-retrieval --mode hybrid@36`; `RETRIEVAL_BM25_MIN_SCORE` | v0.11.0 | Controle e piso |
| `eval --replan off`; `eval-compare --a --b` | v0.12.0 | Ablação |
| Ferramentas `request_sale_cancellation`, `confirm_sale_cancellation` (escopo `support:write`) | v0.12.0 | Escrita com confirmação; aditivo |
| `GET /v1/conversations/{id}` | v0.12.0 | + `summary`, `facts`; aditivo |
| `GET /v1/auth/authorize`, `POST /v1/auth/token` (`authorization_code`, `refresh_token`), `GET /v1/auth/login` (página) | v0.13.0 | Aditivo; `password` mantido |
| `OIDC_ISSUERS` | v0.13.0 | Tokens de emissor externo aceitos |
| `POST /v1/webhooks/deliveries/{id}/resend` | v0.13.0 | Aditivo |
| Serviço `telegram` (compose, perfil) | v0.13.0 | Novo; desligado por padrão |
| `uvicorn --workers 2` | v0.13.0 | Compose |
| `OTEL_EXPORTER_OTLP_ENDPOINT`; perfil `otel` | v0.13.0 | Opcional |
| `image: ghcr.io/...` | v1.0.0 | Compose usa a imagem publicada |

Contrato `/v1` aditivo em tudo. Nenhuma mudança incompatível.

## Estratégia de testes

| Nível | v0.11.0 | v0.12.0 | v0.13.0 | v1.0.0 |
| --- | --- | --- | --- | --- |
| Unidade | extração e máscara de página; truncamento; cálculo do veredito a partir das afirmações; kappa por afirmação e por resposta; adjudicação; piso BM25; `hybrid@36`; régua combinada | resumo cacheado por id; registro de fatos a partir de `outcomes`; guarda com fatos; estados do pedido de cancelamento; idempotência; `replan=off` | PKCE S256; código de uso único; refresh rotativo e família revogada; descoberta e JWKS de emissor externo (falso); lease e órfã; `exhausted`; `recover_orphans` | verificador de links |
| Contrato | `judge_claims.v1`, `judge.v5` | ferramentas de cancelamento; `summary`, `facts` | authorize/token; resend; Telegram (Bot API falsa) | — |
| Integração (programada) | avaliação com servidor de páginas em processo; calibração ponta a ponta com dois CSVs | conversa de 30 turnos com protocolo no turno 2; jornada de cancelamento (sim, não, repetição); ablação com modelo roteirizado | login por redirecionamento na interface (`AppTest`); dois processos reais e `taskkill`; webhook reenviado; caso órfão na subida; spans no coletor falso | suíte dentro da imagem |
| Validação real | rejulgar `general_web` com páginas; sonda Sonnet 5 casos; juiz 3× nas 60 por candidato; retrieval nos dois splits; jornadas pela régua combinada | conversa longa real; ablação em dev + holdout + conversas (1 execução, juiz 1×); jornada de cancelamento | 10 exemplos com 2 workers e emissor externo; Telegram com o bot do responsável | smoke pela imagem e pelo túnel |
| Docker | — | — | perfis `oidc`, `telegram`, `otel`; `checar-memoria.ps1` | imagem publicada |

## Riscos técnicos

| Risco | Mitigação / retorno |
| --- | --- |
| Página citada bloqueia ou devolve HTML sem texto | Fallback no resumo da busca com nota; extrator dos snapshots já lida com as páginas da Getnet |
| `judge_claims` lista afirmações demais ou de menos | Rotuladores podem acrescentar; kappa por afirmação mostra o efeito; ajuste só na fase (a), antes do selo |
| Duas chamadas por julgamento estouram o teto | Sonda de 5 casos; DeepSeek primeiro; Sonnet só se couber |
| `replan=off` reabrir laços antigos | O grafo sem `replan` é o da v0.7.0, coberto pela suíte; limites de chamadas e tempo valem |
| Confirmação de cancelamento mal classificada | Rótulo do Router validado em código; sem `yes` explícito nada executa; teste com "sim, mas…" → `other` |
| Refresh rotativo e clientes concorrentes | Família revogada em reuso; janela de tolerância de 10 s documentada |
| Dex não disponível para Windows no notebook | Imagem oficial no compose; teste com emissor falso em processo quando o Docker estiver fora |
| Dois workers e SQLite | WAL; `BEGIN IMMEDIATE`; teste real com dois processos; retorno: `--workers 1` no compose |
| Telegram exige rede e o sandbox bloqueia | QA com Bot API falsa cobre o fluxo; teste real só pelo responsável |
| `git mv` de `docs/` quebra links do README e dos ADRs | Verificador de links; AGENTS.md e CLAUDE.md por PR separado |

Retorno por versão: tag anterior + migração descendente.

## Orçamento

Situação em 2026-11-06: os três ledgers somam **US$5,14** liquidados (OpenAI 1,44; campanha v080 0,84; Anthropic 2,86), acima do teto global de US$5,00. O ledger Anthropic tem teto próprio de US$4,00 (folga US$1,14). **Nenhuma chamada paga deste ciclo antes da decisão Q21.**

Proposta ao responsável: novo teto global **US$6,25**; reserva de planejamento do ciclo **US$1,00**, mais a sonda e a eventual campanha do Sonnet decididas à parte depois da sonda.

| Etapa | Reserva | Limite operacional |
| --- | ---: | --- |
| v0.11.0: rejulgar `general_web` com páginas; ajuste v5 nas 24; juiz 3× nas 60 (DeepSeek); retrieval; jornadas | US$0,30 | Campanha `v0110-qa`, montagem única |
| v0.11.0: sonda Sonnet 5.5 (5 casos) | US$0,05 | Ledger Anthropic; decide a campanha Sonnet (fora desta reserva) |
| v0.12.0: conversa longa; ablação com × sem (dev 44 + holdout 25 + 4 conversas, 1 execução, juiz 1×); jornada de cancelamento | US$0,35 | Campanha `v0120-qa` |
| v0.13.0: 10 exemplos com 2 workers e emissor externo; Telegram | US$0,10 | Campanha `v0130-qa` |
| v1.0.0: smoke pela imagem e pelo túnel | US$0,05 | — |
| Contingência | US$0,15 | Só por decisão do responsável |
| **Total** | **US$1,00** | Sujeito a Q21 |

Regras como no ciclo anterior: estimativa antes de cada campanha; o limite efetivo no processo é o menor entre o teto da campanha e o saldo do ledger; falha da guarda é parada, nunca ampliação.

## Plano de implementação

Cada item vira um arquivo em `docs/tasks/` na abertura da versão.

**v0.11.0 — Juiz e retrieval**

87. Resumo da busca no trace (`web_summary`) e páginas citadas como evidência na avaliação, com cache, máscara, fallback e servidor de páginas em processo nos testes (RF-109, RF-110).
88. `judge_claims.v1` e `judge.v5`; veredito calculado em código; `--rubric v5` em `eval`, `eval-rejudge` e `eval-calibrate`; gravação das afirmações (RF-111).
89. Calibração por afirmação: pacotes, CSV de afirmações, dois rotuladores, adjudicação, kappa por afirmação e por resposta, amostra enriquecida e selada (RF-112, RF-113).
90. Retrieval: `hybrid@36`, piso BM25, tabela nos dois splits; régua combinada das jornadas (RF-114, RF-115).
91. Fechamento: regressão, candidato, revisão, QA real na ordem fixa da decisão 6 (a calibração humana entra quando o responsável e o segundo rotulador devolverem os CSVs), evidência, ADR 0023, README/CHANGELOG, tag.

**v0.12.0 — Orquestração, memória e escrita**

92. Resumo rolante e registro de fatos; guarda de saída com fatos; migração 0013 (RF-116).
93. `replan=off`, `eval --replan`, `eval-compare`, seção das decisões `model` (RF-117).
94. Cancelamento com confirmação: tabela, ferramentas, rótulo de confirmação no Router, `support.v8`, jornada (RF-119).
95. ADR 0024 supervisor × grafo (RF-118).
96. Fechamento: regressão, candidato, revisão, QA real (conversa longa, ablação, jornada), evidência, README/CHANGELOG, tag.

**v0.13.0 — Segurança e operação**

97. Authorization code com PKCE, refresh rotativo, página de login, interface por redirecionamento; migração 0014 (RF-120).
98. Emissor OIDC externo (Dex) no compose e `OIDC_ISSUERS` (RF-121).
99. Lease multi-worker, locks removidos, WAL, `--workers 2`, teste com dois processos; `exhausted` e resend; `recover_orphans`; migração 0015 (RF-123, RF-124, RF-125).
100. Adaptador Telegram (RF-122).
101. OTLP e dashboard (RF-126); fechamento: regressão, candidato, revisão, QA real, evidência, ADR 0025, README/CHANGELOG, tag.

**v1.0.0 — Leitura e acesso**

102. Imagem no GHCR por tag, `uv.lock`, compose com `image:`, suíte dentro da imagem (RF-127).
103. `docs/process/` com índice e verificador de links; PR separado para AGENTS.md e CLAUDE.md (RF-128).
104. README antes × depois por critério, trilha de 10 minutos, capturas, túnel testado; CHANGELOG; fechamento e tag `v1.0.0` (RF-129, RF-98).

**Paralelismo.** Dois escritores quando os arquivos não se tocam: 87 com 90; 92 com 94; 97 com 99; 102 com 103. A rotulagem humana (89) corre em paralelo com 92 a 94 se os CSVs atrasarem; a decisão do juiz (91) só fecha com eles.

**Estimativa.** Pela régua do ciclo anterior (quatro versões em três noites com dois times): v0.11.0 uma noite mais a rotulagem (~2 h do responsável, ~3 h do segundo rotulador); v0.12.0 uma noite; v0.13.0 uma noite e meia; v1.0.0 meia noite. **Cerca de quatro noites de fluxo**, sem vídeo.
