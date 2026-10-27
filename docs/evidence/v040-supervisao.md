# Supervisão da v0.4.0

## Estado reconciliado

v0.3.0 concluída: PR #4 integrado, main e tag remotas no merge
`bd549cc921ccffb37bd304a0959b8a4b690d6421`. [Registro Git](v030-git-integracao.json).
Main atualizada antes de criar `codex/v0.4.0-perfis-interface` nessa base.

Supervisor preparou [plano](../specs/perfis-interface-v040-plano.md), tarefas
27–32, [contratos propostos](../specs/api-v040-proposta.md),
[ADR 0013](../architecture/decisions/0013-sessoes-api-e-perfis-v040.md),
[base web proposta](../specs/base-web-v040-proposta.md) e
[história versão 1](../historias/perfis-interface-v040.md).

O responsável aprovou o plano completo sem chamadas pagas em 2026-10-27.
Developer `/root/developer_v040` acionado explicitamente `gpt-6-luna/high`,
`fork_turns=none`; sem agentes adicionais. Os três agentes v0.3.0 concluíram
suas passagens e são históricos. Reviewer/QA da v0.4.0 serão contextos novos,
acionados em sequência após as passagens. A sessão principal continua Supervisor.

## Fonte da base web e limites

Template local versão 0.2.0. SHA256 lidos sem alterar a fonte:

| Arquivo fonte | SHA256 |
| --- | --- |
| AGENTS.md | `0c51916f69aff1d13525df2f047aa7c8a55180ce21f3da4a2fb9501d2f999505` |
| CLAUDE.md | `041914a3429c4afe01f65dc490dcf00e2af0d2689f83ab8992ca006476e3a4bc` |
| .agent-template.json | `117c7365c65d2d8e8bebbd31fe10edfd8b9fa6d47c5f3f1c1fae23782353b591` |

A leitura inicial de metadados Git do template teve permissão negada na
execução restrita. Após a autorização, o acesso ampliado confirmou fonte
limpa e commit, conforme registro da criação abaixo. Destino
`C:\workspace\ai-getnet-case-web` estava ausente antes da preparação.

## Autorização vigente e próxima ação

Implementação concreta aprovada: contratos `/v1`, sessões/papéis, migração
0006 e base/produto web; três subagentes sequenciais `gpt-6-luna/high`; rede
para fontes oficiais/metadados comprovadamente gratuitos e dependências/builds.
Próximo: concluir implementação e validação offline, fixar candidato e
despachar Reviewer. Sem autorização para chamadas pagas, commit/push/remoto/tag
v0.4.0 ou publicação. Retorno e critérios descritos no plano.

Orçamento do projeto permanece **US$0,59283583 de US$5**; nenhum gasto nesta
preparação. Guarda da validação v0.3.0 preservada; saldo não transferido como
nova autorização para provedores ou experimentos da v0.4.0.

## Validação inicial do planejamento, anterior à implementação

Conferidos 14 documentos e 50 links locais; validação estrutural padrão e
`git diff --check` aprovados. Nenhum teste de produto foi repetido por este
delta documental. Manifesto Git da tag reconferido por blobs: 49 arquivos,
runtime31 e insumos126; main/HEAD/tag apontam para o merge v0.3.0.
Arquivos protegidos e código/testes/prompts/configuração do backend sem
alteração nesta branch. Destino web segue ausente. Aprovação específica do
conjunto da v0.4.0 foi posteriormente concedida: “Aprovar plano completo sem
chamadas pagas”. Os resultados de implementação/base são registrados abaixo.

## Base web concluída e autorização aplicada

Base criada em destino ausente, com escrita exclusiva de arquivos novos.
Fonte confirmada limpa em `7f556a5a8afbaba865e382fb436e96a8be5b6886`, versão
0.2.0. O acesso Git da fonte foi autorizado e obtido nesta etapa; a limitação
anterior de leitura foi resolvida. 47 arquivos-fonte selecionados; 54 arquivos
iniciais, incluindo adaptações aprovadas; sync criou 18 cópias de 9 skills,
zero remoções/atualizações. [Manifesto de base](v040-base-web.json), 72 hashes.

