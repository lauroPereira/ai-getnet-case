---
id: KB-DEMO-DEVICES-001
version: 0.1.0
source_kind: simulated_internal
environment: demo
domain: devices
---

# Dispositivos e conectividade

Documento operacional fictício, válido somente na demonstração.

## Evidências necessárias

get_device_status retorna dispositivo, modelo, configuração relevante, últimos sinais disponíveis e instante de observação. Vários equipamentos exigem seleção do recurso correto. Os procedimentos reais de uso e manutenção devem vir de uma fonte pública oficial compatível com o modelo.

## Procedimento

Após histórico e healthcheck, conferir modelo e sinais disponíveis. Usar o histórico para evitar orientar novamente um passo já realizado. Perguntar somente o que faltar para escolher um procedimento compatível. O atendimento registra a orientação e o retorno do lojista.

A simulação não executa comandos remotos no terminal. Falta de telemetria é unknown e não confirma que a conexão caiu. Uma alternativa de venda depende dos produtos habilitados e das condições do outro canal; o prazo da captura original não é transferido automaticamente.

## Parada e resultado

Registrar customer_confirmed quando o lojista disser que voltou a funcionar. tool_verified só é usado se um retorno disponível verificar o fato relevante. O cenário inicial limita a dois ciclos de orientação; persistência do problema ou pedido do cliente produz passagem com passos, retornos e evidências.

Aceitação de uma alternativa de venda e recuperação do terminal são resultados diferentes. Uma resposta como “entendi” não confirma funcionamento.
