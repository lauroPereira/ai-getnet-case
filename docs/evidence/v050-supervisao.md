# Supervisão v0.5.0 — preparação

## Base e autorização

Responsável autorizou integrar v0.4, iniciar a próxima versão e permitir ao QA
usar chamadas pagas a partir dela. Backend PR5/main
`ea2355b5ba8fa8dcff66200f34461ae063183250`; web PR1/main
`40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`, ambos privados e com refs conferidos.
Branches `codex/v0.5.0-base-versionada` criadas após pull das duas mains.

## Preparação concreta

[Spec](../specs/base-versionada-v050.md), [plano](../specs/base-versionada-v050-plano.md),
[contrato proposto](../specs/api-kb-v050-proposta.md), história v1, ADR0014 e
tarefas39–44 criados. Não há produto implementado, migração aplicada, agente
novo acionado, chamada paga, novo commit ou push v0.5 nessa preparação.

QA pago não implica converter pytest em despesa automática. Aceite real usa
provedores com cenário sintético, guarda persistente e custo registrado;
unitários/contratos continuam cobrindo os caminhos de falha sem custo.
Estimativa/cap operacional serão fixados antes da rodada, sem renovar saldo
entre tentativas nem aumentar teto global US$5.

## Pré-checagens

Presença das chaves OpenAI/DeepSeek/TypeSafe confirmada sem exibir valores.
Ledger nativo lido em modo somente leitura:850 entradas, comprometido
US$0,34298961; limite configurado US$1. Acumulado entre rodadas já registrado
US$0,59283583, incluindo outros runtimes. QA deve reconciliar os totais e
compartilhar a guarda existente com sublimite, sem copiar/zerar o histórico.
Não foi feito teste autenticado de provedor na preparação.

Disco próximo de250MiB livres: sem instalar/duplicar ambientes ou limpar dados;
monitorar antes de gravar testes/builds. O plano proíbe remoção automática e
registra retorno de versão sem apagar coleções.

## Próximo responsável

O responsável aprovou especificamente APIs/migração0007, fluxo e delegação de
três novos agentes sequenciais gpt-6-luna/high em 2026-10-27, respondendo
“Aprovar a implementação descrita”. Supervisor aciona Developer, depois
Reviewer em contexto novo e QA no candidato fixado. A autorização monetária
já concedida não será pedida outra vez no mesmo escopo.

Na retomada após aprovação, C: apresentou6.924.492.800 bytes livres. A restrição
de250MiB registrada no planejamento é histórica; a melhora não foi atribuída
a limpeza do agente. Nenhum arquivo/coleção foi removido nesta retomada.

## Despacho Developer

Novo `/root/developer_v050` acionado explicitamente como `gpt-6-luna/high`,
`fork_turns=none`, após o aceite. Escopo tarefas39–44 e ambos os projetos;
somente o Developer altera produto nesta etapa. Não executa chamadas pagas:
essa autorização é do QA posterior ao Reviewer e ao candidato fixado.
Reviewer e QA novos ainda não acionados; nenhuma delegação adicional.

O despacho preserva branch já derivada da main atualizada, contratos legados,
políticas/arquivos protegidos e dados/coleções/ledgers existentes. Inclui
reserva prévia e liquidação única de embeddings e preparação do runtime
isolado com guarda persistente injetada, sem executá-lo com provedores agora.

## Preparação de candidato/ambiente pelo Supervisor

Helper temporário `.pytest_cache/v050-freeze-candidate.py` preparado e validado
por Ruff check/format, mas **não executado durante a implementação**. Identifica
os dois repositórios, bases e branch v0.5, fontes por bytes locais, contrato/
história e cap QA. Antes do congelamento, conferir diretórios novos de runtime
e COPYs do Dockerfile final para cobrir todos os insumos. Referências estáticas
de catálogo são fixadas; relatórios mutáveis e ambientes temporários excluídos.

As bases já versionadas usam blobs canônicos Git, registrados no
[baseline](v050-baseline-supervisor.json). Os antigos hashes locais r6 da
v0.4 são históricos anteriores à normalização de finais de linha; não são
critério de comparação literal após checkout. O novo candidato v0.5 será
fixado somente após a passagem do Developer.

