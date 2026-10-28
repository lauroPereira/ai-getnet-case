# Supervisão v0.6.0 — fechamento

## Retomada e revisão (2026-10-27)

O responsável pediu, na sessão Claude Code, retomar o SDD substituindo as antigas v0.6.0 e v0.7.0 por uma única v0.6.0 de simplificação, demonstração e fechamento. Supervisor (Claude Opus 5.5, sessão principal) revisou os dois repositórios, o fechamento da v0.5.0 e o SDD.

- **v0.5.0 aprovada e não integrada:** todo o candidato r7 estava no working tree de `codex/v0.5.0-base-versionada`, com HEAD igual à main v0.4.0 nos dois repositórios. Conferência própria: 46/85 arquivos de fonte, 128 de runtime e 129 de build sem divergência. Fora do manifesto: evidências (versionadas) e `_tmp/` com SQLite temporários da revisão (não versionados, preservados).
- **Lacunas:** sem entrada 0.5.0 no CHANGELOG; tags só até `v0.3.0`; critérios CA-21–24 e CA-32–41 desmarcados apesar de evidências; tarefas 47–53 com status desatualizado; tarefa 46 aberta.

## Orçamento reconciliado (somente leitura)

| Ledger | Entradas | Comprometido | Reservas abertas |
| --- | ---: | ---: | ---: |
| Primário `data/runtime/budget.sqlite3` (teto persistente US$1) | 885 | US$0,34852844 | 0 |
| Campanha v0.5 `.pytest_cache/v050-qa-control/` (contida no primário) | 35 | US$0,00553883 | 0 |
| Validação v0.3 `.pytest_cache/v030-real-runtime/` | 521 | US$0,14123583 | 0 |

Último registro em 2026-10-27T20:41:07Z, igual ao fechamento da v0.5.0. Acumulado do projeto **US$0,59837466 de US$5**; saldo agregado US$4,40162534; saldo efetivo do ledger primário **US$0,65147156**. O ledger do volume Docker não foi lido nesta etapa; não teve uso desde a v0.2.0.

## Integração da v0.5.0

Autorização do responsável: “PRs, merge e tags”. Identidade local conferida (`lauroPereira <lauro.s.pereira@gmail.com>`) e `gh` autenticado como `lauroPereira`.

