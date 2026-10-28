# Dispositivos e conectividade

Documento operacional fictício, válido somente na demonstração.

## Evidências necessárias

get_device_status retorna dispositivo, modelo, configuração relevante, últimos sinais disponíveis e instante de observação. Vários equipamentos exigem seleção do recurso correto. Os procedimentos reais de uso e manutenção devem vir de uma fonte pública oficial compatível com o modelo.

## Procedimento

Após histórico e healthcheck, conferir modelo e sinais disponíveis. Usar o histórico para evitar orientar novamente um passo já realizado. Perguntar somente o que faltar para escolher um procedimento compatível. O atendimento registra a orientação e o retorno do lojista.

A simulação não executa comandos remotos no terminal. Falta de telemetria é unknown e não confirma que a conexão caiu. Uma alternativa de venda depende dos produtos habilitados e das condições do outro canal; o prazo da captura original não é transferido automaticamente.

## Alternativa de venda com a maquininha sem conexão

Quando a maquininha não conecta na internet e o lojista pergunta se pode vender por Link de Pagamento, consultar get_contract_snapshot antes de oferecer a alternativa. Só oferecer o Link de Pagamento se link_de_pagamento constar nos produtos contratados; se não constar, não oferecer a alternativa e seguir com o diagnóstico de conectividade.

## Parada e resultado

Registrar customer_confirmed quando o lojista disser que voltou a funcionar. tool_verified só é usado se um retorno disponível verificar o fato relevante. O cenário inicial limita a dois ciclos de orientação; persistência do problema ou pedido do cliente produz passagem com passos, retornos e evidências.

Aceitação de uma alternativa de venda e recuperação do terminal são resultados diferentes. Uma resposta como “entendi” não confirma funcionamento.