Validadores PowerShell de estrutura/fluxo passaram; links/managed paths e
equivalência das duas cópias de skills passaram. Python padrão comprovou
apenas estrutura, não testes de produto. Fonte preservada; sem .git/.env no
destino, sem identidade configurada ou remoto criado. Supervisor liberou o
Developer para produto web após esse ponto; governança permanece protegida.

| Papel v0.4.0 | Identificação | Modelo/esforço | Estado |
| --- | --- | --- | --- |
| Developer | `/root/developer_v040` | `gpt-6-luna/high`, contexto novo | Passagem r1 concluída; fonte congelado |
| Reviewer | `/root/reviewer_v040` | `gpt-6-luna/high`, contexto novo | Acionado após candidato r1 |
| QA | Após revisão apta | `gpt-6-luna/high`, contexto novo | Ainda não acionado |

## Armazenamento e retomada

A instalação de dependências web encontrou disco cheio. O Developer parou
gravações e encerrou seu único servidor sintético ao atingir zero espaço;
nenhum processo seu permaneceu ativo. Antes disso: 12 testes focados backend,
quatro testes web e contrato OpenAPI com Bearer passaram. A regressão estrita
completa continuou pendente após ajustes de expectativas de versão/migração.
AST de 87 arquivos e lint backend conferidos somente em leitura; uma ordem de
imports web e o fechamento do APIClient ainda exigiam correção.

O responsável autorizou **“Apagar somente as nove pastas listadas”** na
[proposta exata](v040-limpeza-proposta.json). Supervisor reconferiu os nove
nomes, caminhos absolutos/resolvidos sob `.pytest_cache`, ausência de reparse
points em toda a árvore e contagens/tamanhos idênticos aos aprovados antes de
remover. [Resultado](v040-limpeza-resultado.json): nove diretórios removidos,
184.482.264 bytes; espaço livre de zero para 179.695.616 bytes. Runtime real
v0.3.0/guarda e testes v0.4.0 preservados; nenhuma remoção adicional.

Mesmo Developer retomado, mantendo `gpt-6-luna/high`. Reutilizar dependências,
sem novas instalações e sem chamadas pagas; parar gravações se o espaço cair
abaixo de 40 MiB. Próximo: correções pendentes, regressão estrita, AppTest e
fluxo HTTP/UI sintético, passagem e congelamento de candidato. Reviewer e QA
continuam aguardando a implementação/validação completa no escopo autorizado.

## Retomada após limite da ferramenta

Um turno do mesmo Developer falhou por limite de uso da ferramenta de
desenvolvimento, sem realizar chamadas pagas da aplicação. O responsável
pediu retomar. Consulta da disponibilidade confirmou uso normal permitido
após renovação natural da janela; nenhum upgrade, compra ou crédito de reset
foi usado. `/root/developer_v040` retomado com `gpt-6-luna/high`, sem substituir
modelo ou criar agente adicional.

Espaço livre reconferido na retomada: 2.305.855.488 bytes. Essa leitura é
posterior aos 179.695.616 bytes medidos após a limpeza autorizada e não é
atribuída a remoção adicional pelo Supervisor. Dependências declaradas podem
ser completadas no ambiente isolado se necessário; evitar cache/duplicação e
parar gravações em novo esgotamento. Nenhuma nova limpeza autorizada.

## Passagem r1 e revisão independente

[Developer r1](v040-developer-r1.md) concluiu fonte e documentou 202 testes
backend, sete web, ambientes independentes, contrato OpenAPI, fluxo HTTP e
AppTest sem provedores. O Supervisor reconferiu os 48 hashes da passagem e
seu digest antes de mudar esta evidência de coordenação. O manifesto do
Developer é histórico; o candidato autoritativo exclui evidências mutáveis.

