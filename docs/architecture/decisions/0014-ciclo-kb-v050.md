# 0014. Ciclo persistente da base e reserva de build v0.5

## Status

Aceita pelo responsável em 2026-10-27 com o plano v0.5.0. Complementa ADR0009;
não a substitui.

## Contexto e decisão proposta

Registro SQLite de documentos/rascunhos/versões, ponteiro ativo/anterior e
eventos; coleção Qdrant por candidata. Conteúdo congelado e origem imutável.
Build/teste explícitos e limitados, com estimativa/digest e guarda antes de
qualquer embedding. Estado `failed` torna falhas operacionais visíveis sem
trocar a ativa. Retenção física não apaga coleções existentes automaticamente.

Ativação usa comparação da ativa esperada e captura de índice por execução.
Rodadas reais de QA usam guarda existente injetada no runtime sintético
isolado, com sublimite persistente e sem reset de ledger/configuração global.

Complemento aceito em 2026-10-27 (revisão r2, R2-06): o teto de cada ledger
fica em arquivo `<ledger>.limit` criado uma vez, sem alterar o SQLite; ledger
pré-existente recebe no máximo US$1 e nenhuma remontagem amplia o teto
(máximo absoluto US$5). Ativação e retorno exigem coleção íntegra contra o
manifesto; coleções existentes nunca são reconstruídas no lugar.

## Alternativas

Rebuild da ativa no lugar expõe atendimento a versão incompleta. Mutação de
índice compartilhado viola captura por execução. Fila/serviço novo acrescenta
operação desnecessária para o corpus pequeno atual.

## Consequências e retorno

Mais metadados e índices candidatos; espaço monitorado. Limpeza é decisão
separada. Migração0007 reversível só em teste sintético; código anterior pode
usar a coleção de referência preservada. Nenhum arquivo oficial é sobrescrito.
Elevar o teto de um ledger exige edição manual do arquivo pelo responsável;
`bootstrap` mantém coleção existente defasada e só avisa, e conteúdo novo
entra por versão pela API administrativa.