Nenhum ambiente real foi iniciado e nenhum controle de gasto foi zerado.
Reviewer/QA ainda serão criados em sequência. Custo conhecido, guarda e limite
adicional persistente serão conferidos pelo QA antes da primeira chamada real.

## Checkpoint parcial do Developer

Developer informou backend conectado: registro/drafts/hash, estimativa,
coleção UUID candidata, estados/teste, CAS/eventos de ativação/retorno e
índice/versão capturados por run. Embeddings reservam antes e liquidam uma
vez; uso desconhecido conserva a reserva. Nove testes focados sintéticos e
Ruff src/tests passaram. A rodada completa inicial apontou expectativa de
schema antigo e diff vazio, corrigidos; validação estrita final, interface,
OpenAPI e passagem ainda pendentes. É checkpoint, não parecer ou candidato.

Checkpoint seguinte: estrita backend219 e web15, Ruff/estrutura passaram;
trace/índice antigo após ativação e conflito CAS exercitados. OpenAPI exportado
de montagem offline sem chaves, HashEmbedder/Qdrant em memória. Nenhum novo
diretório persistente de dados requerido; índices usam runtime/qdrant e
registro usa merchant.sqlite3 do runtime. Fechamento/harness real ainda será
checado na passagem. Supervisor solicitou guarda existente injetada antes de
bootstrap e cobertura de todas as tentativas, sem retry SDK opaco fora da reserva.

Developer informou clientes OpenAI/aplicação/CLI e DeepSeek com retry interno0,
JEV HTTP sem loop; preparou `FixedBudgetGuard` (cap/ID fixados uma vez, máximo
US$0,25) e `CombinedBudgetGuard` (campanha e guarda primária, cancelando reserva
pré-rede da campanha se o primário negar). `build_orchestrator` aceita guarda
injetada com runtime separado. Não instanciou o controle real nem abriu ledger
do responsável. Nova estrita final em execução após esse ajuste; revisão
independente ainda será necessária, sem aceitar o checkpoint como parecer.

## Passagem e candidato r1

[Developer r1](v050-developer-r1.md) encerrou implementação e validação:
backend221/web15, Ruff/estrutura/skills, OpenAPI0.5 com22 operações. Não iniciou
provedor/controle real nem tocou ledger nativo; descreveu a injeção de guarda
composta antes do bootstrap, com runtime independente e cap persistente.

[Candidato r1](v050-candidato-r1.json) fixado:32 backend e84 web, fonte
`0f9a4af3a7026877c7d1764a08f31b585cbe1e00cb6afd123fcdd6eeaaf22f7b`,
runtime `2168ca8bfcc638034bc9c7c68865878f83fbc8ef36fa89eadee5a47fb16005d5`.
Novo `/root/reviewer_v050` acionado explicitamente `gpt-6-luna/high`,
`fork_turns=none`, com critérios/fontes/manifesto, sem relatório/conclusão do
Developer. Fonte congelada, só evidências mutáveis fora do fingerprint.

Supervisor iniciou build do Dockerfile canônico r1, com source congelada e
dependências autorizadas; ainda não é declarado concluído nesta anotação.
Não iniciou aplicação real ou inferência paga. Novo QA aguarda revisão apta.

## Resultado técnico r1 e correções

Build canônico concluído: imagem
`sha256:d2a2e75273821c7d97d6d72870d82e83f14f198c9a26f5bdab197183b7c40378`,
125 arquivos instalados conferidos contra o manifesto, sem divergência.
Ambiente HTTP/UI sintético respondeu com versão0.5/schema7, sem provedor
real. Container e processos web identificados foram parados; imagem, logs e
evidências preservados. [Registro Docker](v050-docker-r1.json) e
[ambiente desativado](v050-qa-environment-r1.json).

[Reviewer r1](v050-reviewer-r1.md) concluiu **correções necessárias**, com
seis achados sobre CLI/guarda, imutabilidade e integridade de coleções,
liquidação única, estados publicados e teto absoluto. Uma errata factual
esclareceu que o candidato web é o working tree local sobre HEAD v0.4;
os hashes conferidos não foram confundidos com o commit-base.

