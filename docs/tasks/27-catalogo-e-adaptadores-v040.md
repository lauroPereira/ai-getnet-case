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

- [x] Catálogo registra, por modelo, a capacidade comprovada na documentação oficial datada.
- [x] JEV e LLM produzem o mesmo RouterDecision validado; erros explícitos sem troca silenciosa.
- [x] Modelos desconhecidos/preço ausente não são selecionáveis; estimativa respeita guarda e faixa peak.
- [x] Testes offline aprovados; execução real aguarda autorização monetária.

## Resultado

Adaptadores JEV e DeepSeek com saída tipada, catálogo datado com fontes oficiais e recusa de modelo sem preço ou capacidade antes do provedor. Suíte estrita do backend: 214 testes, sem chamada externa; a chamada real ao JEV (CA-32) entrou na v0.5.0. Evidência: [catálogo](../evidence/v040-catalogo-fontes.md), [parâmetros](../evidence/v040-parametros-modelo-fontes.md) e [resultado da v0.4.0](../evidence/v040-resultado.md).

## Status

```text
concluída (v0.4.0)
```
