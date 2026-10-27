# Tarefa: Continuidade técnica após encaminhamento

## Objetivo

Preservar rota de suporte, status de encaminhamento e protocolo quando o lojista informa que o problema técnico continua após um handoff.

## Especificação relacionada

RF-28 a RF-30; CA-18, CA-19 e CA-28. Cenário reservado FU02 já existente, sem alteração de critérios.

## Pré-condições

Rodada HTTP real r2 e fontes preservadas em [v030-real-http-r2.json](../evidence/v030-real-http-r2.json). Mesmo teto adicional US$0,15; saldo após rodada US$0,01415107.

## Arquivos prováveis

Nova versão do prompt Router e evidências. Código de estado somente se necessário para respeitar o contrato já existente; não modificar guardrails ou o cenário reservado para aprovar.

## Passos

1. Reproduzir FU02: primeiro pedido técnico, tentativa sem sucesso, novo retorno `Still the same, nothing works.` após handoff.
2. Corrigir a orientação de roteamento: falha persistente não é mero agradecimento/acknowledgement; manter suporte e sinal de falha, inclusive após encaminhamento. Preservar acknowledgements reais e confirmação de resolução.
3. Reutilizar o mesmo protocolo; não abrir novo encaminhamento nem repetir etapas esgotadas.
4. Validar regressões sem custo, revisar candidato e repetir somente a conversa afetada via HTTP real, no ledger autorizado.

## Critérios de conclusão

- [x] FU02 mantém uma rota aceita pelo cenário, status `handoff`, caso `handoff` e mesmo protocolo no último turno.
- [x] Agradecimento simples e confirmação de resolução continuam distintos.
- [x] Nenhum encaminhamento duplicado, cálculo financeiro pelo modelo ou relaxamento de proteção.
- [x] Cenário reservado e critérios preservados; revisão e revalidação real identificam o novo candidato.

## Validação

R2 original preservado: FU02 falhou no terceiro turno como
`acknowledgement`/`answered`. Router 5 corrigiu a continuidade. Na repetição
HTTP real r3 sobre o candidato r6, **4/4 conversas passaram**; FU02 preservou
`knowledge_and_support`, `handoff`, caso e protocolo nos turnos 2 e 3.
Regressões de agradecimento/resolução passaram; critérios reservados não
mudaram. Reviewer e QA independentes aptos, validação estrita **191 testes**.
Acumulado da guarda: **US$0,14123583 / US$0,15**.
[Resultado e limitações](../evidence/v030-resultado.md).

## Status

```text
concluída e validada no candidato r6
```