[Candidato r1](v040-candidato-r1.json) fixado: 39 arquivos alterados backend,
83 frontend; fingerprint `91184b73d1c91f5b1790b831038e9853a54b20a1791407447ecd4a7380eeeaec`,
runtime completo `c5adab307e7e2e1a6f0519d64dc6b70ce25471520c4de44b8d843ee07e7da41c`.
Reviewer novo `/root/reviewer_v040` explicitamente `gpt-6-luna/high`,
`fork_turns=none`, acionado com fontes/critérios/manifesto, sem histórico ou
diagnóstico do implementador. Fonte permanece congelado; alterações de
produto exigirão novo candidato e revisão do escopo afetado.

Supervisor preparou [API e Streamlit de QA](v040-qa-environment-r1.json)
somente em loopback, sem credenciais de provedor, com ScriptedLLM,
HashEmbedder e mocks em processo. Prontidão API 200/schema6/145 trechos e
saúde web 200; PIDs dos listeners conferidos como filhos dos lançadores
iniciados pelo Supervisor. Nenhuma mensagem ou inferência enviada nessa
preparação. QA independente só será despachado após parecer apto.

Catálogo documentado por fontes oficiais; nova consulta autenticada a
`GET /models` não foi feita sem comprovação de gratuidade. CA-32 JEV real
continua pendente e deve permanecer explícito. O manifesto não declara build
Docker novo. Commit, push, remoto web, tag e publicação continuam sem autorização.

## Revisão r1: correção de erro de orçamento

[Reviewer r1](v040-reviewer-r1.md) reconferiu integridade antes/depois,
executou testes focados, frontend e fluxo HTTP próprios. Parecer: correções
necessárias por P2 na comparação quando `BudgetExceeded` não recebe tratamento
operacional. A guarda continua impedindo a chamada, mas o endpoint pode
devolver 500 genérico. [Tarefa 33](../tasks/33-erro-orcamento-comparacao-v040.md)
aberta dentro do escopo aprovado, preservando guarda/contabilização.

Mesmo Developer retomado para correção cirúrgica e regressões sem custo.
Os processos próprios do ambiente r1 foram identificados e parados antes
das edições; seus runtimes/logs foram preservados. Manifesto/parecer r1 ficam
históricos. Novo candidato r2 e reavaliação pelo mesmo Reviewer serão
necessários; QA ainda não acionado.

## Revisão r2 e contrato da interface

[Reviewer r2](v040-reviewer-r2.md) revalidou a correção de orçamento e sua
contabilização parcial. Novo achado P2: snapshot OpenAPI do frontend omitiu
o 429 já emitido/documentado pelo backend. [Tarefa 34](../tasks/34-sincronizacao-openapi-web-v040.md)
aberta; mesmo Developer acionado para regeneração determinística e checagem
do consumidor, mantendo backend/guarda inalterados. QA ainda não iniciado.

[Build Docker r2](v040-docker-r2.json) concluído com insumos fixados no
manifesto r2. Imagem `sha256:67f4dc3fa6c06f34950246b4ab64527ae2ffe277fc4f3c758450faec12fa62a1`.
Contêiner sintético instalado responde `/ready` 200/app0.4/schema6/145trechos
em `127.0.0.1:18841`, sem chaves, com ScriptedLLM/HashEmbedder. O schema
desse backend será fonte HTTP para sincronizar o snapshot web. Não é
bootstrap de produção nem validação real de provedor. A imagem pode ser
reutilizada no próximo candidato somente se runtime/insumos backend forem
idênticos; não reconstruir por alteração exclusivamente documental/frontend.

## Candidato r3 e QA

[Developer r3](v040-developer-r3.md) sincronizou o snapshot com o schema servido
pelo backend Docker e conferiu idempotência do gerador/cliente. Nenhuma fonte
runtime/build backend mudou. [Manifesto r3](v040-candidato-r3.json): 41 hashes
backend, 83 frontend; fingerprint
`31f10d7dfb249bdc7f517ee0ef6144a40061aaac766ad2dd5c63bd018d9f1e8e`.
[Reviewer r3](v040-reviewer-r3.md) reconferiu integridade, igualdade estrutural
completa dos contratos, nove testes web e seis focados; parecer apto para QA.

