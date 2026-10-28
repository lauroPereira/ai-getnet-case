<!-- Papel: plano técnico dos incrementos pós-núcleo, por versão, derivado da especificação complementar. -->

# Plano: incrementos pós-núcleo

Versão 0.3 — 2026-10-27 — **recorte final aprovado pelo responsável em 2026-10-27**: as linhas 0.6.0 e 0.7.0 antigas foram substituídas por uma única v0.6.0 ([plano detalhado](fechamento-v060-plano.md), [ADR 0015](../architecture/decisions/0015-recorte-final-v060.md)). A 0.2 (2026-10-26) aprovou a sequência até a v0.7.0; as decisões 0006 a 0012 foram aceitas depois.

## Especificação relacionada

[docs/specs/incrementos-pos-nucleo.md](incrementos-pos-nucleo.md), que complementa [docs/specs/assistente-multiagente-lojista.md](assistente-multiagente-lojista.md).

## Decisões técnicas

| Tema | Proposta | Registro |
| --- | --- | --- |
| Versões | SemVer, tag por versão, `CHANGELOG.md`, migrações numeradas e reversíveis | [0006](../architecture/decisions/0006-versionamento-changelog-e-migracoes.md) |
| Interface | Streamlit em projeto separado, só via API `/v1`, papéis demo e admin verificados no backend | [0007](../architecture/decisions/0007-interface-streamlit-separada-via-api.md) |
| Configuração | Perfis, prompts e rubricas como versões imutáveis com ativação explícita; snapshot congelado por execução | [0008](../architecture/decisions/0008-registro-versionado-de-configuracao.md) |
| Base de conhecimento | Uma coleção Qdrant por versão e ponteiro para a ativa; build → teste → ativação → retorno | [0009](../architecture/decisions/0009-versoes-da-base-de-conhecimento.md) |
| MCP | SDK oficial `mcp` (2.x), transporte stdio, sobre a mesma camada de domínio | [0010](../architecture/decisions/0010-servidor-mcp-sobre-o-dominio.md) |
| Serviços fictícios | PRaaS e cobrança como app HTTP separada no compose, consumida por clientes com timeout | [0011](../architecture/decisions/0011-servicos-ficticios-de-pricing-e-cobranca.md) |
| Exposição pública | Só a interface exposta, autenticação, HTTPS quando possível, limites por sessão e sublimite de orçamento | [0012](../architecture/decisions/0012-exposicao-publica-da-demonstracao.md) |
| ~~Avaliação por etapa~~ | ~~Registro determinístico por execução + Evaluation Agent assíncrono, rubricas versionadas~~ — substituída na 0.3 | — |
| Recorte final | Sem Evaluation Agent nem propostas; avaliação sob demanda com verificações e avaliador existentes; comparação pequena; persistência mínima (migração 0008) | [0015](../architecture/decisions/0015-recorte-final-v060.md) |

## Componentes por versão

| Versão | Backend (`ai-getnet-case`) | Interface (`ai-getnet-case-web`) |
| --- | --- | --- |
| 0.2.0 | Migrações; conversas e mensagens; estado do caso; tentativas; ciclo técnico; servidor MCP e cliente de demonstração | — |
| 0.3.0 | App `mocks` (PRaaS e cobrança); `simulate_pricing`, `get_fee_breakdown`, `get_contract_snapshot` ampliado; comparador em centavos; `get_enablement_requests`; `get_sale_cancellation_context` | — |
| 0.4.0 | Adaptador JEV; adaptador DeepSeek; catálogo de modelos e capacidades verificado; perfis versionados; API `/v1` com autenticação; comparação de Routers | Repositório próprio criado a partir do ai-dev-template; chat com cenários e estado; seleção de perfil; toggle LLM/JEV; inspeção de execuções; modo com respostas simuladas |
| 0.5.0 | Versões da base: documentos, rascunhos, diff, build de índice candidato, teste, ativação e retorno | Lista e editor de documentos; acompanhamento do build; ativação e retorno |
| ~~0.6.0 / 0.7.0~~ | ~~Evaluation Agent, propostas, experimentos e quatro gráficos~~ — substituídos na 0.3 | — |
| 0.6.0 | Catálogo curto de cenários; avaliação sob demanda de execução persistida; comparação pequena isolada; estabilização (tarefa 46 e pendências); limite por sessão demo; API do compose só local | Três áreas (Atendimento, Resultados, Administração); avaliação sob demanda; dois gráficos e tabela; guia de execução e compartilhamento |

