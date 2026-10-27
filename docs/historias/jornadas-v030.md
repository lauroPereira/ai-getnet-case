# História de uso: jornadas de negócio da v0.3.0

## Objetivo e pessoa usuária

Um lojista sintético entende uma cobrança, acompanha uma bandeira e consulta cancelamento de venda pela API do assistente. Roteiro versão 1; nenhuma operação financeira é executada.

## Critérios e candidato

CA-21, CA-22, CA-23, CA-28 e CA-31; tarefas 21 a 24. Manifesto e hashes serão fixados pelo Supervisor após implementação e revisão.

## Condições iniciais

Banco e runtime sintéticos isolados, relógio fixo, fixtures independentes de pricing e cobrança, modelo programado e índice local para testes sem custo. A validação com modelo real é uma rodada separada, sujeita a autorização e à guarda de orçamento. API sem interface gráfica nesta versão.

## Momentos da história

| Momento | Ação pela entrada normal | Resultado esperado | Critério | Evidência | Ponto de retorno |
| --- | --- | --- | --- | --- | --- |
| Preço coerente | Pergunta sobre cobrança de venda com condições correspondentes | Regra e cobrança sustentam a conclusão e valores | CA-21, CA-31 | Resposta HTTP e trace | Nova conversa isolada |
| Condições diferentes | Contesta taxa comparando condições distintas | Explica diferenças sem declarar erro de cobrança | CA-21, CA-31 | Resposta e duas fontes | Nova conversa |
| Divergência | Consulta venda com cobrança divergente | Diferença em centavos calculada no código; encaminha com contexto, sem prometer ressarcimento | CA-21, CA-31 | Resposta, comparação e encaminhamento | Nova conversa |
| Evidência insuficiente | Consulta venda sem evidência aplicável completa | Expõe a lacuna e próximo passo; não inventa taxa nem calcula no modelo | CA-21, CA-31 | Resposta e trace | Nova conversa |
| Bandeira pendente | Pergunta pelo pedido já aberto | Reaproveita protocolo; não cria solicitação | CA-22, CA-31 | Resposta e registros antes/depois | Somente consulta |
| Cadastro e dispositivo | Bandeira ativa que não aparece no equipamento | Distingue cadastro ativo e equipamento; orienta sem executar ativação | CA-22, CA-31 | Resposta e fatos das ferramentas | Somente consulta |
| Cancelamento de venda | Pede situação de cancelamento de venda própria | Consulta estado e limites, sem executar cancelamento | RF-34, CA-31 | Resposta e registros | Somente consulta |
| Encerramento contratual | Diz que deseja encerrar o contrato | Esclarecimento/atendente; nenhuma ferramenta de venda | CA-23 | Trace sem ferramenta de venda | Somente encaminhamento simulado |
| Outro lojista | Informa identificador de recurso de outro cliente | Bloqueio estruturado e auditoria, sem dados vazados | RF-15 | Resposta/erro e auditoria | Somente consulta |
| Dependência falha | Serviço de pricing/cobrança indisponível | Resposta controlada e lacuna explícita, sem valores inventados | RF-02 | Resposta e erro estruturado | Restabelecer serviço isolado |
| Núcleo e MCP | Executa exemplos originais, conversas e cliente MCP | Sem regressão; domínio e MCP equivalentes | CA-28, CA-30 | Relatórios e saídas | Runtime isolado |

## Experiência e exceções

Respostas no idioma da mensagem; exercitar português e inglês. Fontes fictícias identificadas como tais; dinheiro, datas e estados têm suporte nas ferramentas. Falta de dados difere de falha de dependência. Não há tela nesta entrega. QA usa a entrada HTTP e o cliente MCP; não altera critérios ou produto.

## Resultado da rodada

Pendente: registrar candidato, ambiente, esperado e observado, limitações e defeitos reproduzíveis.

## Como terminou

A preencher após a rodada funcional, com o que o lojista conseguiu realizar e o que permaneceu pendente.
