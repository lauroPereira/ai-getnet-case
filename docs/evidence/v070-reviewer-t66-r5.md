# Revisão independente da T66 — rodada 5

- **Candidato:** `0592641d9dc99a23b17ba6f3eed05a8c2d4c9885`, branch `codex/v0.7.0-identidade-hitl`, worktree destacado `C:\workspace\ai-getnet-case-wt\review-a2`; HEAD e `git status` iguais antes e depois. Escopo: diff `386025a..0592641` em `src/`, `tests/` e `docker-compose.yml` (9 arquivos), com regressão rápida do que a rodada 4 comprovou.
- **Independência:** subagente `reviewer` (sonnet/xhigh) em contexto frio; leu a tarefa até "Validação", a spec, o parecer da rodada 4 e o diff; não leu as passagens do Developer. Gravado pelo Supervisor a partir do relatório do Reviewer.
- **Parecer do Reviewer:** correções necessárias, com um P2 só de teste e nenhum defeito de produto; "se o Supervisor tratar como P3, o resto está apto para QA".
- **Decisão do Supervisor:** o P2 de teste é reclassificado como P3 e a T66 fica **apta para QA** neste candidato. Os testes das guardas (abaixo) e o P3-2 entram na rodada da T68, que gera candidato novo com suíte estrita e revisão própria.

## Achados

**Lacuna de teste (P2 do Reviewer, P3 por decisão do Supervisor) — guardas de `_complete_interrupted_handoff` sem teste.** `orchestration/graph.py:417-442`. O código está correto (sondas G0–G6), mas 6 de 7 mutantes desse trecho sobrevivem aos 94 testes do conjunto: checkpoint sempre "ausente" ou falha de leitura tratada como ausente (re-salva o fluxo, ou marca `checkpoint_failed` num caso íntegro), e a remoção das guardas de `queue_state`, `ticket_id`, `thread_id` e canal (anúncio indevido a caso respondido, a caso com ticket, a caso anterior à v0.7.0 e pelo canal `in_process`). Nenhum teste confere "sem duplicar checkpoint".

## P3

1. A recuperação de `handoff.closed` na subida (`api/webhooks.py:121`) não tem teste do filtro de destino (mutante N09): sem ele, caso fechado sem URL do ticketing deixaria intenção pendente a cada reinício.
2. URL configurada sem segredo acumula intenção para sempre: `webhook_targets` (`data/webhook_outbox.py:18-21`) olha só a URL, e `dispatch_pending` (`api/webhooks.py:160`) pula sem segredo; a descida da 0010 fica recusada. Erro de configuração; o compose traz os segredos padrão.
3. Regra de canal da criação sem teste (N20, `graph.py:388`); já era o P3-9 da rodada 4.
4. Caso aberto pela CLI (`in_process`) passa a ser anunciado ao ticketing quando o lojista repete a mesma mensagem pela API. Razoável; documentar.
5. Documentação pendente para o fechamento: `failed`/`rejected` sem reenvio e sucessores invisíveis em `GET /v1/handoffs/{id}`; guarda da descida da 0010; limitação aceita do reenvio da mesma mensagem; dependência `api` → `ticketing` no compose.
6. `api` espera o `ticketing` saudável: um ticketing que não sobe segura o assistente (decisão do Supervisor, registrada).

## Limitação aceita, medida

Depois de uma queda entre o INSERT do caso e a transação do fim do turno, a recuperação depende de o lojista reenviar a mesma mensagem na mesma conversa. Com outra mensagem, ou nenhuma, o caso anterior fica `open` na fila do assistente sem checkpoint, ticket nem intenção, indistinguível de um caso saudável; ação nele responde `503` repetível e o ticketing nunca o vê. A janela vai do Escalation ao fim do turno (milissegundos offline; a latência da Personality com modelo real, não medida). A chave de deduplicação inclui o `reason` do Router ou do Support, que com modelo real pode variar entre tentativas e abrir outro caso (não medido).

## Comprovado por execução

- **Recuperação após queda:** subprocessos encerrados antes do checkpoint, depois do checkpoint, dentro da transação, e falha ao gravar a outbox. Em todos, o reenvio da mesma mensagem dá 1 caso, o mesmo protocolo, 1 `handoff.created` entregue uma vez (id determinístico, assinado, mascarado), checkpoint com as mesmas linhas do controle e 1 turno; segundo reenvio não envia nada; `ticket.assigned` e `ticket.action` aceitos com `resume_status=done`. Com o ticketing real em processo: ticket `new`, resposta aceita, cópia ao lojista sem `operator_id`, `solve` fecha e gera `handoff.closed`. Dois reenvios simultâneos: 1 caso, 1 intenção, 1 entrega.
- **Teto de três após reinício:** teste novo mata o mutante `+6`; mortes na 1ª, 2ª e 3ª tentativa terminam `failed/3` sem quarta chamada.
- **Locks entre processos:** os testes novos com dois processos matam a remoção do lock do caso e do lock de entrega; os quatro sobreviventes da rodada 4 (M09, M14, M19, M22) agora morrem.
- **Destino sem URL:** nenhuma intenção para ele; descida e subida da 0010 passam nos quatro arranjos.
- **Recuperação que falha na subida:** com a tabela da outbox removida, a API registra o erro e responde em `/health` e `POST /messages`; o renome está completo.
- **Compose:** `docker compose config --quiet` numa cópia sem `.env` → código 0; `api` depende de `mocks`, `qdrant` e `ticketing`, sem ciclo.
- **Regressão CA-47/CA-48:** `test_v070_ticketing_integration.py`, `test_v070_webhooks.py` e `test_webhook_outbox.py` → **54 passed**; sondas de ticketing real e de quedas da rodada 4 repetidas com o mesmo resultado.
- **Mutação:** 22 mutantes nos pontos novos, 13 mortos; N21 equivalente; N09, N14–N20 nas lacunas acima. Ruff limpo.
- **Suíte estrita** (Supervisor, neste candidato): **579 passed**, código 0.

## Não comprovado

Linux e Docker em execução; modelo real (janela da queda e estabilidade do `reason`); MCP por execução; carga com muitos ids; P3 5 e 7 a 11 da rodada 4 não reavaliados.
