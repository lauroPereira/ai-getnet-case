<!-- Papel: detalhamento executável da v0.3.0, derivado das especificações aprovadas. -->

# Plano: jornadas de negócio da v0.3.0

## Especificação relacionada

[Principal](assistente-multiagente-lojista.md): RF-32 a RF-34, CA-21 a CA-23.
[Complementar](incrementos-pos-nucleo.md): RF-46, UC-23 a UC-25, CA-28 e CA-31.
[Plano por versões](incrementos-pos-nucleo-plano.md) e decisões aceitas 0006 e 0011.

## Decisões técnicas

- Preservar o núcleo e o contrato de `POST /messages`; usar o mesmo domínio pela API e pelo MCP.
- App FastAPI `mocks` separada, acessível somente na rede interna do Compose. Pricing e cobrança usam dados sintéticos independentes; cobrança não é recalculada pela regra de pricing.
- Clientes HTTP com timeout, validação de respostas e erros estruturados. Testes usam transporte ASGI em processo, sem rede ou APIs pagas; a montagem de produção usa HTTP para o serviço separado.
- Comparação em inteiros (centavos), com resultados explícitos: cobrança coerente, condições diferentes, divergência, evidência insuficiente. Aplicabilidade, versão, componentes e parcelas acompanham a regra; nenhuma conta financeira fica a cargo do modelo.
- Bandeiras distinguem solicitação com protocolo, ativação no cadastro e disponibilidade no dispositivo. Cancelamento é consulta de venda; encerramento contratual segue esclarecimento/atendimento humano.

## Componentes afetados

App e fixtures de `mocks`; clientes HTTP; ferramentas e registro; montagem da aplicação; dados e seed; prompts versionados e política programada de avaliação; Compose; testes; README, changelog e evidências.

## Modelo de dados

Proposta sujeita à aprovação explícita antes de implementar: migração reversível 0005 com contexto contratual de pricing, `enablement_requests` e `sale_cancellations`, preservando tabelas e registros anteriores. Fixtures de pricing e cobrança têm armazenamento independente do banco do assistente. Testar subida, descida e preservação do esquema 0004. Não executar migrações sobre o runtime existente do responsável.

## APIs ou interfaces

Adições previstas pela decisão 0011: `POST /pricing/simulations` e `GET /charges/{transaction_id}` no serviço interno. Os schemas tipados devem ser documentados antes de sua integração. A identidade do lojista vem do contexto confiável do backend e o recurso é verificado antes de qualquer retorno.

Ferramentas novas previstas: `simulate_pricing`, `get_fee_breakdown`, `get_enablement_requests` e `get_sale_cancellation_context`; ampliação aditiva de `get_contract_snapshot`. A comparação determinística pode integrar a ferramenta de simulação. Nenhuma ferramenta executa alteração financeira, habilitação ou cancelamento. Não alterar autenticação, guardrails, permissões ou orçamento.

## Estratégia de testes

- Unidade: arredondamento e comparação em centavos, aplicabilidade e ausência de evidência, parcelas e migração reversível.
- Contrato/integração: duas fontes via HTTP em processo, timeout/indisponibilidade/resposta inválida, schemas e isolamento entre lojistas, inclusive MCP.
- Jornada pela API: quatro resultados de preço, pedido de bandeira pendente com protocolo reutilizado, cadastro ativo/dispositivo divergente, cancelamento de venda e encerramento contratual sem ferramentas de venda. Exercitar português e inglês.
- Regressão: `python tools/scripts/lint_and_tests.py --strict`, núcleo e conversas, avaliação programada sem custo, demonstração MCP e configuração do Compose.
- Validação real limitada e Docker: somente após preparar o candidato e obter as autorizações de rede/gasto necessárias. Não substituir evidência real por testes programados nem declarar versão liberada sem comprovação.

## Riscos técnicos

Confundir condições contratuais com divergência; comparar fontes com identificadores ou parcelas diferentes; vazar recursos entre clientes; tratar pendência como falha; confundir venda e contrato. Mitigar com validação tipada, fixtures independentes, comparação determinística e cenários negativos. Retorno pelo código da v0.2.0 e pela migração 0005 → 0004 em ambiente sintético isolado.

## Plano de implementação

21. [Serviço fictício de pricing e cobrança](../tasks/21-servico-mocks-pricing-cobranca.md).
22. [Ferramentas e comparação de preço](../tasks/22-jornada-preco-contestacao.md).
23. [Bandeiras e cancelamento de venda](../tasks/23-bandeiras-e-cancelamento.md).
24. [Regressão e candidato da v0.3.0](../tasks/24-regressao-candidato-v030.md).

História: [jornadas-v030](../historias/jornadas-v030.md). A sessão principal exerce Supervisor. Autorização nesta sessão: três subagentes sequenciais, Developer → Reviewer → QA, todos `gpt-6-luna`, esforço `high`, com contexto novo e parâmetros explícitos. Correções retornam ao mesmo Developer. Commit, push, merge, tag, chamadas pagas e publicação dependem de autorização aplicável.
