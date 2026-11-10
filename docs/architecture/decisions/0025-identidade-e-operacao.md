# 0025. Identidade e operação: login por redirecionamento com refresh rotativo, emissor OIDC externo, lease entre workers, reenvio de webhook, operador no Telegram e spans OTLP

## Título

Levar a identidade da demonstração ao fluxo padrão de login web (authorization code com PKCE e refresh rotativo) e aceitar emissores OIDC externos ao lado do emissor próprio; rodar a API com mais de um worker sem estado por processo; dar reenvio às entregas de webhook esgotadas e completar na subida os casos abertos sem aviso ao ticketing; atender o operador no Telegram sobre a fila que já existe; exportar spans OTLP e versionar um painel sobre `/metrics`.

## Status

**Aceita** (v0.13.0). Complementa as ADRs [0017](0017-identidade-principal-escopos.md) (identidade), [0018](0018-interrupcao-retomada-webhooks.md) (fila, webhooks e outbox) e [0022](0022-rubrica-v4-operacao-retomavel.md) (comparação retomável, métricas). Spec: [identidade-operacao-v0130.md](../../specs/identidade-operacao-v0130.md); plano: [decisões 14 a 19](../../specs/roadmap-v0110-v100-plano.md).

## Contexto

1. Desde a v0.7.0 (ADR 0017) o assistente emite JWT RS256 por `password` e `client_credentials`. A interface pedia a senha do usuário dentro dela, e o authorization code com PKCE ficou registrado como o caminho de produção. O verificador aceitava um único emissor: o próprio ou, por `JWT_JWKS_URL`, um que assinasse no formato do assistente (`role`, `scope`, `customer_id`), o que um provedor OIDC padrão não faz.
2. A comparação de perfis guardava em memória o registro das execuções em curso, e a fila de casos usava locks por processo (ADR 0022): a API rodava com um worker.
3. Uma entrega de webhook que esgotava as tentativas virava `failed` e ficava assim; um caso aberto por um turno que parou antes de avisar o ticketing esperava o lojista reenviar a mensagem (ADR 0018).
4. O operador trabalhava pela tela do ticketing, pela API ou pela CLI, sempre num computador.
5. A observabilidade tinha logs, traces em SQLite, `/metrics` e regras de alerta (ADR 0022), sem exportação num protocolo padrão e sem painel.

## Decisão

**Login por redirecionamento e refresh rotativo** (RF-120, tarefa 97).
- `GET /v1/auth/authorize` com `response_type=code`, `client_id` e `redirect_uri` registrados em `OAUTH_REDIRECT_URIS` (só clientes públicos; `https`, ou `http` no loopback; comparação exata), `code_challenge` S256 (RFC 7636) e `state` obrigatórios. Cliente ou URI não registrados recebem uma página de erro, sem redirecionamento; os demais erros voltam ao cliente com `error`, `state` e `iss` (RFC 9207).
- A página de login é HTML servido pela API, sem script, com `frame-ancestors 'none'`, `form-action` limitado à própria origem e à do `redirect_uri`, `no-store` e `no-referrer`; as tentativas contam no mesmo limite do `/v1/auth/token`. A senha certa devolve `303` ao cliente com `code`, `state` e `iss`.
- O código tem 256 bits, vale 60 s, fica no banco só como digest e é consumido na primeira apresentação. `POST /v1/auth/token` com `authorization_code` confere cliente, URI e `code_verifier`; qualquer divergência responde o mesmo `400 invalid_grant`. Um código reapresentado revoga a família que abriu.
- O refresh é rotativo: cada uso gasta o token e devolve outro da mesma família, com novo acesso e os escopos do papel. Vale 8 h sem uso e 24 h por família. Um refresh já usado, ou apresentado por outro cliente, revoga a família inteira, refresh e acessos. `POST /v1/auth/revoke` aceita o refresh do mesmo principal.
- `password` continua para o smoke e a CLI, marcado como demonstração no `/docs`. Migração **0015** (reversível): `auth_codes`, `refresh_tokens` e `api_principals.issuer`.