[Tarefa45](../tasks/45-correcao-revisao-v050-r1.md) retorna ao mesmo Developer.
Manifesto r1 permanece histórico; helper exclui temporários `_tmp` criados
pela revisão e inclui a tarefa45 para o próximo congelamento. Nenhum desses
temporários foi apagado ou movido. Não há QA novo acionado, chamada paga,
controle real de campanha inicializado ou integração v0.5.

## Retomada com nova delegação (2026-10-27)

Responsável pediu retomar a v0.5.0 a partir do parecer r1 e autorizou
explicitamente subagentes **Claude Sonnet 5.5** para Developer, Reviewer e QA,
em substituição aos agentes `gpt-6-luna/high` anteriores, para conter consumo
da ferramenta. Supervisor permanece na sessão principal (Claude Opus 5.5).
Escopo inalterado: tarefa45, sem ampliar API, permissões, orçamento ou cap QA.
Estado reconciliado: backend e web em `codex/v0.5.0-base-versionada`, HEAD
igual às bases fixadas (`ea2355b…`, `40ff199…`), `main` local igual a
`origin/main` sem fetch; delta v0.5 apenas no working tree. C: com ~5,5GiB
livres. Nenhum arquivo, coleção, ledger ou `_tmp` removido.

## Developer r2 e candidato r2

Novo Developer Claude Sonnet 5.5 (contexto novo) executou a tarefa45 e entregou
[passagem r2](v050-developer-r2.md): R1-01–R1-06 relatados como corrigidos,
estrita backend relatada com 293 testes, web inalterado. Supervisor conferiu
o estado local: `data/runtime/` intocado (sem sidecar `.limit`), `_tmp/` sem
novos itens, web sem diferença em relação ao r1. O Developer encontrou
`budget.py` já alterado após o congelamento r1 (mtime 13:42, provável início da
tarefa45 pelo agente anterior) e o tratou como ponto de partida auditado.

Duas consequências de projeto aceitas pelo Supervisor por seguirem a correção
esperada no parecer r1, sujeitas à revisão: (1) teto persistente em sidecar
`<ledger>.limit`, criado no primeiro uso, sem alterar o SQLite; ledger
pré-existente fica em US$1; configuração maior que o teto fixado é recusada;
(2) `bootstrap` não reconstrói coleção existente defasada: mantém e avisa;
conteúdo novo exige versão pela API administrativa.

[Candidato r2](v050-candidato-r2.json): 38 backend e 84 web, fonte
`22b0c92dd79ac9db710ecb69e95eb69101b0c332951a2653b21ffcc5e92786b0`, runtime
`22556665c215a837fa5d9cc1b7b8dacd52fa3b06b40ed46e8e1b86b9ef40ce0e`, build
`c74764b0d0932851a123ff8f5f13b11e96e266f8530b2a4ae5ee2e1016d1c3a5`. A mudança
do plano desde r1 é só a nota de estado do Supervisor anterior (13:40).
Novo Reviewer Claude Sonnet 5.5 acionado em contexto novo, com critérios,
fontes e manifesto, sem passagens do Developer.

## Parecer r2, decisão R2-06 e candidato r3 para QA

[Reviewer r2](v050-reviewer-r2.md) (Claude Sonnet 5.5, contexto novo):
**apto para QA** no candidato r2, sem P1/P2; R1-01–R1-06 corrigidos com
evidência própria; estrita backend 293 passed, web 15 passed; hashes
conferidos antes/depois. Exposição incidental a linhas das passagens do
Developer via busca textual foi declarada pelo Reviewer e não usada como
evidência; Supervisor considera a independência preservada.

R2-06 apresentado ao responsável, que **aceitou** em 2026-10-27 a criação de
`data/runtime/budget.sqlite3.limit` = 1.00 quando o QA montar o ledger real,
pedindo que a especificação registrasse isso e que o QA **não** fosse iniciado
agora (será chamado depois). Registrado em spec, plano (decisão 8, QA e
delegação) e ADR0014. P3 R2-01–05/07/08 abertos na tarefa46, após o QA.
Tarefa45 concluída.

