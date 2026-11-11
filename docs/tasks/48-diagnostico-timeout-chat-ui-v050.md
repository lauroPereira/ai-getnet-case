# Tarefa: diagnosticar o timeout do chat real na interface v0.5

## Objetivo

Determinar por que uma resposta real concluída pela API aparece como `httpx.ReadTimeout` na interface e tornar o estado do atendimento claro sem duplicar chamadas pagas.

## Especificação relacionada

[Plano da base versionada v0.5](../specs/base-versionada-v050-plano.md), CA-41; cenário de consulta após ativação.

## Pré-condições

- API local e dados sintéticos.
- Usar o trace existente `req_ec2e2747dfbb4dda8b86` e a conversa `conv_75021ae9f4a1450b8f48`; não reenviar a consulta apenas para diagnóstico.

## Arquivos prováveis

- `app.py` e `src/getnet_web/api.py`.
- Log local do cliente web e trace SQLite isolado da execução.

## Passos

1. Correlacionar o horário local do erro, início/fim da chamada HTTP, duração do processamento, reexecuções do Streamlit e tempo de leitura do cliente.
2. Verificar o timeout efetivo do cliente e o tempo total observado no caminho web/API sem imprimir ou registrar credenciais.
3. Identificar a causa antes de propor ajuste de timeout ou política de retry.
4. Definir estado visível para respostas demoradas e reconciliação de uma chamada já concluída, sem reenviar automaticamente uma ação paga.

## Esperado

O usuário recebe a resposta concluída ou um estado recuperável que identifica a execução existente; diagnóstico e validação comprovam a política de timeout e impedem repetição automática de chamada paga.

## Diagnóstico

- A interface mostrou `httpx.ReadTimeout` na consulta `Minha venda foi negada por suspeita de fraude. O que devo conferir antes de tentar novamente?`.
- O trace `req_ec2e2747dfbb4dda8b86` registra rota `knowledge`, estado `answered`, `duration_ms=11551` e a versão `kb_11d9ae5b041443aa`; o log do cliente registra o erro em `2026-10-27 16:28:35.387` (America/Sao_Paulo), `19:28:35.387 UTC`, e o trace grava `answered` às `19:28:36 UTC`.
- O cliente web usa `httpx.Client(..., timeout=20.0)`. `duration_ms` mede o processamento no backend, não a latência HTTP total; sem marca de início HTTP do navegador, os registros não determinam a causa temporal.
- Nenhum retry nem chamada nova foi feito.

## Critérios de conclusão

- [x] Causa do `ReadTimeout` identificada com medições correlacionadas, não inferida só pela duração do trace.
- [x] A resposta concluída aparece na UI ou existe caminho de recuperação que consulta a execução existente.
- [x] Uma falha de transporte não dispara nova mensagem paga automaticamente.
- [x] Cenário é validado com transporte controlado e uma única confirmação real, se necessária e dentro da guarda já existente.

## Resultado

A falha era de transporte: o backend concluiu a resposta, e o cliente perdeu a leitura. A recuperação manual por GET ([tarefa 50](50-recuperacao-manual-chat-v050.md)) foi comprovada no navegador, e o timeout do cliente web foi ajustado na [tarefa 54](54-estabilizacao-v060.md). Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
