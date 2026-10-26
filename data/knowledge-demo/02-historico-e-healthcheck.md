---
id: KB-DEMO-INTAKE-001
version: 0.1.0
source_kind: simulated_internal
environment: demo
domain: support_intake
---

# Entrada de um caso de suporte

Documento operacional fictício, válido somente na demonstração.

## Etapa 1: histórico

Na abertura de um caso de suporte, get_complaint_history consulta casos e tentativas anteriores do cliente permitido. Se houver um caso aberto sobre a mesma operação ou habilitação, o atendimento recupera seu contexto antes de propor novo encaminhamento.

Histórico sem registros é um resultado válido. Falha de acesso ao histórico é um estado diferente e não pode ser apresentado como ausência de reclamações. O resumo de tentativas conserva o que foi feito e seu resultado, sem repetir perguntas já respondidas.

## Etapa 2: healthcheck funcional

run_customer_healthcheck executa um conjunto predefinido de verificações limitado ao assunto e aos produtos do cliente. Preço pode conferir acessibilidade de pricing, contrato e cobrança; habilitação pode conferir contrato, workflow e configuração do dispositivo. Os destinos são cadastrados na aplicação, sem URLs fornecidas pelo modelo.

O retorno distingue ok, pending, attention, unknown, unavailable e not_applicable por verificação, com instante, origem e observação. Um pedido pendente pode ser normal. Um sistema acessível não comprova que o produto esteja habilitado corretamente. Um sistema indisponível não comprova defeito no terminal.

## Continuidade e limites

O prefixo ocorre por caso, com reaproveitamento na sessão. Resultados vencidos ou uma mudança relevante podem exigir nova consulta. Perguntas de clima, câmbio e conceitos de produto seguem a rota de conhecimento adequada e não exigem consultar histórico individual.

Após o prefixo, o Knowledge Agent recupera o procedimento do assunto. O Customer Support escolhe as consultas especializadas com base no procedimento e nos fatos. Toda execução continua sujeita ao catálogo, contexto de cliente, prazo e orçamento.

Se uma fonte essencial falhar, o atendimento preserva as evidências obtidas e informa a lacuna. Pedido explícito de atendimento humano não fica condicionado ao sucesso do healthcheck. A passagem inclui limitações das consultas.
