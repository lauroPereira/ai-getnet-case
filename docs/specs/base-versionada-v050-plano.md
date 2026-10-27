# Plano: base versionada v0.5.0

## Especificação relacionada

[Spec](base-versionada-v050.md), [API proposta](api-kb-v050-proposta.md),
[história v1](../historias/base-versionada-v050.md), ADR0009 e
[complemento proposto0014](../architecture/decisions/0014-ciclo-kb-v050.md).
**Estado: aprovado pelo responsável em 2026-10-27; correções da tarefa45
revisadas; QA real r1 executado, com defeitos web nas tarefas47/48.** Correções
49/50 autorizadas, seguidas de revisão focada e revalidação no mesmo cap.
Pendências P3 da revisão r2 ficam na tarefa46. A aprovação veio com a resposta
“Aprovar a implementação descrita”. Inclui APIs, migração0007 em banco
sintético, guarda prévia de embeddings, interface nos dois projetos, rede de
documentação/dependências/QA e três novos agentes sequenciais gpt-6-luna/high.
Produto não tinha sido implementado no momento do aceite.

## Decisões técnicas

1. Registrar documentos iniciais a partir dos snapshots públicos e corpus
   fictício existentes. Não editar arquivos-fonte via API. Rascunhos e versões
   ficam no SQLite; snapshot de conteúdo/hash é congelado na candidata.
2. Migração reversível0007, aditiva: `kb_documents`, `kb_drafts`, `kb_versions`,
   `kb_state` (ativa/anterior/revisão) e `kb_events`. Remoção dessas tabelas
   somente em teste de downgrade de banco sintético isolado; dados anteriores
   e ledger não mudam. Manifesto/conteúdo de versão publicada são imutáveis.
3. Coleção própria para cada candidata; alocar identidade no servidor e
   recusar colisão antes de chamar `KnowledgeIndex.rebuild`. Não usar rebuild
   contra coleção ativa/anterior. Estados building/testing/ready/active/retired
   e failed, com erro saneado. Nenhuma coleta de lixo automática nesta rodada:
   retenção física depende de aprovação de remoção, sem apagar coleções existentes.
4. Build/teste síncronos e limitados para o corpus atual, sem nova fila ou
   dependência. Timeout/falha deixa candidata não ativável. Registro persistido
   permite inspecionar o resultado; repetição exige ação explícita.
5. Estimativa sem inferência e digest do corpus antes do build. Recomputar e
   conferir digest/revisões/limite antes de reservar. Cada lote de embedding,
   incluindo consulta/teste, reserva antes do provedor e liquida uso depois,
   evitando dupla contabilização do callback existente.
6. Capturar um `KnowledgeIndex` identificado por execução, em vez de mutar o
   índice compartilhado. Troca atômica do ponteiro com ativa esperada; manter
   coleções referenciadas por execuções em andamento. O manifesto fixa modelo
   e dimensão; incompatibilidade nunca reutiliza silenciosamente outro índice.
7. UI administrativa: documentos, editor/diff, estimativa/confirmação, build,
   teste, ativação/retorno e estado. Cliente/snapshot OpenAPI sincronizados;
   rascunhos e ações não se repetem em rerun. Credenciais continuam só no backend.
8. Teto persistente por ledger em `<ledger>.limit` (aceito em 2026-10-27,
   R2-06): criado uma vez no primeiro uso, sem tocar no SQLite; ledger
   pré-existente fica em no máximo US$1; remontagem não amplia o teto e o
   máximo absoluto é US$5. Ativação/retorno conferem a coleção contra o
   manifesto; `bootstrap`/`index` não reconstroem coleção existente.
9. Após QA real, o responsável aprovou a recuperação manual da conversa:
   ID conhecido antes do POST, falha de transporte recuperável e consulta
   somente GET, sem reenviar mensagem paga automaticamente. Sem alteração
   de API pública, autenticação, timeout ou orçamento. Escopo da tarefa50 e
   [proposta aprovada](../evidence/v050-recuperacao-chat-proposta.md).

## Componentes afetados

Backend `rag/`, montagem do runtime/grafo/contexto, migrações, API `/v1`,
metadados de trace/snapshot e testes. Web app/cliente/fixtures/testes e docs.
Não alterar AGENTS/CLAUDE/skills, autenticação, finanças ou o contrato legado.

## Modelo de dados

Documentos têm ID/origem imutáveis; rascunhos têm revisão, conteúdo e hash.
Versões contêm parent, manifesto, snapshot dos documentos, coleção, embedding,
estado, testes e erro. Ponteiro tem ativa/anterior e revisão otimista. Eventos
registram principal administrativo, ação, versões, horário e evidência.

## APIs ou interfaces

Superfície aditiva [proposta](api-kb-v050-proposta.md), com papéis atuais e
erros estruturados. Trace/snapshot acrescentam identificação da versão usada;
request/response legado permanecem iguais. Nenhum consumidor novo depende do
contrato até sua aprovação.

## Estratégia de testes

- Unidade/contrato:0006→0007→0006, fontes oficiais, tipos/limites, revisão/CAS,
  estados inválidos, custo desconhecido/negado e falhas antes/depois do provedor.
