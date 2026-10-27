# Tarefa: distinguir reserva interna de parâmetro efetivo JEV

## Objetivo

Registrar na comparação e no snapshot somente parâmetros efetivamente aplicados
ao provedor, preservando a estimativa e a guarda de orçamento do JEV.

## Especificação relacionada

RF-47, RF-49, RF-51 e CA-34/CA-36; plano
`docs/specs/perfis-interface-v040-plano.md`; tarefa 36 e
[Reviewer r4](../evidence/v040-reviewer-r4.md).

## Pré-condições

Candidato r4 preservado. A reprodução independente usa transporte fake:
payload JEV contém `model`, `questions`, `state`, enquanto o mapa efetivo
afirma `max_output_tokens: 80`. Esse valor pertence apenas à reserva estimada.
Não há autorização para inferência real ou alteração da guarda/ledger.

## Arquivos prováveis

Contexto de execução, metering/configuração de chamadas, comparação/snapshot e
testes dos adaptadores/API. Alterar apenas o necessário; sem nova migração.

## Passos

1. Reproduzir o achado com transporte falso e sem chaves de provedor.
2. Separar a informação interna de reserva do parâmetro enviado ao provedor.
3. Preservar reserva, liquidação, limites, decisão e ausência de fallback.
4. Cobrir comparação e atendimento que reutiliza a decisão JEV, confirmando
   mapas efetivos vazios para campos não suportados; preservar o caso positivo
   de limite enviado ao LLM, inclusive reserva/payload iguais.
5. Executar validações proporcionais, registrar passagem e fixar novo candidato
   para o mesmo Reviewer; QA permanece etapa posterior.

## Critérios de conclusão

- [x] JEV não declara `max_output_tokens` como parâmetro enviado/efetivo.
- [x] Comparação e snapshot preservam essa distinção após reutilizar a decisão.
- [x] Reserva JEV continua em 80 tokens estimados; liquidação/contabilização não muda, sem chamada real.
- [x] Limite suportado do LLM continua aplicado e registrado corretamente.
- [x] Regressões fake reproduzem o defeito anterior e passam na correção.

## Validação

Teste unitário do adaptador JEV confirmou reserva `max_output_tokens=80`, ausência de `effective_parameters` na reserva e payload somente com `model`, `state` e `questions`. Teste integrado com transporte TypeSafe fake e OpenAI/DeepSeek fake verificou, em duas comparações, parâmetros JEV vazios e LLM `max_output_tokens=300`; os atendimentos selecionados para JEV e LLM mantiveram, respectivamente, mapa vazio e parâmetro LLM no snapshot, sem uma nova chamada Router ao reutilizar a decisão. Testes afetados: 8 passaram. Strict backend r5: 216 testes passaram; Ruff e skills passaram. Nenhuma inferência paga.

## Status

Concluída no escopo sem custo: [Reviewer r5](../evidence/v040-reviewer-r5.md)
e [QA r5](../evidence/v040-qa-r5.md) confirmaram metadados JEV/LLM coerentes;
revalidação r6 preservou o comportamento. Sem migração ou mudança incompatível
de contrato. Integração Git autorizada posteriormente pelo responsável.
