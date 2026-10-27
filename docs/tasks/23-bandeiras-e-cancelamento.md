# Tarefa: Bandeiras e cancelamento de venda

## Objetivo

Consultar habilitação de bandeiras e cancelamentos de vendas, distinguindo encerramento contratual sem executar alterações.

## Especificação relacionada

RF-33, RF-34, CA-22, CA-23, CA-31, UC-24 e UC-25; [plano](../specs/jornadas-v030-plano.md).

## Pré-condições

Autorização explícita da migração reversível 0005 e das ferramentas novas.

## Arquivos prováveis

Migrações, seed, ferramentas/registro, prompts novos, política programada, testes de domínio/API/MCP.

## Passos

1. Criar dados de solicitação pendente com protocolo, habilitação ativa e divergência no dispositivo; incluir cancelamentos sintéticos e outro cliente.
2. Implementar `get_enablement_requests` e `get_sale_cancellation_context` com checagem de vínculo.
3. Integrar orientação e encaminhamento sem duplicar pedido nem executar ação sobre venda ou contrato.
4. Testar migração de ida e volta, preservação do núcleo e jornadas nos dois idiomas.

## Critérios de conclusão

- [x] Pedido existente reutiliza o protocolo, sem nova solicitação.
- [x] Ativação e disponibilidade no dispositivo aparecem separadamente.
- [x] Cancelamento de venda é consulta; encerramento contratual não aciona ferramenta de venda.
- [x] Isolamento e auditoria preservados também no MCP.
- [x] Migração reversível validada sobre banco sintético isolado.

## Validação

Validação final: **191 testes**, incluindo migração 0004→0005→0004 em banco
sintético isolado, habilitação/cancelamento e MCP. Revisão independente
confirmou o isolamento, inclusive vínculo da venda. QA por HTTP e MCP
confirmou protocolo existente, cadastro/dispositivo e consulta sem executar
cancelamento; respostas reais foram inspecionadas. Evidências e limitações
no [resultado](../evidence/v030-resultado.md).

## Status

```text
concluída e validada; integração da entrega depende de autorização humana
```
