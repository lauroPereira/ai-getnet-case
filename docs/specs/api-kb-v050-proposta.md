# Proposta de API KB v0.5.0

**Contrato aprovado pelo responsável em 2026-10-27 com o plano v0.5.0 e
implementado pelo Developer r1; revisão independente e QA real pendentes.**

## Papéis e contratos preservados

Bearer/sessões v0.4 mantidos. Leitura de documentos/versões permite demo no
conteúdo publicado sintético/público; rascunhos e operações administrativas
exigem admin. Demo não escolhe dono/papel no corpo. Legado e MCP preservados.

| Rota | Corpo/retorno principal | Permissão |
| --- | --- | --- |
| GET `/v1/kb/documents` | ID, título, origem, versão/hash e editável | Bearer |
| GET `/v1/kb/documents/{id}` | Conteúdo publicado e metadados | Bearer |
| PUT `/v1/kb/drafts/{id}` | `content`, `expected_revision`; nova revisão/hash | admin, só fictício |
| GET `/v1/kb/drafts/{id}/diff` | Texto/diff, revisão e digest | admin |
| POST `/v1/kb/versions/estimate` | Revisões e ativa esperada; digest/chunks/estimativa | admin, sem API paga |
| POST `/v1/kb/versions` | Revisões, ativa esperada, digest esperado, confirmação e teto; candidata | admin |
| GET `/v1/kb/versions` | Estado/manifesto/ativa/anterior; rascunhos só admin | Bearer |
| GET `/v1/kb/versions/{id}` | Manifesto/testes/estimativa de teste saneados | Bearer no publicado; admin nos demais |
| POST `/v1/kb/versions/{id}/test` | Confirmação/teto se teste requer embedding; resultado | admin |
| POST `/v1/kb/versions/{id}/activate` | Ativa esperada e confirmação; ponteiro/evento | admin |
| POST `/v1/kb/versions/{id}/rollback` | Ativa esperada e confirmação; anterior íntegra/evento | admin |

## Validação

IDs resolvidos pelo registro, sem caminhos de arquivo fornecidos pelo cliente.
Texto Markdown limitado a64KiB UTF8 por documento fictício; origem não editável.
Revisão obsoleta ou digest divergente retorna409 antes do build. Publicação de
versão altera apenas ponteiro; manifesto/conteúdo congelados não são editados.

Build inclui todos os documentos da base pai e somente revisões explícitas de
rascunho. Estimativa usa preço registrado e limite conservador de tokens; o
cliente confirma e fornece teto que nunca aumenta os limites do servidor.
Sem confirmação, sem reserva suficiente ou sem preço conhecido não há envio.
Testes pagos também exigem confirmação e orçamento; navegação/GETs não inferem.

Erros:401 sessão,403 papel/origem imutável,404 recurso fora do escopo,409 revisão/
estado/conflito,422 formato/limite,429 orçamento,503 infraestrutura/provedor.
Corpo estruturado v0.4, sem traceback ou segredo. Nenhuma rota de remoção.

## Execuções e versões

O run/trace registra ID da versão da base e coleção/embedding efetivos como
metadados aditivos; cada execução consulta um único índice congelado no início.
Ativação não muda a execução em curso. A versão anterior permanece disponível
para retorno; coleção incompleta/failed não pode ser ativada.
