# Tarefa: regressão e validação real da v0.5.0

## Objetivo

Fixar os dois candidatos e validar a história com provedores reais sob guarda.

## Especificação relacionada

CA-28/32–37/41/44/45 e [plano](../specs/base-versionada-v050-plano.md).

## Pré-condições

Conjunto aprovado e tarefas 39–43 concluídas, com revisão independente apta.
Validação paga autorizada pelo responsável para esta versão. Dados públicos e sintéticos.

## Arquivos prováveis

Testes, evidências, harness de validação, controles persistentes e docs dos dois repos.

## Passos

1. Executar validação Python estrita e web; fixar fonte, contrato e fixtures.
2. Revisão independente re-deriva os critérios, sem conclusões do implementador.
3. Fixar candidato e ambiente; a validação confere hashes e percorre UI e HTTP.
4. Verificar preços e modelos, apresentar estimativa e fixar uma vez cap adicional
   até US$0,25, inferior ao saldo total; usar a guarda existente sem reset entre tentativas.
5. Executar baseline/JEV real, edição/build/teste/ativação/retorno e regressão
   pertinente; registrar uso/custo real ou estimado, versões e falhas individuais.
6. Qualquer defeito gera correção, novo candidato, revisão e revalidação.

## Critérios de conclusão

- [x] Testes determinísticos passam; a validação de aceite usa provedores reais nos caminhos pagos.
- [x] CA-32/modelos pendentes da v0.4 têm evidência real ou bloqueio concreto registrado.
- [x] Cada chamada paga reservada; gastos/tentativas agregados sem zerar ledger.
- [x] CA-41 e captura de versão demonstrados na interface; fonte/ambiente fixados.
- [x] Sem publicação/commit/push da v0.5 sem autorização própria da entrega.

## Resultado

Suíte estrita do backend: 293 testes; web: 20. Validação real pela interface: confirmações, build, teste, ativação e retorno, versão capturada durante a troca e recuperação da resposta por GET sem POST repetido; JEV real (CA-32) e comparação DeepSeek/JEV com evidência. Campanha de US$0,00532161 no cap adicional de US$0,25, zero reservas abertas. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
