# Especificação: base editável e versionada v0.5.0

Estado: entregue na v0.5.0 (2026-10-27; [resultado](../evidence/v050-resultado.md)).

## Problema

A v0.4.0 seleciona perfis e registra execuções, mas a base depende de arquivos
e de uma coleção fixa. Não há jornada administrativa segura para editar uma
orientação fictícia, avaliar o índice candidato, ativá-lo e retornar à anterior.

## Usuário afetado

Administrador da demonstração e lojista sintético que consulta a base ativa.

## Resultado desejado

O administrador edita um rascunho fictício, revisa o diff, confirma o custo,
constrói e testa uma candidata, ativa-a explicitamente e pode retornar. Cada
atendimento captura uma única versão, inclusive durante ativação concorrente.

## Escopo

RF-63–66, CA-41, partes aplicáveis de CA-28/44/45, ADR 0009 e plano incremental
aprovado, sobre a v0.4.0 integrada nos dois repositórios.

## Fora do escopo

Evaluation Agent e propostas automáticas (v0.6), experimentos/gráficos/acesso
público (v0.7), alterações de guardrails, regras financeiras, segredos, papéis
ou fontes oficiais. Não há coleta de novos dados privados, limpeza automática
de coleções existentes, publicação de serviço ou integração Git da v0.5.0.

## Requisitos funcionais

- Listar documentos e origem; editar somente `simulated_internal`. Origem e
  identidade são atribuídas pelo servidor, nunca promovidas pelo conteúdo.
- Rascunho com revisão otimista e diff; fontes `public_official` somente leitura.
- Construir coleção nova por versão, com manifesto de documentos/hashes,
  embedding/modelo/dimensão e resultado de testes. Nunca reconstruir a ativa
  no lugar, nem fazer candidata incompleta substituir a ativa.
- Ativar somente versão pronta, com confirmação da ativa esperada; retornar
  explicitamente a uma anterior íntegra. Registrar ator, momento e evidência.
- Capturar base/índice no início do atendimento, registrar a versão no trace
  e snapshot e concluir execução em andamento nessa mesma base.
- A interface acessa exclusivamente `/v1`, apresenta vazio/carregando/erro e
  só dispara build/teste/ativação/retorno por ação explícita. Reruns são leitura.
- Texto editado continua evidência: não concede ferramenta nem substitui PRaaS.

## Requisitos não funcionais

Compatibilidade HTTP legado/MCP, permissões backend, persistência, concorrência
e isolamento mantidos. Toda chamada paga, incluindo embeddings, deve reservar
antes do envio e liquidar depois na guarda persistente; custo desconhecido
bloqueia. Teto global US$5, acumulado anterior registrado US$0,59283583.

Teto persistente por ledger (aceito pelo responsável em 2026-10-27):
configuração e guardas recusam limite não finito ou acima de US$5. O teto de
cada ledger fica em `<ledger>.limit`, criado uma única vez no primeiro uso,
sem alterar o SQLite; ledger pré-existente sem o arquivo recebe no máximo
US$1. Limite configurado acima do teto gravado é recusado no arranque; elevar
o teto exige edição manual consciente do responsável (máximo US$5). Inclui a
criação de `data/runtime/budget.sqlite3.limit` = 1.00 quando a validação real montar o
ledger com `BUDGET_LIMIT_USD=1.00`.

Testes unitários/de contrato permanecem determinísticos. A validação de aceite
da v0.5 usa provedores reais para os caminhos pagos,
com cenários sintéticos/fontes públicas e custo registrado. Simulação não
fecha requisito de comportamento real. Falhas/limites continuam explícitos.

## Casos de uso

1. Admin altera orientação fictícia, revisa diff e cria candidata sem alterar ativa.
2. Falha no build/teste mantém ativa e informa erro recuperável.
3. Admin ativa candidata pronta; nova conversa usa nova base e trace a identifica.
4. Conversa em execução termina na versão capturada; rollback afeta as próximas.
5. Demo tenta escrever/ativar e recebe403; alteração de fonte oficial é recusada.

## Critérios de aceitação

- [ ] CA-41 demonstrado ponta a ponta na UI: editar, diff, build, teste, ativar e retornar.
- [ ] Oficial imutável, demo sem escrita, revisão obsoleta rejeitada, sem caminho arbitrário.
- [ ] Falha/custo negado não muda ativa e não faz chamada não reservada.
- [ ] Execução concorrente consulta uma única versão identificada; legado/MCP preservados.
- [ ] Navegação/rerun não dispara chamada paga ou nova publicação.
- [ ] Validação real limitada registra configuração efetiva, evidência, custo e pendências.

## Riscos e questões em aberto

Concorrência de ativação e custo de embeddings, tratados por troca atômica do ponteiro e reserva antes de cada lote.
Preservar coleções/ledgers existentes; qualquer remoção exige autorização
específica. Contrato e migração foram aprovados pelo responsável em 2026-10-27 antes da
implementação. A disponibilidade dos provedores é medida
na validação real, não inferida da presença da chave.