**Emissor OIDC externo** (RF-121, tarefa 98).
- `OIDC_ISSUERS` lista os emissores aceitos ao lado do próprio, que continua o padrão: `issuer`, `audience`, `groups` (grupo → `merchant`, `operator` ou `admin`) e, opcionalmente, `algorithms`, `groups_claim` e `customer_id_claim`. Configuração inválida impede a subida. `JWT_JWKS_URL` continua servindo para trocar o emissor próprio por um que assine no formato do assistente.
- O `iss` ainda não verificado só escolhe o caminho: emissor próprio, emissor configurado ou `401 invalid_issuer`, sem nenhuma busca. Para o externo valem só algoritmos assimétricos configurados, `kid` obrigatório, chave da JWKS com `alg` e `use` compatíveis, `iss` exato, `aud`, `exp` e `iat` obrigatórios, `nbf` quando presente, tolerância de 30 s e vida de até 24 h.
- O papel vem da claim de grupos, que precisa apontar exatamente um papel (senão `403 insufficient_scope`); os escopos são os do papel, nunca o `scope` do token. O lojista vem de uma claim controlada pelo administrador do emissor. O principal externo usa `<papel>:<sub percent-encoded>@<issuer percent-encoded>`; cada componente codifica seus bytes UTF-8 separadamente, e o `issuer` é a URL configurada exata, incluindo esquema e barra final. Os IDs locais permanecem iguais. O `operator_id` externo exposto em handoffs é o sufixo desse principal e, portanto, é opaco e pode mudar quando a configuração do emissor mudar.
- Descoberta e JWKS ficam em cache por 5 min. Um `kid` desconhecido renova no máximo uma vez a cada 30 s por emissor. Uma busca por vez, sem fila: os outros pedidos usam as chaves em cache. Cada resposta tem prazo total de 4 s, até 256 KiB e nenhum redirecionamento. Uma busca que falha suspende novas buscas daquele emissor por 30 s e mantém as chaves em cache por até 24 h; os outros emissores e o próprio seguem atendendo.
- Na demonstração, o Dex roda no perfil `oidc` do compose, com usuários sintéticos estáticos (lojista, operadora e um visitante sem papel). Os usuários estáticos do Dex v2.41.1 não emitem `groups`, então o exemplo mapeia o e-mail por endereço exato (`groups_claim` `email`); o e-mail precisa vir com `email_verified: true`, sem a qual não há papel. O exemplo lê o lojista de `name`; as duas claims são definidas pelo administrador (tarefa 102a).

**Lease entre workers** (RF-123, tarefa 99).
- Cada comparação em curso guarda `worker_id` (host, pid e um token da reivindicação) e `heartbeat_at`. A execução renova a lease a cada 5 s; passados 20 s sem renovação, qualquer worker marca a comparação `interrupted`.
- A retomada lê a linha, confere estado, fatores fixos, orçamento e limite da demo e grava a nova lease na mesma transação `BEGIN IMMEDIATE`. A reserva de orçamento de cada chamada, incluindo embeddings de consulta, confere a lease e o identificador da célula sob o lock que também serializa a interrupção. A chamada ao provedor ocorre após liberar esse lock.
- Ao interromper, a comparação restaura o resultado durável da célula e preserva `budget_denied` como falha. Sem resultado, o ledger comprova se a célula pode voltar a pendente. Uma reserva registrada ou um ledger inconclusivo exige retry explícito, e o custo de uma tentativa interrompida é registrado em `interrupted_attempts`.
- O registro em memória das comparações e os locks por caso saem; o SQLite serializa entre processos, com `journal_mode=WAL` conferido na abertura. Limite de taxa, fila e outbox já viviam no banco. O compose roda `API_WORKERS=2`; `1` volta a um worker.

**Reenvio de webhook e caso órfão** (RF-124, RF-125, tarefa 99).
- A entrega cujas tentativas acabaram fica `exhausted`. O operador a reenvia com `POST /v1/webhooks/deliveries/{delivery_id}/resend` (`handoff:operate`, auditado), e a subida de um worker reenvia uma vez as esgotadas há mais de 1 h. A ordem por caso e destino continua: os eventos seguintes esperam e saem depois do reenvio. Uma recusa do receptor é final.
- Na subida, `recover_orphans()` grava a intenção de `handoff.created` do caso `open` cujo fluxo está salvo em `human_review`, sem ticket, sem evento do ticketing e sem intenção no outbox, criado há mais de 2 min. O caso cujo fluxo ainda não foi salvo se completa quando o lojista reenvia a mensagem (ADR 0018).
- Migração **0016** (reversível): lease em `comparisons`, `webhook_outbox.status` com `exhausted` e `resend_count`.

