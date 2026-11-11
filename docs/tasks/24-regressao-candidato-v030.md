# Tarefa: Regressão e candidato da v0.3.0

## Objetivo

Fixar um candidato revisável da v0.3.0 com regressão, história de uso, revisão e validação independentes.

## Especificação relacionada

CA-28 e CA-31; RF-38 a RF-40; [plano](../specs/jornadas-v030-plano.md).

## Pré-condições

Tarefas 21 a 23 implementadas e candidato completo antes da validação.

## Arquivos prováveis

README, changelog, versão do pacote, cenários, `docs/evidence/` e manifesto com hashes.

## Passos

1. Executar validação estrita, regressão programada e jornadas novas, sem rede e sem custo.
2. Preparar instruções de execução, limitações e retorno; fixar hashes dos arquivos locais e da história.
3. Submeter o candidato a revisão independente em contexto novo; correções geram novo candidato.
4. Validar pela história da entrega, sem alterar o produto para aprovação.
5. Preparar estimativa e comandos para a execução real e o Docker; executar somente sob autorização aplicável e registrar lacunas.

## Critérios de conclusão

- [x] Validações locais sem custo aprovadas e registradas.
- [x] Revisão e validação independentes identificam exatamente o candidato validado.
- [x] Documentação informa dados, contratos aditivos, limitações e retorno.
- [x] Execução real e Docker comprovados ou explicitamente pendentes, sem declaração indevida de liberação.
- [x] Nenhum commit, push, tag ou publicação sem autorização.

## Resultado

Suíte estrita: 191 testes; stack Docker saudável. Casos HTTP reais: 40/40 por reavaliação determinística das respostas originais; conversas: 4/4 repetidas com modelo real. Gasto adicional de US$0,14123583, dentro do teto de US$0,15. Evidência: [resultado da v0.3.0](../evidence/v030-resultado.md).

## Status

```text
concluída (v0.3.0)
```
