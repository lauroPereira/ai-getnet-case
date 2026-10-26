# Evidência: primeira execução real dos 10 exemplos (desenvolvimento)

Tarefas: [08](../tasks/08-orquestracao-estado-e-limites.md) a [12b](../tasks/12b-personality.md). Data: 2026-10-26. Verificação manual com o sistema real em processo (`gpt-6-luna`, `text-embedding-3-small`, busca web da OpenAI, Qdrant local, `cliente1988`). Amostra de desenvolvimento: não substitui a avaliação da tarefa 14.

## Resultado por exemplo

| Exemplo | Rota | Agentes | Custo (US$) | Latência | Observação |
| --- | --- | --- | --- | --- | --- |
| Get Clássica vs Get Smart | knowledge | router, knowledge, personality | 0,0006 | 9,5 s | Diferenças e preços de aluguel das páginas oficiais; avisa que condições dependem do contrato |
| Previsão do tempo em Porto Alegre | general_web | router, knowledge, personality | 0,0104 | 6,5 s | Fonte é um provedor de dados da busca (sem URL); citado após ajuste |
| Dinheiro das vendas de ontem | support | router, customer_support, personality | 0,0006 | 8,9 s | Valores líquidos e datas da agenda; Pix já creditado; demais sem crédito confirmado |
| Pix sem conta bancária | knowledge | router, knowledge, personality | 0,0004 | 5,1 s | Chave Pix ligada à conta de recebimento (FAQ oficial) |
| Maquininha sem internet | knowledge_and_support | router, knowledge, customer_support, personality | 0,0010 | 13,7 s | Estado do dispositivo, passos oficiais de Wi-Fi e chip, histórico do caso anterior |
| Antecipação | knowledge | router, knowledge, personality | 0,0006 | 8,3 s | Passos no app, mínimo de R$ 50,00, antecipação automática |
| Cotação do euro | general_web | router, knowledge, personality | 0,0107 | 6,6 s | Após ajuste, converte para real (BRL) e cita a fonte |
| Erro de transação negada | knowledge_and_support | router, knowledge, customer_support, personality | 0,0009 | 15,2 s | Motivo documentado (saldo/limite), próximo passo e "não é defeito da maquininha" |
| Parcelas no crediário | knowledge | router, knowledge, personality | 0,0005 | 5,3 s | Até 48x, conforme o emissor |
| WhatsApp com Link de Pagamento | knowledge | router, knowledge, personality | 0,0004 | 5,1 s | Venda pelo WhatsApp com envio do link |

A guarda de saída não encontrou valores sem evidência em nenhuma resposta.

## Ajustes feitos a partir desta execução

- `support` v2: usar o valor líquido para o dinheiro a receber (a primeira resposta citou o valor bruto).
- `personality` v2: datas em formato natural, nunca o carimbo técnico.
- `knowledge_web` v2: conversão de moeda para real quando o destino não for informado (a primeira resposta trouxe euro em dólar) e citação obrigatória da fonte.
- Busca web: fontes extraídas também da chamada de busca, inclusive provedores sem URL (o tempo vinha de um provedor de dados, sem anotação).
- Um erro de programação nesse ajuste (URL ausente) foi contido pelo próprio grafo: o nó falhou, a resposta saiu controlada e o erro apareceu no trace. Corrigido em seguida.

## Custo

US$0,071 nesta etapa (índice real, primeira pergunta, 10 exemplos, reexecuções e uma chamada de diagnóstico), dentro da reserva de desenvolvimento. As buscas web respondem por cerca de 80% do custo dos exemplos.
