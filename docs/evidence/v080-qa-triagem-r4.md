# Triagem offline do QA pré-holdout da v0.8.0

O QA independente releu as respostas, a evidência do juiz, as expectativas de desenvolvimento e as traces do candidato `f8daab03`. A reprovação da r3 permanece registrada. A triagem não fez novas chamadas a modelos.

| Casos | Classificação | Tratamento |
| --- | --- | --- |
| `V030-PRICE-CONDITIONS`, `V030-PRICE-INSUFFICIENT`, `V030-PT-PRICE-CONSISTENT`, `V030-PT-PRICE-INSUFFICIENT`, `V030-PT-SALE-CANCELLATION` | Sete falsos negativos prováveis de correspondência literal. As respostas preservaram a conclusão esperada. | Revisar equivalências nos rótulos dev e testar contradições. |
| `V030-PRICE-DIVERGENCE` | “Discrepancy” e os valores sustentam a divergência nas duas falhas de conteúdo. Nas repetições 1 e 3 o juiz sinalizou o protocolo porque a evidência entregue a ele omitia o registro da escalada. | Corrigir o critério textual e a captura da evidência da escalada. Preservar o sinal original e reavaliar no reteste. |
| `REPLAN-PROCEDURE` | A repetição 1 omitiu o procedimento pelo app apesar de recuperar fonte oficial. | Verificar a composição do procedimento junto à resposta de conta. |
| `REPLAN-WEB` | A repetição 2 deu resposta afirmativa sobre outros modelos sem deixar claro que o modelo solicitado não foi confirmado. | Corrigir a resposta quando a evidência não sustenta o item consultado. |
| `FU01` | O segundo turno resolveu o caso com `customer_confirmed`, mas usou rota inicial `knowledge_and_support` em vez de `acknowledgement`. | Corrigir o tratamento de confirmação de resolução e proteger mensagens que também trazem pedido novo. |
| `REPLAN-TOOL-DOWN` | A condição de teste foi inválida. As três simulações funcionaram. | Executar isoladamente com falha de preço e verificar a ferramenta, o encaminhamento e a trace. |

Repetir as 13 jornadas de negócio e os quatro cenários CA-49 três vezes e repetir a conversa afetada. Definir outros casos pela análise de impacto da correção. O teto, a integridade do holdout e a separação das duas fases D12 continuam sendo condições da rodada. [Parecer r3](v080-d12-pre-holdout-r3.md) [Traces recuperadas](v080-d12-traces-recuperadas-r3.md) [Projeção](v080-revalidacao-orcamento-r4.md)
