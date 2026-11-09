<!-- Papel: plano técnico do roadmap v0.11.0 a v1.0.0, derivado de roadmap-v0110-v100.md. -->

# Plano: roadmap v0.11.0 a v1.0.0

## Especificação relacionada

[Roadmap v0.11.0 a v1.0.0](roadmap-v0110-v100.md). Este plano detalha as capacidades e decisões técnicas das versões relacionadas.

## Decisões técnicas

### v0.11.0 — Juiz e retrieval

1. **Resumo da busca no trace** (RF-109). O passo `knowledge` em modo `web` e o passo `web` gravam em `detail` o texto da busca mascarado, com limite de 4 000 caracteres e truncamento anotado, além das URLs. O campo `web_summary` identifica texto gerado pelo modelo.
2. **Páginas citadas como evidência** (RF-110). Na avaliação, cada URL citada é buscada somente por HTTPS, com timeout, limite de bytes, proteção contra redirecionamento entre domínios, extração de texto, máscara e cache. Páginas indisponíveis usam o resumo da busca com nota explícita; nenhum acesso ocorre no turno do lojista.
3. **Juiz por afirmação** (RF-111). `judge_claims.v1` lista as afirmações; `judge.v5` julga cada uma contra a evidência e os quatro critérios. O código calcula `unsupported_claim` a partir dos vereditos. `judge.v5` é o padrão após a regra D6; v3 e v4 continuam selecionáveis.
4. **Calibração por afirmação** (RF-112). A ferramenta produz pacotes Markdown e CSVs de respostas e afirmações, permite mais de um rotulador, adjudicação divergente e medidas de concordância e kappa por resposta e por afirmação.
5. **Amostra selada** (RF-113). A amostragem aceita exclusões, estratos, rotas enriquecidas e semente explícita. O selo SHA-256 é conferido antes da importação; respostas e rótulos da calibração são mantidos separados do julgamento do modelo.
6. **Regra de promoção** (RF-113). A rubrica candidata precisa alcançar κ ≥ 0,6 contra o rótulo ouro no conjunto selado, sem queda superior a 0,05 no acordo ±1 de qualquer critério. `judge.v5` foi selecionado; a evidência da decisão está em [ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md) e na [síntese v0.11.0](../evidence/v0110-resultado.md).
7. **Retrieval** (RF-114). `eval-retrieval --mode hybrid@36` expõe a fusão RRF de mesma profundidade do reranker, cortada em 6, sem chamada de modelo. `RETRIEVAL_BM25_MIN_SCORE` filtra hits exclusivos de BM25 antes da fusão. O padrão é `RETRIEVAL_MODE=hybrid`, `RERANK=on`; `RERANK=off` preserva a ordem da fusão. A decisão e as [métricas](../evidence/v0110-retrieval.md) ficam registradas.
8. **Régua combinada** (RF-115). Os relatórios separam verificações determinísticas e conteúdo julgado; `passed = deterministic and content`. A opção `--rubric literal` mantém disponível a régua anterior.

### v0.12.0 — Orquestração, memória e escrita

