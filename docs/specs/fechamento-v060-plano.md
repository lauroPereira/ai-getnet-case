# Plano: simplificação, demonstração e fechamento v0.6.0

## Especificação relacionada

[Spec v0.6.0](fechamento-v060.md), [especificação complementar 0.3](incrementos-pos-nucleo.md#recorte-final-v060), [história v1](../historias/fechamento-v060.md) e [ADR 0015](../architecture/decisions/0015-recorte-final-v060.md).

**Estado: recorte aprovado pelo responsável em 2026-10-27**, com contratos `/v1` aditivos, migração 0008, limite por sessão demo, API do compose só local, três subagentes Claude Opus 5.5 com esforço high e teto de campanha US$0,50. Base: mains com a v0.5.0 integrada (backend `c3a9027b7c218f560345576770a646d4ec2bc098`, web `4192169afc8b37f150d88fdf16e3529a0fd33b90`, tags `v0.5.0`); branches `codex/v0.6.0-fechamento`.

## Decisões técnicas

1. **Catálogo de cenários.** Arquivo curto versionado em `data/scenarios/` (10 cenários na entrega; o 6–8 inicial foi ampliado na revisão r1 para cobrir habilitação e cancelamento) derivado dos casos rotulados existentes, incluindo o cenário de D e ao menos um de cada jornada essencial. Entra na imagem Docker. `GET /v1/scenarios` lista; `POST /v1/messages` aceita `scenario_id` opcional, validado contra o catálogo e gravado no snapshot da execução.
2. **Verificações determinísticas.** Reutilizar `evaluation/runner._checks` (ajuste mínimo para receber resposta e trace persistidos) e os rótulos do cenário. Sem rótulo, só as verificações independentes dele; as demais ficam "não avaliado". Falhas críticas: `grounded_ok` falso, `forbidden_ok` falso, erro de isolamento e recusa quando o rótulo espera atendimento.
3. **Avaliação por modelo sob demanda.** Reutilizar `JudgeScore` e o prompt `judge` versionado; avaliador com configuração fixa (provedor, modelo e parâmetros vindos da configuração do backend), registrada em cada avaliação, independente do perfil avaliado. Estimativa pelo preço do catálogo, confirmação, reserva e liquidação na guarda persistente. Mesma configuração e execução devolve o registro existente, salvo `repeat=true`. O campo `evaluation` dos perfis permanece no esquema e não é usado.
4. **Comparação.** Execução fora da requisição, em thread do próprio processo da API (sem fila nem serviço novo), com estado persistido e atualização por GET explícito. Limites: 2–3 perfis, até 3 cenários, até 2 repetições, no máximo 18 células. Uma versão da base capturada para toda a comparação. Efeitos de domínio (conversas, casos, tentativas, encaminhamentos) numa cópia temporária do banco sintético; traces e snapshots no armazenamento normal, marcados com `purpose=comparison` e o ID da comparação, para abrir as execuções. Reuso de execuções compatíveis rotuladas como gravadas.
5. **Gráficos.** No Streamlit, com seleção que só relê dados gravados: custo × qualidade por perfil (duração média e tamanho da amostra no rótulo) e custo por agente/modelo com seleção que abre as execuções. Tabela de células. Router-only em seção própria.
6. **Efeito da documentação.** Texto da V2 do documento fictício de dispositivos preparado na tarefa 57, com a diferença esperada registrada antes; validação offline com política programada e embeddings falsos; aceite real pelo QA. O trace já registra documentos recuperados (`hits`), `chunk_id` das citações, versão da base e ferramentas.
7. **Interface.** Três abas: Atendimento, Resultados, Administração (só quando a sessão é `admin`). Reaproveitar componentes atuais de conversa, comparação de Routers, inspeção e administração de perfis e base. Cliente e snapshot OpenAPI regenerados.
8. **Estabilização.** Itens da [triagem](fechamento-v060.md#e-estabilização), sem redesenhar autenticação, orçamento, migrações ou versionamento.
9. **Exposição.** Compose publica a API em `127.0.0.1:8000`; Streamlit roda nativo no projeto web e é o único serviço com endereço externo (`--server.address 0.0.0.0`); HTTPS com certificado próprio quando possível; limite configurável de mensagens por sessão demo, recusado no backend com erro claro. Redirecionamento de porta e regra de firewall são ações do responsável.

## Componentes afetados

Backend: `api/v1.py`, `evaluation/runner.py` (reuso), `orchestration/graph.py` (cenário e `purpose`), `data/migrations.py` (0008), `data/scenarios/`, `orchestration/budget.py`, `rag/kb.py`, `cli.py`, `config.py`, `docker-compose.yml`, testes, README e CHANGELOG. Web: `app.py`, `src/getnet_web/api.py`, cliente gerado, snapshot OpenAPI, fixtures, testes, README. Não alterar AGENTS.md, CLAUDE.md, skills, autenticação, regras financeiras, guardrails ou o contrato legado.

## Modelo de dados

Migração 0008 reversível e aditiva, testada 0007 → 0008 → 0007 em SQLite sintético isolado:

- `run_evaluations`: ID, `request_id`, principal, método (`deterministic`/`model`), rubrica e versão, configuração do avaliador, resultado por critério, evidências usadas, falhas críticas, custo, estado (`completed`/`failed`), criação.
- `comparisons`: ID, principal, estado (`running`/`completed`/`failed`/`partial`), configuração (perfis e versões/digests, cenários, repetições, mecanismo, versão da base, prompts, avaliador), células (cenário, perfil, repetição, execução, origem real ou gravada, resultado, duração, custo e custo por agente), falhas, estimativa, custo, criação e atualização.
- Contador de mensagens por sessão demo: coluna aditiva em `api_sessions` ou tabela mínima, o que for mais simples e reversível.

Nenhuma outra entidade de experimento. Dados, ledgers e coleções existentes não mudam.

## APIs ou interfaces

Todas exigem token; papéis verificados no backend; erros estruturados existentes (`401`, `403`, `404`, `409`, `422`, `429`).

| Rota | Papel | Comportamento |
| --- | --- | --- |
| `GET /v1/scenarios` | demo, admin | Lista cenários: ID, título, idioma, mensagem e verificações aplicáveis |
| `POST /v1/messages` + `scenario_id?` | demo, admin | Igual ao atual; cenário validado e gravado no snapshot; demo sujeito ao limite por sessão (`429` claro) |
| `GET /v1/runs/{id}` | dono | Igual ao atual, acrescido de verificações determinísticas aplicáveis e avaliações registradas |
| `POST /v1/runs/{id}/evaluations/estimate` | dono | Estimativa, método, rubrica e avaliador; sem chamada paga |
| `POST /v1/runs/{id}/evaluations` | dono | Exige estimativa confirmada; reserva, avalia a resposta persistida e grava; repetição só com `repeat=true` |
| `POST /v1/comparisons/estimate` | demo, admin | Células, reusos, novas execuções, fatores fixos, estimativa; sem chamada paga |
| `POST /v1/comparisons` | demo, admin | Exige estimativa confirmada; cria e inicia; `202` com ID |
| `GET /v1/comparisons/{id}` | dono | Estado, configuração, células, falhas e agregados para os gráficos |

Uma listagem `GET /v1/runs` só entra se a área Resultados precisar de execuções fora da sessão atual, e depende de aprovação antes da implementação.

## Estratégia de testes

- Unidade/contrato: catálogo e validação de `scenario_id`; verificações sobre resposta persistida; estimativa, reserva negada, custo desconhecido e idempotência da avaliação; migração 0008 sobe e desce; limite por sessão demo; comparação com limites, reuso, falha parcial e isolamento (contagens do domínio original inalteradas); itens de E com regressão que falha antes e passa depois.
- Integração sem custo: comparação e avaliação com modelo programado; D com política programada e embeddings falsos mostrando a mudança de ferramenta entre V1 e V2 e o retorno.
- Web (`AppTest`): três áreas, Administração ausente para demo, gráficos e tabela a partir de fixtures, nenhum POST em rerun, troca de aba ou seleção de gráfico, recuperação por GET, erros com ação de recuperação.
- Validação estrita backend (`python tools/scripts/lint_and_tests.py --strict`) e web com código 0.
- QA real conforme a história, no candidato fixado.

## QA real, orçamento e Docker

- Antes da rodada, o Supervisor reconcilia os ledgers em modo somente leitura. Estado em 2026-10-27: primário 885 entradas, US$0,34852844, zero reservas, teto persistente US$1; acumulado do projeto US$0,59837466.
- Campanha `v060-qa`: `FixedBudgetGuard` com teto fixo US$0,50 em `.pytest_cache/v060-qa-control/budget.sqlite3`, combinada com o ledger primário, montada uma vez pelo QA. Correções não renovam.
- Estimativa da rodada ≈ US$0,15: regressão real (40 casos + 4 conversas) ≈ 0,07; comparação ≈ 0,03; D ≈ 0,02; chat, toggle, Docker e acesso externo ≈ 0,02; avaliações por modelo ≈ 0,01.
- Docker: o contêiner usa o ledger do seu volume. O QA lê esse ledger antes e depois, soma o delta ao total da campanha e mantém o agregado abaixo de US$0,50; a rodada no Docker é um smoke pequeno.
- Developer e Reviewer não fazem chamadas pagas. Testes automatizados nunca chamam APIs pagas.

## Delegação aprovada

No máximo três subagentes, em sequência e com contexto novo: Developer, Reviewer e QA, **Claude Opus 5.5 com esforço high** (substituto de `gpt-6-luna`, indisponível nesta sessão, escolhido pelo responsável em 2026-10-27). Sem delegação aninhada nem agentes adicionais. Correções voltam ao mesmo Developer; revalidação pelo mesmo Reviewer e QA, cobrindo o delta e as regressões pertinentes. Reviewer não recebe conclusões do implementador. O Supervisor fixa o candidato por hashes antes de revisão e QA e registra o resultado central em `docs/evidence/v060-resultado.md`, com passagens únicas por papel (rodadas acrescentadas no mesmo arquivo).

## Riscos técnicos e retorno

Retorno de código pela tag `v0.5.0`; dados pela migração 0008 → 0007 em banco sintético. Comparação interrompida fica `partial`, com gastos e falhas registrados. Thread de comparação perdida em reinício fica `failed` na próxima leitura. Disco: monitorar antes de builds; nenhuma limpeza autorizada por este plano.

## Plano de implementação

54. [Estabilização e contratos](../tasks/54-estabilizacao-v060.md)
55. [Atendimento, Resultados e avaliação sob demanda](../tasks/55-atendimento-resultados-avaliacao-v060.md)
56. [Comparação de perfis](../tasks/56-comparacao-perfis-v060.md)
57. [Efeito da documentação no comportamento](../tasks/57-efeito-documentacao-v060.md)
58. [Execução, compartilhamento e documentação final](../tasks/58-execucao-compartilhamento-v060.md)
59. [Validação e aceite da v0.6.0](../tasks/59-validacao-aceite-v060.md)

Ordem: 54 primeiro (orçamento e integridade); 55 antes de 56 (cenários e avaliação alimentam a comparação); 57 depende de 55 (catálogo e Resultados); 58 por último no Developer; 59 com Reviewer e QA.

## Aprovação registrada e limites

O responsável aprovou em 2026-10-27 o recorte, os contratos e dados acima, a delegação e o teto de campanha. Commits e push da v0.6.0, PRs, merges, tag e abertura de porta continuam dependendo de autorização própria no fechamento. Sem limpeza de dados, remoção de coleções ou mudança de credenciais.
