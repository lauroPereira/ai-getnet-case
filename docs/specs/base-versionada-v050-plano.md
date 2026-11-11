# Plano: base versionada v0.5.0

## Especificação relacionada

[Spec](base-versionada-v050.md), [API proposta](api-kb-v050-proposta.md),
[história v1](../historias/base-versionada-v050.md), ADR 0009 e
[ADR 0014](../architecture/decisions/0014-ciclo-kb-v050.md).
**Estado:** entregue na v0.5.0 (2026-10-27; [resultado](../evidence/v050-resultado.md)).
Aprovado pelo responsável em 2026-10-27: APIs, migração 0007 em banco
sintético, guarda prévia de embeddings e interface nos dois projetos.

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
   e failed, com erro saneado. Nenhuma coleta de lixo automática nesta versão:
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
8. Teto persistente por ledger em `<ledger>.limit` (aceito em 2026-10-27):
   criado uma vez no primeiro uso, sem tocar no SQLite; ledger
   pré-existente fica em no máximo US$1; remontagem não amplia o teto e o
   máximo absoluto é US$5. Ativação/retorno conferem a coleção contra o
   manifesto; `bootstrap`/`index` não reconstroem coleção existente.
9. Depois da validação real, o responsável aprovou a recuperação manual da conversa:
   ID conhecido antes do POST, falha de transporte recuperável e consulta
   somente GET, sem reenviar mensagem paga automaticamente. Sem alteração
   de API pública, autenticação, timeout ou orçamento. Escopo da tarefa 50.

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
- Revisão independente, candidato identificado por hash nos dois repositórios e validação real pela história.

## Validação real e orçamento

Validação paga a partir da v0.5.0: APIs reais no aceite dos caminhos pagos e na
regressão, sem tornar o pytest comum um teste pago. Cobre baseline, JEV real,
comparação, perfis, build/teste/ativação/retorno e regressão do atendimento.

Teto da campanha: US$0,25 (estimativa inicial até US$0,15), dentro do teto de
US$5. Preços, IDs e capacidades conferidos em fontes oficiais antes do envio;
chamada de custo desconhecido não é executada. A guarda persistente é
reutilizada sem reset, injetada no runtime isolado da validação; a primeira
montagem com `BUDGET_LIMIT_USD=1.00` cria `data/runtime/budget.sqlite3.limit` = 1.00.
Toda tentativa consumida permanece registrada.

## Riscos técnicos e retorno

Falha/timeout não ativa coleção; conflito de versão retorna 409; bloqueio de
custo ocorre antes da rede. Retorno normal troca ponteiro para anterior íntegra.
Retorno de código pela tag v0.4.0; a descida da 0007 é testada em SQLite
sintético, sem apagar coleções.

## Plano de implementação

39. [Registro/migração](../tasks/39-registro-kb-e-migracao-v050.md).
40. [Documentos/rascunhos/diff](../tasks/40-documentos-rascunhos-diff-v050.md).
41. [Índice/custo](../tasks/41-indice-candidato-e-custo-v050.md).
42. [Ativação/retorno/snapshot](../tasks/42-ativacao-retorno-snapshot-v050.md).
43. [Interface](../tasks/43-interface-base-versionada-v050.md).
44. [Validação real/regressão](../tasks/44-validacao-real-e-regressao-v050.md).
45. [Embeddings sob guarda, coleções preservadas e liquidação única](../tasks/45-correcao-revisao-v050-r1.md).
46. [Teto gravado exato, prontidão sem escrita e clientes sem retry](../tasks/46-pendencias-revisao-v050-r2.md).
47. [Formulários de confirmação da base](../tasks/47-formularios-confirmacao-ui-v050.md).
48. [Timeout do chat real na interface](../tasks/48-diagnostico-timeout-chat-ui-v050.md).
49. [Confirmações nas ações da base](../tasks/49-correcao-confirmacoes-qa-v050.md).
50. [Recuperação manual](../tasks/50-recuperacao-manual-chat-v050.md).
51. [Reconfirmação do teto](../tasks/51-reconfirmar-teto-kb-v050.md).
52. [Resposta persistida após recuperação por GET](../tasks/52-recuperar-conversa-get-ui-v050.md).
53. [Consumo do contrato real](../tasks/53-consumir-contrato-real-conversa-v050.md).

## Aprovação registrada e limites

O responsável aceitou APIs aditivas, migração 0007, fluxo administrativo e
reserva antes de embeddings, dentro do teto de US$5. Sem exposição pública,
limpeza, remoção de coleção ou mudança de credencial nesta versão.