9. **Resumo rolante** (RF-116). `conversations.summary`, `conversations.summary_until_message_id`; `ConversationStore.history()` devolve `{"summary": str | None, "recent": [...]}`; o resumo é gerado por `summary.v1` (esforço mínimo, ≤ 200 tokens, mascarado) só quando há mensagem nova fora da janela; prompts de Router, Support e Personality recebem o resumo como bloco de dados "Earlier in this conversation (summary)". Cacheado por id: uma chamada por avanço da janela.
10. **Registro de fatos** (RF-116). Tabela `conversation_facts(conversation_id, kind, value, source_tool, source_message_id, created_at)`, preenchida em `orchestration/graph.py` ao final do turno a partir de `ctx.outcomes` (valores, datas, protocolos, status, produtos) e de `cases.py` (protocolo `HO-`, pedido de cancelamento); nunca a partir de texto do modelo. A guarda de saída (`personality.py`) une `evidence_texts` com os valores do registro. O resumo nunca entra na guarda.
11. **Ablação** (RF-117). `Settings.replan = on|off`; com `off`, o grafo liga cada especialista diretamente a `personality` como antes da v0.8.0 (o plano inicial do Router continua). `eval --replan off` grava `replan=off` na configuração da campanha; `eval-compare --a <rel> --b <rel>` (sem chamada) gera o relatório pareado por caso, critério e rota, com bootstrap da diferença, e a seção "decisões de origem `model`" lida dos traces.
12. **ADR 0024** (RF-118). Documento; sem código. Inclui o diagrama dos dois desenhos e a condição de revisão (por exemplo, ablação mostrando ganho só nas decisões do modelo).
13. **Cancelamento com confirmação** (RF-119). Tabela `sale_cancellation_requests(request_id, customer_id, sale_id, amount, sale_date, state ∈ {pending_confirmation, confirmed, declined, expired}, protocol, created_at, confirmed_at, idempotency_key)`; ferramenta `request_sale_cancellation(sale_id)` com escopo `support:write`, que cria `pending_confirmation` e devolve o resumo; `confirm_sale_cancellation(request_id)` executada **por código**, não por function calling, quando o turno seguinte do lojista é uma confirmação explícita (classificação pelo Router: rótulo `confirmation` com `yes|no|other`); `no` ou 2 turnos sem confirmação → `declined`/`expired`. `support.v8` instrui a mostrar o resumo e pedir confirmação. Auditoria com o escopo de escrita. Jornada `V0120-CANCEL-CONFIRM` (3 turnos) no catálogo.

### v0.13.0 — Segurança e operação

14. **Emissor próprio** (RF-120). `api/identity.py`: `GET /v1/auth/authorize` (parâmetros `client_id`, `redirect_uri` registrado, `code_challenge` S256, `state`), página de login mínima do emissor (HTML servido pela API, sem framework), `POST /v1/auth/token` com `grant_type=authorization_code` (+ `code_verifier`) e `refresh_token` (rotativo: o anterior é revogado ao usar; família revogada se um token já usado reaparecer). Tabelas `auth_codes` e `refresh_tokens`. A interface Streamlit usa o redirecionamento; `password` fica marcado "demo" no `/docs`.
15. **Emissor externo** (RF-121). **Dex** (CNCF, Go, ~20 MB) no compose, perfil `oidc`, com usuários sintéticos estáticos; `OIDC_ISSUERS` (lista) com descoberta e JWKS cacheado; mapeamento de claims (`groups` → papel, escopos por papel) em `identity.py`; `iss` desconhecido → `401 invalid_issuer`.
16. **Telegram** (RF-122). Módulo `integrations/telegram.py`: serviço pequeno no compose (perfil `telegram`), recebe `handoff.created` como destino de webhook assinado, envia ao `TELEGRAM_OPERATOR_CHAT_ID` via Bot API, faz long polling dos comandos, chama `/v1/handoffs/{id}/claim|actions` com token de operador (`client_credentials` de um principal `operator` de serviço). Testes com Bot API falsa em processo. Desligado sem `TELEGRAM_BOT_TOKEN`.
17. **Lease multi-worker** (RF-123). `comparisons.worker_id`, `comparisons.heartbeat_at`; a thread renova a cada 5 s; órfã = heartbeat há mais de 20 s; `resume` reivindica em `BEGIN IMMEDIATE`; `_ACTIVE` sai; `_CASE_LOCKS` de `handoffs.py` sai onde `BEGIN IMMEDIATE` já serializa; `PRAGMA journal_mode=WAL` confirmado na abertura; `uvicorn --workers 2` no compose; teste de integração com dois processos reais e `taskkill` no dono.
18. **Webhooks e caso órfão** (RF-124, RF-125). Estado `exhausted` em `webhook_outbox`; `POST /v1/webhooks/deliveries/{id}/resend` (escopo `handoff:operate`); na subida, `exhausted` com idade > 1 h reentra uma vez; `handoffs.py` ganha `recover_orphans()` na subida: `open` sem evento de ticketing e sem intenção no outbox → intenção recriada.
19. **OTLP e dashboard** (RF-126). `opentelemetry-sdk` + exportador OTLP como dependência opcional (`[otel]`); spans por passo do trace já existente; coletor `otel/opentelemetry-collector` por perfil `otel`; `observability/grafana/assistant.json` com painéis sobre as métricas de `/metrics` (mistura de rotas, p95, custo por provedor, orçamento, encaminhamentos, origens do replan).

