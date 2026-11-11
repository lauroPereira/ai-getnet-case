# Validação da v0.13.0

Registro da validação e da revisão independente da v0.13.0: login por redirecionamento com PKCE, emissor OIDC externo, dois workers com comparações retomáveis sem pagamento duplicado, reenvio de entregas e casos órfãos, operador no Telegram e telemetria por OTLP. Critérios CA-68 a CA-72 da [especificação](../specs/identidade-operacao-v0130.md). Resultado consolidado: [v0130-resultado.md](v0130-resultado.md).

## Candidato

| Item | Valor |
| --- | --- |
| Backend integrado na `main` | commit `bb7d860` ("Release v0.13.0"), árvore `8a30b12`, pelo merge `2bf3b59` (2026-11-10) |
| Interface integrada | commit `342da22`, árvore `0efb695`, pelo merge `4c2c86d` na `main` do repositório da interface |
| Login pela interface com dois workers | no candidato integrado (backend e interface), sem chamada paga |
| Ida e volta no Telegram | na integração sobre a v0.12.0, com a Bot API real e modelos roteirizados |
| Validação com modelo real | campanha `v0130-qa`, na linha de desenvolvimento da versão, antes da integração sobre a v0.12.0 |

## Ambiente

- **Modelo real:** Docker Compose com volumes novos e `API_WORKERS=2`; perfis `oidc` (Dex como emissor externo), `otel` (coletor, Prometheus e Grafana) e `telegram` (bot real); agente `gpt-6-luna`; Router `deepseek-flash` no perfil `hybrid` da comparação; embeddings `text-embedding-3-small`; teto da campanha US$0,15, com `MAX_REQUEST_COST_USD=0.012` na comparação.
- **Candidato integrado:** API com dois workers e interface Streamlit 1.66.1; Chrome em modo headless, com eventos reais de mouse e teclado e popup real de `window.open`; credenciais só as fictícias de `.env.example`; sem chave de provedor e com orçamento zero.

## Validação com modelo real, momento a momento

