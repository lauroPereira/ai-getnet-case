# 0005. OpenAI como baseline e guarda de orçamento persistente

## Título

Usar OpenAI como provedor baseline dos agentes, embeddings e busca web, com uma guarda de orçamento persistente e o Jev como mecanismo opcional do Router.

## Status

```text
aceita
```

Aceita pelo responsável em 2026-10-26. Os identificadores de modelo são configuração: a tarefa 02 confirma disponibilidade e preços sem alterar esta decisão.

## Contexto

O responsável tem créditos em OpenAI e DeepSeek e um teto total de US$5. O desafio pede busca web para perguntas gerais. O avaliador precisa subir o sistema com o mínimo de credenciais. O seletor LLM/Jev no Router foi pedido pelo responsável para demonstração e comparação, sem alterar o restante do fluxo.

## Decisão

- Interface única de modelo com três implementações: cliente OpenAI (Responses API, saídas estruturadas, busca web), modelo programado para testes e, na fatia 4, adaptador Jev para a decisão do Router.
- Configuração candidata: `gpt-6-luna` para os quatro agentes, `text-embedding-3-small` para embeddings e a busca web da OpenAI acionada pelo Knowledge Agent. Modelos trocam por configuração.
- Guarda de orçamento com registro persistente em `data/runtime/`, tabela de preços versionada, reserva antes de cada chamada paga, limites por requisição e bloqueio quando preço ou consumo forem desconhecidos.
- DeepSeek fica como experimento opcional, sem fallback automático pago.

## Alternativas consideradas

- **Vários provedores desde o início:** mais adaptadores e testes sem ganho para os requisitos.
- **Modelos locais:** sem custo por chamada, mas imagem pesada, qualidade incerta em português e sem busca web.
- **Contabilizar custo só depois da chamada:** não impede estourar o teto.

## Consequências

O avaliador precisa apenas de `OPENAI_API_KEY`. O custo é controlado antes de gastar. A comparação Jev/LLM depende de acesso viável dentro do orçamento e não bloqueia o núcleo. O controle local não enxerga o uso das mesmas contas por outros projetos.

## Data

2026-10-26
