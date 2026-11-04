# Resultado da v0.7.0

Identidade e HITL real. Spec: [identidade-hitl-v070.md](../specs/identidade-hitl-v070.md) (versão 2); história: [identidade-hitl-v070.md](../historias/identidade-hitl-v070.md); ADRs [0017](../architecture/decisions/0017-identidade-principal-escopos.md) e [0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md), aceitas.

## Candidato

[v070-candidato-r1.json](v070-candidato-r1.json): backend `e97d7f0` (branch `codex/v0.7.0-identidade-hitl`), web `932aeb6` (mesma branch), fingerprint `12adae52…ad8f`, hashes de 118 + 13 arquivos conferidos pelo QA antes e depois. O fingerprint é o SHA-256 de `json.dumps({"backend": …, "web": …}, sort_keys=True)` com as duas seções completas do manifesto.

## Fluxo e correções

| Etapa | Resultado | Evidência |
| --- | --- | --- |
| T63 identidade, T64 fila, T65 interrupção e retomada (Time A) | Aptas para QA (duas rodadas cada) | [Reviewer](v070-reviewer.md), [Developer](v070-developer.md) |
| T66b serviço de ticketing (Time B) | Apta para QA (quatro rodadas) | [Reviewer Time B](v070-reviewer-time-b.md) |
| T66 webhooks (Time A) | Cinco rodadas de revisão: assinatura malformada e deduplicação concorrente (retomada); recusa repetida virando sucesso, perda de `handoff.closed` após queda, janela de retomada e arquivo por id (r2); descida da 0010 apagando pendências (r3); `handoff.created` não recuperável após queda e teto sem teste (r4); apta na r5, lacunas de teste levadas à T68 | [retomada](v070-reviewer-t66-retomada.md), [r2](v070-reviewer-t66-r2.md), [r3](v070-reviewer-t66-r3.md), [r4](v070-reviewer-t66-r4.md), [r5](v070-reviewer-t66-r5.md) |
| T67 interface web (Time B) | Seis rodadas: sincronização do OpenAPI confirmada; estado de um usuário herdado pelo seguinte no mesmo navegador (conversa, campos do operador, widgets sem chave) e recuperação da resposta humana na ordem real; apta na r6 | `ai-getnet-case-web/docs/evidence/v070-reviewer-web.md` |
| T68 regressão e fechamento (Time A) | Teste da história com ticketing real e dois processos; `content_ok` programado de volta ao nível da v0.6.0; cenário `SC-HANDOFF` do catálogo com o protocolo novo; apta na r2 | [Reviewer T68](v070-reviewer-t68.md) |
| QA real r1 | **Apto com ressalvas**; nenhum defeito reproduzido | [QA](v070-qa.md), [história](v070-qa-historia.md), [regressão](v070-qa-regressao-real.md) |

Suíte estrita do candidato: backend **640 passed**, web **92 passed**, Ruff limpo, código 0 (Supervisor e QA).

## Aceite

| Critério | Resultado | Evidência principal |
| --- | --- | --- |
| CA-46 identidade | Apto | `401` sem token, adulterado e revogado; `403 identity_mismatch`; 4 tool calls = 4 linhas de auditoria com principal, escopo e resultado; outro lojista recebe `404`/`403`/`401` sem nenhum dado de `cliente1988` (momentos 1–5 e 17) |
| CA-47 ticket e resposta humana | Apto | Caso vira ticket `new` com o mesmo id de evento nos dois lados; `reply`, `approve` (tela e CLI) e `reject` (Support reexecutado uma vez sob `operator:op_ana`) com turno `via=operator`, webhook ao lojista sem `operator_id`, `human_reply` sem chamada a modelo; resolver fecha o caso (momentos 6–15) |
| CA-48 idempotência e reinício | Apto | `409 claimed_by_other`, mesma chave `replayed`, `409 idempotency_conflict`, `409 already_resumed`; duas quedas abruptas da API com checkpoint intacto; no Docker, reinício do container `api` entre encaminhar e agir (momentos 9, 11, 16, 18) |
| Regressão | Apto com ressalva | Desafio 10/10, núcleo 17/17, conversas 4/4; jornadas 6/13 (v0.6.0: 7/13); rota e ferramentas 0,95 iguais à v0.6.0; valores 1,0 (era 0,975) |
| Docker | Apto | `up` sem editar o `.env.example`, smoke com token 10/10, ciclo do ticket por `curl`, bancos do assistente e do ticketing em volumes próprios |

## Custos

| Ledger | US$ |
| --- | ---: |
| Campanha `v070-qa` nativa (290 entradas, zero reservas): índice 0,00074, regressão 0,06856, história 0,00365, repetição de 5 casos 0,00249 | 0,07543317 |
| Ledger do volume Docker (0 → 50 entradas) | 0,02596878 |
| **Total da campanha** (teto US$0,20) | **0,10140195** |

Acumulado do projeto: cerca de US$0,79 de US$5,00. O custo da ferramenta de desenvolvimento (subagentes) é controle separado e está no relatório do Supervisor.

## Decisões tomadas no fechamento (Supervisor, reversíveis)

- **Rótulo "human" de `V030-CONTRACT-TERMINATION`:** a frase de encaminhamento em inglês do `personality.v4` perdeu "human" junto com o texto de simulação (D7). Não foi ajustada nesta versão; vai para a tarefa 72b da v0.8.0 (jornadas).
- **`approve` com ajuste de voz:** a Personality pode mexer na forma do rascunho aprovado (ex.: tirar a saudação), conforme o prompt; a tela diz "sem alterações". Mantido; o texto da tela fica como P3 do web.
- **"Envio pendente" no `reject`:** a retomada com modelo real levou 6,2 s, acima dos 3 s de espera do ticketing; a nova tentativa com a mesma chave completou com uma única retomada (D26). Aceito; aumentar a espera fica para depois.
- **Premissa do momento 9:** na tela, "Assumir" só aparece para ticket `new`; o conflito entre operadores aparece na ação. Registrado na história.
- **`ticket_id` no caso (O-8):** investigado no começo da v0.8.0 ([tarefa 68b](../tasks/68b-ticket-id-no-caso.md)); não é defeito: o campo é gravado no primeiro evento do operador e fica vazio antes disso (recepção), por desenho da tarefa 66. No banco do QA, 4 de 5 casos tinham o `ticket_id`; o quinto foi trabalhado só pela CLI, sem evento do ticketing. Ganhou teste de regressão.

## Limitações

Ver CHANGELOG 0.7.0 e README "Limitations": entrega esgotada ou recusada sem reenvio e prendendo os eventos seguintes do mesmo caso e destino; recuperação de um turno interrompido dependente do reenvio da mesma mensagem; bloqueios entre processos exercitados só no Windows; identidade com emissor próprio e usuários sintéticos. Atritos e observações do QA (A-1 a A-3, O-4 a O-9) estão em [v070-qa.md](v070-qa.md).

## Como voltar à v0.6.0

Parar a pilha, garantir a outbox sem pendências (ou recriar o runtime), `merchant-assistant migrate --to 8`, checkout de `v0.6.0`, remover `checkpoints.sqlite3`, os arquivos de bloqueio e o banco do ticketing.