| Momento | Esperado | Observado | Evidência |
| --- | --- | --- | --- |
| Emissor externo (CA-68) | Token do Dex aceito; papel pelo e-mail verificado | `op_ana@operador.example`: `GET /v1/handoffs` 200 com `id_token` e com `access_token`. `cliente1988@lojista.example`: `POST /messages` 200, sem acesso à fila (403). Visitante com e-mail verificado e fora do mapeamento: 403 `insufficient_scope` | `req_9aecdcb657fc47758a8f`, `req_bd79003ff1c74394aa36`, `req_a19907701b104c0882e0`, `req_7943cba4b94043e4999c` |
| Emissor desconhecido (CA-68) | Recusado | 401 `invalid_issuer` em `GET /v1/handoffs` e em `POST /messages` | `req_791e797f3d77460c89a0`, `req_c186123ad0d743c48a91` |
| Login por redirecionamento na página da API (CA-68) | Código com PKCE S256 e refresh rotativo | 303 com `code`, `state` e `iss`; troca 200 com refresh; refresh antigo reapresentado: 400 `invalid_grant` e os acessos da família passam a 401; código reapresentado ou verificador errado: 400 | `req_994cb42b520440b599a4` |
| Dois workers (CA-70) | Atendimento nos dois processos | 10 de 10 exemplos com 200, 6 num processo e 4 no outro | Logs com `pid` |
| Worker morto na comparação (CA-70) | Retomada pelo outro processo sem célula duplicada | Comparação `pcmp_e9ba78bc7a3543289e56` (2 perfis × 3 cenários); `kill -9` no dono da lease com 4 células concluídas; `interrupted` em 19,8 s; `resume` 202 com 2 células; `completed`; novo `resume` 409 `comparison_completed`. 6 `request_id` distintos no ledger, um por célula; `cost_usd` de US$0,00475628 igual à soma das células e da tentativa interrompida | Ledger do volume |
| Ações simultâneas e limite de taxa (CA-70) | Uma ação vence; limite vale entre processos | Duas `reply` em paralelo: uma 200, outra 409 `already_resumed`. 32 mensagens em 47,9 s: as 30 primeiras respondidas (recusadas pela guarda de entrada, sem custo), a 31ª e a 32ª com 429 `rate_limited`, nos dois processos | `HO-20261108-A87927`, `req_bbd63ff4c3104ec699ce`, `req_80c3fb1167654d52b326` |
| Reenvio (CA-71) | Entrega esgotada reenviada, na ordem | Com o ticketing parado, 3 tentativas `exhausted`; com o ticketing de volta, reenvio 202 e `resend_count` 1; no ticket, `created` antes de `reply_delivered`; novo reenvio 409 `delivery_not_exhausted` | `HO-20261108-7E62A1`, `dlv_f5453c604ccc468596eb` |
| Caso órfão (CA-71) | Completado na subida | Caso sem intenção de entrega: uma recuperação na subida seguinte, com ticket criado; reiniciar a API não recupera de novo | `HO-20261108-31C024` |
| OTLP e painel (CA-72) | Spans no coletor; painel sobre `/metrics` | 312 spans em 52 traces, um `turn` raiz por requisição, atributos só dos conjuntos fechados (nenhum texto, lojista, token ou id); filhos com os mesmos nomes, ordem, durações e status dos passos de `GET /traces/{id}`; com o coletor parado, resposta 200 sem erro; Prometheus com o alvo ativo e 4 regras `ok`; Grafana 11.4.0 com os seis gráficos com dados | `req_8dd3c597a6b847bda78e`, `req_cf8cd89aac2247c49587`, `req_e627fbb2b6e04ed184b8` |
| Telegram desligado por padrão (CA-69) | Sem o perfil, sem adaptador | O serviço `telegram` não existe sem o perfil e `TELEGRAM_BOT_TOKEN` está vazio na API | `docker compose config --services` |
| Caso no Telegram (CA-69) | Caso no grupo do operador, sem dado sensível | `handoff.created` entregue na primeira tentativa; corpo só com `case_id`, protocolo e resumo, sem cartão, CPF, lojista ou transcrição; token do bot, id do grupo e segredos com 0 ocorrências nas 1.044 linhas do log do compose | `HO-20261108-EB4A51`, `req_edaf3b157f2d4d0baa5a` |
| Tokens do Dex nos dois workers (CA-70) | Atendimento e retorno da operadora | 3 turnos e um encaminhamento; a operadora do Dex assume e responde; a mensagem seguinte do lojista volta com `route: human_reply` e `via: operator`; cada evento entregue uma vez por destino | `HO-20261108-6F882A`, `req_649f654e1dfe4cbfa4af` |

## Validação sem chamada paga

| Verificação | Esperado | Observado |
| --- | --- | --- |
| Login pela interface (CA-68) | Sessão aberta pela janela do emissor | 10 logins: 10 trocas de código, 10 sessões abertas, nenhum login sem dono; a janela de login fecha sozinha; um envio do retorno por tentativa |
| Dois workers pela interface (CA-70) | Código emitido num processo e trocado no outro | 4 trocas cruzadas, todas com sessão aberta; a renovação também passou de um processo ao outro |
| Logout | Revogação no emissor | Depois de "Encerrar sessão", access 401 e refresh 400, para lojista e operadora |
| Operadora | Papel e fila | `op_ana` com papel operator e a aba Ticketing; `GET /tickets?status=new` 200 |
| Renovação | Sem pedir login | Com TTL de 90 s no ambiente de validação: `refresh_token` 200 e a sessão segue. Refresh antigo reapresentado: 400, e a família é revogada (refresh atual 400, access 401); a interface pede novo login com aviso |
| Recusas | Nenhuma troca indevida | URL da API não pareada ao emissor: aviso e nenhuma requisição. Troca de URL com sessão aberta: revogação no emissor original. `iss` adulterado: nenhuma troca. `state` adulterado: retorno ignorado. Janela bloqueada (emulada): aviso e nenhuma requisição |
| Exposição | Nada sensível na página | 42 valores sensíveis cruzados com 61 artefatos da aba: nenhum token nem verifier na página, na URL final ou no console; o `code` aparece só no envio do retorno ao próprio servidor da interface |
| Ida e volta no Telegram (CA-69) | Resposta do operador chega ao lojista | Caso sintético `HO-20261026-81D334` no grupo com protocolo, resumo e o botão Assumir; o operador assume e responde com `/reply` na mensagem do caso; caso `answered`, `claimed_by=telegram`; texto exato no histórico HTTP com `via=operator` e `operator_action=reply`, e o turno seguinte com `route=human_reply` |

