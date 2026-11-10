<!-- Papel: especificação complementar da v0.13.0 (login por redirecionamento, emissor externo, operador no celular, múltiplos workers, reenvio de webhook, telemetria). -->

# Identidade e operação — v0.13.0

Complementa o [roadmap](roadmap-v0110-v100.md) (RF-120 a RF-126) e o [plano](roadmap-v0110-v100-plano.md) (decisões 14 a 19, tarefas 97 a 102). As migrações 0015 e 0016 seguem a migração de memória 0014 da v0.12.0.

## Resultado desejado

1. Login pela interface por redirecionamento (authorization code com PKCE) e renovação silenciosa por refresh token rotativo; o login por senha continua para smoke e CLI, marcado como demonstração.
2. A API aceita tokens de um emissor OIDC externo configurado, com mapeamento de grupos para papéis e escopos; emissor desconhecido é recusado.
3. O operador recebe o caso no Telegram e responde de lá; a resposta chega ao lojista na mesma conversa.
4. A API roda com dois workers; uma comparação interrompida num worker é retomada pelo outro sem pagar célula duas vezes.
5. Entrega de webhook esgotada pode ser reenviada; caso aberto sem ticket é completado na subida da API.
6. Exportação OTLP opcional dos spans e um dashboard versionado sobre `/metrics`.

## Decisões

| ID | Decisão | Motivo |
| --- | --- | --- |
| D1 | `GET /v1/auth/authorize` (cliente e `redirect_uri` registrados, PKCE S256, `state`), página de login mínima servida pela API, `POST /v1/auth/token` com `authorization_code` e `refresh_token`; código de uso único com validade curta; refresh rotativo com família revogada se um token já usado reaparecer; migração **0015** (`auth_codes`, `refresh_tokens`, `api_principals.issuer`) | Fluxo padrão de login web e renovação segura |
| D2 | Emissor externo **Dex** no compose (perfil `oidc`, usuários sintéticos estáticos); `OIDC_ISSUERS` com descoberta e JWKS em cache; `groups` → papel (ou o e-mail verificado e exato, quando o emissor não emite grupos, como os usuários estáticos do Dex; tarefa 102a); `iss` desconhecido → `401 invalid_issuer`; o emissor próprio continua o padrão. Principais externos identificam papel, `sub` e URL exata completa do `issuer`, com componentes percent-encoded separadamente; IDs locais permanecem iguais. O `operator_id` externo exposto em handoffs é o sufixo do principal, opaco e sujeito a mudança quando a configuração do emissor mudar. | Leve para o notebook; aberto |
| D3 | Adaptador Telegram como serviço pequeno (perfil `telegram`): recebe `handoff.created` como destino de webhook assinado, envia o resumo mascarado ao chat do operador, lê `/claim`, `/approve`, `/reply <texto>`, `/reject <instrução>` por long polling e chama `/v1/handoffs` com token de um principal `operator` de serviço; desligado sem `TELEGRAM_BOT_TOKEN` | Operador no celular, sobre a API que já existe |
| D4 | Registro de comparações por lease no banco (`worker_id`, `heartbeat_at`, renovação a cada 5 s, órfã depois de 20 s), retomada reivindicada em `BEGIN IMMEDIATE`; reservas pagas, incluindo embeddings de consulta, conferem a lease e a célula sob o mesmo lock da interrupção, liberado antes de chamar o provedor; resultado durável da mesma célula é restaurado sem nova chamada e recusa do orçamento permanece falha; sem resultado, só ledger comprovadamente sem tentativa paga permite retomar como `pending`, enquanto tentativa paga ou ledger incerto exige `retry_failed=true`; locks por processo removidos onde o SQLite já serializa; WAL confirmado; compose com `--workers 2`; migração **0016** (lease e `webhook_outbox.status = exhausted`, `resend_count`) | Múltiplos workers sem estado por processo |
| D5 | `exhausted` com reenvio manual (`POST /v1/webhooks/deliveries/{id}/resend`, escopo `handoff:operate`) e automático na subida para entregas esgotadas há mais de 1 h; `recover_orphans()` na subida recria a intenção de casos `open` com fluxo salvo, sem evento de ticketing nem intenção no outbox; o caso cujo turno parou antes do checkpoint se completa quando o lojista reenvia a mensagem (ADR 0018) | Recuperar entregas esgotadas preservando a ordem por caso e destino |
| D6 | OTLP opcional (`[otel]`, `OTEL_EXPORTER_OTLP_ENDPOINT`), spans por passo do trace, coletor por perfil `otel`; `observability/grafana/assistant.json` com rotas, p95, custo por provedor, orçamento, encaminhamentos e origens do replanejamento | Exportar traces e acompanhar métricas do serviço |

## Critérios de aceitação

- **CA-68** Authorization code com PKCE e refresh rotativo na interface; token do emissor externo aceito; emissor desconhecido recusado.
- **CA-69** Caso chega ao Telegram e a resposta do operador chega ao lojista; adaptador desligado por padrão.
- **CA-70** Dois workers; worker morto no meio de uma comparação; retomada pelo outro sem célula duplicada; rate limit, handoffs e outbox corretos com dois processos.
- **CA-71** Entrega esgotada reenviada; caso órfão completado na subida.
- **CA-72** Spans no coletor OTLP; dashboard carregado sobre `/metrics`.

## Tarefas

97. [Login por redirecionamento e refresh token](../tasks/97-authorization-code-refresh.md).
98. [Emissor OIDC externo](../tasks/98-emissor-externo.md).
99. [Múltiplos workers, reenvio de webhook e caso órfão](../tasks/99-workers-webhooks-orfaos.md).
100. [Operador no Telegram](../tasks/100-telegram.md).
101. [Telemetria OTLP e dashboard](../tasks/101-otlp-dashboard.md).
102. [Documentação e metadados da versão](../tasks/102-fechamento-v0130.md): contrato, configurações, README, CHANGELOG e versão do pacote.
102a. [Mapeamento dos usuários estáticos do Dex](../tasks/102a-dex-sem-claim-groups.md): usar e-mail verificado quando o emissor não inclui a claim `groups`.
