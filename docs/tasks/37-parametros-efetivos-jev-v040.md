# Tarefa: distinguir reserva interna de parâmetro efetivo JEV

## Objetivo

Registrar na comparação e no snapshot somente parâmetros efetivamente aplicados
ao provedor, preservando a estimativa e a guarda de orçamento do JEV.

## Especificação relacionada

RF-47, RF-49, RF-51 e CA-34/CA-36; plano
`docs/specs/perfis-interface-v040-plano.md`; tarefa 36.

## Pré-condições

A reprodução usa transporte fake:
payload JEV contém `model`, `questions`, `state`, enquanto o mapa efetivo
afirma `max_output_tokens: 80`. Esse valor pertence apenas à reserva estimada.
Não há autorização para inferência real ou alteração da guarda/ledger.

## Arquivos prováveis

Contexto de execução, metering/configuração de chamadas, comparação/snapshot e
testes dos adaptadores/API. Alterar apenas o necessário; sem nova migração.

## Passos

1. Reproduzir a divergência com transporte falso e sem chaves de provedor.
2. Separar a informação interna de reserva do parâmetro enviado ao provedor.
3. Preservar reserva, liquidação, limites, decisão e ausência de fallback.
4. Cobrir comparação e atendimento que reutiliza a decisão JEV, confirmando
   mapas efetivos vazios para campos não suportados; preservar o caso positivo
   de limite enviado ao LLM, inclusive reserva/payload iguais.
5. Executar validações proporcionais e fixar novo candidato para revisão.

## Critérios de conclusão

- [x] JEV não declara `max_output_tokens` como parâmetro enviado/efetivo.
- [x] Comparação e snapshot preservam essa distinção após reutilizar a decisão.
- [x] Reserva JEV continua em 80 tokens estimados; liquidação/contabilização não muda, sem chamada real.
- [x] Limite suportado do LLM continua aplicado e registrado corretamente.
- [x] Regressões fake reproduzem o defeito anterior e passam na correção.

## Resultado

JEV registra a reserva de 80 tokens sem declará-la como parâmetro efetivo, com payload só de `model`, `state` e `questions`; o LLM mantém `max_output_tokens=300` na reserva, no payload e no snapshot, inclusive ao reutilizar a decisão. 8 testes afetados aprovados; suíte estrita do backend: 216 testes; nenhuma inferência paga. Evidência: [resultado da v0.4.0](../evidence/v040-resultado.md).

## Status

```text
concluída (v0.4.0)
```
