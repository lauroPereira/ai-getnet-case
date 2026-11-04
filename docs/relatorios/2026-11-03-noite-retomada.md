# Relatório do Supervisor — retomada da noite de 03/11/2026 (v0.7.0, em andamento)

Período: a partir de 19h50, horário local, no Claude Code. Base: backend `41552c6` (produto em `5ebbfa6`) e web `733cc37`, branch `codex/v0.7.0-identidade-hitl` nos dois repositórios.

Subagentes desta rodada: `developer`, `reviewer` e `qa` de `.claude/agents/`, despachados com modelo **sonnet** e esforço **xhigh** por decisão do responsável nesta sessão, para comparar com o relatório da tarde (opus/high).

- **até 19h57 — reconciliação e preparação:** estado conferido com os relatórios da noite (branches, HEADs, worktrees, branch WIP da T68, lacre do holdout da v0.8.0, identidade Git e memória). O diretório de cópias da revisão da T66 saiu da raiz do backend para `C:\workspace\ai-getnet-case-wt\_preservado\` (movido, não apagado: 2.173 arquivos, mesmos bytes), para a suíte estrita não varrer as cópias mutadas. Despertador de 20 minutos ativo.

- **19h57 às 20h17 — suíte estrita e descida segura da 0010 (T66):** a suíte estrita do candidato da sessão anterior, pendente, rodou pela primeira vez: 558 aprovados e 2 falhas, ambas testes antigos que ainda esperavam a versão 9 do esquema. A descida da migração da outbox passou a recusar, sem alterar nada, enquanto houver notificação não entregue, e desce com a tabela vazia ou só com entregues; os dois testes antigos foram alinhados. Suíte estrita do novo candidato: **568 aprovados, código 0**.
- **20h00 às 21h09 — revisões frias e correções em paralelo (T66, T67):** a revisão da integração por webhooks comprovou por execução os critérios de ponta a ponta e de idempotência, com o serviço de ticketing real, dois processos disputando o mesmo evento, quedas e reinícios e migrações com dados, mas pediu duas correções: o aviso de caso novo ao ticketing se perde numa queda no meio do turno, e o teto de três tentativas após reinício não tem teste. No web, a sincronização do OpenAPI foi confirmada; a revisão achou que um lojista via a conversa do anterior no mesmo navegador e que a resposta humana não era recuperada na ordem real da conversa. Ambos corrigidos e confirmados; resta o rascunho do operador herdado por outro operador. As duas correções estão com os Developers.

**Decisões tomadas:**

- **Migrações reservadas (responsável, nesta sessão):** 0009 e 0010 → v0.7.0; 0011 → v0.8.0; 0012 → v0.10.0. A 0010 é a outbox durável autorizada na sessão anterior. Plano, tabela de donos de arquivo e referências das tarefas 70 e 78 atualizados em `docs/specs/evolucao-pos-feedback-plano.md`.
- **Três tentativas (Supervisor, confirmada):** teto total por evento e destinatário, inclusive após reinício; falha esgotada continua visível.
- **Descida da 0010 (Supervisor):** a recusa vale também para `rejected`, porque o corpo só existe na outbox.
- **Web, primeiro login (Developer, aceita):** o primeiro login da sessão do navegador sempre limpa a conversa; só o mesmo principal depois de expirar a mantém.
- **P3 da T66 (Supervisor):** destino sem URL não recebe intenção; `api` depende do `ticketing` no compose; recuperação na subida não derruba a API; sem comando de reenvio nesta versão (limitação documentada no fechamento); colisão de faixas de lock, id finalizado sem comparação de corpo e emissão só pelos canais `api` e `web` ficam como limitações documentadas.
- **T68:** aproveitar `codex/v0.7.0-wip-68` por cherry-pick (arquivos sem sobreposição com a T66), com os testes ajustados à outbox e ao esquema 10.
- **T67 sem nova sincronização:** o OpenAPI do backend é idêntico entre `7079920`, `5ebbfa6` e `386025a`; reconferir no candidato final.

**Processo:** o worktree `review-a2` foi reposicionado para a revisão da T66 enquanto o Reviewer da T67 ainda o usava para exportar o OpenAPI; ele refez os exports por `git archive`, sem efeito no parecer. Daqui em diante, um worktree por Reviewer até o fim da revisão.