**Operador no Telegram** (RF-122, tarefa 100).
- O adaptador é um serviço à parte (`integrations/telegram.py`, perfil `telegram`), desligado sem `TELEGRAM_BOT_TOKEN`. Para o assistente, ele é mais um destino de webhook assinado: recebe `handoff.created` só com `case_id`, `protocol` e o resumo mascarado, mascara de novo e envia ao único chat configurado.
- O operador responde por `/claim`, `/approve`, `/reply <texto>` e `/reject <instrução>` (ou pelos botões), lidos por long polling. Só o chat configurado é atendido, e só comandos sem sufixo ou com o `username` do próprio bot, lido por `getMe` antes da primeira leitura.
- Cada comando vira uma chamada a `/v1/handoffs` com o token de um operador de serviço (`telegram-operator`, `client_credentials`, papel `operator`). Cada update é aplicado uma vez: o id fica gravado antes da resposta, o offset avança depois e a chave de idempotência é `telegram-<update_id>`.
- O token do bot fica fora dos logs e das representações; o serviço não recebe as chaves dos provedores de modelo.

**Spans OTLP e painel** (RF-126, tarefa 101).
- Com o extra `[otel]` e `OTEL_EXPORTER_OTLP_ENDPOINT`, cada trace salvo vira um span `turn` com um filho por passo (nó, ferramenta, resposta do operador), com início, duração e status do próprio passo. A exportação é OTLP/HTTP em lote, com timeout de 2 s, num `TracerProvider` próprio: o provider global fica intocado.
- Os atributos vêm dos mesmos conjuntos fechados dos rótulos de `/metrics` (ADR 0022): rota, status, passo, agente, origem do replanejamento e provedores. Nenhum texto de mensagem, identificador, token ou texto de erro entra num span. Sem a variável, nada de `opentelemetry` é importado.
- `observability/grafana/assistant.json` mostra mistura de rotas, p95, custo por provedor, orçamento, encaminhamentos e origens do replanejamento, só com métricas que existem em `/metrics` (um teste confere cada consulta). O perfil `otel` sobe coletor, Prometheus (com `alerts/rules.yml`) e Grafana, com as portas no loopback.

## Alternativas consideradas

- **Keycloak como emissor externo da demonstração:** cerca de 1 GB de memória e subida lenta (ADR 0017). O Dex é leve e atende OIDC padrão; o verificador aceita qualquer emissor por configuração.
- **Refresh com janela de tolerância para renovações simultâneas:** a reapresentação de um refresh já usado é o sinal de roubo que o refresh rotativo existe para detectar, então revoga a família na hora. A interface renova do lado do servidor, num só lugar.
- **Só `JWT_JWKS_URL` para emissores externos:** exigiria do provedor o formato de claims do assistente. `OIDC_ISSUERS` mapeia grupos para papéis e mantém os escopos no código.
- **Telegram por `setWebhook`:** exige URL pública com HTTPS. O long polling funciona atrás de NAT, no notebook, sem expor a API.
- **Adaptador dentro do processo da API:** misturaria o token do bot com as chaves dos provedores e criaria um caminho de operador fora da fila. Como serviço à parte, ele usa as rotas de qualquer operador e sai do ar sem afetar a API.
- **Fila ou cache externo (Redis) para coordenar workers:** mais um serviço para a mesma garantia que o SQLite em `BEGIN IMMEDIATE` já dá num host.
- **Instrumentação automática do FastAPI e do httpx:** exportaria caminhos, parâmetros e endereços. Os spans saem do trace já gravado, com atributos de conjuntos fechados.

## Consequências

- A interface passa a entrar por redirecionamento e a renovar o acesso sem pedir a senha de novo. A mudança do lado do cliente fica no projeto web: PKCE, `state` e `iss` conferidos, troca do código e renovação no servidor, revogação do refresh no logout. O `password` atende o smoke e a CLI.
- Um provedor OIDC da organização entra por configuração, sem mudar rotas nem ferramentas; papéis e escopos continuam definidos no código.
- A API escala para mais workers num host com o mesmo SQLite; uma comparação interrompida num worker é retomada por outro sem pagar célula concluída de novo.
- Entregas esgotadas podem ser reenviadas manual ou automaticamente sem perder a ordem por caso; casos com fluxo salvo sem notificação ao ticketing têm a intenção recriada na subida.
- O operador atende do celular com as mesmas garantias da fila (idempotência, conflito, auditoria com `operator_id` `telegram`). O adaptador depende do acesso à Bot API e é opcional.
- A telemetria entra em qualquer coletor OTLP e num Grafana sem código novo; sem o extra ou a variável, o comportamento é o da v0.12.0.
- Contrato `/v1` aditivo. As migrações 0015 e 0016 são reversíveis; a descida da 0016 converte `exhausted` em `failed`, e a da 0015 remove códigos e refresh (efeito: novo login).

## Data

2026-11-07