- Integração: candidata isolada, manifesto, ativação/retorno, índice capturado
  com ativação concorrente, consulta única por run e compatibilidade legado/MCP.
- Web: jornada administrativa, demo403, erro/vazio/loading e nenhum envio em rerun.
- Reviewer independente, candidato por SHAs/hashes dos dois repos e QA pela história.

## QA real e orçamento já autorizado

O responsável autorizou QA pago **a partir da v0.5.0**. Usar APIs reais no
aceite dos caminhos pagos e regressão, sem converter o pytest comum em teste
pago automático. A rodada cobre baseline, JEV real/comparação/perfis ainda
pendentes, build/teste/ativação/retorno e regressão relevante do atendimento.

Planejar estimativa inicial até US$0,15 e teto operacional adicional persistente
US$0,25, sempre inferior ao saldo global. Verificar preços/IDs/capacidades em
fontes oficiais antes do envio; resposta real pode confirmar o modelo disponível.
Não executar chamada de custo desconhecido, comprar crédito ou alterar chave.

Pré-checagem somente de presença confirmou OpenAI/DeepSeek/TypeSafe configurados.
Ledger nativo existente tem850 entradas e US$0,34298961 comprometidos dentro
do limite configurado US$1; o acumulado total entre rodadas é US$0,59283583.
O QA deve reconciliar esses registros, reutilizar a guarda persistente sem
reset e fixar o limite adicional uma vez (não renová-lo a cada tentativa).
Pode injetar a mesma guarda no runtime isolado de QA, preservando defaults e
a configuração/ledger originais. Toda tentativa consumida permanece registrada.
O QA monta o ledger real uma única vez com `BUDGET_LIMIT_USD=1.00`, o que cria
`data/runtime/budget.sqlite3.limit` = 1.00 (aceito pelo responsável), confere
o conteúdo do arquivo e não usa limite mais estrito nessa primeira montagem.

## Riscos técnicos e retorno

Falha/timeout não ativa coleção; conflito de versão retorna409; bloqueio de
custo ocorre antes da rede. Retorno normal troca ponteiro para anterior íntegra.
Retorno de código parte dos merges v0.4 conhecidos; downgrade0007 só será
testado em SQLite sintético, sem apagar coleções ou bancos do responsável.
Disco tem cerca de250MiB livres na preparação: evitar instalações/duplicações,
reusar dependências e parar gravações se cair abaixo de80MiB; nenhuma limpeza
está autorizada por este plano.

## Plano de implementação

39. [Registro/migração](../tasks/39-registro-kb-e-migracao-v050.md).
40. [Documentos/rascunhos/diff](../tasks/40-documentos-rascunhos-diff-v050.md).
41. [Índice/custo](../tasks/41-indice-candidato-e-custo-v050.md).
42. [Ativação/retorno/snapshot](../tasks/42-ativacao-retorno-snapshot-v050.md).
43. [Interface](../tasks/43-interface-base-versionada-v050.md).
44. [Validação real/regressão](../tasks/44-validacao-real-e-regressao-v050.md).
45. [Correções da revisão r1](../tasks/45-correcao-revisao-v050-r1.md).
46. [Pendências P3 da revisão r2](../tasks/46-pendencias-revisao-v050-r2.md).
47. [Defeito de confirmação UI](../tasks/47-formularios-confirmacao-ui-v050.md).
48. [Diagnóstico do timeout](../tasks/48-diagnostico-timeout-chat-ui-v050.md).
49. [Correção de confirmações](../tasks/49-correcao-confirmacoes-qa-v050.md).
50. [Recuperação manual](../tasks/50-recuperacao-manual-chat-v050.md).
51. [Reconfirmação do teto](../tasks/51-reconfirmar-teto-kb-v050.md).
52. [Defeito GET de conversa](../tasks/52-recuperar-conversa-get-ui-v050.md).
53. [Consumo do contrato real](../tasks/53-consumir-contrato-real-conversa-v050.md).

## Delegação aprovada

Autorizados neste conjunto: três novos subagentes em sequência
Developer → Reviewer → QA, explicitamente `gpt-6-luna/high`, contexto novo e
nenhum adicional. Em 2026-10-27, a partir da tarefa45, o responsável trocou a
delegação para subagentes Claude Sonnet 5.5 nos mesmos três papéis.
Na retomada Codex após a revisão r2, autorizou explicitamente QA
gpt-6-luna/high e, após os defeitos reais, a reutilização de Developer e
Reviewer gpt-6-luna/high para49/50 e retorno ao mesmo QA, sem agente adicional.
Correções voltam ao Developer vigente. Supervisor coordena,
Reviewer não recebe conclusões do implementador e QA valida candidato fixado.

## Aprovação registrada e limites

O responsável aceitou APIs aditivas, migração0007, fluxo administrativo,
reserva antes de embeddings e delegação acima. QA pago já está autorizado;
este aceite não aumenta US$5. A alternativa apresentada foi manter
somente o plano local sobre a v0.4 integrada. Sem novos commits/pushes da
v0.5.0, exposição pública, limpeza, remoção de coleção ou mudança de credencial.
Inclui rede para documentação oficial, dependências/builds de teste e chamadas
de QA autorizadas; operações nos dois diretórios do projeto permanecem no escopo.
