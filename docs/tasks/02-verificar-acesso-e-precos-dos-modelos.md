# Tarefa: Verificar acesso e preços dos modelos

## Objetivo

Confirmar que a conta OpenAI acessa os modelos candidatos (agentes, embeddings e busca web), registrar os preços vigentes e verificar a viabilidade do Jev.

## Especificação relacionada

[Especificação](../specs/assistente-multiagente-lojista.md): RNF-02, questão Q4. [Decisão 0005](../architecture/decisions/0005-modelos-openai-e-guarda-de-orcamento.md).

## Pré-condições

- `OPENAI_API_KEY` em `.env` local, fornecida pelo responsável.
- Gasto máximo desta tarefa: US$0,05, dentro da reserva de ingestão e calibração.

## Arquivos prováveis

- `src/merchant_assistant/llm/prices.json` (novo; tabela versionada com fonte e data)
- `docs/evidence/2026-10-acesso-e-precos-dos-modelos.md` (novo)

## Passos

1. Consultar as páginas oficiais de preço da OpenAI, do Jev e da DeepSeek e registrar valores, unidade e data.
2. Listar os modelos disponíveis na conta pela API.
3. Fazer uma chamada mínima com saída estruturada no modelo candidato e uma busca web mínima; registrar tokens e custo.
4. Se um candidato não estiver disponível, propor substituto e registrar a mudança na decisão 0005 enquanto ela estiver como proposta.
5. Verificar acesso e condições de crédito do Jev, sem contratar nem comprar nada.

## Critérios de conclusão

- [x] Modelos confirmados ou substitutos propostos.
- [x] Tabela de preços com fonte e data.
- [x] Gasto observado registrado e abaixo de US$0,05.
- [x] Situação do Jev registrada.

## Validação

Chamadas mínimas reais em 2026-10-26 (saída estruturada, busca web, embeddings) e listagem de modelos dos três provedores. Gasto estimado US$0,0209. Detalhes em [docs/evidence/2026-10-26-acesso-e-precos-dos-modelos.md](../evidence/2026-10-26-acesso-e-precos-dos-modelos.md).

## Status

```text
concluída
```
