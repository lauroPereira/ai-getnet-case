# Relatório do Supervisor — retomada da noite de 03/11 a madrugada de 04/11/2026 (v0.7.0 concluída)

Período: 19h50 de 03/11 às 02h00 de 04/11, horário local, no Claude Code. Base: commits deste repositório `fa4f0d4`..`fed905e` (merge na `main`) e do web `40b3797`..`0a8e12f`.

Subagentes desta rodada: `developer`, `reviewer` e `qa` de `.claude/agents/`, despachados com modelo **sonnet** e esforço **xhigh** por decisão do responsável, para comparar com a tarde (opus/high). O Supervisor (sessão principal) rodou em Opus 5.5.

- **até 19h57 — reconciliação e preparação:** estado conferido com os relatórios da noite (branches, HEADs, worktrees, branch WIP da T68, lacre do holdout da v0.8.0, identidade e memória); nada divergiu. As cópias mutadas da revisão anterior saíram da raiz do backend para `C:\workspace\ai-getnet-case-wt\_preservado\` (movidas, mesmos 2.173 arquivos). Migrações 0009 e 0010 reservadas para a v0.7.0.
- **19h57 às 21h29 — integração por webhooks endurecida (T66):** a suíte estrita do candidato pendente rodou pela primeira vez (2 testes antigos esperando o esquema 9). A descida da migração da outbox passou a recusar enquanto houver aviso não entregue. A revisão fria seguinte comprovou por execução os critérios de ponta a ponta e de idempotência — ticketing real, dois processos disputando o mesmo evento, quedas e reinícios, migrações com dados — e pediu que o aviso de caso novo sobrevivesse a uma queda no meio do turno; corrigido, com o destino sem URL deixando de acumular avisos e a API dependendo do ticketing no compose.
- **20h00 às 22h36 — interface do operador e do lojista no web (T67):** sincronização do contrato confirmada; quatro rodadas fecharam vazamentos de estado entre usuários no mesmo navegador (conversa do lojista anterior, rascunho do operador anterior, escolhas sem chave) e a recuperação da resposta humana na ordem real da conversa. Apta na rodada 6.
- **22h36 às 00h44 — regressão integrada (T68):** teste da história de ponta a ponta com ticketing real e reinício em dois processos; a queda de `content_ok` do eval programado foi explicada (protocolo novo e uma palavra perdida na frase de encaminhamento) e corrigida; o cenário da bancada que ainda esperava o protocolo antigo foi alinhado. Candidato fixado nos dois repositórios.
- **00h45 às 01h41 — QA real:** os 18 momentos da história passaram por `curl`, CLI, interface no navegador, duas quedas abruptas da API e Docker (smoke com token, ciclo do ticket, reinício do container entre encaminhar e agir). **Apto com ressalvas, nenhum defeito reproduzido.**
- **01h41 às 02h00 — fechamento:** evidência de resultado, README e CHANGELOG com as duas quebras e as chamadas do avaliador, ADRs 0017 e 0018 aceitas (a 0018 alinhada aos dois grafos e à outbox), suíte estrita final verde e **merge local da v0.7.0 na `main` dos dois repositórios** (`fed905e` e `0a8e12f`).
- **Em paralelo (23h–01h) — v0.8.0 preparada a pedido do responsável:** spec complementar, história e tarefas 69 a 73 escritas na branch `codex/v0.8.0-avaliacao`; revisadas e **aprovadas pelo responsável** com as decisões D12 e D16 a D19 e as condições de execução.

**Custo e tempo por agente** (de `tools/scripts/medir-agentes.py --desde 2026-11-03`; rodadas retomadas por mensagem contam na mesma passagem):

| Passagem (tarefa) | Modelo | Rodadas | Min. ativos | US$ equiv. |
| --- | --- | ---: | ---: | ---: |
| Developer T66 (r4, r5) | sonnet/xhigh | 2 | 28,7 | 4,42 |
| Developer T67 (r4, r5, r6) | sonnet/xhigh | 3 | 47,5 | 8,71 |
| Developer T68 (r1, r2) | sonnet/xhigh | 2 | 60,9 | 13,82 |
| Reviewers T66 (r4, r5) | sonnet/xhigh | 2 | 108,6 | 8,38 |
| Reviewers T67 (r3, r4, r5, r6) | sonnet/xhigh | 4 | 121,8 | 11,84 |
| Reviewers T68 (r1, r2) | sonnet/xhigh | 2 | 47,2 | 5,18 |
| QA real (T68) | sonnet/xhigh | 1 | 54,6 | 17,30 |
| **Total da rodada** | | **16** | **469** | **69,65** |

Campanha real da versão: **US$0,10140195** de US$0,20 (nativa 0,07543317 + ledger do volume Docker 0,02596878); acumulado do projeto cerca de US$0,79 de US$5,00. Rodadas de correção pedidas pela revisão nesta rodada: T66 2, T67 3, T68 1; QA: nenhuma.

**Comparação sonnet/xhigh × opus/high (tarde).** Medição por papel e por unidade feita nesta rodada; os números ficam em material local do responsável, fora do repositório. A leitura que ficou para o processo está em `docs/wiki/agents/README.md` ("Por que `opus`/`high` nos três").

**Decisões tomadas por padrão (reversíveis):**

- **Três tentativas:** teto total por evento e destinatário, inclusive após reinício (confirmada).
- **Descida da 0010:** recusa também com avisos `rejected`, porque o corpo só existe na outbox.
- **P3 da T66:** destino sem URL não recebe aviso; destino com URL e sem segredo também não, com alerta na subida; `api` depende do `ticketing` no compose; recuperação na subida não derruba a API; sem comando de reenvio nesta versão (limitação documentada).
- **Lacuna de teste da T66 r5** reclassificada de P2 para P3 (sem defeito de produto) e fechada na T68.
- **T68:** aproveitar a branch WIP por cherry-pick; manter `personality.v4` (o rótulo "human" vai para a 72b da v0.8.0); catálogo da bancada mantém a versão "1".
- **Web:** primeiro login da sessão do navegador sempre limpa o estado; escopo da T67 congelado na rodada 6 (P3 registrados para a próxima versão).
- **QA:** `approve` mantém o ajuste de voz da Personality; "envio pendente" no `reject` aceito (D26); `ticket_id` vazio no caso vira a tarefa 68b, no começo da v0.8.0; contrato OpenAPI sem nova sincronização (só `info.version` difere).
- **v0.8.0, Time A como dono único do grafo:** a sugestão do responsável era o time com menos tarefas; só a 69 toca o grafo, e passá-la ao Time B deixaria o A parado.

**Processo:** o worktree `review-a2` foi reposicionado enquanto o Reviewer da T67 r3 ainda o usava (refez os exports por `git archive`, sem efeito no parecer); daí em diante, um worktree por Reviewer. O Developer da T68 criou por engano o diretório vazio `C:\c` (caminho do Git Bash passado ao Python) e apagou as pastas de teste que ele mesmo criou em `.pytest_cache`; nada preservado foi tocado. A limpeza com `-Aplicar` foi barrada pelo classificador de permissões e não foi contornada.

**Estado para retomar:**

| Repositório e branch | HEAD | Situação |
| --- | --- | --- |
| backend `main` (checkout principal) | `fed905e` | v0.7.0 integrada localmente; sem push |
| backend `codex/v0.7.0-identidade-hitl` | `cdcbc0b` | integrada na `main` |
| backend `codex/v0.8.0-avaliacao` (worktree `time-b`) | `190c07f` | holdout lacrado `91aa5158…`; spec, história e tarefas da v0.8.0 aprovadas |
| backend `codex/v0.7.0-wip-68` | `15909cd` | aproveitada por cherry-pick; preservada |
| web `main` | `0a8e12f` | v0.7.0 integrada localmente; sem push |

Worktrees `review-a`, `review-a2` e `review-web` destacados (só leitura); `_preservado`, `_tmp/` e `Claude outputs/` intactos. Volumes Docker do QA (`v070qa_*`) e imagens mantidos.

**Falta:** tag `v0.7.0` e push das duas `main` (responsável). Na sequência, autorizada pelo responsável: abrir a v0.8.0 (68b, 69 e 70 em paralelo; depois 71, 72b, 73, QA técnico e CSV de calibração) e parar na calibração.

**Depende de você:**

- Tag `v0.7.0` (backend `fed905e`, web `0a8e12f`) e push das duas `main`.
- Rodar a limpeza, se quiser recuperar espaço: `tools/scripts/limpar-ambiente.ps1 -Aplicar -SemScratchpad` (runtimes de QA e caches, cerca de 8 MB); os volumes e imagens do Docker do QA ocupam cerca de 1,9 GB.
- Apagar `C:\c` (vazio, 12 pastas, criado por engano às 22h40).
- Calibração humana da v0.8.0 quando o CSV estiver pronto.