## Modelo de dados

Migrações numeradas em `src/merchant_assistant/data/migrations/`, com versão do esquema registrada.

| Versão | Tabelas novas ou alteradas |
| --- | --- |
| 0.2.0 | `schema_version`; `conversations` (dono, estado, topic, criada/atualizada); `messages` (papel, texto mascarado, tokens); `case_attempts` (orientação, resultado, evidência); `prefix_cache` (histórico e healthcheck com validade) |
| 0.3.0 | No serviço `mocks`: `pricing_rules`, `pricing_contexts`, `charges`, `charge_installments`; no backend: `enablement_requests`, `sale_cancellations` |
| 0.4.0 | `profiles` e `profile_versions` (agente → provedor, modelo, parâmetros); `api_principals` (demo/admin); `router_comparisons` |
| 0.5.0 | `kb_documents`, `kb_drafts`, `kb_versions` (estado: building, testing, ready, active, retired; coleção; manifesto) |
| ~~0.6.0 / 0.7.0~~ | ~~`runs`, `run_evidence`, `evaluations`, `proposals`, `activations`, `experiments`, `experiment_runs`, `demo_sessions`~~ — substituídas na 0.3 |
| 0.6.0 | Migração 0008 reversível: `run_evaluations` (método, rubrica, evidências, avaliador, custo) e `comparisons` (configuração, versões, repetições, falhas e execuções); contador de mensagens por sessão demo, se não couber em tabela existente |

## APIs ou interfaces

`POST /messages` não muda de contrato; os campos novos são opcionais (RNF-09).

| Versão | Interface |
| --- | --- |
| 0.2.0 | `POST /messages` com `conversation_id` passa a continuar a conversa (dono verificado); `resolution` ganha evidência; `GET /v1/conversations/{id}` (admin) |
| 0.3.0 | Serviço `mocks`: `POST /pricing/simulations`, `GET /charges/{transaction_id}` (rede interna do compose) |
| 0.4.0 | `POST /v1/sessions` (token demo ou admin); `GET /v1/catalog/models`; `GET/POST /v1/profiles`, `POST /v1/profiles/{id}/publish`; `POST /v1/messages` com `profile` e `router_mechanism`; `POST /v1/router/compare`; `GET /v1/runs/{id}` |
| 0.5.0 | `GET /v1/kb/documents`; `PUT /v1/kb/drafts/{doc}`; `GET /v1/kb/drafts/{doc}/diff`; `POST /v1/kb/versions` (build); `POST /v1/kb/versions/{id}/test`, `/activate`, `/rollback` |
| ~~0.6.0 / 0.7.0~~ | ~~`/v1/evaluations`, `/v1/proposals/*`, `/v1/experiments/*` e agregações~~ — substituídos na 0.3 |
| 0.6.0 | `GET /v1/scenarios`; `scenario_id` opcional em `POST /v1/messages`; `POST /v1/runs/{id}/evaluations/estimate`, `POST /v1/runs/{id}/evaluations`; `POST /v1/comparisons/estimate`, `POST /v1/comparisons`, `GET /v1/comparisons/{id}` |

Toda rota `/v1` exige token; as de escrita administrativa exigem papel `admin`, verificado no backend.

## Estratégia de testes

