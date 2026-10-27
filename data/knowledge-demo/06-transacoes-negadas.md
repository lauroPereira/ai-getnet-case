---
id: KB-DEMO-AUTHORIZATIONS-001
version: 0.2.0
source_kind: simulated_internal
environment: demo
domain: authorizations
---

# Transações negadas

Documento operacional fictício, válido somente na demonstração.

## Evidências necessárias

find_authorization_events consulta as transações recentes do cliente autorizado (negadas, por padrão, nos últimos 7 dias) e retorna status, código de resposta apropriado ao atendimento, origem e instante. O lojista não precisa informar o identificador da transação. As fixtures usam dados fictícios e não contêm número completo de cartão, credenciais ou detalhes internos de prevenção a fraude.

## Procedimento

Após histórico e healthcheck, identificar a transação correta. Diferenciar evento autorizado, negado, pendente ou desconhecido pelo retorno da ferramenta. O procedimento do Knowledge Agent associa somente códigos documentados na demonstração a próximos passos.

Um motivo relacionado a produto não habilitado leva à conferência de contrato e workflow; um sinal pertinente ao dispositivo leva ao procedimento técnico. Ausência de informação não permite atribuir causa ao emissor, ao saldo do comprador ou ao equipamento.

## Resultado e limites

Explicar o status e os próximos passos sustentados pela evidência. Não repetir automaticamente uma venda, alterar decisões de autorização ou contornar controles. Se o problema persistir ou o código não tiver tratamento documentado, a passagem conserva o identificador da operação e as consultas realizadas.

“Motivo explicado” e “venda aprovada” são desfechos distintos. O caso não é marcado como venda concluída com base em uma explicação sobre a negativa.

## Códigos de resposta documentados na demonstração

Códigos sintéticos do ambiente de demonstração. Um código fora desta tabela tem motivo desconhecido.

| Código | Categoria | O que significa para o lojista | Próximo passo |
| --- | --- | --- | --- |
| 05 | issuer_declined | O banco emissor do cartão não autorizou a compra. | Pedir ao comprador que fale com o banco emissor ou use outro meio de pagamento. |
| 51 | insufficient_funds | Saldo ou limite insuficiente no cartão do comprador. | Oferecer outro meio de pagamento, como outro cartão ou Pix. |
| 57 | not_permitted | Transação não permitida para este cartão. | Confirmar se a bandeira e a modalidade estão habilitadas; se estiverem, pedir outro meio de pagamento. |
| 91 | issuer_unavailable | Emissor temporariamente indisponível. | Aguardar alguns minutos e tentar novamente. |

Negativas por saldo, limite ou decisão do emissor não indicam defeito na maquininha. Mensagens "Erro ADQ" na tela são erros do equipamento e seguem a página oficial de erros da maquininha.
