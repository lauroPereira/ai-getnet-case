# Passagem do Developer — jornadas v0.3.0

- Papel e responsável: Developer; execução delegada pelo Supervisor.
- Objetivo e critérios: implementar tarefas 21–23 e preparar localmente a tarefa 24, preservando os contratos existentes e a história de uso.
- Escopo: serviço interno HTTP de pricing e cobrança sintéticos, comparação de preços, consulta de habilitação/cancelamento, migração reversível 0005, ferramentas API/domínio/MCP, prompts versionados, cenários programados, Compose e documentação de contrato.
- Estado: implementação apta para revisão independente; build/smoke Docker final, Reviewer e QA pendentes.
- Branch e PR: `codex/v0.3.0-jornadas`; sem PR.
- Base e versão final: HEAD de base `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`; candidato local sem commit. A correção de empacotamento das fixtures e da regressão NOEV integra o candidato congelado para build r2. O Supervisor deverá fixar os hashes dos insumos do build antes de emitir pareceres.
- Independência: não se aplica ao papel Developer; Reviewer e QA ainda não executados neste candidato.

## Evidência observada

- `.venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`, com `PYTHONUNBUFFERED=1` e `PYTEST_ADDOPTS=--basetemp=.pytest_cache/v030-strict-20261027c`: **164 testes passaram em 91,09 s**; Ruff, verificação de estrutura e validação de skills passaram. Executado localmente com permissão ampliada para permitir os testes ASGI/HTTP sem trocar o transporte. Nenhuma chamada externa ou paga foi feita.
- `COMPOSE_DISABLE_ENV_FILE=1 docker compose config --quiet`: código de saída 0. A validação não carregou `.env` e não executou build.
- Relatório programado: [avaliação final scripted](2026-10-27-avaliacao-programada-v030-final.md) e [dados JSON](2026-10-27-avaliacao-programada-v030-final.json). 40 casos; 25 aprovados (0,625), custo US$ 0. Rota, status, ferramentas, valores, fontes e regras de proibição: 1,0. Conteúdo: 0,625. Os 13 cenários da v0.3.0 e as quatro conversas multi-turno passaram. Os 15 casos não aprovados são legados e falharam somente em `content_ok` com a política scripted; isso não comprova qualidade de modelo real.
- Cobertura direcionada da implementação inclui quatro estados de comparação de preço, consistência de cliente/transação/moeda/condições/soma de componentes e parcelas, bloqueio de contexto incompatível, seleção de venda sem IDs no schema, duas fontes HTTP independentes, consulta aditiva ao contrato, migração sintética 0004→0005→0004, habilitação pendente/ativa com divergência do dispositivo, cancelamento informativo, encerramento contratual sem ferramenta de venda e paridade MCP. Estes caminhos também fazem parte da suíte estrita aprovada.
- R1 do Docker identificou que fixtures eram procuradas relativamente ao pacote instalado. O candidato passou a resolver fixtures por `MOCK_SERVICES_DIR` ou `DATA_DIR`, com fallback para a árvore de desenvolvimento; o Compose monta `/app/data/mock-services`. A rodada r1 permanece exploratória em [v030-docker-r1.json](v030-docker-r1.json), não é aceite. Build e smoke r2 pelo Supervisor estão pendentes.
- As tarefas 21–23 registram implementação e provas disponíveis; a executabilidade final no contêiner da tarefa 21 e a revisão/QA da tarefa 24 permanecem pendentes.

## Critérios e limitações

- Tarefas 21–23: código, testes locais, migração sintética e avaliação scripted comprovados conforme status e validação nos arquivos de tarefa.
- Não verificados: build/smoke final em contêiner após correção de empacotamento; avaliação com modelo real; revisão independente; QA pela história; decisão humana de aceite/liberação.
- Avaliação scripted não representa aceite real e suas falhas de conteúdo legado não foram removidas nem tiveram a rubrica alterada.
- Nenhum commit, push, merge, tag, publicação, acesso a API paga ou chamada de rede externa foi realizado pelo Developer.

## Próxima ação

Supervisor: executar build/smoke Docker r2 sem mudar os arquivos congelados e registrar os hashes exatos. Em seguida, encaminhar este candidato fixado a Reviewer independente e, após revisão apta, a QA pela história `docs/historias/jornadas-v030.md`. Qualquer correção de produto exige novo candidato e nova validação.

- Decisão humana pendente: aceite da entrega/liberação após build, revisão e QA; evidência offline não equivale a liberação.
