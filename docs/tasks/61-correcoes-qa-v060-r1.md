# Tarefa: Router JEV no envio e na comparação, e ajustes da demonstração (v0.6.0)

## Objetivo

Corrigir o toggle JEV e os pontos pequenos que afetam a demonstração, encontrados na [validação real](../evidence/v060-qa.md), mais um ponto da revisão independente sobre a devolução do limite demo.

## Especificação relacionada

[Spec v0.6.0](../specs/fechamento-v060.md) (A, B, C), CA-32, CA-33, CA-47, CA-48, [tarefa 60](60-correcoes-revisao-v060-r1.md) e a [revisão independente](../evidence/v060-reviewer.md).

## Pré-condições

Sem chamada paga. Contratos aprovados inalterados além do necessário.

## Passos

1. Com `router_mechanism=jev` em `POST /v1/messages`, o Router precisa ser executado pelo adaptador JEV (TypeSafe), não pelo LLM padrão nem pelo do perfil; snapshot, trace, ledger e interface devem registrar o mecanismo e o modelo efetivamente usados. Causa observada: `execute_run` exclui `router` de `agent_models` e o orquestrador só aplica `router_llm` aos nomes presentes nesse dicionário. Vale também para a comparação de perfis com Router JEV. Teste que comprove a chamada ao adaptador JEV e a ausência de chamada LLM do Router.
2. Valores em reais (`R$ 80,00 … R$ 148,06`) não podem virar fórmula no Streamlit; o texto exibido é igual ao gravado.
3. Depois de "Atualizar conversa", o estado do caso mostra a rota e o status da resposta recuperada.
4. A devolução do limite demo não pode falhar aberta; decidir pelas linhas do ledger do `request_id` ou pelo `model_calls` do contexto da execução, e não devolver quando a informação faltar.
5. Observações da validação real, se pequenas: seletor de perfil começa em Referência; nomes dos perfis exibidos em português (Referência, Híbrido, Ajustado); teto do teste da candidata pré-preenchido com a estimativa; `/ready` mostra a coleção da versão ativa; rótulos do gráfico custo × qualidade sem sobreposição; CHANGELOG com 10 cenários.
6. Validação estrita backend e web com código 0.
7. Todo texto exibido com valores em reais aparece literal, inclusive a "Pergunta pendente" e o comentário do avaliador por IA (hoje com `st.write`).
8. Testes de falha aberta na devolução das células da comparação (decidir pelo trace; ledger ilegível), equivalentes aos da mensagem.

## Critérios de conclusão

- [x] Toggle JEV executa o adaptador JEV de verdade no envio direto e na comparação; registros coerentes.
- [x] Cada item com teste que falharia antes, ou justificativa registrada.
- [x] Nenhuma chamada paga; validação estrita com código 0 nos dois repositórios.

## Resultado

Com `router_mechanism=jev`, o adaptador JEV executa o Router no envio direto e em cada célula nova da comparação, e ledger, snapshot e trace registram `jev-1.14.0`; valores em reais aparecem literais; a devolução do limite demo decide pelas linhas do ledger. Suíte estrita: backend 349 testes, web 42. Na validação real, o JEV registrou `router · jev-1.14.0` sem linha de Router LLM. Evidência: [resultado da v0.6.0](../evidence/v060-resultado.md).

## Status

```text
concluída (v0.6.0)
```