[Candidato r3](v050-candidato-r3.json): delta só documental sobre r2 (spec,
plano, ADR0014, tarefas45/46). Fonte
`4fca76056153e40aa2213d03737b2af5f5c351324e8b13ec621e4f6d186b9687`; runtime
`22556665…ce0e` e build `c74764b0…c3a5` idênticos ao r2, então o parecer r2
vale para o código do r3. Este é o candidato para o QA.

Pronto para o QA (Claude Sonnet 5.5), quando o responsável acionar: conferir
hashes do r3; montar o ledger real uma vez com `BUDGET_LIMIT_USD=1.00` e
inspecionar o `.limit`; `CombinedBudgetGuard(primário real, campanha fixa
US$0,25)` com o mesmo caminho de campanha em todas as tentativas; roteiro em
[preparação QA](v050-qa-preparacao.md) e tarefa44. Imagem Docker r1 não
corresponde ao r2/r3; rebuild ou execução local fica a cargo do QA, com
~5,5GiB livres. O container `ai-getnet-case-api-1` usa volume Docker próprio,
não `data/runtime/`. Nenhuma chamada paga, commit, push ou remoção nesta etapa.

## Disco antes do QA (levantamento parcial, 2026-10-27)

C: com 2,9GiB livres (5,5GiB no início desta retomada; ~0,3GiB vem de novos
basetemps de teste, o resto não foi isolado). Medição interrompida a pedido do
responsável; nada foi apagado. Oportunidades, da maior para a menor:

| Item | Tamanho | Ganho provável | Risco/observação |
| --- | ---: | ---: | --- |
| Disco virtual Docker `docker_data.vhdx` | 12,9GiB | até ~5GiB após compactar | Uso interno ~7,5GiB; o arquivo não encolhe sozinho. Compactar com Docker parado |
| Cache de build Docker | 4,3GiB | ~2,2GiB (`docker builder prune`) | Só cache; próximos builds ficam mais lentos |
| `~/.cache` | 4,5GiB | a verificar | Conteúdo não inspecionado |
| `~/.codex` | 2,1GiB | a verificar | Sessões/logs dos agentes anteriores |
| `.pytest_cache` do backend | 1,2GiB | ~1GiB | Basetemps v030/v040/v050-dev-r1..r8; manter `v050-freeze-candidate.py`, logs e `.iid` citados em evidências |
| `~/.vscode` | 1,4GiB | baixo | Extensões |
| `AppData/Local/Temp` | 1,2GiB | parcial | Inclui o scratchpad desta sessão |
| Imagens/containers Docker v030/v040 parados | ~0,4GiB reais | ~0,4GiB | Citados em evidências históricas; remoção exige decisão |
| `.venv`/`.venv-v040` | 0,25/0,39GiB | nenhum | Necessários aos testes |
| Cache pip | 0,35GiB | 0,35GiB | Seguro |

Não medidos: `hiberfil.sys`/`pagefile.sys`, Windows Update e demais pastas.
Qualquer remoção exige confirmação explícita do responsável.

Com aprovação explícita do responsável, `docker builder prune -f` liberou
2,167GB de cache de build dentro do disco do Docker (cache restante 2,136GB,
em uso por builds anteriores). Imagens, containers e volumes não foram tocados.
O ganho só chega ao C: após compactar `docker_data.vhdx` (não executado).

Com aprovação explícita do responsável, foram apagadas 65 pastas de basetemp
pytest antigas em `.pytest_cache` (27 v030, 30 v040, `v050-dev-r1..r8`), sem
falhas, liberando ~805MB no C:. Preservados: scripts, logs, `.iid`, JSON e as
35 pastas não-basetemp (runtimes com `budget.sqlite3`, wheels, temporários web,
`v030-qa-r6-mcp`), além dos basetemps v050 da tarefa45/revisão r2. Citações de
basetemps nas evidências históricas passam a ser só registro textual.

## Retomada somente QA na sessão Codex

Responsável informou que Developer e Reviewer já terminaram e pediu retomar
somente QA. Supervisor reconciliou os relatórios e não repetiu essas etapas.
Conferência própria do r3:39 arquivos backend,84 web,128 runtime e129 build,
sem divergências. Runtime/build iguais ao r2, preservando o parecer apto.

