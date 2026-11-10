# Registros de decisão

Índice das ADRs do projeto. Regras de uso em [../README.md](../README.md); modelo em [decision-record.md](../../templates/decision-record.md).

| ADR | Decisão |
| --- | --- |
| [0001](0001-python-fastapi-pydantic.md) | Python, FastAPI e Pydantic |
| [0002](0002-orquestracao-langgraph-estado-tipado.md) | Orquestração com LangGraph e estado tipado |
| [0003](0003-rag-qdrant-e-copia-versionada-do-conteudo.md) | RAG com Qdrant e cópia versionada do conteúdo coletado |
| [0004](0004-dados-sinteticos-sqlite-e-ferramentas-de-dominio.md) | Dados sintéticos em SQLite e ferramentas como funções de domínio |
| [0005](0005-modelos-openai-e-guarda-de-orcamento.md) | OpenAI como baseline e guarda de orçamento persistente |
| [0006](0006-versionamento-changelog-e-migracoes.md) | Versionamento SemVer, changelog e migrações reversíveis |
| [0007](0007-interface-streamlit-separada-via-api.md) | Interface Streamlit em projeto separado, consumindo só a API |
| [0008](0008-registro-versionado-de-configuracao.md) | Registro versionado de configuração com snapshot por execução |
| [0009](0009-versoes-da-base-de-conhecimento.md) | Versões da base de conhecimento com coleção por versão |
| [0010](0010-servidor-mcp-sobre-o-dominio.md) | Servidor MCP sobre a camada de domínio |
| [0011](0011-servicos-ficticios-de-pricing-e-cobranca.md) | Serviços fictícios de pricing e cobrança como app HTTP separada |
| [0012](0012-exposicao-publica-da-demonstracao.md) | Exposição pública da demonstração |
| [0013](0013-sessoes-api-e-perfis-v040.md) | Sessões opacas e escopo da API da interface |
| [0014](0014-ciclo-kb-v050.md) | Ciclo persistente da base e reserva de build v0.5 |
| [0015](0015-recorte-final-v060.md) | Recorte final: v0.6.0 única, sem Evaluation Agent nem propostas |
| [0016](0016-reabertura-roadmap-producao.md) | Reabertura do escopo: roadmap de produção |
| [0017](0017-identidade-principal-escopos.md) | Identidade: credencial → JWT → principal → escopos → lojista |
| [0018](0018-interrupcao-retomada-webhooks.md) | HITL: interrupção do grafo, fila idempotente e ticketing por webhooks assinados |
| [0019](0019-replanejamento.md) | Replanejamento: um nó que observa o resultado de cada especialista e decide o próximo passo |
| [0020](0020-retrieval-hibrido-holdout.md) | Retrieval híbrido (BM25 + denso com RRF), reranker opcional e holdout de retrieval lacrado |
| [0021](0021-juiz-modelo-e-regua.md) | Juiz da avaliação: modelo padrão por experimento pré-registrado, régua literal como piso |
| [0022](0022-rubrica-v4-operacao-retomavel.md) | Rubrica `judge.v4` medida e não promovida; comparação retomável; métricas e alertas versionados |
| [0023](0023-juiz-por-afirmacao-evidencia-web.md) | Promover `judge.v5` e `RERANK` após medir o controle de profundidade |
| [0024](0024-desenho-da-orquestracao.md) | Desenho da orquestração: grafo com replanejamento por regras, não supervisor com especialistas como ferramentas |
| [0025](0025-identidade-e-operacao.md) | Identidade e operação: login por redirecionamento com refresh rotativo, emissor OIDC externo, lease entre workers, reenvio de webhook, operador no Telegram e spans OTLP |
| [0026](0026-tunel-com-login-por-redirecionamento.md) | Túnel de demonstração numa única origem com a interface e só a rota de autorização da API (emenda à 0012) |
