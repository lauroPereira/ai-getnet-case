# Tarefa: Regressões encontradas na validação real da v0.3.0

## Objetivo

Corrigir falhas observadas com o modelo real e tornar as verificações de conteúdo das novas jornadas compatíveis com respostas naturais, mantendo critérios e proteções.

## Especificação relacionada

RF-08, RF-15, RF-16, RF-32 e RF-46; CA-21, CA-28 e CA-31. Complementa a tarefa 24. Evidência original preservada em [v030-real-r1.json](../evidence/v030-real-r1.json), candidato de origem r1.

## Pré-condições

Rodada real autorizada com teto adicional persistente de US$0,15. Correção P2 de isolamento já implementada pelo Developer, aguardando revisão do candidato final.

## Arquivos prováveis

Prompts novos versionados, ferramentas de pricing, testes financeiros/integração, cenários novos de avaliação e evidências. Não alterar guardrails, permissões ou orçamento.

## Passos

1. **PT08:** sem período explícito, o modelo consultou autorizações somente em `today`, não encontrou a negativa de R$230 disponível no histórico recente e pediu um código que podia consultar. Esclarecer o uso do histórico recente e o respeito a períodos explícitos.
2. **Divergência em EN/PT:** pricing devolve valores brutos/líquidos em campos `*_minor`; a resposta os cita, mas o guardrail existente não os reconhece como os fatos monetários normalizados das outras ferramentas. A resposta final reparada pode perder a diferença de R$0,75. Normalizar fatos financeiros retornados pelas fontes usando o padrão existente de dinheiro; não flexibilizar o guardrail nem transferir contas financeiras ao modelo. Testar fato válido e valor sem evidência.
3. **V030-PT-PRICE-INSUFFICIENT:** a mensagem fornece crédito em duas parcelas, mas o Router pediu esclarecimento antes de consultar a venda identificável por filtros. Ajustar a orientação para consulta com filtros, preservando perguntas gerais de taxas na rota de conhecimento e ambiguidade real como esclarecimento.
4. **Verificação de conteúdo:** cinco respostas factualmente corretas falharam por exigir expressões exatas como `conditions differ`, `valores coerentes` ou `status do cancelamento da venda`. Ampliar somente as alternativas semânticas justificadas dos cenários novos; preservar rotas, status, ferramentas, valores, fontes, violações e os critérios do produto. Acrescentar negativos pertinentes para não aceitar afirmação contraditória. Não editar o relatório original nem alterar o holdout para ocultar defeito.
5. Registrar diffs e evidências, fixar novo candidato, passar por nova revisão independente e revalidar o escopo afetado com modelo real dentro do mesmo teto persistente.

## Critérios de conclusão

- [x] Consulta sem período usa evidência recente disponível; período explícito permanece respeitado.
- [x] Fatos monetários de pricing são reconhecidos pelo guardrail existente; valor sem evidência continua bloqueado.
- [x] Divergência real inclui diferença e encaminhamento, sem promessa financeira.
- [x] Consulta de taxa com filtros suficientes usa ferramentas antes de pedir dado desnecessário.
- [x] Cenários aceitam equivalência semântica sustentada por fatos, sem reduzir verificações críticas.
- [x] Nova revisão e revalidação identificam hashes e o escopo afetado; custo acumulado da validação <= US$0,15.

## Validação

Rodada original preservada: 31/40, com cinco falsos negativos de redação e
falhas reais de consulta/roteamento/apresentação financeira em quatro casos.
Após correções, a rodada HTTP r2 aprovou todos os checks não semânticos dos
40 casos. O replay r6 das mesmas respostas aprovou **40/40**, preservando os
17 holdouts e todos os checks não semânticos. Reviewer verificou positivos,
contradições, dúvidas qualificadas e ban literal de privacidade; QA inspecionou
as respostas e as jornadas. Validação estrita: **191 testes**. Acumulado da
guarda: **US$0,14123583 / US$0,15**. [Resultado e limitações](../evidence/v030-resultado.md).

## Status

```text
concluída e validada no candidato r6
```