### v1.0.0 — Leitura e acesso

20. **Imagem e lockfile** (RF-127). `validate.yml` ganha o job `image` em tag: build e push para `ghcr.io/<owner>/ai-getnet-case:<tag>`; `docker-compose.yml` com `image:` e `build:` (a imagem publicada vence quando existe); `uv.lock` versionado; README "Run the tests inside the image".
21. **README** (RF-129, RF-98). Tabela antes × depois por área; trilha de 10 minutos; capturas (aba Operador, ticketing, Telegram); túnel testado com evidência.

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
| `data/migrations.py` | 0013 | 0014 | 0015, 0016 | — |
| `prompts/` | `judge_claims.v1`, `judge.v5` | `summary.v1`, `support.v8`, `router.v7` | — | — |
| `cli.py` | `eval-calibrate` (pacotes, `--rater`, `--adjudication`), `eval-retrieval --mode hybrid@36`, `--rubric v5` | `eval --replan`, `eval-compare` | — | — |
| `tests/` | páginas em processo, v5, calibração a dois, piso, régua combinada | resumo, fatos, ablação, cancelamento, jornada | PKCE, refresh rotativo, emissor externo, Telegram falso, dois processos, resend, órfãos, OTLP | links, imagem |
| `docker-compose.yml`, `.env.example` | — | — | perfis `oidc`, `telegram`, `otel`; `--workers 2` | `image:` |
| `.github/workflows/` | — | — | — | job `image` |
| Projeto web | — | — | login por redirecionamento | capturas |
| `docs/` | spec complementar, tarefas 87–91 e 91a, ADR 0023 | tarefas 92–96, ADR 0024 | tarefas 97–101, ADR 0025 | tarefas 102 e 104 |

Não alterar: `judge.v3`, `judge.v4`, holdouts selados da v0.8.0 e v0.9.0, snapshots públicos, regras financeiras das ferramentas, ledger. AGENTS.md, CLAUDE.md e `.claude/` só por PR aprovado.

## Modelo de dados

**Migração 0013 (v0.11.0), reversível.** `run_evaluations.claims` (JSON) para os julgamentos v5.

**Migração 0014 (v0.12.0), reversível.** `conversations.summary TEXT`, `conversations.summary_until_message_id INTEGER`; `conversation_facts(fact_id, conversation_id, kind, value, source_tool, source_message_id, created_at)`; `sale_cancellation_requests` (campos na decisão 13).

**Migração 0015 (v0.13.0), reversível.** `auth_codes(code_hash, principal_id, client_id, redirect_uri, code_challenge, expires_at, used_at)`; `refresh_tokens(token_hash, family_id, principal_id, issued_at, expires_at, used_at, revoked_at)`; `api_principals.issuer` (padrão: emissor próprio).

**Migração 0016 (v0.13.0), reversível.** `comparisons.worker_id`, `comparisons.heartbeat_at`; `webhook_outbox.state` aceita `exhausted`; `webhook_outbox.resend_count`.

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
| Validação do produto | calibração contra rótulos ouro; retrieval em dev e holdout; jornadas com régua combinada | conversa longa; ablação do replan; confirmação de cancelamento | identidade, recuperação multi-worker, webhooks e Telegram | imagem e acesso externo |
| Docker | — | — | perfis `oidc`, `telegram`, `otel` | imagem publicada |

## Riscos técnicos