| Nível | Novo em | Verificação |
| --- | --- | --- |
| Unidade | 0.2.0+ | Migrações sobem e descem; máquina de estados do caso; comparador de centavos; validação de capacidades; congelamento do perfil; estados da versão da base |
| Contrato | 0.3.0+ | OpenAPI do serviço `mocks` e da API `/v1`; schemas MCP iguais aos da camada de domínio |
| Integração sem custo | todas | Conversas multi-turno com modelo programado; MCP com cliente em memória; JEV simulado (sucesso, timeout, decisão inválida); experimento com modelo programado não cria casos; editor → índice candidato com embedder lexical |
| Interface | 0.4.0+ | Testes do Streamlit (`AppTest`) contra respostas simuladas; nenhuma chamada paga em reexecução |
| Real limitada | cada versão | Rodada de regressão do núcleo (27 casos) e dos cenários novos, com custo registrado |
| Externa | 0.6.0 (era 0.7.0) | Acesso pelo IP público a partir de outra rede |

## Riscos técnicos

| Risco | Mitigação ou retorno |
| --- | --- |
| Migração quebrar dados locais | Migrações reversíveis; `docker compose down -v` recria o ambiente sintético |
| Estado da conversa crescer demais | Histórico limitado por tokens; resumo determinístico das tentativas |
| JEV com contrato diferente do LLM | Adaptador traduz a resposta do JEV (rótulos e confiança) para `RouterDecision`; validação pelo mesmo código |
| Streamlit disparar chamadas a cada rerun | Toda chamada paga só por botão explícito; cache dos resultados gravados |
| Índice candidato ocupar o Qdrant | Manter só ativa, candidata e anterior; remover as demais |
| Exposição externa | Revisão de segurança antes de abrir a porta; desligar ao fim da janela de demonstração |

## Plano de implementação

Cada versão termina com regressão do núcleo, changelog, instruções de retorno e tag autorizada. As tarefas da v0.2.0 estão detalhadas; as das versões seguintes serão escritas no início de cada uma.

**v0.2.0 — Versionamento, memória, acompanhamento e MCP**

15. [Referência da v0.1.0, changelog e migrações](../tasks/15-referencia-v010-changelog-e-migracoes.md)
16. [Conversas com dono e histórico curto](../tasks/16-conversas-e-historico-curto.md)
17. [Estado do atendimento e evidência de resolução](../tasks/17-estado-e-evidencia-de-resolucao.md)
18. [Acompanhamento técnico em dois ciclos](../tasks/18-acompanhamento-tecnico-dois-ciclos.md)
19. [Servidor MCP e demonstração](../tasks/19-servidor-mcp-e-demonstracao.md)
20. [Regressão e liberação da v0.2.0](../tasks/20-regressao-e-liberacao-v020.md)

**v0.3.0 — Jornadas de negócio:** serviço `mocks`, preço e contestação com os quatro comportamentos, habilitação de bandeiras, cancelamento × encerramento. Detalhamento no [plano da v0.3.0](jornadas-v030-plano.md), tarefas 21 a 24 e [história de uso](../historias/jornadas-v030.md).

**v0.4.0 — JEV, modelos por agente e interface inicial:** [plano detalhado proposto](perfis-interface-v040-plano.md), tarefas 27–32, contratos/sessões e base web apresentados antes da aprovação específica. Adaptador JEV real, adaptador DeepSeek (preços e capacidades verificados na documentação oficial antes do uso), catálogo de capacidades, perfis versionados, API `/v1` com papéis, projeto `ai-getnet-case-web` preparado com o ai-dev-template, Streamlit com chat, perfis, toggle e inspeção. A configuração pública do roteador permanece ação do responsável.

**v0.5.0 — Base editável e versões:** [plano](base-versionada-v050-plano.md), tarefas 39–53; integrada e com tag `v0.5.0`.

~~**v0.6.0 — Avaliação por etapa e melhoria supervisionada**~~ e ~~**v0.7.0 — Experimentos, gráficos e compartilhamento**~~: substituídas na 0.3.

**v0.6.0 — Simplificação, demonstração e fechamento:** [plano detalhado](fechamento-v060-plano.md), tarefas 54–59 e [história](../historias/fechamento-v060.md). Última versão com expansão funcional do case.

Dependências: 0.2.0 antes de tudo (migrações e conversas); 0.4.0 depende de 0.2.0 (estado exibido na interface); 0.6.0 depende de 0.4.0 (perfis) e 0.5.0 (versões da base). A 0.3.0 pôde ser feita em paralelo à 0.4.0.