Terceiro agente `/root/qa_v040` acionado explicitamente `gpt-6-luna/high`,
`fork_turns=none`, depois da revisão apta, pela história fixada. Fonte congelado.
Usa Streamlit r3 em `127.0.0.1:18540` e backend Docker sintético em `18841`;
montagem/modelos programados, sem credenciais de provedor ou APIs pagas.
Imagem r2 reutilizada porque runtime/build backend r3 são idênticos. O
Supervisor verificou saúde HTTP da interface/API antes do despacho.
[Estado central](v040-resultado.md); relatório esperado `v040-qa-r3.md`.

A automação anterior retornou inexistente ao tentar atualizar seu estado;
não foi recriada e não altera a continuidade manual solicitada pelo usuário.

## QA r3 e correções 35/36

[QA r3](v040-qa-r3.md) encerrou com parecer reprovado: resposta Gravada
rotulada como Simulada e ausência de parâmetro de modelo compatível configurável
por agente (RF-49). As suítes completas passaram (206 backend, nove web), e os
hashes originais foram reconferidos sem divergências. As tarefas 35 e 36
registram reproduções e critérios positivos; história e critérios preservados.

Mesmo Developer retomado em `gpt-6-luna/high` para ambas as correções dentro
do plano já aprovado. Nenhum quarto agente, chamada paga ou integração Git.
Os serviços próprios r3 (Streamlit lançador 7840/listener 28260 e contêiner
`getnet-v040-synthetic-r2`) foram identificados e interrompidos; arquivos,
imagem e ambiente foram preservados. Próxima passagem exige candidato r4,
revisão do mesmo Reviewer e revalidação do mesmo QA. Fonte r3 é histórico.

Na retomada, a conferência de integridade comparou 29 arquivos protegidos web
(AGENTS/CLAUDE e as três cópias das nove skills) com a base inicial: nenhum
delta. O diff Git dos caminhos protegidos backend também permaneceu vazio;
frontend continua sem `.git`. Foram feitas somente leituras nessa conferência.

## Candidato r4 e ambiente incremental

[Developer r4](v040-developer-r4.md) devolveu correções 35/36, 214 testes
backend estritos e 12 web, Ruff/skills e geração idempotente do cliente.
[Manifesto r4](v040-candidato-r4.json): 48 backend e 84 web, fingerprint
`e785167251c25158cc1d5e82c1cd487785d0132244c3aa890dadf0e4d5caf5ef`.
Inclui explicitamente as três referências estáticas de catálogo, parâmetros e
metadados públicos; relatórios mutáveis continuam excluídos. Mesmos base/HEAD,
história v1 e critérios. Mesmo Reviewer retomado em `gpt-6-luna/high`, sem
receber diagnósticos ou conclusões do Developer. Fonte congelado.

Espaço C: voltou a cair a cerca de 365 MB, sem limpeza adicional. Como receita
Docker/dependências/dados/prompts são idênticos a r2, o Supervisor preparou
[imagem incremental r4](v040-docker-r4.json): wheel de 121.221 bytes com
63 arquivos do pacote coincidentes, instalado sobre imagem r2 fixada, sem
rede no build nem reinstalação de dependências. Novo consumo medido perto de
5 MB. Não houve rebuild completo do Dockerfile canônico; esse limite é explícito.
124 arquivos instalados coincidem com r4, sem divergências; API pronta 200,
schema6/145 trechos. [Ambiente r4](v040-qa-environment-r4.json) em loopback,
Streamlit pronto 200, fontes/modelos sintéticos e sem chaves. QA só retoma
após revisão apta. Nenhuma autorização destrutiva adicional foi necessária.

## Revisão r4 e tarefa 37

