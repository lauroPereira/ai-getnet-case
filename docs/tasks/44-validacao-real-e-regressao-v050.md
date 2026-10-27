# Tarefa: regressão, revisão e QA real v0.5

## Objetivo

Fixar os dois candidatos e validar a história com provedores reais sob guarda.

## Especificação relacionada

CA-28/32–37/41/44/45 e [plano](../specs/base-versionada-v050-plano.md).

## Pré-condições

Conjunto aprovado e tarefas39–43 concluídas; Reviewer independente apto.
QA pago autorizado pelo responsável para esta versão. Dados públicos/sintéticos.

## Arquivos prováveis

Testes, evidências, harness de QA, controles persistentes e docs dos dois repos.

## Passos

1. Developer executa validação Python estrita e web; fixa fonte/contrato/fixtures.
2. Reviewer re-deriva critérios e revisa sem conclusões do implementador.
3. Supervisor fixa candidato/ambiente; QA confere hashes e percorre UI/HTTP.
4. QA verifica preços/modelos, apresenta estimativa e fixa uma vez cap adicional
   atéUS$0,25, inferior ao saldo total; usa guarda existente sem reset entre tentativas.
5. Executar baseline/JEV real, edição/build/teste/ativação/retorno e regressão
   pertinente; registrar uso/custo real ou estimado, versões e falhas individuais.
6. Qualquer defeito volta ao mesmo Developer; novo candidato/revisão/revalidação.

## Critérios de conclusão

- [ ] Testes determinísticos passam; QA de aceite usa provedores reais nos caminhos pagos.
- [ ] CA-32/modelos pendentes da v0.4 têm evidência real ou bloqueio concreto registrado.
- [ ] Cada chamada paga reservada; gastos/tentativas agregados sem zerar ledger.
- [ ] CA-41 e captura de versão demonstrados na interface; fonte/ambiente fixados.
- [ ] Sem publicação/commit/push da v0.5 sem autorização própria da entrega.

## Validação e status

Validação determinística do Developer r1 concluída: backend estrito com 221 testes; web com 15 testes, Ruff e estrutura. O Developer não fez chamadas pagas. Cap persistente e injeção do guard foram preparados; QA real continua pendente após revisão independente e candidato fixado. A autorização paga não compra crédito nem autoriza remover dados.
