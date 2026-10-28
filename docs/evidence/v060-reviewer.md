# Passagem de papel: revisão independente da v0.6.0 (candidato r1)

## Rodada 1 — 2026-10-28

- Papel e responsável: Reviewer independente (Claude Opus 5.5, esforço high), despachado pelo Supervisor; sem delegação.
- Objetivo e critérios: revisar o candidato `v0.6.0-local-r1` contra [spec](../specs/fechamento-v060.md) (A–F, triagem E, 10 aceites), [plano](../specs/fechamento-v060-plano.md), [história v1](../historias/fechamento-v060.md), [ADR 0015](../architecture/decisions/0015-recorte-final-v060.md), seção "Recorte final" de [incrementos-pos-nucleo.md](../specs/incrementos-pos-nucleo.md#recorte-final-v060) (RF-76–79, CA-47–51) e Objetivo/Passos/Critérios das tarefas 54–58.
- Escopo: backend `C:\workspace\ai-getnet-case` e web `C:\workspace\ai-getnet-case-web`, working tree sem commit sobre as bases.
- Estado: **apto para QA** (nenhum P1/P2; 10 P3).
- Branch e PR: `codex/v0.6.0-fechamento` nos dois repositórios; sem PR.
- Base e versão final: backend HEAD `c3a9027b7c218f560345576770a646d4ec2bc098`, web HEAD `4192169afc8b37f150d88fdf16e3529a0fd33b90` (ambos conferidos com `git rev-parse`); manifesto [v060-candidato-r1.json](v060-candidato-r1.json), fingerprint `789d6f5303016125e1b0ef6ff8a8315ed06aec1ff053a331ff48e4133310c714`.
- Independência: independente. Não li `v060-developer.md`, `v060-supervisao.md` nem as seções "Validação"/"Status" das tarefas 54–59. Li `v060-qa-preparacao.md` (artefato da tarefa 57 sob revisão: diferença esperada e roteiro) e README/CHANGELOG como documentos sob revisão; as contagens de testes neles citadas não foram usadas como evidência — foram re-executadas.

### Hashes do candidato

| Momento | Resultado |
| --- | --- |
| Antes da revisão | 51 arquivos do backend e 13 do web com SHA-256 idêntico ao manifesto; nenhuma divergência; fingerprint reproduzido com `json.dumps({backend, web}, sort_keys=True)` → `789d6f53…c714` |
| Depois da revisão | Mesma conferência: 0 divergências, mesmo fingerprint, HEADs inalterados |
| Fora do manifesto | Só `_tmp/**` (exclusão declarada), `v060-candidato-r1.json` e `v060-supervisao.md` (registros mutáveis excluídos pela regra do manifesto) |

### Comandos executados (sem rede, sem custo, sem Docker)

| Comando | Resultado |
| --- | --- |
| Script de hashes (scratchpad `verify.py`, `git status --porcelain -uall`, `git rev-parse HEAD`) antes e depois | 0 divergências |
| Backend: `.venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` (pytest no temp do sistema) | **326 passed** em 215 s; Ruff "All checks passed!"; estrutura e skills válidas; **exit 0** |
| Web: `.venv-v040/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` (o `.venv-v040` fica no repo web, não no backend) | **30 passed** em 20 s; Ruff ok; **exit 0** |
| Testes novos de `test_v060_stabilization.py` contra o código do HEAD (`git archive HEAD` no scratchpad, `PYTHONPATH` para o `src` do HEAD) | 10 de 14 **falham antes** (R2-01 ×3, R2-02, campanha 0,50, R2-03, R2-05/08a, DeepSeek, R2-07, compose); os 4 que passam antes são regressões de comportamento já correto (teto não sobrescrito, registro único, R2-08b ×2) |
| Mutações numa cópia do candidato no scratchpad (16) | Detectadas: M1 CLI sem timeout, M2 integridade sem `points > 0` (R2-08b), M3 limite demo desligado, M4 comparação sem cópia do domínio, M5 avaliação sem idempotência, M6 avaliação sem reserva no ledger, M8b negação de orçamento ignorada, M9 avaliação sem confirmação, M10 comparação sem teto confirmado, M12 nota do avaliador com avaliação parcial, M13 verificações rotuladas em mensagem livre, M14 comparação perdida não marcada, M15 teto de campanha ampliado. **Sobrevivem**: M7 (célula sem base fixa), M11 (reuso sem conferir versão da base) — ver P3-09. M8 parcial sobrevive porque o teste exercita o outro ramo de detecção (M8b detecta) |
| OpenAPI do backend (`create_app(Settings(demo_mode=True)).openapi()`) × `openapi-v1.json` do web | **Idênticos**; frente ao snapshot do HEAD, só `POST /v1/messages` e `V1MessageRequest` mudam (aditivo: `scenario_id`, resposta 429); 6 rotas novas, exatamente as do plano; **não existe `GET /v1/runs`**; 31 caminhos, 28 operações geradas |
| Sonda no scratchpad: comparação com `SC-INJECTION` e `SC-HANDOFF` | Células concluídas têm custo por agente e aparecem nas barras; só células com falha ficam sem acesso (P3-07) |

### Verificação por eixo

1. **Escopo.** Nada do "Fora do escopo": sem Evaluation Agent (reuso de `judge`/`JudgeScore`), sem propostas, sem fila ou serviço novo (thread no processo da API), um gráfico de cada tipo pedido, sem redesenho de autenticação, orçamento ou migrações. Componentes alterados batem com o plano; AGENTS/CLAUDE/skills intocados.
2. **Contratos.** Só as rotas aprovadas; legado `POST /messages`, MCP e `/v1` existentes sem mudança de comportamento (parâmetros novos de `Orchestrator.handle` com padrão; trace e snapshot só ganham campos). Cliente web regenerado coincide com o snapshot; uma execução acidental de `tools/generate_client.py` (ver Limitações) regravou bytes idênticos, o que confirma a reprodutibilidade.
3. **Orçamento.** Avaliação: preço desconhecido → 503 antes de reservar; reserva por `BudgetMeter` no ledger (`eval:<id>`), liquidação única, falha com uso desconhecido mantém a reserva como gasto; teto confirmado conferido; idempotente salvo `repeat=true`. Comparação: estimativa limitada por célula (`MAX_REQUEST_COST_USD`), confirmação com digest, recusa se a estimativa excede o saldo, reservas por chamada, negação de orçamento interrompe as restantes e é registrada. Embeddings sem mudança. Teto persistente: `repr` exato, publicação por arquivo temporário + `os.link`, nunca sobrescrito; teto absoluto US$5 intacto. R2-01/02/03/05/07/08 corrigidos com regressão real (tabela acima); R2-04 só como risco aceito (spec E, CHANGELOG, roteiro do QA).
4. **Comparação.** Efeitos de domínio numa cópia `backup()` do banco, apagada ao fim; contagens das seis tabelas de domínio inalteradas no teste (M4 detecta); uma versão da base capturada e conferida no início; células reaproveitadas rotuladas `recorded`; falhas, repetições, amostra, digests e versões no registro; qualidade determinística sob os mesmos rótulos; nota do avaliador só com todas as execuções avaliadas pela mesma configuração, senão `not_evaluated`; Router-only em seção própria do Atendimento.
5. **Permissões.** Rotas de KB e perfis continuam com dependência `ADMIN`; aba Administração só para `role == "admin"`; limite demo atômico (`UPDATE … WHERE message_count+?<=?`); compose publica `127.0.0.1:8000:8000` (teste dedicado).
6. **Interface.** Três abas; reruns, troca de aba e seleção de barra só fazem GET (testes `AppTest` contam operações); recuperação de pergunta pendente só por GET; timeout 20 s para leituras e 105 s para operações que esperam trabalho pago; erros com ação de recuperação nos caminhos de demo; real/simulado/gravado rotulados (também nas células).
7. **Bloco D.** Diferença esperada registrada em `v060-qa-preparacao.md` por ferramenta (`get_contract_snapshot`), fato (`link_de_pagamento` no contrato) e condição; V2 = V1 + uma seção (diff sem remoções), sem dígitos, sem ferramenta nova (`AGENT_TOOLS` inalterado); teste sem custo verifica trecho nos `hits`, versão da base no trace, ferramentas, fonte do contrato, conversas independentes e retorno. A política programada aplica o trecho recuperado: prova o caminho dos dados, não o modelo real (declarado no próprio teste e no roteiro).
8. **Migração 0008.** Aditiva; down remove as duas tabelas e a coluna; teste 8 → 7 → 8 preserva `api_sessions` e `run_snapshots`; `migrate --to 7` do CLI usa conexão sem auto-migração. Coleções não tocadas.
9. **Documentação.** Guia único com Docker/nativo/testes distintos, compartilhamento (API em loopback, `LOCK_BACKEND_URL`, HTTPS próprio, ações do responsável, outra rede, túnel como alternativa, fim da janela) e limitações; README/CHANGELOG descrevem o candidato como pendente de revisão e QA. Busca por chaves, e-mails, caminhos locais e `discovery` nos documentos publicados: nada encontrado. Exceção pontual de exatidão em P3-05.
10. **Pontos pedidos pelo Supervisor.**
    - a. `CAMPAIGN_CAP_LIMIT_USD` 0,25 → 0,50: **aceitável**. É o mínimo necessário para montar o `v060-qa` aprovado; o valor fixado de cada campanha continua imutável (um ledger fixado em 0,25 recusa 0,50 e vice-versa), o `.limit` do ledger primário e o teto absoluto não mudam, e o guard combinado usa o menor saldo. Testes cobrem 0,5000001/0,51/5,0/nan/inf (M15 detecta).
    - b. Exclusões `.pytest_cache`, `_tmp` (e `.venv*` no web): **nenhuma fonte deixa de ser verificada** — `git ls-files '*.py'` e os não rastreados fora de `_tmp/` não têm nenhum caminho com esses componentes nos dois repositórios; o pytest usa `testpaths = ["tests"]`, independente da lista.
    - c. `LOCK_BACKEND_URL` desligado por padrão: risco **P3-04**. O guia manda ligá-lo no compartilhamento; se esquecido, o visitante faz o servidor Streamlit enviar requisições a qualquer host/porta (rotas fixas do cliente). Mesmo ligado, a trava é só `disabled` no widget.
    - d. Limite demo contando execuções novas de comparação: **coerente** (cada célula nova é um atendimento pago). Contar o envio com comparação de Routers obsoleta (409) é consequência da ordem do código e cobra uma mensagem sem inferência — **P3-03**, junto com o fato de a comparação de Routers e a avaliação não contarem.
    - e. Timeout longo também para comparação de Routers, avaliação e build/teste: **adequado** (todas esperam chamadas pagas de até 30 s cada; `create_comparison` responde 202 e segue curto; GETs continuam 20 s). Resta que build/teste de candidata não tratam `TransportError` — **P3-05**.

### Achados

Nenhum P1. Nenhum P2.

**P3-01 — Leitura de comparação pode sobrescrever o resultado final com estado `failed`.**
[comparisons.py](../../src/merchant_assistant/comparisons.py:400) `read()` lê a linha (`running`) e só depois confere se a thread vive (linhas 408–416). Se a thread gravar o estado final e sair de `_ACTIVE` entre esses dois passos, o GET grava `failed`/`interrupted` com as células antigas por cima do resultado concluído (`_save` não condiciona a `state='running'`). Requisito: estados coerentes (spec E), CA-48. Reprodução: janela de corrida entre o SELECT da leitura e o `_ACTIVE.pop` no `finally` de `_run`; improvável com atualização manual, não reproduzida em execução. Correção esperada: `UPDATE … WHERE comparison_id=? AND state='running'` na marcação de interrompida (e reler a linha antes de responder).

**P3-02 — Idempotência da avaliação é verificar-e-agir sem trava.**
[on_demand.py](../../src/merchant_assistant/evaluation/on_demand.py:138) e inserção na linha 183. Dois POST simultâneos com o mesmo digest e sem avaliação concluída fazem duas chamadas pagas e gravam dois registros. A interface serializa reruns por sessão, então o risco real vem de duas abas ou de cliente direto; o gasto continua limitado pela guarda. Requisito: spec A7/B4 (proteção contra repetição). Correção esperada: reservar a avaliação de forma atômica (linha `running` ou índice único por `request_id`+`config_digest` para `repeat=false`).

**P3-03 — Contabilidade do limite demo: cobra 409 e não cobre outras ações pagas.**
[v1.py](../../src/merchant_assistant/api/v1.py:943) consome a mensagem antes de validar `comparison_id` (linha 952): um envio com comparação de Routers obsoleta ou divergente volta 409 e gasta uma mensagem sem inferência. Por outro lado, `POST /v1/router/compare` (linha 690, duas chamadas pagas) e `POST /v1/runs/{id}/evaluations` (linha 1100, inclusive com `repeat=true`) não contam. O limite é por sessão e se renova ao entrar de novo (documentado); o controle efetivo de gasto é o ledger. Requisito: RNF-10, RF-73, spec E. Correção esperada: consumir depois da validação da comparação, no mesmo bloco transacional; decidir e documentar se comparação de Routers e avaliação contam.

**P3-04 — Endereço do backend editável por padrão e trava só no widget.**
[app.py](../../../ai-getnet-case-web/app.py:465) (linha 469). Sem `LOCK_BACKEND_URL`, o visitante de um compartilhamento público pode apontar o servidor Streamlit para qualquer endereço alcançável a partir da máquina do responsável (requisições fixas `/v1/...`, mensagens de erro exibidas). Com a variável ligada, o campo fica `disabled`, mas o valor ainda vem do widget. Requisito: RF-72, RNF-10, ADR 0012. Correção esperada: quando travado, não criar o campo (usar `BACKEND_API_URL` diretamente); considerar travar por padrão quando o Streamlit escuta fora do loopback, ou incluir a conferência no passo 7 do guia como item obrigatório.

**P3-05 — Administração não trata falha de transporte; README afirma o contrário.**
[app.py](../../../ai-getnet-case-web/app.py:889) e linhas 928, 941–942, 978, 1044, 1092, 1117, 1144 só capturam `APIError`. Um `ReadTimeout` no build/teste de candidata (agora com 105 s) ou na carga da base gera exceção do Streamlit em vez de mensagem com ação; após a falha, estimativa e confirmação continuam em sessão e um novo clique faz outro build pago (o backend não deduplica builds). Pré-existente na v0.5.0 e restrito ao admin, mas o [README web](../../../ai-getnet-case-web/README.md:24) diz "no internal error is displayed". Requisito: spec A5, CA-44, prioridade de "recuperação sem POST repetido". Correção esperada: tratar `httpx.TransportError` nesses pontos com "atualize as versões (GET) antes de repetir" e limpar a estimativa/confirmação após falha de transporte; ou ajustar a frase do README.

**P3-06 — Reuso aceita execuções com histórico de conversa.**
[comparisons.py](../../src/merchant_assistant/comparisons.py:61) considera compatível qualquer execução do mesmo principal com mesmo cenário, perfil, mecanismo, base, prompts e modo, inclusive a segunda ou terceira mensagem de uma conversa (a interface sempre envia `conversation_id`). Histórico e estado do caso influenciam rota e resposta, então a célula "gravada" pode não ser comparável a uma nova. Requisito: RF-78/C2 (execuções compatíveis), C6 (fatores fixos). Correção esperada: reaproveitar só execuções sem histórico (primeira mensagem da conversa ou `purpose=comparison`), registrando isso no snapshot.

**P3-07 — Acesso à execução pela tabela e pelos pontos do gráfico 1.**
[app.py](../../../ai-getnet-case-web/app.py:313) (tabela de células na linha 406): a tabela mostra o `request_id`, mas só as barras do gráfico 2 abrem execuções; células com falha (sem custo por agente) não aparecem em nenhuma barra e não podem ser abertas, e os pontos do gráfico 1 não abrem nada. Requisito: spec C9 ("com acesso à execução") e a redação de CA-48/história ("cada ponto abre as execuções"). Correção esperada: seleção de célula/perfil que leia as execuções por GET, como já feito para as barras.

**P3-08 — Catálogo sem habilitação e cancelamento.**
[catalog.json](../../data/scenarios/catalog.json) tem 8 cenários (conhecimento, recebíveis, dispositivo, negação, preço, handoff, injeção, D). O plano (decisão 1) pede "ao menos um de cada jornada essencial"; habilitação (CA-22) e cancelamento (CA-23) ficaram de fora, e o limite de 6–8 impede incluí-los sem trocar outros. A regressão real de 40 casos continua cobrindo essas jornadas. Requisito: plano decisão 1. Correção esperada: registrar a interpretação de "jornada essencial" ou trocar dois cenários.

**P3-09 — Lacunas de teste e arestas de agregação.**
(a) Mutações M7 (cada célula captura a base ativa em vez da base fixada) e M11 (reuso sem conferir a versão da base) passam em toda a suíte: falta teste com ativação durante a comparação e com execução gravada noutra versão. (b) O teste do bloco D só cobre o lojista que tem `link_de_pagamento`; o ramo "não oferecer se não constar" não é exercitado. (c) [comparisons.py](../../src/merchant_assistant/comparisons.py:459) converte custo ausente em 0,0 na média/total (RF-75: desconhecido nunca como zero) e a linha 480 atribui o custo total do agente a cada modelo quando um agente usa mais de um modelo na mesma execução. Correção esperada: os dois testes de (a), um caso negativo em (b), e tratar custo `None` como "desconhecido" e não duplicar custo por modelo em (c).

**P3-10 — Papel admin simulado visível no compartilhamento.**
[app.py](../../../ai-getnet-case-web/app.py:452): no modo Simulado o visitante escolhe "Papel simulado: admin" e vê a aba Administração com dados de fixture. Não há acesso ao backend e o modo é rotulado, mas contradiz a leitura literal do momento "Entrar como demo: não vê Administração" num compartilhamento público. Correção esperada: esconder o papel admin simulado quando `LOCK_BACKEND_URL` estiver ligado, ou registrar como limitação.

### Riscos residuais (sem achado)

- `os.link` exige sistema de arquivos com hard link; em volume sem suporte a montagem falha fechada (sem gasto). Os volumes nomeados do compose e o NTFS suportam.
- O pior caso de duração de um atendimento pode passar dos 105 s do cliente (chamadas iniciadas perto do limite, embeddings de consulta); a recuperação por GET cobre esse caso no Atendimento.
- Todas as sessões demo compartilham o principal `demo:default`; IDs de execução e comparação são aleatórios, e a estimativa expõe IDs de execuções gravadas de cenário de outros visitantes do mesmo principal (conteúdo sintético e de catálogo).

### Critérios comprovados e não verificados

- Comprovados offline: contratos e snapshot; R2-01/02/03/05/07/08 com regressão que falha antes; limite demo no backend; avaliação sem nova inferência, com estimativa, confirmação, reserva, idempotência e falha registrada; comparação isolada, rastreável, com limites, reuso, falha parcial e interrupção; migração 0008 reversível; ausência de POST em rerun/aba/seleção (AppTest); validação estrita backend e web com código 0.
- Não verificados (dependem do QA real ou do responsável): comportamento dos modelos reais em D (CA-49), JEV real, Docker exercitado (CA-51), acesso de outra rede e HTTPS (CA-43/51, Q11/Q14/Q15), gasto real da campanha `v060-qa`, `docker compose config` com `.env`.

### Limitações e conduta desta revisão

- Nenhuma chamada paga, chave de provedor, aplicação com provedor real ou Docker. Nenhum comando Git que escreva.
- Uma busca `grep -rl KB-DEMO-DEVICES-001 data` sem escopo varreu arquivos de `data/runtime/` e imprimiu dois nomes de arquivo (índice Qdrant e traces); nenhum conteúdo foi exibido, usado ou alterado. `git status` listou nomes em `_tmp/`; nada foi aberto.
- Rodei `tools/generate_client.py --help` no repo web supondo uma ajuda; o script ignora argumentos e regravou `src/getnet_web/generated_api.py`. O SHA-256 depois é idêntico ao do manifesto (`210b603c…e6`); só a data de modificação mudou.
- Arquivos temporários e cópias (HEAD, candidato mutado, logs) ficaram no scratchpad da sessão, fora dos repositórios. O único arquivo escrito nos repositórios é este parecer.

### Passagem

- Ação externa autorizada: nenhuma realizada.
- Próxima ação e responsável: Supervisor decide entre encaminhar ao QA já (P3 podem seguir) ou devolver ao Developer os P3 baratos (P3-01, P3-03, P3-04, P3-05) antes; se houver correção, novo manifesto e revalidação do delta por este Reviewer.
- Decisão humana pendente: se o limite por sessão demo deve cobrir comparação de Routers e avaliação (P3-03) e se `LOCK_BACKEND_URL` passa a ser obrigatório/padrão no compartilhamento (P3-04).

## Rodada 2 — 2026-10-28

- Papel e responsável: o mesmo Reviewer independente da rodada 1 (Claude Opus 5.5, esforço high), sem delegação.
- Objetivo e critérios: revisão focada no delta r1 → r2. Critérios: Objetivo, Pré-condições, Passos e Critérios da [tarefa 60](../tasks/60-correcoes-revisao-v060-r1.md) (não li Validação nem Status); decisões do responsável repassadas pelo Supervisor (P3-04 mantido; o limite demo conta toda ação paga e recusa sem inferência não consome); ajustes do Supervisor (catálogo com 10 cenários e plano atualizado; CHECK de `run_evaluations.state` alterado dentro da 0008); regressão do que foi aprovado na rodada 1.
- Estado: **apto para QA** (nenhum P1/P2; 4 P3 novos ou residuais).
- Base e versão final: HEADs inalterados (backend `c3a9027b…`, web `4192169a…`); manifesto [v060-candidato-r2.json](v060-candidato-r2.json), pai `v060-candidato-r1.json`, fingerprint `d16c4e506190fefb00b8c3a7db1f1f04ed89ce7d61a3e5742a45fd856ad44e97`.
- Independência: independente. Não li `v060-developer.md`, `v060-supervisao.md` nem Validação/Status das tarefas.

### Hashes

| Momento | Resultado |
| --- | --- |
| Antes | 61 arquivos do backend e 13 do web idênticos ao manifesto r2; fingerprint reproduzido (`d16c4e50…4e97`); HEADs conferem |
| Depois | Mesma conferência: 0 divergências, mesmo fingerprint |
| Fora do mapa | `_tmp/**`, os dois manifestos, `v060-reviewer.md` e `v060-supervisao.md` (relatórios mutáveis, conforme a regra do r2) |
| Delta r1 → r2 (comparação dos manifestos) | Backend: `.env.example`, `CHANGELOG.md`, `README.md`, `catalog.json`, `api-v040.md`, `v060-developer.md`, `v060-qa-preparacao.md`, `guia-demonstracao.md`, `roteiro-teste-manual.md`, `fechamento-v060-plano.md`, `v1.py`, `comparisons.py`, `migrations.py`, `on_demand.py`, `test_v060_api.py`, `test_v060_doc_effect.py` e os novos `tasks/60` e `test_v060_r2.py`. Web: `README.md`, `app.py`, `test_v060_interface.py`. Coincide com a lista do Supervisor |

### Comandos executados (sem rede, sem custo, sem Docker)

| Comando | Resultado |
| --- | --- |
| Backend `lint_and_tests.py --strict` | **337 passed** (219 s), Ruff ok, skills ok, **exit 0** |
| Web `.venv-v040` `lint_and_tests.py --strict` | **34 passed** (25 s), Ruff ok, **exit 0** |
| OpenAPI do backend (`demo_mode=True`) × `openapi-v1.json` | **Idênticos**. Frente ao HEAD continua mudando só `POST /v1/messages`/`V1MessageRequest`, com as mesmas 6 rotas novas; `router/compare`, `evaluations`, `messages` e `comparisons` declaram `429`. `409 evaluation_running`, `history_turns` e `cost_unknown_runs` não alteram o esquema (corpos não tipados, mesmo padrão dos outros `409`) |
| 13 mutações novas no backend (cópia r2 no scratchpad) | 12 detectadas: R1 (marcação de interrompida sem condição de estado), R2 (avaliação sem trava `running`), R3/R4 (comparação de Routers e avaliação fora do limite), R5/R5b (sem devolução em recusa de orçamento), R6 (reuso com histórico), R7 (célula sem base fixa; era M7), R8 (reuso sem versão da base; era M11), R9 (custo ausente como zero), R10 (claim antigo sem expiração), R12 (`history_turns` sempre 0). **Sobrevive** R11: retirar o consumo do limite no envio que usa a decisão da comparação de Routers (ver P3-R2-03) |
| Mutações da rodada 1 sobre o r2 | M1, M2, M3, M4, M6, M9, M10, M12, M13, M14 e M15 continuam detectadas. M5 agora sobrevive porque a verificação antiga ficou redundante: a reserva atômica devolve o registro existente (coberto por R2) |
| 6 mutações no web (cópia no scratchpad, linha de base 34 passed) | Todas detectadas: build e teste sem tratar transporte, papel admin simulado no compartilhamento, célula e ponto que não abrem, custo desconhecido como zero na tabela |
| Rótulos dos dois cenários novos × `tests/scenarios/business_journeys.jsonl` | `SC-ENABLEMENT` = `V030-PT-ENABLEMENT-PENDING` e `SC-SALE-CANCELLATION` = `V030-PT-SALE-CANCELLATION`; todos os campos iguais, exceto o `id` |
| Sondas (testes descartáveis na cópia) | Ver P3-R2-01 |
| Banco migrado com a 0008 do r1 e aberto com o código do r2 | Gravar o claim (`state='running'`) → `IntegrityError: CHECK constraint failed` (ver P3-R2-02) |

### Situação dos achados da rodada 1

| Achado | Situação | Evidência |
| --- | --- | --- |
| P3-01 | **Resolvido** | `UPDATE … WHERE state='running'` e releitura; teste com corrida simulada; R1 detecta |
| P3-02 | **Resolvido** | Reserva `running` dentro de `BEGIN IMMEDIATE`. Dois POST simultâneos (inclusive com `repeat=true`) → uma única chamada do juiz e `409 evaluation_running`. O claim antigo expira em 10 min. R2 e R10 detectam |
| P3-03 | **Parcial** | Comparação de Routers e avaliação contam; o 409 de comparação obsoleta não consome (consumo na mesma transação); recusa de orçamento devolve a ação na comparação de Routers e na avaliação. Falta o mesmo para mensagens e células de comparação (P3-R2-01) |
| P3-04 | Mantido por decisão do responsável | O guia traz o passo como obrigatório |
| P3-05 | **Resolvido** | Build, teste, ativação e retorno tratam `TransportError`: descartam estimativa e confirmações e pedem GET antes de repetir; README coerente; W1/W6 detectam |
| P3-06 | **Resolvido** | `history_turns` no snapshot; só reaproveita execuções sem turnos anteriores; execuções anteriores ao r2 (sem o campo) não são reaproveitadas; R6/R12 detectam |
| P3-07 | **Resolvido** | A seleção de célula (inclusive com falha) e de ponto abre as execuções por GET; W3/W5 detectam |
| P3-08 | **Resolvido** | 10 cenários, incluindo habilitação e cancelamento; plano atualizado (decisão 1); o teste exige as 10 jornadas |
| P3-09 | **Resolvido**, com resíduo de exibição (P3-R2-04) | (a) testes de ativação durante a comparação e de reuso noutra versão (R7/R8 detectam); (b) caso negativo do bloco D com `cliente_demo_002`; (c) custo ausente fica nulo e é contado em `cost_unknown_runs`; um agente com vários modelos vira uma barra combinada |
| P3-10 | **Resolvido** | Com `LOCK_BACKEND_URL` ligado, o Simulado oferece só `demo`; W2 detecta |

Regressão do que foi aprovado na rodada 1: nada encontrado. Contratos, legado, isolamento, reserva e migração continuam cobertos pelas mutações acima e pela suíte.

### Achados novos ou residuais

Nenhum P1. Nenhum P2.

**P3-R2-01 — Recusa sem inferência ainda consome em mensagens e células de comparação; a documentação afirma o contrário.**
[v1.py](../../src/merchant_assistant/api/v1.py:974) consome antes de `execute_run`, e os ramos `RunFailure`/`RuntimeError` (linhas 1021–1030) não devolvem a ação. [comparisons.py](../../src/merchant_assistant/comparisons.py:245) consome todas as execuções novas no início; células puladas por base alterada (linha 303), teto da comparação (330) ou negação de orçamento (365/379) não são devolvidas. Numa sonda com `reserve` sempre negando, a mensagem volta `503 router_unavailable` com **0 chamadas ao modelo e contador 1**, e a comparação de 4 células termina `failed`/`skipped` sem inferência com **contador 4**. O [guia](../guia-demonstracao.md) (linha 29), o CHANGELOG e o README dizem que "orçamento negado antes da primeira chamada" não conta. O impacto prático é pequeno: com o orçamento negado nenhuma ação paga é possível, e o ledger continua protegendo o gasto. Mas a regra decidida não vale nesses casos. Correção esperada: devolver a ação quando a execução terminar sem chamada ao modelo (`model_calls == 0` no trace) e devolver as células não executadas; ou ajustar a documentação.

**P3-R2-02 — CHECK alterado dentro da 0008 quebra bancos que já aplicaram a 0008 do r1.**
[migrations.py](../../src/merchant_assistant/data/migrations.py) passou a aceitar `running` sem nova migração. Um banco que subiu com o r1 fica na versão 8 com o CHECK antigo, e o r2 não o corrige. Reproduzi o `IntegrityError` ao gravar o claim, o que vira erro 500 em toda avaliação por IA. Os testes usam bancos novos. A mudança é aceitável enquanto a 0008 não for publicada, mas o QA precisa partir de bancos que nunca rodaram o r1. Não verifiquei `data/runtime/` nem o volume Docker (fora dos meus limites). Correção esperada: antes do QA, conferir só por leitura, em cada banco que será usado, `SELECT sql FROM sqlite_master WHERE name='run_evaluations'` (deve conter `'running'`), ou confirmar que o esquema ainda está na versão 7.

**P3-R2-03 — Falta teste do consumo no envio que usa a decisão da comparação de Routers.**
A mutação R11 (trocar o `consume_demo_messages` da linha 995 de [v1.py](../../src/merchant_assistant/api/v1.py:995) por `if False`) passa em `test_v060_r2.py`, `test_v060_api.py` e `test_v1_api.py`. Sem esse teste, uma regressão deixaria fora do limite o atendimento iniciado pela decisão dos Routers. Correção esperada: um teste com limite 1 em que comparar e usar a decisão esgote o limite.

**P3-R2-04 — A interface ainda mostra custo desconhecido como número em dois pontos.**
[app.py](../../../ai-getnet-case-web/app.py:282) exibe `US$ 0.000000` para avaliação `running` ou interrompida (`cost_usd` nulo). As barras do gráfico 2 (linhas 441 e 451) usam `bar["cost_usd"]` e ignoram o `cost_unknown` que o backend já envia, então um agente com custo ausente aparece como zero ou como soma parcial. Requisito: RF-75 ("nunca aparece como zero"). Correção esperada: usar `money()` nesses rótulos e marcar a barra como "custo desconhecido" quando `cost_unknown` for verdadeiro.

### Observações

- O catálogo mudou de conteúdo (8 → 10 cenários) mantendo `"version": "1"`. Como nada foi publicado, não é achado; mas, se houver comparações gravadas com o catálogo de 8, o `scenario_catalog_version` registrado não as distingue.
- Pela decisão do responsável, a comparação de Routers e o atendimento que usa a decisão contam como duas ações. É coerente com "toda ação paga": as duas fazem chamadas pagas.

### Limitações e conduta

- Nenhuma chamada paga, chave, Docker, comando Git que escreva nem execução de `tools/generate_client.py`. Não acessei `data/runtime/`, controles de campanha, `.env`, `_tmp/` nem `discovery/`.
- Cópias do r2 (backend e web), bancos de sonda e logs ficaram no scratchpad da sessão. O único arquivo alterado nos repositórios foi este parecer, com esta seção acrescentada.

### Passagem

- Ação externa autorizada: nenhuma realizada.
- Próxima ação e responsável: o Supervisor confere a pré-condição de P3-R2-02 antes de despachar o QA. Os demais P3 podem seguir ou voltar ao Developer, a critério do Supervisor.
- Decisão humana pendente: nenhuma nova. P3-R2-01 é uma escolha entre corrigir o código ou ajustar a documentação.

## Rodada 3 — 2026-10-28

- Papel e responsável: o mesmo Reviewer independente (Claude Opus 5.5, esforço high), sem delegação.
- Objetivo e critérios: revisão focada no delta r2 → r3. Critérios: itens 11–14 da seção "Resíduos da revisão r2" e os Critérios de conclusão da [tarefa 60](../tasks/60-correcoes-revisao-v060-r1.md) (sem Validação/Status); a regra do responsável ("o limite demo conta toda ação paga; recusa sem inferência não consome"); os pontos pedidos pelo Supervisor.
- Estado: **apto para QA** (nenhum P1/P2; 1 P3 novo).
- Base e versão final: HEADs inalterados (backend `c3a9027b…`, web `4192169a…`); manifesto [v060-candidato-r3.json](v060-candidato-r3.json), pai `v060-candidato-r2.json`, fingerprint `d8d9178df2dcc97acd40d5bf4300a9db75f8ba4b641c24f1ffd61e24cabf819d`.
- Independência: independente. Não li `v060-developer.md`, `v060-supervisao.md` nem Validação/Status.

### Hashes

| Momento | Resultado |
| --- | --- |
| Antes | 61 arquivos do backend e 13 do web idênticos ao manifesto r3; fingerprint reproduzido (`d8d9178d…819d`); HEADs conferem |
| Depois | Mesma conferência: 0 divergências, mesmo fingerprint |
| Delta r2 → r3 (comparação dos manifestos) | Backend: `.env.example`, `CHANGELOG.md`, `README.md`, `v060-developer.md`, `guia-demonstracao.md`, `tasks/60`, `v1.py`, `comparisons.py`, `test_v060_r2.py`. Web: `README.md`, `app.py`, `test_v060_interface.py`. Coincide com a lista do Supervisor |

### Comandos executados (sem rede, sem custo, sem Docker)

| Comando | Resultado |
| --- | --- |
| Backend `lint_and_tests.py --strict` | **340 passed** (242 s), Ruff ok, skills ok, **exit 0** |
| Web `.venv-v040` `lint_and_tests.py --strict` | **35 passed** (23 s), Ruff ok, **exit 0** |
| OpenAPI do backend (`demo_mode=True`) × `openapi-v1.json` | **Idênticos**; frente ao HEAD continua mudando só `POST /v1/messages`/`V1MessageRequest`. `model_calls` das células fica dentro do JSON de `cells` (corpo não tipado): só acréscimo, sem efeito no esquema nem na migração |
| Mutações no backend (cópia r3 no scratchpad) | Todas detectadas: **R11** (que sobrevivia no r2), R13 (mensagem sem devolução), R14 (células sem devolução), R15 (mensagem sempre devolvida), R16 (células sempre devolvidas) e, de regressão, R2, R3, R6 e M4 |
| Mutações no web (cópia r3) | Todas detectadas: W7 (avaliação com custo nulo vira `US$ 0.000000`), W8 (barra ignora `cost_unknown`) e, de regressão, W2 e W4 |
| Sonda: mensagens comuns (injeção, cartão mascarado, "oi", handoff, texto curto) | Todas fazem de 1 a 3 chamadas ao modelo e **consomem** o limite; recusa determinística comum não fica de graça (a Personality responde) |
| Sonda: falha de persistência (`sqlite3.OperationalError` em `_persist`) depois das chamadas pagas | HTTP 500; ledger com `router` e `personality` liquidados; contador **devolvido para 0** (ver P3-R3-01) |

### Situação dos resíduos do r2

| Resíduo | Situação | Evidência |
| --- | --- | --- |
| P3-R2-01 | **Resolvido** | Mensagem: `finally` devolve a ação quando o trace registra 0 chamadas (`v1.py:1029`). Comparação: no fim, as células novas sem chamada são devolvidas (`comparisons.py:390`), inclusive as puladas por base alterada, teto ou orçamento. Testes de mensagem com orçamento negado e de comparação com 3 de 4 células devolvidas; R13/R14 e R15/R16 detectam. Guia, CHANGELOG, README e `.env.example` coerentes |
| P3-R2-02 | Encerrado sem código | Pré-condição atendida pela conferência do Supervisor (esquema 4, sem `run_evaluations`; o QA cria runtime novo). Não verifiquei `data/runtime/` |
| P3-R2-03 | **Resolvido** | Teste: comparar + usar a decisão esgota o limite 2; R11 agora detecta |
| P3-R2-04 | **Resolvido** | `usd()` mostra "desconhecido" para custo nulo da avaliação; barras com `cost_unknown` saem do gráfico com legenda e rótulo "custo desconhecido"; W7/W8 detectam |

### Ponto 2 — a devolução abre brecha de custo ou de abuso?

Não encontrei brecha de custo explorável pelo visitante:

- O critério é o `model_calls` do contexto da execução, que só sobe depois de uma reserva bem-sucedida no ledger ([run.py](../../src/merchant_assistant/orchestration/run.py)). Zero chamadas significa que nenhuma chamada paga de modelo foi reservada nessa execução.
- A única chamada paga fora do contexto é o embedding da consulta. Ele ocorre depois do Router, que conta como chamada, exceto quando a decisão vem de uma comparação de Routers, e essa comparação já consumiu uma ação. O custo residual é de embedding (ordem de 10⁻⁶ US$) e continua sob a guarda.
- A recusa determinística comum chama a Personality e consome (sonda). Execuções com zero chamadas só surgem com o orçamento negado, provedor indisponível ou falha antes da primeira reserva, casos em que nada pago acontece. O efeito é apenas que essas requisições sem custo deixam de ser limitadas por sessão. Como o limite já se renova ao entrar de novo (limitação documentada), isso não muda o controle efetivo, que segue sendo o ledger.

O resíduo é a fonte da informação, descrita abaixo.

### Achado novo

Nenhum P1. Nenhum P2.

**P3-R3-01 — Devolução decidida pelo trace falha aberta quando a execução aborta depois de chamadas pagas.**
[v1.py](../../src/merchant_assistant/api/v1.py:810) `model_calls_made` lê o trace e devolve 0 quando ele não existe. O trace só é gravado no fim de `handle` (`_record`, depois de `_persist`). Uma exceção inesperada depois das chamadas pagas, por exemplo `database is locked` ao persistir a conversa, deixa o run sem trace: a mensagem volta 500, o ledger tem as chamadas liquidadas e a ação é devolvida (sonda: contador 1 → 0). O mesmo vale para células `execution_failed` da comparação. O visitante não consegue provocar isso pela interface e o gasto continua limitado pelo ledger, mas a regra "recusa sem inferência" fica aplicada a uma execução com inferência. Correção esperada: decidir pela existência de linhas no ledger com o `request_id` (o ledger já guarda o `request_id` de cada reserva) ou pelo `model_calls` do contexto, e não pela presença do trace. Na falta de informação, não devolver.

### Limitações e conduta

- Nenhuma chamada paga, chave, Docker, comando Git que escreva nem execução de `tools/generate_client.py`. Não acessei `data/runtime/`, controles de campanha, `.env`, `_tmp/` nem `discovery/`.
- Cópias r3, sondas descartáveis e logs ficaram no scratchpad. O único arquivo alterado nos repositórios foi este parecer, com esta seção acrescentada.

### Passagem

- Ação externa autorizada: nenhuma realizada.
- Próxima ação e responsável: Supervisor despacha o QA com o candidato r3. P3-R3-01 pode seguir como pendência ou voltar ao Developer (correção pequena e isolada).
- Decisão humana pendente: nenhuma.

## Rodada 4 — 2026-10-28

- Papel e responsável: o mesmo Reviewer independente (Claude Opus 5.5, esforço high), sem delegação.
- Objetivo e critérios: revisão focada no delta r3 → r4 (correções do QA r1). Critérios: Objetivo, Passos e Critérios da [tarefa 61](../tasks/61-correcoes-qa-v060-r1.md) (sem Validação/Status), CA-32/33/47/48 e os pontos pedidos pelo Supervisor. Não li `v060-qa.md`, `v060-qa-environment.json`, `v060-developer.md` nem `v060-supervisao.md`; o contexto do P1 veio da tarefa 61 e da mensagem do Supervisor.
- Estado: **apto para QA** (nenhum P1/P2; 2 P3 novos).
- Base e versão final: HEADs inalterados (backend `c3a9027b…`, web `4192169a…`); manifesto [v060-candidato-r4.json](v060-candidato-r4.json), pai `v060-candidato-r3.json`, fingerprint `b5748d7e48ca5153c8b124d4da9206198d68881d12bcb1a3832d4adeb1e6f307`.
- Independência: independente.

### Hashes

| Momento | Resultado |
| --- | --- |
| Antes | 63 arquivos do backend e 13 do web idênticos ao manifesto r4; fingerprint reproduzido (`b5748d7e…f307`); HEADs conferem |
| Depois | Mesma conferência: 0 divergências, mesmo fingerprint |
| Delta r3 → r4 (comparação dos manifestos) | Backend: `CHANGELOG.md`, `README.md`, `v060-developer.md`, `tasks/61`, `v1.py`, `comparisons.py`, `graph.py` e o novo `test_v060_r4.py`. Web: `README.md`, `app.py`, `test_v060_interface.py`. Coincide com a lista do Supervisor |

### Comandos executados (sem rede, sem custo, sem Docker)

| Comando | Resultado |
| --- | --- |
| Backend `lint_and_tests.py --strict` | **347 passed** (303 s), Ruff ok, skills ok, **exit 0** |
| Web `.venv-v040` `lint_and_tests.py --strict` | **40 passed** (31 s), Ruff ok, **exit 0** |
| OpenAPI do backend (`demo_mode=True`) × `openapi-v1.json` | **Idênticos**. `/ready` declara resposta sem esquema (`{}`), então o campo `knowledge_base` não muda o contrato. `api/app.py` (legado `POST /messages`, `/ready`) e `mcp_server.py` sem alteração em relação ao HEAD |
| 9 mutações no backend (cópia r4 no scratchpad) | Detectadas: **J1** (`execute_run` volta a excluir o `router` em JEV, o defeito do QA), **J2** (o grafo ignora `router_llm`), J3 (`paid_attempts` sempre 0), J4 (ledger ilegível devolve), J6 (conta reservas canceladas), J8/J9 (sem devolução em mensagem e em células). **Sobrevivem** J5 e J7: o lado da comparação voltar ao trace, ou devolver com `None` (ver P3-R4-02) |
| 6 mutações no web (cópia r4) | Detectadas: L1 (`R$` sem escape vira fórmula), L2 (recuperação sem estado do caso), L3 (nomes sem português), L4b (ordem alfabética dos perfis), L5 (teto do teste volta a 0). A L4 inicial (ordem alfabética inversa) não era mutação válida, porque mantinha Referência em primeiro |

### Verificação dos pontos pedidos

1. **JEV de verdade nos dois caminhos.** `execute_run` passa todos os agentes do perfil (`v1.py:907`), e o grafo substitui a entrada `router` por `router_llm` quando ele existe (`graph.py:225`). Com isso, o Router em JEV é sempre o adaptador TypeSafe e nunca chega a construir o LLM do perfil. Os testes usam transporte JEV falso e conferem:
   - envio direto e comparação de perfis em JEV: uma chamada ao adaptador por execução e nenhuma chamada LLM do Router;
   - ledger com `router`/`jev-1.14.0`;
   - snapshot `router_mechanism=jev` e `models.router=typesafe:jev-1.14.0`, com `models_by_agent.router` no snapshot, no trace e no custo por agente das células;
   - toggle LLM continua chamando o Router do perfil, sem payload JEV.

   J1 e J2 reintroduzem o defeito e são detectadas. Com a decisão vinda de uma comparação de Routers, o Router não é chamado em nenhum dos dois modos.
2. **Comparação só dos Routers.** `POST /v1/router/compare` (`compare`/`_decision`) não mudou. O `diff` de `v1.py` só toca `paid_attempts`, `agent_models` e o `finally` de `messages_v1`.
3. **P3-R3-01.** A decisão passou a ser o número de linhas `reserved`/`settled` do `request_id` no ledger primário (`paid_attempts`, `v1.py:816`); `None` (caminho em memória ou erro de leitura) nunca devolve, tanto na mensagem (`== 0`) quanto nas células (`comparisons.py:400`). A falha de persistência depois das chamadas pagas, que devolvia no r3, agora mantém a ação contada, e J3/J4/J6 detectam.
   - Brecha nova: não encontrei. A reserva cancelada só acontece antes do envio ao provedor. No guard combinado, a linha primária só existe se as duas reservas passaram. Embeddings de consulta não carregam `request_id`, mas só ocorrem depois do Router (já contado) ou de uma decisão de comparação (já contada).
   - Custo de desempenho: uma conexão SQLite curta por mensagem e por célula, desprezível.
4. **Observações do QA.**
   - Perfis: ordem Referência/Híbrido/Ajustado e nomes em português.
   - Teto do teste: pré-preenchido com a estimativa do build, e a ação paga continua exigindo confirmação.
   - `/ready`: campo `knowledge_base` com versão e coleção ativas, coberto por teste com ativação.
   - Gráfico 1: rótulos movidos para a legenda.
   - Recuperação de conversa: o estado do caso mostra rota, status e estado da conversa recuperada, a partir de campos que o `GET` de conversa já devolve; protocolo e versão da base ficam "—".

### Achados novos

Nenhum P1. Nenhum P2.

**P3-R4-01 — O escape de `$` só cobre o histórico do chat.**
`literal()` ([app.py](../../../ai-getnet-case-web/app.py:89)) é aplicado às mensagens do chat (linha 642), mas não à "Pergunta pendente" (linha 701, texto livre do lojista em `st.write`) nem ao comentário do avaliador por IA (linha 306, saída do modelo em `st.write`). Um texto com dois valores em reais, como "paguei R$ 10 e R$ 20", ainda vira fórmula nesses dois pontos. Requisito: P3-QA-02 ("texto exibido igual ao gravado"). Correção esperada: aplicar `literal()` também nesses dois pontos.

**P3-R4-02 — Devolução das células da comparação sem teste de falha aberta.**
As mutações J5 (células voltam a decidir pelo trace) e J7 (células devolvem quando o ledger é ilegível) passam em `test_v060_r4.py` e `test_v060_r2.py`. O código de `comparisons.py:400` está correto, mas só a mensagem tem os testes de "falha depois de chamada paga" e "ledger ilegível". Correção esperada: os mesmos dois testes para uma célula de comparação (`execution_failed` sem trace com linhas no ledger, e `paid_attempts` devolvendo `None`).

### Limitações e conduta

- Nenhuma chamada paga, chave, Docker, comando Git que escreva nem execução de `tools/generate_client.py`. Não acessei `data/runtime/`, controles de campanha, runtimes reais, `.env`, `_tmp/` nem `discovery/`.
- Cópias r4, scripts de mutação e logs ficaram no scratchpad. O único arquivo alterado nos repositórios foi este parecer, com esta seção acrescentada.

### Passagem

- Ação externa autorizada: nenhuma realizada.
- Próxima ação e responsável: Supervisor reencaminha ao QA a revalidação do item 3 (JEV real) e das observações com o r4. P3-R4-01/02 podem seguir como pendência ou voltar ao Developer (correções pequenas).
- Decisão humana pendente: nenhuma.

## Rodada 5 — 2026-10-28

- Papel e responsável: o mesmo Reviewer independente (Claude Opus 5.5, esforço high), sem delegação.
- Objetivo e critérios: revisão rápida do delta r4 → r5. Critérios: itens 7 e 8 da seção "Resíduos da revisão r4" da [tarefa 61](../tasks/61-correcoes-qa-v060-r1.md) (sem Validação/Status) e os três pontos do Supervisor.
- Estado: **apto para QA** (nenhum achado novo).
- Base e versão final: HEADs inalterados (backend `c3a9027b…`, web `4192169a…`); manifesto [v060-candidato-r5.json](v060-candidato-r5.json), pai `v060-candidato-r4.json`, fingerprint `3b6b697e53623ac08c54a521cc0aa094e2e5cc7e247b83a4c11e3ca9075a2639`.
- Independência: independente; não li relatórios do Developer, QA ou Supervisor.

### Hashes

| Momento | Resultado |
| --- | --- |
| Antes | 63 arquivos do backend e 13 do web idênticos ao manifesto r5; fingerprint reproduzido (`3b6b697e…2639`); HEADs conferem |
| Depois | Mesma conferência: 0 divergências, mesmo fingerprint |
| Delta r4 → r5 | Backend: `CHANGELOG.md`, `README.md`, `v060-developer.md`, `tasks/61`, `test_v060_r4.py`. Web: `README.md`, `app.py`, `test_v060_interface.py`. Coincide com a lista do Supervisor. `comparisons.py` e `v1.py` estão byte a byte iguais ao r4 (comparação sem CR com a cópia r4 do scratchpad) |

### Comandos executados (sem rede, sem custo, sem Docker)

| Comando | Resultado |
| --- | --- |
| Backend `lint_and_tests.py --strict` | **349 passed** (235 s), Ruff ok, skills ok, **exit 0** |
| Web `.venv-v040` `lint_and_tests.py --strict` | **42 passed** (32 s), Ruff ok, **exit 0** |
| Mutações J3, J4, J5, J7 e J9 na cópia r4 com o teste do r5 | **Todas detectadas**; J5 e J7, que sobreviviam no r4, agora caem nos dois testes novos da comparação |
| Mutações de escape no web (cópia r5) | Detectadas: L6 (pergunta pendente sem escape), L7 (comentário do avaliador), L8 (mensagem de erro do backend em `explain`). Sobrevive L9 (mensagem do cenário sem escape), ver Observações |

Registro de contagem: na rodada 4 o log da validação estrita do web registrou **40 passed** (era o que estava na tabela desta passagem). O "35" da minha resposta ao Supervisor naquela rodada foi erro de transcrição: repeti a contagem da rodada 3.

### Verificação

1. **P3-R4-01 — resolvido.** `literal()` passou a cobrir:
   - a pergunta pendente (`st.write`);
   - o comentário do avaliador;
   - toda mensagem de erro do backend, via `explain()`;
   - os títulos de fontes;
   - os avisos de falha da comparação;
   - a mensagem do cenário.

   Revisei todas as chamadas `st.write/markdown/caption/info/warning/error/success` com variáveis em `app.py`. As restantes interpolam só identificadores, enums, números, trechos em código (entre crases) ou o nome de uma chave (`KeyError`). Nenhuma tem texto livre com `$`. Os trechos recuperados usam `st.text` e o diff usa `st.code`, ambos literais.

   O escape é só de exibição. O histórico guarda o texto cru e o teste confirma que `pending_message.message` continua igual ao digitado. O que é enviado e gravado não muda.
2. **P3-R4-02 — resolvido.** Dois testes novos de comparação:
   - célula que falha depois de chamadas pagas sem deixar trace não é devolvida (contador 2);
   - com ledger ilegível, a célula iniciada fica contada e só a nunca iniciada é devolvida.

   `comparisons.py` não mudou.
3. **Regressões:** nenhuma. Suítes completas passam e as mutações anteriores pertinentes continuam detectadas.

### Observações (sem achado)

- O escape da mensagem do cenário não tem teste (L9). Hoje nenhum cenário do catálogo contém `$`. Fontes e avisos de falha também foram escapados sem teste dedicado.

### Limitações e conduta

- Nenhuma chamada paga, Docker, comando Git que escreva nem `generate_client.py`. Não acessei `data/runtime/`, controles de campanha, `.env`, `_tmp/` nem `discovery/`.
- Cópias e logs no scratchpad. O único arquivo alterado nos repositórios foi este parecer, com esta seção acrescentada.

### Passagem

- Ação externa autorizada: nenhuma realizada.
- Próxima ação e responsável: Supervisor segue com o QA focal no r5.
- Decisão humana pendente: nenhuma.