- Backend: `716eb2f` (produto e SDD) e `c719719` (evidências e CHANGELOG 0.5.0), sem `_tmp/`. Web: `f8800ff`. Blobs conferidos contra o r7: backend 25 idênticos e 21 com normalização de fim de linha; web 51 e 34; zero divergências.
- PRs: [backend #6](https://github.com/lauroPereira/ai-getnet-case/pull/6) e [web #2](https://github.com/lauroPereira/ai-getnet-case-web/pull/2), limpos e sem checks de CI configurados.
- **Incidente de identidade:** `gh pr merge` criou os merges `6598683` e `8f82128` com o e-mail principal da conta GitHub, diferente da identidade do projeto. O AGENTS.md pede merge local nesse caso. Com aprovação explícita do responsável (“Refazer merge local”), os merges foram recriados com a identidade do projeto, mesma árvore e mesmos pais, e publicados com `--force-with-lease`: backend `c3a9027b7c218f560345576770a646d4ec2bc098`, web `4192169afc8b37f150d88fdf16e3529a0fd33b90`. Os PRs continuam como merged; os commits antigos ficam sem referência nas branches. Próximas integrações: merge local.
- Tags anotadas com a identidade do projeto: `v0.4.0` (backend `ea2355b`, web `40ff199`) e `v0.5.0` (backend `c3a9027`, web `4192169`), publicadas e conferidas no remoto.
- Branches `codex/v0.6.0-fechamento` criadas a partir das mains atualizadas nos dois repositórios.

## Recorte aprovado

Respostas do responsável em 2026-10-27: recorte “como descrito”, incluindo contratos `/v1` aditivos, migração 0008, limite por sessão demo e API do compose só local; subagentes **Claude Opus 5.5** com esforço high (substituto de `gpt-6-luna`, indisponível nesta sessão); teto da campanha `v060-qa` **US$0,50**.

SDD gravado na branch v0.6.0: [especificação complementar 0.3](../specs/incrementos-pos-nucleo.md), [plano complementar 0.3](../specs/incrementos-pos-nucleo-plano.md), [spec](../specs/fechamento-v060.md) e [plano](../specs/fechamento-v060-plano.md) da v0.6.0, [história v1](../historias/fechamento-v060.md), [ADR 0015](../architecture/decisions/0015-recorte-final-v060.md), tarefas 54–59 e status das tarefas 46–53. Nenhum produto implementado, agente acionado ou chamada paga nesta etapa.

## Despacho do Developer

O responsável aceitou o SDD e mandou acionar o Developer (“Acionar Developer”). Novo subagente Developer acionado como **Claude Opus 5.5, esforço high**, contexto novo (sem herdar a conversa do Supervisor), para as tarefas 54–58 nos dois repositórios, na branch `codex/v0.6.0-fechamento`. Limites passados: nenhuma chamada paga; sem acesso a `data/runtime/`, controles de campanha, runtimes reais, `.env`, `_tmp/` e `discovery/`; sem commit, push ou Git destrutivo; sem editar arquivos protegidos ou evidências históricas; só as rotas aprovadas (`GET /v1/runs` fora); sem delegação aninhada. Passagem única esperada em `docs/evidence/v060-developer.md`. Reviewer e QA ainda não acionados.

## Passagem do Developer e candidato r1

[Developer](v060-developer.md) relatou as tarefas 54–58 concluídas na sua parte, com validação estrita backend 326 testes e web 30 testes, ambos código 0, sem chamada paga, commit ou build Docker. Única ação de rede: instalar `ruff==0.17.2` no ambiente web existente.

Conferência do Supervisor: HEADs inalterados (`c3a9027`, `4192169`); `AGENTS.md`, `CLAUDE.md`, `skills/`, `.claude/`, `.agents/`, `docs/raw/` e evidências históricas intactos; ledger primário 885 entradas/US$0,34852844 e campanha v0.5 35/US$0,00553883, sem reservas e com `data/runtime/` sem modificação; `_tmp/` com os mesmos 29 arquivos.

Decisões do Developer além do texto literal do plano, avaliadas pelo Supervisor:

| Decisão | Avaliação |
| --- | --- |
| `CAMPAIGN_CAP_LIMIT_USD` 0.25 → 0.50 | Necessária para a campanha `v060-qa` de US$0,50 aprovada pelo responsável |
| Scripts estritos excluem `.pytest_cache` e `_tmp` (web também `.venv*`) | Aceita: artefatos não versionados; Reviewer confere que nenhuma fonte fica de fora |
| Timeout longo também para comparação de Routers, avaliação e build/teste | Coerente com a tarefa 54 |
| Limite demo conta execuções novas de comparação | Coerente com o limite próprio de consumo do demo (RF-73) |
| `LOCK_BACKEND_URL` opcional, desligado por padrão | Controle de segurança novo. Responsável decidiu em 2026-10-27 “Manter opcional”: desligado por padrão e obrigatório no compartilhamento (o comando de exposição do guia já o liga); o QA confere o travamento na interface exposta |
| `BudgetMeter` aceita `effective_parameters` | Correção de defeito no caminho pago do CLI |
| Ajustado em banco v0.5 existente publicado pelo admin | Documentado no guia |

`GET /v1/runs` não foi implementado (não aprovado). [Candidato r1](v060-candidato-r1.json): 59 arquivos backend e 13 web sobre os HEADs, fingerprint `789d6f5303016125e1b0ef6ff8a8315ed06aec1ff053a331ff48e4133310c714`.

## Despacho do Reviewer

Novo Reviewer **Claude Opus 5.5, esforço high**, contexto novo, com manifesto, critérios e fontes; instruído a não ler as seções Validação/Status das tarefas 54–58 nem a passagem do Developer. Somente leitura do produto, sem chamada paga, Docker, Git de escrita ou delegação; parecer em `docs/evidence/v060-reviewer.md`. Pontos explícitos: teto da campanha, exclusões do lint, `LOCK_BACKEND_URL`, contagem do limite demo e alcance do timeout.

## Parecer r1 e correções antes do QA

[Reviewer r1](v060-reviewer.md): **apto para QA**, 0 P1, 0 P2, 10 P3. Hashes de 51 arquivos backend e 13 web e o fingerprint conferidos antes e depois; estrita backend 326 e web 30 passaram; 14 de 16 mutações detectadas; OpenAPI do backend idêntico ao snapshot web, só rotas aprovadas. Duas ocorrências declaradas pelo Reviewer: `tools/generate_client.py --help` regravou o cliente web com o mesmo hash (só mudou a data de modificação); um `grep` sem escopo listou dois nomes de arquivo em `data/runtime/`, sem conteúdo exibido ou alterado.

Decisões do responsável em 2026-10-27: corrigir antes do QA os P3 de orçamento, integridade e aceite (01, 02, 03, 05, 06, 07, 08, 09, 10); o limite demo conta **toda ação paga**, e recusa sem inferência não consome; P3-04 segue a decisão anterior (opcional). [Tarefa 60](../tasks/60-correcoes-revisao-v060-r1.md) devolvida ao mesmo Developer. Depois, revisão do delta pelo mesmo Reviewer e QA no novo candidato.

## Rodada 2 do Developer e candidato r2

[Developer rodada 2](v060-developer.md#rodada-2--2026-10-27): P3-01/02/03/05/06/07/08/09/10 corrigidos, estrita backend 337 e web 34, código 0, sem chamada paga. P3-04 intocado. Desvios aceitos pelo Supervisor: catálogo com 10 cenários (plano ajustado) e CHECK de `run_evaluations.state` alterado dentro da migração 0008 ainda não publicada; runtimes sintéticos do r1 precisam ser recriados. Acréscimos de contrato nas rotas aprovadas: `409 evaluation_running`, `429` do limite demo nas novas ações pagas, campos `history_turns` e `cost_unknown_runs`.

Conferência: HEADs inalterados, protegidos e históricos intactos, ledger primário 885/US$0,34852844 com `data/runtime/` sem modificação, `_tmp/` com 29 arquivos. [Candidato r2](v060-candidato-r2.json): 61 arquivos backend e 13 web, fingerprint `d16c4e506190fefb00b8c3a7db1f1f04ed89ce7d61a3e5742a45fd856ad44e97`; a partir dele, os relatórios do Reviewer e do QA são mutáveis e ficam fora do mapa. Mesmo Reviewer reativado para o delta r1 → r2.

## Parecer r2 e resíduos

[Reviewer rodada 2](v060-reviewer.md): **apto para QA**, 0 P1, 0 P2, 4 P3. Hashes r2 conferidos antes e depois; estrita backend 337 e web 34; OpenAPI idêntico; mutações novas 12/13 e web 6/6 detectadas. P3-01/02/05/06/07/08/09/10 resolvidos; P3-03 parcial.

Resíduos P3-R2-01 (recusa sem inferência ainda consome em mensagem com orçamento negado e células puladas), P3-R2-03 (teste do envio com decisão de Routers) e P3-R2-04 (custo desconhecido mostrado como número na interface) voltam ao mesmo Developer como rodada 3 da tarefa 60, dentro da decisão já tomada pelo responsável de corrigir antes do QA. P3-R2-02 (CHECK alterado na 0008 quebra bancos com a 0008 do r1): conferido pelo Supervisor, em leitura, que `data/runtime/merchant.sqlite3` está no esquema 4 e sem `run_evaluations`; Docker não executado desde a v0.5; o QA cria runtime novo.

## Rodada 3 e candidato r3

[Developer rodada 3](v060-developer.md): P3-R2-01/03/04 corrigidos com teste; estrita backend 340 e web 35, código 0. Desvio aceito: execução sem chamada ao modelo (inclusive recusa determinística) devolve a ação demo, coerente com a regra do responsável. [Candidato r3](v060-candidato-r3.json): 61 backend e 13 web, fingerprint `d8d9178df2dcc97acd40d5bf4300a9db75f8ba4b641c24f1ffd61e24cabf819d`; HEADs, protegidos, ledgers e `_tmp/` inalterados.

[Reviewer rodada 3](v060-reviewer.md): **apto para QA**, 0 P1, 0 P2, 1 P3 novo. Resíduos do r2 resolvidos; mutações detectadas; OpenAPI idêntico. Sem brecha de custo explorável pelo visitante. **P3-R3-01** (devolução do limite demo falha aberta quando o trace não é gravado após falha interna) fica pendente, não bloqueante: entra na próxima rodada do Developer se o QA devolver defeitos; caso contrário, risco conhecido.

## Despacho do QA

Ledgers reconciliados antes da rodada: primário 885/US$0,34852844, zero reservas, `.limit` = 1; acumulado US$0,59837466. Novo QA **Claude Opus 5.5, esforço high**, contexto novo, no r3: campanha `v060-qa` (US$0,50, montada uma vez, combinada com o primário), runtime real isolado novo em `.pytest_cache/v060-qa-real-runtime`, navegador embutido para a UI, Docker somente se o daemon já estiver ativo (estava parado na verificação do Supervisor), sem exposição fora de loopback; teste de outra rede pendente com o responsável. Relatório único em `docs/evidence/v060-qa.md`.

Responsável iniciou o Docker Desktop (daemon 29.8.0). A stack antiga (`ai-getnet-case-api-1`, imagem `sha256:375b4a0f…` de 2026-10-27 01:48, era v0.2) voltou sozinha por `restart: unless-stopped`, publicada em `0.0.0.0:8000`; log sem chamada paga (índice atual, sem rebuild; só `/health`). Ledger do volume `ai-getnet-case_runtime`, lido em modo somente leitura: 46 entradas, US$0,02523039, zero reservas, último registro 2026-10-27T01:50:12Z (já incluído no histórico da v0.2); sem `.limit`. Informado ao QA como linha de base; compose do candidato recria a API em loopback; nada removido.

Responsável pediu limpar no Docker, depois dos testes, tudo o que puder ser limpo. Plano do Supervisor ao fim do QA: inventário com tamanhos; remover contêineres parados, imagens antigas e soltas e cache de build; preservar os volumes `ai-getnet-case_runtime` (ledger) e de Qdrant (coleções), salvo confirmação específica; apresentar a lista antes de apagar. Compactar `docker_data.vhdx` fica com o responsável.

## Fechamento sem o responsável presente

Em 2026-10-28 o responsável pediu para finalizar o projeto durante a noite e preparar um resumo de estudo para a gravação do vídeo. Supervisor conduz: QA até o fim, correções pelo mesmo fluxo, limpeza Docker preservando volumes de ledger e coleções e, com QA apto, integração da v0.6.0 por merge local com a identidade do projeto. Acesso externo permanece pendente com o responsável.

Conferência só de presença no `.env` (sem ler valores): chaves OpenAI, DeepSeek e TypeSafe presentes; `API_DEMO_ACCESS_KEY` e `API_ADMIN_ACCESS_KEY` **vazias**, então o login `/v1` da stack Docker não funciona até o responsável defini-las. Credenciais não foram criadas pelo Supervisor; o passo está no resumo de estudo entregue ao responsável.

## QA r1 (candidato r3): reprovado no item 3

[QA r1](v060-qa.md): hashes conferidos antes e depois; nove itens aptos (alguns com ressalva) e item 3 reprovado por **P1-QA-01**: com o toggle em JEV, `POST /v1/messages` executa o Router pelo LLM padrão e registra JEV. Supervisor confirmou no código: `api/v1.py:884` exclui `router` de `agent_models` quando o mecanismo é JEV, e `graph.py:225-227` só aplica `router_llm` aos nomes desse dicionário. Defeito já presente na v0.5 (o QA da v0.5 validou JEV só pela comparação de Routers, que usa outro caminho). P3: `R$` virando fórmula no Streamlit, estado do caso desatualizado após recuperação; observações menores de interface e documentação.

Destaques aptos: bloco D comprovado com modelo real (V1 sem `get_contract_snapshot`; V2 `kb_29225785334648e3` com o trecho novo como primeiro resultado e a ferramenta; V1 restaurada sem ela); comparação de 3 perfis × 2 cenários com reuso e drill-down; avaliação sob demanda com reuso sem custo; recuperação com uma POST e um GET; demo `403`/`429`; Docker empacotado com API só em loopback, schema 8 e smoke real. Regressão real: núcleo e desafio 27/27, conversas 4/4, jornadas de negócio 7/13 (quatro casos de preço só na rubrica literal; `EN-PRICE-CONDITIONS` em `clarify`, caminho do Router inalterado na v0.6) — registrados como limitação.

Custos reconciliados pelo Supervisor: campanha nativa 316 entradas/US$0,08176871; Docker delta US$0,00102027 (volume 46 → 55); primário 885 → 1201/US$0,43029715 (mesmo gasto, sem dupla soma); zero reservas. **Campanha US$0,08278898 de US$0,50; acumulado do projeto US$0,68116364.** Stack Docker parada sem `-v`. Acesso externo e login `/v1` no Docker (chaves vazias no `.env`) pendentes com o responsável.

[Tarefa 61](../tasks/61-correcoes-qa-v060-r1.md) devolvida ao mesmo Developer: P1-QA-01, P3-QA-02/03, P3-R3-01 e observações pequenas. Depois: revisão do delta, QA focal no mesmo cap.

Inventário Docker para a limpeza final (somente leitura): 21 imagens (2,94 GB), 12 contêineres parados, 3 volumes (748 MB), cache de build 3,11 GB.

## Rodada 4 e candidato r4

[Developer rodada 4](v060-developer.md): P1-QA-01 corrigido (o orquestrador substitui a entrada `router` pelo adaptador JEV no envio direto e na comparação de perfis; comparação de Routers intocada), P3-QA-02/03, P3-R3-01 (devolução decidida pelas linhas `reserved`/`settled` do ledger para o `request_id`; ledger ilegível nunca devolve) e observações pequenas; único contrato novo é o campo aditivo `knowledge_base` em `/ready`. Estrita backend 347 e web 40, código 0, sem chamada paga. [Candidato r4](v060-candidato-r4.json): 63 backend e 13 web, fingerprint `b5748d7e48ca5153c8b124d4da9206198d68881d12bcb1a3832d4adeb1e6f307`; o ambiente do QA passa a ser mutável fora do mapa. HEADs, protegidos, ledgers e `_tmp/` inalterados. Mesmo Reviewer reativado para o delta.

[Reviewer rodada 4](v060-reviewer.md): **apto para QA**, 0 P1, 0 P2, 2 P3. JEV real nos dois caminhos comprovado com transporte falso; mutações J1 e J2 (reintroduzir o defeito) detectadas; comparação de Routers, legado e MCP intocados; OpenAPI idêntico (`/ready` sem esquema declarado). O Reviewer relatou "35 testes" no web; o Supervisor reexecutou e obteve **40 passed**, igual ao Developer. P3-R4-01 (`$` ainda vira fórmula na pergunta pendente e no comentário do avaliador) e P3-R4-02 (testes de falha aberta nas células) devolvidos ao mesmo Developer como rodada 5 da tarefa 61.

[Developer rodada 5](v060-developer.md): `$` literal em todo texto livre exibido como Markdown (pergunta pendente, comentário do avaliador, erros, cenário, fontes, falhas de comparação) e dois testes de falha aberta nas células; `comparisons.py` intocado. Estrita backend 349 e web 42, código 0. [Candidato r5](v060-candidato-r5.json): 63 backend e 13 web, fingerprint `3b6b697e53623ac08c54a521cc0aa094e2e5cc7e247b83a4c11e3ca9075a2639`. Mesmo Reviewer para o delta.

[Reviewer rodada 5](v060-reviewer.md): **apto para QA**, sem achados novos; hashes r5 conferidos; estrita backend 349 e web 42; `v1.py` e `comparisons.py` iguais ao r4; o Reviewer corrigiu o registro da contagem web da rodada 4 (40, não 35). Mesmo QA reativado para rodada focal no r5: JEV real pela UI e ledger, P3 e observações, rebuild Docker do r5 com smoke mínimo, reuso justificado do restante.

## QA r2 e fechamento

[QA rodada 2](v060-qa.md) no r5: **apto** nos dez itens; JEV real confirmado por `router · jev-1.14.0` no ledger e nenhuma linha de Router LLM; P3 do r1 corrigidos na interface; Docker r5 com smoke real; acesso de outra rede pendente com o responsável. Supervisor reconciliou em leitura: campanha 344/US$0,08627102, volume Docker 60/US$0,02696424 (delta v0.6 US$0,00173385), primário 1229/US$0,43479946; zero reservas. **Custo v0.6.0 US$0,08800487; acumulado US$0,68637953.**

Limpeza Docker executada conforme o pedido do responsável (detalhes no [resultado](v060-resultado.md#limpeza-do-docker)): contêineres e imagens de rodadas anteriores, imagens soltas, cache de build e rede sem uso removidos; volumes de ledger e coleções preservados.

Documentação de fechamento: README, CHANGELOG e README web no estado validado; critérios com evidência marcados (CA-21–24, CA-32, CA-34–37, CA-44–50); CA-25 (gravação), CA-33 (sem exercício ao vivo), CA-43 e CA-51 (outra rede) seguem abertos com nota; tarefas 54–61 concluídas; [resultado central](v060-resultado.md).

## Integração da v0.6.0

Commits com a identidade do projeto: backend `cdc1fdc` (produto e SDD) e `4bc0e8d` (evidências); web `ab01b58`. Varredura do diff sem segredos (só placeholders sintéticos de teste), sem arquivos grandes e sem `discovery/`, `data/runtime/`, `.env` ou `_tmp/`. Blobs conferidos contra o r5: todo o código igual; diferenças só nos documentos de fechamento editados depois do QA (o contrato `api-v040.md` difere apenas por normalização de fim de linha). Branches publicadas e PRs abertos: [backend #7](https://github.com/lauroPereira/ai-getnet-case/pull/7) e [web #3](https://github.com/lauroPereira/ai-getnet-case-web/pull/3), limpos e sem checks configurados.

O merge local na `main` foi **bloqueado pelo modo automático da ferramenta** (“Merge Without Review”) e não foi contornado; nada foi executado (mains em `c3a9027`/`4192169`). Merge e tag `v0.6.0` aguardam confirmação explícita do responsável, por merge local com a identidade do projeto (o merge pela interface do GitHub usa o e-mail principal da conta, como no incidente da v0.5.0).

## Próximo responsável

Responsável confirma o merge e a tag da v0.6.0, preenche `API_DEMO_ACCESS_KEY`/`API_ADMIN_ACCESS_KEY`, grava o vídeo e, se quiser, testa o acesso de outra rede.