O plano passou a registrar Sonnet5.5; esse modelo não está disponível nesta
sessão. Perguntado pela RNF-12, o responsável respondeu explicitamente
**“Usar gpt-6-luna/high nesta sessão”** para somente QA. Novo
`/root/qa_v050` acionado com `model=gpt-6-luna`, `reasoning_effort=high`,
`fork_turns=none`. Nenhum novo Developer ou Reviewer foi acionado nesta
retomada. O agente Developer antigo estava encerrado por limite de uso;
não fez novas alterações após a retomada.

QA recebe candidato r3, história v1, critérios e pendências P3, com cap
persistente adicional US$0,25 e primário nativo US$1 sem reset. Caminho fixo
de campanha: `.pytest_cache/v050-qa-control/budget.sqlite3`, ID `v050-qa`.
Domínio de teste separado sob `.pytest_cache/v050-qa-real-runtime`.
Supervisor não montou esse controle nem realizou chamada paga. Disco antes
do despacho:3.668.484.096 bytes livres. Build canônico r3 será preparado
sem usar a imagem r1 para alegar aceite do novo código.

Build canônico r3 concluído com código0, imagem
`sha256:852e5c4ec8448fc686bed994e9feb00c246d1a6483e1a1f8147e0a8cdf6ece2b`.
Inspeção em contêiner novo sem rede/rootfs somente leitura conferiu125
arquivos instalados, sem divergência. Contêiner de inspeção parado e
preservado. [Evidência Docker r3](v050-docker-r3.json). QA escolheu ambiente
nativo Python3.13.3/SDK OpenAI3.39.0; a imagem tem3.13.13/3.40.0. Não se
confunde inspeção de instalação com aceite real de provedores nessa imagem.

Checkpoint QA: ledger nativo permanece850 entradas/US$0,34298961 antes das
chamadas. Montou primário uma vez aUS$1 e conferiu `.limit=1`; campanha fixa
US$0,25 montada no caminho declarado. O primeiro smoke de embedding real
retornou `APIConnectionError`; conservou reserva deUS$0,00000056 e parou
expansão para diagnóstico. Nenhuma redefinição de saldo ou retry SDK.

## QA real r1 e retorno autorizado para correção

[QA r1](v050-qa-r1.md) encerrou o candidato r3 como **reprovado CA-41 UI**.
Embedding real, baseline40documentos/145trechos, build/teste/ativação pelo backend,
proteções403/409/429 e comparação real DeepSeek/JEV tiveram evidência.
No navegador, marcar confirmação não habilitou build/teste; chat terminou
no backend, mas mostrou ReadTimeout na interface. Causa temporal ainda
indeterminada, diagnosticada pela tarefa48 sem prescrever aumento de timeout.
[Ambiente real](v050-qa-real-environment-r1.json) tem nome distinto do
registro sintético antigo, que permanece preservado.

Campanha17entradas/US$0,00282289, sem reservas abertas; primário850→867
entradas eUS$0,34298961→0,34581250. Delta é o mesmo gasto da campanha, sem
dupla soma; acumulado histórico reconciliadoUS$0,59565872. Primeira falha de
DNS foi isolada à execução sem elevação, e sua reserva foi conservada.
Tentativa explícita elevada funcionou, sem desabilitar TLS/retry de SDK.

QA parou somente Streamlit18553 (PID29556 e pai26808), preservando API6932/
18853, fixtures26544/18854, domínio e guardas. Fonte r3 permaneceu íntegra.
Tarefas47/48 registradas pelo QA. Responsável aprovou
“Autorizar correção e revisão com gpt-6-luna/high”, após a
[proposta concreta](v050-correcao-qa-proposta.md).

Mesmo `/root/developer_v050` reativado explicitamente gpt-6-luna/high para
[tarefa49](../tasks/49-correcao-confirmacoes-qa-v050.md), somente controles
web e diagnóstico sem custo da tarefa48. Antes da correção, Supervisor
reconferiu os128 arquivos backend runtime: iguais ao r3, inclusive budget.py.
Nenhuma reversão/patch da antiga tarefa45 deve ser reaplicada. Novo candidato
e revisão focada seguirão a passagem; QA é reutilizado depois, com o mesmo
cap e todos os gastos preservados. Nenhum novo subagente adicional.

## Correção de controles r4 e recuperação autorizada

