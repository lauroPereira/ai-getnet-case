# Tarefa: concorrência, limite demo e custo desconhecido (v0.6.0)

## Objetivo

Corrigir, antes da validação real, os pontos da [revisão independente](../evidence/v060-reviewer.md) que afetam orçamento, integridade ou o aceite, sem ampliar o escopo.

## Especificação relacionada

[Spec v0.6.0](../specs/fechamento-v060.md), [plano](../specs/fechamento-v060-plano.md), tarefas 54–58 e a revisão independente.

## Pré-condições

- Decisões do responsável em 2026-10-27: corrigir antes da validação real; o limite por sessão demo conta **toda ação paga** (mensagens, execuções novas de comparação, comparação de Routers e avaliação por IA), e recusa sem inferência (por exemplo `409`) não consome.
- `LOCK_BACKEND_URL` opcional, desligado por padrão, mantido por decisão do responsável; fora desta tarefa.
- Sem chamada paga.

## Passos

1. Marcar comparação interrompida como `failed` só quando ainda estiver `running` (atualização condicional), sem sobrescrever resultado concluído.
2. Idempotência da avaliação sem corrida (restrição única ou reserva atômica); dois POST simultâneos com a mesma configuração resultam numa única chamada paga.
3. Limite demo aplicado a toda ação paga, conforme a decisão acima; recusa sem inferência não consome.
4. Administração trata falha de transporte (timeout) no build e no teste de candidata sem exceção do Streamlit e sem permitir repetir a ação paga às cegas; o estado é consultado por GET. README do web coerente.
5. Comparação reaproveita só execuções independentes (sem histórico de conversa).
6. Células com falha e pontos do gráfico custo × qualidade abrem as execuções correspondentes (CA-48).
7. Catálogo cobre habilitação de bandeiras e cancelamento de venda, além das jornadas atuais.
8. Custo ausente não vira zero na agregação (aparece como desconhecido); testes de ativação da base durante a comparação, de reuso com outra versão da base e do caso negativo do bloco D.
9. Modo simulado não expõe papel admin quando a interface está compartilhada (`LOCK_BACKEND_URL` ligado).
10. Validação estrita backend e web com código 0.
11. Recusa sem inferência não consome o limite demo também em mensagem com orçamento negado e em células de comparação puladas (mudança da base, teto ou orçamento); código e documentação coerentes.
12. Teste do consumo do limite no envio que usa a decisão da comparação de Routers.
13. Interface nunca mostra custo desconhecido como número (avaliação em andamento; barras do gráfico 2 respeitam `cost_unknown`).
14. Migração 0008 sem correção de código: ainda não publicada, e a validação real cria runtime novo a partir do candidato.

## Critérios de conclusão

- [x] Cada item com teste que falharia antes e passa depois, ou justificativa registrada.
- [x] Contratos aprovados, legado e MCP inalterados além do necessário a estes itens.
- [x] Nenhuma chamada paga; validação estrita com código 0 nos dois repositórios.

## Resultado

Comparação interrompida não sobrescreve estado final; avaliações simultâneas chamam o juiz uma vez; o limite demo conta toda ação paga e devolve recusas sem inferência; custo desconhecido nunca aparece como número; catálogo com 10 cenários. Suíte estrita: backend 340 testes, web 35, nenhuma chamada paga. Evidência: [resultado da v0.6.0](../evidence/v060-resultado.md).

## Status

```text
concluída (v0.6.0)
```
