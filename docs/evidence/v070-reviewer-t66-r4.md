# Revisão independente da T66 — rodada 4

- **Candidato:** `386025a6546fd8e9a14e4ffe34f3a148bc5660fc`, branch `codex/v0.7.0-identidade-hitl`, worktree destacado `C:\workspace\ai-getnet-case-wt\review-a2`; HEAD igual e `git status` vazio antes e depois. Escopo: a T66 inteira, desde `c7affe5`.
- **Independência:** subagente `reviewer` (sonnet/xhigh) em contexto frio; leu a tarefa até "Validação", a spec, o plano e os pareceres anteriores; não leu as passagens do Developer. Gravado pelo Supervisor a partir do relatório do Reviewer.
- **Parecer:** **correções necessárias** — 2 P2, nenhum P1. CA-47 e CA-48 comprovados por execução.

## Achados

**P2-1 — `handoff.created` não é atômico com a criação do caso e não se recupera.** O caso é gravado em autocommit no nó Escalation (`agents/escalation.py:134`); a intenção só entra na outbox numa transação posterior, no fim do turno (`orchestration/graph.py:382-401`), depois da Personality, da guarda de saída e de `_suspend`. Uma queda nessa janela deixa caso `open` sem intenção nem ticket. Na nova mensagem do lojista, o deduplicador do Escalation (`escalation.py:58-75`) devolve `created=False`, e `graph.py:382-384` não grava checkpoint nem intenção; `recover_handoff_closed` (`api/webhooks.py:104-123`) só vê linhas existentes. Reproduzido: processo encerrado no lugar de `_suspend` deixa caso `open` e outbox vazia, também após reinício; o reenvio da mesma mensagem responde `200 handoff` com o mesmo protocolo, sem intenção nem checkpoint, e a ação do operador recebe `503 resume_failed` (`checkpoint_missing`). Por inspeção, o mesmo vale se a gravação da outbox falhar: o teste de rollback de `handoff.created` só confere as mensagens, não o caso.

**P2-2 — a decisão "três tentativas totais, inclusive após reinício" não tem teste.** O código está correto (sonda confirma), mas trocar `api/webhooks.py:204` (`if attempt > self.settings.webhook_max_attempts:`) por `+ 6` mantém os 60 testes verdes (mutante M09). Com a mutação, a sonda faz uma quarta chamada ao receptor depois do reinício.

## P3

1. Exclusão entre processos sem teste: sem o lock do caso (`handoffs.py:273-281`, M14) ou o de entrega (`api/webhooks.py:180-189`, M22) a suíte passa; só as sondas com dois processos pegam.
2. `enqueue` sem teste de "nunca substitui o corpo" (M19, `INSERT OR REPLACE` em `data/webhook_outbox.py:35`).
3. Sem URL configurada (`api/webhooks.py:159-160`) as intenções ficam `pending` para sempre, sem entrega visível, e a descida da 0010 fica recusada sem saída.
4. `failed`/`rejected` não têm reenvio; os sucessores do mesmo caso e destino ficam `pending` sem linha em `webhook_deliveries`, invisíveis em `GET /v1/handoffs/{id}`. A tolerância a queda do ticketing é de 3 a 9 s, e o `api` do compose não depende do `ticketing`: o primeiro ticket após `docker compose up` pode se perder.
5. Colisão de faixas de lock (64 + 64): evento ou caso de outra chave na mesma faixa de uma retomada longa recebe `503 resume_failed` após 5 s (retentável).
6. `app.py:131` chama a recuperação no lifespan sem tratamento de exceção; o nome `recover_handoff_closed` engana (recupera todas as intenções).
7. Id finalizado com `200` devolve `replayed` sem comparar o corpo (conforme a spec).
8. Primeira retomada bem-sucedida depois de `503` responde `replayed` (cosmético).
9. `handoff.created` só sai pelos canais `api` e `web` (`graph.py:384`); `ask` e `in_process` não geram ticket, o MCP não cria caso. Fecha a lacuna "CLI e MCP" das revisões anteriores: não emitem, por desenho.
10. Guarda da descida não é atômica com uma API em execução (a docstring manda parar a API).
11. Permanecem: assinatura inválida sem auditoria (`api/integrations.py:138-139`); `GET /merchant/events` sem autenticação nem limite no `mocks`; QA com runtime e volume novos (0009 ampliada); M05 equivalente.

## Comprovado por execução

- **CA-47, ticketing real:** `tests/integration/test_v070_ticketing_integration.py` 5 passed. Sonda com assistente, ticketing e `mocks` em processo: ticket nasce sem PAN nem CPF; `reply` retoma; `conversation.replied` ao lojista sem `operator_id` e ao ticketing com ele; `solve` fecha o caso e gera `handoff.closed`; 4 entregas `delivered`; HMAC conferido de forma independente com o segredo de cada sentido.
- **CA-48 e idempotência:** `test_v070_webhooks.py` 36 passed (55 com outbox e migração). Mesmo `id` e mesma chave sem efeito; outra chave → `409 already_resumed`; recusas `409`/`422`/`404` repetidas devolvem o corpo original sem efeito nem auditoria; `503` não é guardado e a repetição retoma (D26).
- **Dois processos reais** no mesmo runtime, 6 ensaios (`reply`, `approve`, `reject`, `assigned`, `solved` e retomada lenta de 7 s): sempre uma aplicação, um evento, um turno e uma auditoria; na lenta, o perdedor recebe `503` retentável.
- **Queda e reinício** (processos encerrados com `os._exit`): `handoff.created`, `conversation.replied` e `handoff.closed` entregues uma vez após reinício, mesmo id e corpo; teto de três respeitado após mortes na primeira, segunda e terceira tentativas.
- **Entrada:** 24 requisições recusadas com `401`/`403` (segredo errado ou de outro sentido, janela, corpo adulterado, 10 formas malformadas, inclusive não ASCII por socket cru, sem token, token inválido, papéis sem escopo); estado do caso idêntico.
- **Receptor fora do ar:** porta fechada e receptor mudo → 3 tentativas registradas, `failed/3`, requisição do lojista em 0,2 a 0,3 s.
- **Migrações com dados:** 0 → 8 → 9 → 10 íntegras; descida recusada com pendente, falha e recusa (banco idêntico, versão 10, CLI com código 1); com só entregues ou tabela vazia desce e sobe de novo, preservando caso, mensagens e inbox.
- **Mutação:** 22 mutantes em cópia, 17 mortos por asserção ou comportamento; sobreviventes M05 (equivalente), M09, M14, M19 e M22.
- **Compose:** `docker compose config --quiet` numa cópia sem `.env` → código 0; segredos fictícios e URLs iguais nos três serviços.
- Achados das rodadas anteriores (assinatura malformada, deduplicação concorrente, recusa repetida, perda de `handoff.closed`, retomada pendente por 5 min, lock por id, descida da 0010) confirmados como corrigidos.

## Não comprovado

Linux e Docker reais (locks exercitados só no Windows); modelo real; suíte estrita (rodada pelo Supervisor: 568 passed); variante do P2-1 com falha na gravação da outbox; tempos do ticketing real; MCP por execução; carga com muitos ids.
