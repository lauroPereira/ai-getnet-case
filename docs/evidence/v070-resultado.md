# Resultado da v0.7.0

Identidade e humano no circuito. Spec: [identidade-hitl-v070.md](../specs/identidade-hitl-v070.md) (versão 2); história: [identidade-hitl-v070.md](../historias/identidade-hitl-v070.md); ADRs [0017](../architecture/decisions/0017-identidade-principal-escopos.md) e [0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md).

## Capacidades

- `POST /messages` exige `Authorization: Bearer`: o lojista vem do token, e um `user_id` divergente recebe `403 identity_mismatch`.
- Um emissor JWT próprio (RS256, JWKS, discovery) autentica usuários sintéticos com hash PBKDF2 e o serviço de ticketing por `client_credentials`, com revogação, papéis, escopos e limites por principal e por tentativa de login; cada chamada de ferramenta confere escopo e lojista e é auditada com principal, escopo e resultado.
- A fila de encaminhamento tem estados, eventos, claim e ações idempotentes, pela API e pela CLI `operator`.
- O grafo pausa em `human_review` quando um caso abre e retoma com `approve`, `reply` ou `reject`, também depois de reiniciar a API; a resposta do operador chega ao lojista na mensagem seguinte, sem chamada a modelo.
- Um serviço de ticketing separado leva o ticket por `new → open → pending → solved`, com o login do operador validado pelo JWKS do assistente.
- Webhooks assinados nos dois sentidos (HMAC-SHA256, janela de 300 s) saem por uma outbox gravada na mesma transação da mudança, com três tentativas por evento e destino, também entre reinícios.

## Validação

| Verificação | Resultado |
| --- | --- |
| Candidato | [v070-candidato-r1.json](v070-candidato-r1.json): backend `e97d7f0`, interface `932aeb6`, fingerprint `12adae52…ad8f`, hashes de 118 + 13 arquivos conferidos antes e depois da validação. O fingerprint é o SHA-256 de `json.dumps({"backend": …, "web": …}, sort_keys=True)` com as duas seções completas do manifesto |
| Suíte estrita | Backend 640 aprovados, interface 92 aprovados, Ruff limpo, código 0 |
| Revisão independente | Tarefas 63 a 68 e 66b aptas, com mutação e sondas reais entre processos e de queda ([identidade, fila e retomada](v070-reviewer.md), [ticketing](v070-reviewer-time-b.md), [webhooks](v070-reviewer-t66-r5.md), [regressão](v070-reviewer-t68.md)) |
| Validação com modelos reais | Apta nos 18 momentos da história, pela interface, por `curl`, pela CLI e pelo Docker ([validação](v070-qa.md), [história momento a momento](v070-qa-historia.md)) |
| CA-46 identidade | `401` sem token, com token adulterado e com token revogado; `403 identity_mismatch`; 4 chamadas de ferramenta = 4 linhas de auditoria com principal, escopo e resultado; outro lojista recebe `404`/`403`/`401` sem nenhum dado de `cliente1988` (momentos 1–5 e 17) |
| CA-47 ticket e resposta humana | O caso vira ticket `new` com o mesmo id de evento nos dois lados; `reply`, `approve` (tela e CLI) e `reject` (Support reexecutado uma vez sob `operator:op_ana`) com turno `via=operator`, webhook ao lojista sem `operator_id` e `human_reply` sem chamada a modelo; resolver fecha o caso (momentos 6–15) |
| CA-48 idempotência e reinício | `409 claimed_by_other`, mesma chave `replayed`, `409 idempotency_conflict`, `409 already_resumed`; duas quedas abruptas da API com o checkpoint intacto; no Docker, reinício do contêiner `api` entre encaminhar e agir (momentos 9, 11, 16 e 18) |
| Regressão real | Desafio 10/10, núcleo 17/17, conversas 4/4; rota e ferramentas 0,95, iguais à v0.6.0; valores 1,0 (eram 0,975); jornadas de negócio 6/13 pela rubrica literal (13/13, 12/13 e 12/13 na v0.8.0) ([regressão](v070-qa-regressao-real.md)) |
| Docker | `up` sem editar o `.env.example`, smoke com token 10/10, ciclo do ticket por `curl`, bancos do assistente e do ticketing em volumes próprios |

## Gasto

| Ledger | US$ |
| --- | ---: |
| Campanha `v070-qa` (290 entradas, zero reservas): índice 0,00074, regressão 0,06856, história 0,00365, repetição de 5 casos 0,00249 | 0,07543317 |
| Ledger do volume Docker (0 → 50 entradas) | 0,02596878 |
| **Total da campanha** (teto US$0,20) | **0,10140195** |

Acumulado do projeto: cerca de US$0,79, com teto de US$5,00 na época.

## Decisão

As decisões de identidade e de interrupção e retomada estão nas ADRs [0017](../architecture/decisions/0017-identidade-principal-escopos.md) e [0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md). O retorno à v0.6.0 está no CHANGELOG, seção 0.7.0.