| Risco | Mitigação / retorno |
| --- | --- |
| Página citada indisponível ou sem texto útil | Fallback no resumo da busca, identificado como resumo, e cache. |
| `judge_claims` lista afirmações demais ou de menos | Rotuladores podem acrescentar afirmações; métricas de calibração expõem divergências. |
| A amostra selada muda sem ser percebida | Hash conferido na importação; regras de atributos preservam os bytes no checkout. |
| Reranker falha ou a requisição alcança o limite de chamadas | A recuperação volta à ordem da fusão; `RERANK=off` segue disponível. |
| O piso BM25 remove um resultado útil | Padrão zero; comparação com os modos de controle. |
| `replan=off` reabre laços antigos | O grafo sem replan permanece coberto pela suíte; limites da requisição continuam ativos. |
| Confirmação de cancelamento mal classificada | Só uma confirmação explícita permite executar a ação; demais respostas não alteram o estado. |
| Refresh rotativo e clientes concorrentes | Reuso revoga a família de tokens; a tolerância está documentada. |
| Lease multi-worker e SQLite | WAL e transações `BEGIN IMMEDIATE` coordenam a propriedade da comparação. |
| Integração Telegram indisponível | O adaptador é opcional e os eventos continuam disponíveis no outbox assinado. |

## Orçamento

Chamadas a modelos com custo passam pela guarda de orçamento persistente da aplicação, que limita cada instalação conforme sua configuração. A avaliação de rubricas e o reranker de retrieval consomem esse limite; uma requisição sem reserva disponível é recusada antes da chamada. Os testes usam provedores simulados e não fazem chamadas pagas.

## Plano de implementação

**v0.11.0 — Juiz e retrieval**

87. Resumo da busca no trace e páginas citadas como evidência na avaliação, com cache, máscara e fallback (RF-109, RF-110).
88. `judge_claims.v1` e `judge.v5`, cálculo do veredito em código, seleção explícita de rubrica e persistência das afirmações (RF-111).
89. Calibração com pacotes, CSVs de afirmações, múltiplos rotuladores, adjudicação, medidas por resposta e por afirmação e amostra selada (RF-112, RF-113).
90. Controle `hybrid@36`, piso BM25 e régua combinada das jornadas (RF-114, RF-115).
91. Coerência entre a decisão do juiz, os padrões de retrieval, as evidências da versão e a documentação.
91a. Preservação dos bytes dos CSVs selados em qualquer checkout.

**v0.12.0 — Orquestração, memória e escrita**

92. Resumo rolante e registro de fatos; guarda de saída com fatos; migração 0014 (RF-116).
93. `replan=off`, `eval --replan`, `eval-compare`, seção das decisões `model` (RF-117).
94. Cancelamento com confirmação: tabela, ferramentas, rótulo de confirmação no Router, `support.v8`, jornada (RF-119).
95. ADR 0024 supervisor × grafo (RF-118).
96. Fechamento: regressão, candidato, revisão, QA real (conversa longa, ablação, jornada), evidência, README/CHANGELOG, tag.

**v0.13.0 — Segurança e operação**

97. Authorization code com PKCE, refresh rotativo, página de login, interface por redirecionamento; migração 0015 (RF-120).
98. Emissor OIDC externo (Dex) no compose e `OIDC_ISSUERS` (RF-121).
99. Lease multi-worker, locks removidos, WAL, `--workers 2`, teste com dois processos; `exhausted` e resend; `recover_orphans`; migração 0016 (RF-123, RF-124, RF-125).
100. Adaptador Telegram (RF-122).
101. OTLP e dashboard (RF-126); fechamento: regressão, candidato, revisão, QA real, evidência, ADR 0025, README/CHANGELOG, tag.

**v1.0.0 — Leitura e acesso**

102. Imagem no GHCR por tag, `uv.lock`, compose com `image:`, suíte dentro da imagem (RF-127).
104. README antes × depois por área, trilha de 10 minutos, capturas, túnel testado; CHANGELOG; fechamento e tag `v1.0.0` (RF-129, RF-98).
