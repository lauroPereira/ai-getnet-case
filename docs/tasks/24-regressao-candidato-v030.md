# Tarefa: Regressão e candidato da v0.3.0

## Objetivo

Fixar um candidato revisável da v0.3.0 com regressão, história de uso e pareceres independentes.

## Especificação relacionada

CA-28 e CA-31; RF-38 a RF-40; [plano](../specs/jornadas-v030-plano.md).

## Pré-condições

Tarefas 21 a 23 implementadas e candidato completo antes de QA.

## Arquivos prováveis

README, changelog, versão do pacote, cenários, `docs/evidence/` e manifesto com hashes.

## Passos

1. Executar validação estrita, regressão programada e jornadas novas, sem rede e sem custo.
2. Preparar instruções de execução, limitações e retorno; fixar hashes dos arquivos locais e da história.
3. Despachar Reviewer em contexto novo; devolver correções ao Developer e fixar novo candidato se necessário.
4. Despachar QA pela história da entrega, sem alterar o produto para aprovação.
5. Preparar estimativa e comandos para rodada real e Docker; executar somente sob autorização aplicável e registrar lacunas.

## Critérios de conclusão

- [x] Validações locais sem custo aprovadas e registradas.
- [x] Revisão independente e QA identificam exatamente o candidato validado.
- [x] Documentação informa dados, contratos aditivos, limitações e retorno.
- [x] Rodada real e Docker comprovados ou explicitamente pendentes, sem declaração indevida de liberação.
- [x] Nenhum commit, push, tag ou publicação sem autorização.

## Validação

Validação final estrita: **191 testes**, Ruff, estrutura e skills aprovados.
Stack Docker saudável, com imagens e insumos identificados; Reviewer r6 e QA
r6 independentes aptos. Casos reais HTTP: **40/40** por replay determinístico
das respostas originais r2; conversas: **4/4** repetidas com modelo real no
candidato r6. O replay não é uma nova execução do modelo nem nova medição de
latência/custo. QA adicional por HTTP e MCP usou modelo programado sem chave.
Gasto adicional total: **US$0,14123583**, dentro do teto autorizado US$0,15.
Detalhes, hashes e limitações no [resultado](../evidence/v030-resultado.md).

## Status

```text
validação concluída; candidato pronto para aceite e integração autorizada
```