[Reviewer r4](v040-reviewer-r4.md) reproduziu P2: limite interno de reserva
JEV é exposto como parâmetro efetivo, embora não pertença ao payload do
provedor. Hashes 48/84/127/128 íntegros; oito testes backend, três de interface
e três de contrato passaram. A fonte precisa distinguir essas semânticas;
[tarefa 37](../tasks/37-parametros-efetivos-jev-v040.md) registrada sem alterar
critérios, guarda ou orçamento. Mesmo Developer retomado em `gpt-6-luna/high`.
Serviços r4 próprios foram identificados e parados; imagem/arquivos preservados.
Novo candidato r5 exige reavaliação antes de QA; nenhum quarto agente criado.

## Candidato r5

[Developer r5](v040-developer-r5.md) corrigiu a distinção reserva/parâmetro
aplicado e a propagação de comparação para snapshot. Strict: 216 testes,
Ruff/skills; oito focados. Web inalterada desde r4, sem repetição de suíte.
[Manifesto r5](v040-candidato-r5.json): 50 backend/84 web,
`a65496ada0c9757e11a581fb61a6236a6606f0fd5a5ed02c31f44ce407999d34`.
Mesmo Reviewer acionado em `gpt-6-luna/high`, sem relato do Developer.

[Imagem incremental r5](v040-docker-r5.json) construída sem rede sobre r2
com wheel novo; 63 arquivos do pacote e 124 instalados coincidem. Mapas
50/84/127/128 reconferidos após empacotamento. [Ambiente r5](v040-qa-environment-r5.json)
pronto em loopback: API18841/Streamlit18540, ambos HTTP200, modelos programados
e sem chaves. Receita canônica não reconstruída. O disco passou a cerca de
673 MB livres antes do novo build, sem limpeza adicional pelo Supervisor.

[Reviewer r5](v040-reviewer-r5.md) apto para QA: sete testes focados e um de
consumo único, reprodução própria sem provedor, contrato com 13 caminhos e
18 schemas, hashes íntegros. Mesmo QA retomado em `gpt-6-luna/high` para as
jornadas afetadas 35–37, na interface e HTTP sintéticos do candidato fixado,
mantendo QA r3 histórico e CA-32 real não verificado.

O primeiro despacho QA r5 falhou por limite de uso. A revisão automática
também não conseguiu processar uma atualização documental; a ação não foi
executada e não houve determinação de risco. Após o responsável pedir
retomada, o serviço confirmou `ordinaryUsageAllowed=true`; o mesmo QA foi
retomado, sem compra, reset, upgrade, troca de modelo ou novo agente. Mapas
50/84/127/128 e saúde API/Streamlit 200 reconferidos antes do novo despacho.

## QA r5 e tarefa 38

[QA r5](v040-qa-r5.md) confirmou Gravado, rerun, publicação de parâmetro
Support256 e snapshot, rejeição HTTP422 sem mudar versão/digest, comparação
pré-selecionada JEV/LLM e consumo único. Treze testes backend e três web
passaram; hashes 50/84/127/128 íntegros. Parecer reprovado pela seleção após
comparar: radio JEV marcado, resumo LLM e execução LLM.

[Tarefa 38](../tasks/38-selecao-comparacao-v040.md) volta ao mesmo Developer
em `gpt-6-luna/high`. O Supervisor esclareceu a solução admissível conforme
contrato já aprovado: preservar método vinculado ao ID, invalidar/bloquear
mudança com feedback claro e exigir ação explícita para nova comparação;
nunca criar chamadas automaticamente no rerun. Não altera critérios de
aceite, API ou vínculo de segurança. Serviços r5 próprios foram conferidos
e interrompidos, imagens/relatórios preservados. Próximo candidato r6;
backend pode ser reutilizado somente se runtime/build permanecerem idênticos.

## Candidato r6

[Developer r6](v040-developer-r6.md) limitou o delta à tarefa 38 e ao web
app/testes/README. Mudança de método invalida resultado, exige novo clique
explícito e não altera o ID armazenado. Quatorze testes web, Ruff e validação
estrutural passaram. Backend216 anterior permanece aplicável, sem repetição.
[Manifesto r6](v040-candidato-r6.json): 51 backend/84 web, fingerprint
`d54fbd3799cecfefd0c467be217eb841e59d4ae9c89f607dc1a64967ae4d9367`.
Runtime/build comparados integralmente e idênticos a r5. Mesmo Reviewer
retomado em `gpt-6-luna/high`, com fonte congelada e sem relato do Developer.

