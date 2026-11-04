# Revisão independente da T66 — rodada 2

- **Candidato:** `b25252333f12d1e4678c9add77254e1458643cf6`, base `70f8f14`, branch `codex/v0.7.0-identidade-hitl`.
- **Independência:** Reviewer em contexto novo; não consultou passagem do Developer nem diagnóstico do Supervisor.
- **Parecer:** correções necessárias: três P1 e um P2. CA-47 e CA-48 não foram comprovados por completo.

## Achados

1. **P1 — recusa repetida interpretada como sucesso.** `api/integrations.py:147` devolve `200 replayed` para ID cuja resposta final foi `409` ou `422`. Sonda observou `409 claimed_by_other` seguido de `200 replayed`, sem reivindicação aceita. Se a primeira resposta se perde, o ticketing interpreta a repetição como entregue e avança seu estado (`ticketing/outbox.py:98`, `ticketing/store.py:482`). A spec exige tanto `200` em ID repetido quanto propagação de 409/422; a escolha entre as regras foi encaminhada ao responsável.
2. **P1 — perda de `handoff.closed` após queda.** `api/integrations.py:207` conclui o fechamento antes da emissão e só emite quando o fechamento não é repetição. Com queda simulada imediatamente após o commit, reenvio retornou `replayed`, fila ficou `closed` e nenhuma notificação saiu. A consequência para o receptor decorre do contrato. O envio em thread sem persistência prévia também deixa eventos em trânsito sujeitos a perda.
3. **P1 — repetição termina antes de a retomada ficar elegível.** Uma ação interrompida permanece `pending` por cinco minutos (`handoffs.py:354`); a entrada retorna `503` nesse intervalo. Sonda confirmou que retomada pendente há três segundos não é reivindicada e uma há 301 segundos é. Por inspeção, o ticketing esgota três tentativas com esperas de 1 e 2 segundos e marca a entrega como falha. A recuperação automática entre serviços não foi demonstrada.
4. **P2 — arquivo de coordenação permanente por ID.** `api/integrations.py:140` cria um SQLite por ID, sem removê-lo. Dois IDs na sonda deixaram dois arquivos. O acúmulo contínuo de eventos autenticados pode esgotar recursos; preservar exclusão entre processos com recursos limitados.

## Validação e limites

O Supervisor executou, no candidato, `tests/integration/test_v070_webhooks.py` com suporte a hardlink: **24 testes passaram**, código 0. A execução inicial do Reviewer parou por `WinError 5` na guarda de orçamento; a guarda não foi substituída na suíte. Sondas próprias usaram dados sintéticos, sem rede nem chamadas pagas. Uma mutação em memória confirmou a importância da comparação do conteúdo reservado. Não foi comprovada pela execução própria uma disputa de requisições completas entre processos distintos. Custo dos agentes não medido.

Próximo passo: corrigir os achados, fixar novo candidato e submeter a outra revisão. A regra de repetição após recusa depende da decisão contratual do responsável.