Suítes do candidato integrado: backend com 2.944 testes aprovados, sem falhas nem pulados; Ruff, links e caminhos pessoais limpos. Interface com 158 testes aprovados (1 pulado sem o backend no caminho), 3 de integração com a API em processo e 2 do componente de login em JavaScript. Migrações 0015 e 0016 em sequência depois da 0014, nos dois sentidos, sem perda de dados.

## Custo

Campanha `v0130-qa`: US$0,06430987 (teto US$0,15). O login pela interface e a ida e volta no Telegram não usaram chamada paga.

## Revisão independente

A versão inteira, a integração com a v0.12.0, o candidato integrado e a interface passaram por revisão em contexto novo, sobre clone limpo.

### Re-derivado

- **Contrato:** OpenAPI só com acréscimos (duas rotas novas e `grant_type` ampliado); `api-v1.md` coerente com o código, incluindo os códigos da retomada da comparação.
- **Migrações** 0014 → 0015 → 0016 nos dois sentidos, sobre banco com dados das duas versões: estado restaurado byte a byte na descida e esquema igual ao de um banco novo na subida.
- **Identidade:** principais distintos por emissor, com `sub` e emissor codificados; `telegram-operator` só como operador; PKCE e refresh rotativo com revogação da família; revogação e contador por token isolados por emissor.
- **Dois workers:** corrida real de dois processos com o dono suspenso antes e depois da reserva paga: nenhum pagamento duplicado e a lease perdida registrada. Célula sem trace legível termina `failed`; recusa de orçamento nunca conta como célula concluída; a estimativa só reaproveita execução com trace legível e sem recusa; oscilação entre estimativa e início responde `409 estimate_stale`, sem execução nem ledger.
- **Integração com a v0.12.0:** lojista de emissor externo pede e confirma cancelamento, com auditoria `support:write` no principal externo; operador do Telegram retoma caso com pedido pendente com o texto intacto; pedido criado num processo e confirmado no outro sem duplicar; "Sim" simultâneo nos dois processos confirma uma vez.
- **Operação e observabilidade:** estado da intenção e `resend_count` nas entregas do caso; `pid` no log; instância no recurso OTLP; spans dos passos `summary` e `confirmation` com atributos dos conjuntos fechados; healthchecks no compose.
- **Interface:** login só para a URL da API pareada ao emissor; verifier fora do `repr`; um envio do retorno por tentativa; a janela de login fechada pela aba; token rotacionado nunca enviado a outra URL.

### Testes rodados

- Suítes estritas em clone limpo: 2.643 aprovados (2 pulados: ambiente e SDK do OpenTelemetry, exercitado com Docker) na versão inteira; 2.860 aprovados (1 pulado) depois da integração com a v0.12.0, com `test_v0130_workers.py` repetido.
- Integração sobre a v0.12.0: 197 e 187 testes focados; contrato da interface (3 testes) contra o `src` do backend; sondas de trace e custo; migrações 14 → 16 → 14 → 15 → 16 em banco sintético.
- Interface: suíte estrita com 158 aprovados e 1 pulado, 3 de integração e 2 do componente em JavaScript.

### Mutações

| Escopo | Mutações aplicadas | Não detectadas no código final |
| --- | ---: | --- |
| Identidade, operação e observabilidade (versão inteira) | 29 | nenhuma |
| Integração com a v0.12.0 | 14 | 1 (guarda de estado na confirmação concorrente com recusa), que ganhou teste dedicado |
| Comparação com dois workers e custo da retomada | 44 | 4 redundantes na cerca de reservas; 1 em defesa extra |
| Login por redirecionamento na interface | 24 | 1 |

### Conclusão

Apto em todos os escopos. A decisão está registrada na [ADR 0025](../architecture/decisions/0025-identidade-e-operacao.md).