[Ambiente r6](v040-qa-environment-r6.json) tem processos novos e tmpfs novo,
mantendo a imagem instalada r5 porque seus insumos são iguais. [Verificação](v040-docker-r6.json):
124 arquivos instalados coincidem, API/Streamlit200, schema6/145 trechos,
ScriptedLLM/HashEmbedder, sem chaves. Não houve novo build nem é declarado
rebuild canônico. QA retoma somente após parecer técnico apto.

[Reviewer r6](v040-reviewer-r6.md) apto: dois AppTests e reprodução própria
com contadores nos dois sentidos da troca, sem chamadas em rerun e com novo
ID apenas por clique. Mapas 51/84/127/128 íntegros após o parecer. Mesmo QA
retomado em `gpt-6-luna/high` para a tarefa 38 pela UI/HTTP do ambiente novo,
mantendo os positivos r5, a história e os limites de validação real.

## Encerramento da verificação sem custo r6

[QA r6](v040-qa-r6.md) apto na tarefa 38: os dois sentidos foram exercitados
na interface/HTTP, invalidação preservada no rerun, comparação explícita com
novo ID, uso único e snapshot JEV/LLM coerente. Dois testes focados passaram;
nenhum defeito novo exigiu tarefa 39. Positivos de Gravado, publicação do
parâmetro e rejeição HTTP de r5 preservados pelo delta restrito.

[Auditoria final](v040-verificacao-final-r6.json) do Supervisor reconferiu
branch/HEAD, mapas 51/84/127/128, fingerprints, 29 protegidos web, diff protegido
backend e 124 arquivos instalados. Nenhuma divergência; API e interface200.
Relatórios imutáveis de passagem/revisão/QA identificados por SHA-256.

[Resultado central](v040-resultado.md) distingue critérios demonstrados com
modelos programados de CA-32 real e catálogo autenticado pendentes. O build
incremental/reuso de imagem não é declarado rebuild canônico. Total de gasto
real do projeto permanece US$0,59283583, nenhuma API paga nesta versão. Sem
commit, push, tag, remoto web, publicação ou avanço à v0.5.0. Exatamente três
agentes autorizados mantidos em `gpt-6-luna/high`; nenhuma delegação adicional.

## Integração autorizada

Responsável autorizou PRs/merges e início da v0.5.0, com QA pago apenas a
partir da próxima versão. Confirmou repositório web privado e identidade
local Gmail do projeto após divergência da configuração global; global
preservada. Base web real de 70 arquivos publicada em main, atualizada e
branch criada antes dos ajustes de integração.

[Backend PR5](https://github.com/lauroPereira/ai-getnet-case/pull/5) e
[Web PR1](https://github.com/lauroPereira/ai-getnet-case-web/pull/1) abertos e
anexados ao chat. Código/runtime iguais ao r6; somente README/changelog e
estados documentais foram alinhados. [Hashes Git](v040-git-integracao.json)
conferem após commit e normalização de texto. Serviços de QA próprios foram
identificados e parados antes da troca de branches; imagens/evidências
preservadas. Checks e merge ainda são ações a confirmar neste registro.

Confirmação posterior: ambos os PRs merged; main backend
`ea2355b5ba8fa8dcff66200f34461ae063183250`, web
`40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`, iguais local/remoto. Nenhum check/
status/job no GitHub; árvores e ancestralidade conferidas antes do push.
Branches v0.5 criadas somente depois de pull das mains integradas. A primeira
tentativa de criar branches teve timeout de revisão automática antes de
executar; a única repetição permitida concluiu normalmente. Sem bloqueio
remanescente de permissão. [Registro final](v040-integracao-confirmada.json).