[Passagem UI r1](v050-developer-ui-r1.md) relata quatro confirmações com
rerun normal, tetos persistentes e testes web16/Ruff externo aprovados;
script estrito retornou2 por Ruff ausente no venv web. Não se confunde essa
limitação de ambiente com aprovação integral do comando. Reviewer ainda
revalidará o código fixado. Backend permanece igual ao r3.

[R4](v050-candidato-r4.json) foi fixado como incremento de confirmações,
fonte `ddabeba4620776c37a93460c983c702c7522e10c234cd5230744e83e7ac08432`.
Não foi encaminhado ao QA/revisão antes da nova autorização, recebida logo
depois: **“Aprovar recuperação manual da conversa”**, conforme
[proposta](v050-recuperacao-chat-proposta.md). Mesmo Developer voltou à
[tarefa50](../tasks/50-recuperacao-manual-chat-v050.md), sem tocar timeout,
API ou orçamento. Reviewer avaliará o conjunto controles/recuperação em r5,
sem repetir a revisão backend já válida. QA reutilizará o controle de17
entradas e US$0,00282289, sem inicializar outro cap.

## Candidato r5 e revisão final da interface

[Passagem UI r2](v050-developer-ui-r2.md): Developer encerrou alterações de
produto e documentação, com20 testes web/Ruff externo; limitação do script
estrito continua explicitada (código2 por Ruff ausente no venv web).
Não houve chamada paga nessa implementação.

[R5](v050-candidato-r5.json) fixado com43 arquivos backend e84 web; fonte
`71818710468cd1ad63a83c49e8eec61e5db28bf5d824381b0e0e3d509e40d76c`.
Runtime/build são idênticos aos do r3: reutilização da imagem canônica
comprovada em [Docker r5](v050-docker-r5.json), sem rebuild repetido. Delta
web desde r3: `app.py`, `src/getnet_web/api.py`, `tests/test_interface.py`.
Backend desde r3 só tem documentação de escopo/estado aprovada.

Mesmo `/root/reviewer_v050` reativado explicitamente gpt-6-luna/high para
revisão independente do conjunto no r5, com critérios/fontes e QA47/48,
sem passagens ou conclusões do Developer. Não repete a revisão backend
inalterada. Escrita de produto congelada até parecer.

Auditoria somente leitura após implementação: primário867 entradas,
US$0,34581250; campanha17 entradas, US$0,00282289; zero reservas abertas.
Não houve reset, novo cap ou dupla soma de despesas.

## Revisão r5 e correção focal r6

[Reviewer UI r1](v050-reviewer-ui-r1.md) re-derivou mapas e20 testes no r5,
apontando WUI-R1-01 P2: mudar teto após consentimento mantinha a confirmação.
Recuperação manual e demais caminhos não tiveram novos achados. A
[tarefa51](../tasks/51-reconfirmar-teto-kb-v050.md) voltou ao mesmo Developer
no escopo já autorizado; não foi liberado QA sobre r5.

[Developer UI r3](v050-developer-ui-r3.md) entregou correção de aumento e
redução do teto, preservando número digitado e exigindo reconfirmação;20
testes/Ruff externo relatados, sem chamada paga. [R6](v050-candidato-r6.json)
fixado com44backend/84web, fonte
`45073733de04247748d583f5a57af01bfa3180979d8915616bd7db0af971aaa3`.
Runtime/build continuam idênticos ao r3; [Docker r6](v050-docker-r6.json)
reutiliza a imagem comprovada, sem rebuild. Mesmo Reviewer gpt-6-luna/high
acionado para delta focal r5→r6, sem relatório/conclusão do implementador.
QA aguarda parecer apto; fonte congelada e campanha anterior preservada.

## QA r2: jornada de versões aprovada, recuperação reprovada

[QA r2](v050-qa-r2.md) comprovou build/teste/ativação/retorno na UI, teto
reconfirmado e captura de versão durante troca concorrente. A execução
iniciada em `kb_d5cab05206e446f2` terminou nessa versão apesar do rollback
UI para `kb_11d9ae5b041443aa`; a conversa posterior capturou a anterior.

