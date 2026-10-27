# Retomada SDD: jornadas da v0.3.0

## Estado reconciliado

- Base local inicial limpa: `main`, commit `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`, integração da v0.2.0 (PR #3). Tags locais `v0.1.0` e `v0.2.0` presentes.
- Remoto: `git@github.com:lauroPereira/ai-getnet-case.git`. Após autorização explícita nesta sessão, `git pull --ff-only` retornou `Already up to date`.
- Branch criada a partir dessa base: `codex/v0.3.0-jornadas`.
- Entrega escolhida: v0.3.0, conforme sequência aprovada; não iniciar interface ou versões posteriores.

## Fontes e preparação

Skill [Supervisor](../../skills/supervisor/SKILL.md), protocolo de papéis, especificações principal e complementar, decisões aceitas 0006 e 0011. Preparados [plano detalhado](../specs/jornadas-v030-plano.md), tarefas 21 a 24 e [história versão 1](../historias/jornadas-v030.md).

## Autorizações desta sessão

- Retomar o desenvolvimento com SDD.
- Exatamente três subagentes sequenciais: Developer, Reviewer e QA; todos `gpt-6-luna`, esforço `high`, informados expressamente nos parâmetros de criação, sem herança silenciosa.
- Rede somente para atualização de `main` com `git pull --ff-only` (executada).
- Implementação do plano da v0.3.0: rotas internas de pricing/cobrança, quatro ferramentas de consulta, ampliação aditiva do contexto contratual e migração reversível 0005. Preservar `POST /messages`; testar migrações em bancos sintéticos isolados e retorno para esquema 0004.

Sem autorização nesta sessão para chamadas pagas, rede externa adicional, commit, push, merge, tag ou publicação. O teto de US$5 da aplicação não é uma autorização de gasto para a ferramenta de desenvolvimento. Último gasto de APIs registrado antes desta entrega: US$0,4516, conforme [registro](orcamento.md).

Posteriormente o responsável autorizou iniciar Docker Desktop e usar rede para imagens/dependências do build de teste isolado, sem chamadas pagas. Essa autorização não inclui redefinição do Docker nem alteração de configurações do sistema.

O responsável também autorizou remover a pasta temporária acidental `workspaceai-getnet-case.codex-tmppytest-baseline`. Antes da remoção, o caminho absoluto foi validado dentro do workspace, sem redirecionamento, e conferido o escopo de três arquivos/180.224 bytes. Remoção com `Remove-Item -LiteralPath` e verificação `Test-Path=False`; nenhum runtime anterior foi afetado.

**Rodada real autorizada:** OpenAI, 40 casos e quatro conversas, incluindo embeddings e rubrica por modelo; estimativa US$0,08 e teto adicional US$0,15. Execução no contêiner candidato, com runtime e guarda persistente separados em `.pytest_cache/v030-real-runtime`; somente a credencial OpenAI necessária é passada em ambiente, sem valor em argumentos ou relatórios. Fontes públicas e dados sintéticos; nenhuma autorização de integração/publicação acrescentada.

## Despachos e evidências

| Papel | Subagente | Modelo / esforço explícitos | Contexto | Estado |
| --- | --- | --- | --- | --- |
| Developer | `/root/developer_v030` | `gpt-6-luna` / `high` | Novo (`fork_turns=none`), tarefa, fontes e limites | Implementação/correções concluídas; 191 testes |
| Reviewer | `/root/reviewer_v030` | `gpt-6-luna` / `high` | Novo (`fork_turns=none`), critérios e manifesto sem histórico do Developer | R6 apto; fechamento documental confirmado |
| QA | `/root/qa_v030` | `gpt-6-luna` / `high` | Novo (`fork_turns=none`), candidato e história fixados | Apto funcionalmente no r6; fechamento documental confirmado |

O Supervisor não implementa produto nem emite revisão técnica sobre a própria coordenação. Correções retornam ao mesmo Developer. O candidato será identificado por SHA da base e hashes de arquivos locais, já que não foi autorizado commit.

## Estado e próximo responsável

Implementação em andamento. Próximo: passagem do Developer, revisão independente, correções se necessárias, candidato e QA. Validação real e Docker devem ser distinguidos dos testes programados; não declarar a versão liberada por evidência somente simulada.

Atualização: Developer concluiu a implementação local, com passagem em [v030-developer.md](v030-developer.md). [Candidato r1](v030-candidato-r1.md) fixado com 42 hashes locais. Reviewer independente acionado; QA ainda não acionado. A rodada real foi posteriormente autorizada e iniciada, mantendo o código congelado.

## Dependências do ambiente

O comando `docker version --format '{{.Server.Version}}'` encontrou a CLI, mas falhou por ausência do pipe `dockerDesktopLinuxEngine`: daemon Docker Desktop desligado. A execução em contêiner ainda não foi validada nesta sessão; a falha de ambiente não é defeito do produto. Testes locais sem rede podem prosseguir.

Tentativas autorizadas de inicialização pelo executável e por `docker desktop start --timeout 45` não disponibilizaram o engine. Inspeção do aplicativo pela skill de controle do Windows confirmou o diálogo `An unexpected error occurred`: falha em `starting services: initializing Ingest server`, ao renomear `sailor-ingest.sock` para `sailor-ingest.sock.stale` na pasta local do Docker (`The file cannot be accessed by the system`). Nenhuma redefinição de fábrica, envio de diagnóstico, remoção de arquivo ou mudança de segurança foi realizada.

**Dependência resolvida:** nova abertura pelo aplicativo do Windows disponibilizou o engine; `docker version --format '{{.Server.Version}}'` confirmou **29.8.0**. Build do projeto isolado `getnet-v030-validation` concluído para `api` e `mocks`, sem chamadas pagas. O serviço `mocks` ficou saudável sem porta publicada.

O smoke exploratório [r1](v030-docker-r1.json) enviou os dez exemplos e sete jornadas usando modelo programado, API em processo no contêiner e HTTP real para outro contêiner: 14/17 verificações de status/ferramenta passaram. Falhas de pricing reproduziram `FileNotFoundError` porque o pacote instalado buscava fixtures sob `/venv/lib/python3.13/data` em vez do diretório de dados de runtime. O Developer recebeu a reprodução e corrigiu a resolução de diretório, com teste específico. A primeira imagem e seu smoke não identificam o candidato final; reconstrução e nova rodada são necessárias. A verificação seguinte também exigirá ausência de erros nas ferramentas, para distinguir divergência financeira de falha de serviço.

Após a correção, build r2 concluído e mocks saudável. [Smoke r2](v030-docker-r2.json): **17/17**, zero chamadas pagas, também exigindo ausência de erro nas ferramentas. Imagens e hashes no manifesto do candidato. O processo API do smoke usou modelo programado e índice lexical; esse resultado comprova instalação e comunicação HTTP, não qualidade do modelo real.

## Continuação: correções e candidato r3

- Primeira rodada real concluída: [40 casos](v030-real-r1.md), 31/40 automáticos e 4/4 conversas; custo total US$0,06747249. Cinco falsos negativos de redação e quatro casos com falhas reais deram origem à tarefa 25. O orçamento e o contexto exato da execução estão preservados.
- P2 de isolamento do Reviewer r1 corrigido pelo mesmo Developer. Tarefa 25 implementada em prompts Router 4/Support 7, normalização financeira e avaliação; validação estrita com 165 testes, Ruff, estrutura e skills aprovados.
- [Candidato r3](v030-candidato-r3.md): 45 arquivos, fingerprint completo `052bc6ca8e10f053cf9f2612e27563e3367bef34e8adb493657869598f2bc660`; runtime `f0c8d937187e8929a214634cafd3416a8f912314ada5c462be5184c77d983d12`. Build r3 e 125 insumos conferidos.
- [Revisão r3](v030-reviewer-r3.md) confirmou isolamento/validação de execução, mas apontou dois P2 no validador dos cenários: aprovação indevida de negação de divergência e rejeição de formulação correta de insuficiência. Mesmo Developer acionado para r4, restrito a validação/testes. Rodada paga seguinte aguarda nova revisão apta. QA ainda não acionado.
- Stack completo iniciado com imagens r3: API, Qdrant e mocks saudáveis. [Prontidão](v030-ready-r3.json) confirma app 0.3.0, esquema 5, índice real de 145 trechos e prompts Router 4/Support 7. API restrita a `127.0.0.1:18030`. Override de teste remove `.env` do serviço, passa somente OpenAI em ambiente, compartilha o ledger isolado e fixa teto US$0,15.
- Preparada revalidação via HTTP normal (`POST /messages`), sem execução dos casos ainda. Script temporário `.pytest_cache/v030-real-http-run-r2.py` e override `.pytest_cache/v030-compose-validation.yml`; deverão ser identificados no contexto da próxima rodada. O índice do stack consumiu parte do mesmo teto; `/ready` informou saldo US$0,0818.
- Próximo: passagem Developer r4, manifesto/novo fingerprint (reutilizar imagens apenas se 125 insumos/runtime não mudarem), nova revisão do mesmo Reviewer, rodada real HTTP e terceiro subagente QA. Manter o teto persistente, não reinicializar ledger, não fazer commit/push/merge/tag/publicação.

## Continuação: r4, revalidação HTTP e r5

- R4: 173 testes e revisão independente apta. Produto/runtime r3 preservado; correções de avaliação restritas a dois arquivos. [Manifesto r4](v030-candidato-r4.json) e [revisão r4](v030-reviewer-r4.md).
- [Rodada HTTP r2](v030-real-http-r2.md) concluída no stack real: núcleo 27/27; todos os 40 casos com rota, status, idioma, ferramentas, valores, fontes e grounding corretos. Cinco cenários dev tiveram falsos negativos de conteúdo, incluindo uma expressão qualificada tratada como afirmação proibida. Conversas 3/4; FU02 preservou protocolo/caso handoff, mas o último retorno foi `acknowledgement`/`answered`.
- Gasto acumulado da guarda de validação após HTTP r2: **US$0,13584893** (teto US$0,15; saldo US$0,01415107). Total registrado do projeto: US$0,58744893. Não repetir os 40 casos pagos por ajustes de redação.
- Tarefa 26 aberta para continuidade após handoff. R5: Router 5, equivalência/negação dos cenários e regressões; código Python do produto e holdout preservados. **181 testes** e validação estrita aprovados, 19 direcionados, cenários programados 13/13. [Passagem Developer r5](v030-developer-r5.md).
- Um turno do Developer falhou por cota da ferramenta. Consulta de estado confirmou que a janela havia reiniciado e o uso normal estava permitido; o mesmo agente retomou com `gpt-6-luna/high`, sem troca de modelo, compra ou uso de crédito de reset. O orçamento de APIs é separado.
- [Candidato r5](v030-candidato-r5.md): 48 arquivos; fingerprint `8b15414ab90acfc576404ef45c23a71526eea333d0c4cdcf8d46d4f3e4741f97`; runtime `643609655b811641b497b96d5d4555b1dc6f2387016ac5e591ab79914622ab78`; 126 insumos. Imagens reconstruídas, stack e QA sem custo atualizados; [prontidão r5](v030-ready-r5.json) e [ambiente QA](v030-qa-environment-r5.json).
- Reviewer r5 acionado. Após parecer apto: executar `.pytest_cache/v030-replay-http-r2.py` (sem rede/custo, preserva checks não semânticos e prova mudanças só em anotações dev); repetir as quatro conversas com `.pytest_cache/v030-real-conversations-r3.py` por HTTP, no mesmo ledger. Ambos os scripts têm hashes no manifesto.
- O terceiro agente QA ainda não foi acionado. Deve usar `gpt-6-luna/high`, contexto novo, história e candidato r5, ambiente sem credenciais em `127.0.0.1:18031`, além das evidências reais. Não enviar mensagens pagas à API `18030` por conta própria.
- A v0.3.0 ainda não está concluída: faltam revisão/revalidação/QA finais e aceite humano. O pedido de avançar à próxima versão só se aplica depois disso. Nova versão deve partir de main atualizada; commit/integração/tag continuam dependendo de autorização explícita.

## Continuação: r6 e QA final

- Reviewer r5 encontrou uma contradição ainda aceita na rubrica insuficiente. R6 introduziu `must_not_assert` opcional, com regras limitadas EN/PT por oração; ban literal `must_not_include` preservado, sem heurística de negação para privacidade. Código HTTP, ferramentas, Router 5/Support 7, dados e holdout preservados.
- R6: **191 testes** na validação estrita e **29 direcionados**, Ruff/estrutura/skills aprovados. [Passagem Developer r6](v030-developer-r6.md).
- [Manifesto r6](v030-candidato-r6.json): 49 arquivos; fingerprint `f8efcec3918320c287b3b6c2faef2f38edca4847a02b19bcd781ed7e920a1af9`; runtime `e58e5668172b992ebabf9777237686a2e0357cdccd5c7657436acbbc703b1cde`. Imagens reconstruídas e identidades exatas conferidas; [API pronta](v030-ready-r6.json) e [QA isolado](v030-qa-environment-r6.json).
- [Reviewer r6](v030-reviewer-r6.md): **apto para revalidação e QA**, com contradições/qualificações e privacidade literal rederivadas. Sem chamadas pagas pelo Reviewer.
- [Replay determinístico](v030-real-http-r2-replay.md): **40/40** das mesmas respostas HTTP r2, zero chamada/custo adicional. Só cinco resultados dev de conteúdo/afirmação mudaram; holdouts e todos os checks não semânticos permaneceram idênticos. Dados/custos/latências/notas originais preservados.
- [Revalidação HTTP das conversas r3](v030-real-conversations-r3.md): **4/4** no candidato r6. FU02 segue `knowledge_and_support`/`handoff` no último retorno, preservando caso e protocolo; sem relaxar o cenário reservado.
- Gasto acumulado do ledger da validação: **US$0,14123583** de US$0,15; saldo US$0,00876417. Total do projeto **US$0,59283583** de US$5. Não reinicializar ledger nem disparar novas APIs sem necessidade/autorização aplicável.
- Terceiro subagente `/root/qa_v030` **acionado** explicitamente `gpt-6-luna/high`, `fork_turns=none`. Usa `127.0.0.1:18031`, container `getnet-v030-qa-http-r6`, sem credenciais, mesma imagem do candidato e dados próprios. API paga `18030`: somente GETs para QA. Relatório esperado em `docs/evidence/v030-qa-r6.md`.
- Próximo: conferir passagem QA e hashes, concluir registro central, apresentar decisão humana sobre integração. Identidade Git local conferida: `lauroPereira <lauro.s.pereira@gmail.com>`, igual à definida no projeto. Ainda sem autorização para commit/push/merge/tag; não iniciar v0.4.0 na branch atual nem ignorar a base main.

Testes Python na execução restrita encontraram duas limitações: criação de diretório Temp e `socketpair` do loop do Windows bloqueado ao usar FastAPI TestClient. Testes usam agora basetemp novo sob `.pytest_cache/`, ignorado pelo Git. Canário executado com permissão ampliada para os testes locais: `.venv/Scripts/python.exe -m pytest tests/unit/test_health.py --basetemp=.pytest_cache/v030-health-permission-check`: **2 passed em 0,09 s**, sem rede externa/credenciais. Developer orientado a manter TestClient/ASGI e executar a rodada completa com essa permissão; não reduzir cobertura para esconder limitação de ambiente.

## Fechamento funcional e documental

- [QA r6](v030-qa-r6.md) **apto funcionalmente**, sem defeito reproduzível. História percorrida por HTTP e cliente MCP; isolamento e falha controlada comprovados. MCP executado no contêiner Linux da mesma imagem após limitação de loop do Windows. Sem chamada paga pelo QA.
- Limitações mantidas: modelo programado para o QA/falha injetada; ruído de recuperação no segundo turno Visa programado; ausência de nova execução real da falha de dependência; 40 casos reais preservados com replay, distintos das quatro conversas reais repetidas no r6.
- Estados/checklists/evidências das tarefas 21–26 atualizados após QA. [Manifesto r6-docs1](v030-candidato-r6-docs1.json): 49 arquivos, fingerprint `5957a94d44675be57acad3310ece77c574e7edd4aed19d39116bd97068a1fd07`. Somente seis documentos diferem; outros 43 arquivos, runtime 31 e insumos Docker 126 idênticos ao r6. Os critérios e a história permanecem fixados. R6 original preservado como identidade das execuções.
- [Reviewer do fechamento](v030-reviewer-fechamento.md) confirmou os hashes e o suporte factual das conclusões, distinguindo replay e conversas ao vivo. Sua ressalva sobre resumo antigo de QA foi corrigida no resultado central; o manifesto histórico mantém hashes, sem snapshot textual anterior das tarefas.
- QA do fechamento acionado depois da confirmação do Reviewer, nos mesmos agentes/modelos. Checagens adicionais restritas ao delta documental e aos helpers temporários do próprio QA; nenhuma nova API ou execução do produto necessária.
- Supervisor reconferiu os 49 hashes, runtime 31, build 126, ambos fingerprints e 36 links locais. `git diff --check` aprovado; arquivos protegidos sem alteração. Identidade Git confere e remoto local é o SSH do repositório privado previsto; nenhum acesso de rede ao provedor nesta etapa.
- [Integração concreta proposta](v030-integracao-proposta.md) preparada para decisão humana. Nenhum commit/push/PR/merge/tag executado; v0.4.0 não iniciada. A autorização de avanço não elimina as aprovações explícitas exigidas pelo AGENTS.md para Git, rede, contratos, autenticação e migrações.

[QA do fechamento](v030-qa-fechamento.md) confirmou validade, 49 hashes/runtime/build
e preservação das limitações; reconciliou o estado atual do resultado central.
Corrigiu somente sintaxe/imports/formatação de cinco helpers MCP ignorados,
porque o validador local inclui esses temporários; Ruff e análise de sintaxe
aprovados, sem nova execução do produto ou APIs. Conferência final do Supervisor:
hashes e links válidos, `git diff --check` aprovado. Candidato pronto para decisão
humana de integração; nenhuma aprovação fictícia de liberação registrada.

## Aceite humano de integração — 2026-10-27

O responsável autorizou **“Autorizar integração completa e tag v0.3.0”**.
Supervisor reconferiu candidato/identidade, realizou fetch autorizado e
confirmou main remota na base original, repositório privado e ausência de
PR/tag duplicados. Integração conforme [registro](v030-integracao.md), sem
alterar runtime, história, critérios ou teto de APIs. A v0.4.0 deve partir
da main atualizada após conferir o resultado real desta integração.

Developer, Reviewer e QA foram retomados em sequência nos mesmos agentes
`gpt-6-luna/high` para o fechamento editorial de release. README/CHANGELOG
alinhados ao aceite; [manifesto final](v030-release.json), fingerprint
`3de3e863431e81740d014239bd88df093b48e9d37c9614993da59c826767c80a`.
Runtime31 idêntico ao r6; único insumo Docker divergente é README, descrição
do pacote. Não foi declarado novo build/teste de produto. [Reviewer](v030-reviewer-release-docs.md)
e [QA](v030-qa-release-docs.md) confirmaram a validade restrita desse delta.
