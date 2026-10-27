# Tarefa: Catálogo verificado e adaptadores de modelos

## Objetivo

Integrar JEV real e DeepSeek mantendo decisões tipadas, capacidades e custos verificáveis.

## Especificação relacionada

RF-35, RF-47–49, CA-32, CA-33 e CA-37; [plano v0.4.0](../specs/perfis-interface-v040-plano.md).

## Pré-condições

Aprovação específica do plano e da rede para fontes oficiais; nenhuma chamada paga autorizada por esta tarefa.

## Arquivos prováveis

`llm/`, montagem do Router, catálogo versionado, configuração e testes de transportes.

## Passos

1. Verificar documentação oficial, identificadores, parâmetros, capacidades e preços com data/fontes; usar API de modelos apenas se não houver cobrança confirmada.
2. Implementar adaptadores com timeout/saída tipada e guarda existente; JEV somente no Router, sem fallback implícito.
3. Recusar função incompatível ou custo desconhecido antes de invocar o provedor; registrar mecanismo/modelo/versão/tempo/custo.
4. Cobrir sucesso, timeout, contrato inválido, capacidade ausente e orçamento sem rede; identificar lacuna real separadamente.

## Critérios de conclusão

- [ ] Catálogo diferencia identificação via API de capacidade comprovada em documentação.
- [x] JEV e LLM produzem o mesmo RouterDecision validado; erros explícitos sem troca silenciosa.
- [x] Modelos desconhecidos/preço ausente não são selecionáveis; estimativa respeita guarda e faixa peak.
- [x] Testes offline aprovados; execução real aguarda autorização monetária.

## Validação

Fontes oficiais e preços/capacidades datados em [catálogo](../evidence/v040-catalogo-fontes.md); o parâmetro de saída é documentado em [evidência de parâmetros](../evidence/v040-parametros-modelo-fontes.md). Adaptadores e testes offline cobertos por `tests/unit/test_jev_adapter.py`, `tests/unit/test_profile_output_parameters.py` e integração v1. Backend strict r4: 214 testes passaram, incluindo payload de adaptador fake, sem chamada externa. Nenhuma inferência nem `GET /models` autenticado foi enviada: não se comprovou por fonte oficial que o GET é gratuito. Disponibilidade da conta e CA-32 real continuam pendentes.

## Status

Implementada como candidata nos limites sem custo. A identificação via endpoint da conta e validação real do provedor permanecem abertas; Reviewer/QA pendentes.