Recuperação falhou: GET200 trouxe resposta persistida e a UI continuou
pendente. [Tarefa52](../tasks/52-recuperar-conversa-get-ui-v050.md) guarda
evidência de payload real com `role=merchant/assistant` e campo `text`,
para confronto com o consumidor web. Payload sanitizado SHA256
`c43c8e2d273570be2587c05c82adb2333284da92448913ab8580c85572168b7f`.
Não foi feito POST adicional para esse diagnóstico. Resposta ao código91
sem menção à nota fictícia ficou inconclusiva, sem defeito presumido: fonte
oficial não sustenta um prazo fictício como regra real.

Campanha33linhas/US$0,00532161, primário883/US$0,34831122, zero abertas;
delta r2US$0,00249872 e acumulado históricoUS$0,59815744. UI/proxy próprios
parados; API/fixtures, dados e guardas preservados. Fonte r6 permaneceu íntegra.
Mesmo Developer gpt-6-luna/high voltou à tarefa53 no escopo de recuperação
já aprovado, com fixture real e nenhuma alteração de backend/contrato/modelo.

## Correção do contrato GET e candidato r7

[Developer UI r4](v050-developer-ui-r4.md) confrontou o payload real e
ajustou o consumidor para o papel `merchant` da pergunta. Fixture versionada
preserva formato real/sintético; recuperação, cursor, histórico e GET seguro
foram testados sem serviço real.20 testes web/Ruff externo relatados; script
estrito2 por Ruff ausente no venv, como nas rodadas anteriores.

[R7](v050-candidato-r7.json) fixado:46backend/85web, fonte
`ad9cf469cd85e44210280df1949ecac766857688a6f1101bb61f8d0e9e9b8d8c`.
Backend runtime/build ainda iguais ao r3; [Docker r7](v050-docker-r7.json)
reutiliza a imagem canônica sem rebuild. Mesmo Reviewer gpt-6-luna/high
acionado para delta r6→r7 e confronto independente com contrato/payload
real, sem relatório/conclusões do Developer. Nova rodada do mesmo QA aguarda parecer.

Disco foi observado com1.022.971.904 bytes livres durante a implementação,
sem atribuição da queda a uma causa. Nenhuma instalação/build extra ou
limpeza foi executada; limiar operacional de80MiB continua vigente.

[Reviewer UI r3](v050-reviewer-ui-r3.md) aprovou o r7 para revalidação,
conferindo46/85arquivos e o payload capturado contra fixture/rota, além de
testes de recuperação/cursor/POST único e Ruff. Mesmo QA gpt-6-luna/high
reativado para r3, focal na recuperação e lacunas funcionais restantes;
resultados anteriores não afetados são reutilizados, sem novo cap/ledger.

## Encerramento QA e auditoria final

[QA r3](v050-qa-r3.md) comprovou recuperação pelo navegador com uma POST
real e GET manual200: resposta visível, pendência limpa, sem segundo envio.
A sonda opcional do texto fictício foi recusada pelo Router e não alcançou
Knowledge. Após comparar literalmente CA-41/RF63–66/spec/história, o QA
identificou que reproduzir marcador não era requisito obrigatório e emitiu
**apto nos critérios publicados**, mantendo a sonda inconclusiva. Não houve
mudança de critérios, apagamento de limitação ou nova inferência na auditoria.

QA encerrou API/fixtures próprios após verificar PID/comando/porta. Supervisor
conferiu ausência de listeners nas portas18853/18854/18855/18553 pela tabela
do Windows; probes TCP diretos tiveram timeout, sem serem tratados como
prova de serviço ativo. [Auditoria final](v050-auditoria-final-supervisor.json)
confirmou46/85/128/129arquivos sem divergência e guardas em leitura:
campanha35/US$0,00553883; primário885/US$0,34852844; zero reservas abertas;
cap0,25 e teto nativo1 mantidos. Acumulado do projetoUS$0,59837466 deUS$5.

[Resultado consolidado](v050-resultado.md): candidato local r7 apto, com
P3 da tarefa46 e limitação da sonda claramente registradas. Integração Git
v0.5 permanece fora do escopo aprovado; nenhuma ação externa desse tipo foi
executada. Todos os três papéis desta rodada foram reutilizados explicitamente
como gpt-6-luna/high, sem agente adicional ou promoção silenciosa de modelo.
