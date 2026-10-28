# Tarefa: diagnosticar o timeout do chat real na interface v0.5

## Objetivo

Determinar por que uma resposta real concluída pela API aparece como `httpx.ReadTimeout` na interface e tornar o estado do atendimento claro sem duplicar chamadas pagas.

## Especificação relacionada

[Plano da base versionada v0.5](../specs/base-versionada-v050-plano.md), CA-41; cenário de consulta após ativação.

## Pré-condições

- Candidato web inicial `v0.5.0-local-r3`, HEAD `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`.
- API local da rodada e dados de QA sintéticos.
- Usar o trace existente `req_ec2e2747dfbb4dda8b86` e a conversa `conv_75021ae9f4a1450b8f48`; não reenviar a consulta apenas para diagnóstico.

## Arquivos prováveis

- `app.py` e `src/getnet_web/api.py`.
- Evidência local `C:\workspace\ai-getnet-case\.pytest_cache\v050-qa-real-runtime\web.stderr.log` e trace SQLite isolado da rodada.

## Passos

1. Correlacionar o horário local do erro, início/fim da chamada HTTP, duração do processamento, reexecuções do Streamlit e tempo de leitura do cliente.
2. Verificar o timeout efetivo do cliente e o tempo total observado no caminho web/API sem imprimir ou registrar credenciais.
3. Identificar a causa antes de propor ajuste de timeout ou política de retry.
4. Definir estado visível para respostas demoradas e reconciliação de uma chamada já concluída, sem reenviar automaticamente uma ação paga.

## Esperado

O usuário recebe a resposta concluída ou um estado recuperável que identifica a execução existente; diagnóstico e validação comprovam a política de timeout e impedem repetição automática de chamada paga.

## Observado no candidato r3

- A UI apresentou `httpx.ReadTimeout` durante a consulta `Minha venda foi negada por suspeita de fraude. O que devo conferir antes de tentar novamente?`.
- Trace `req_ec2e2747dfbb4dda8b86`, conversa sintética `conv_75021ae9f4a1450b8f48`: campo bruto `duration_ms=11551` (11,551 segundos de duração registrada pelo backend), rota `knowledge`, estado `answered`, snapshot da versão `kb_11d9ae5b041443aa`. A métrica não informa a latência total HTTP.
- Log local registra erro em `2026-10-27 16:28:35.387` (America/Sao_Paulo). O cliente web configura `httpx.Client(..., timeout=20.0)` em `src/getnet_web/api.py:51`.
- A duração registrada no trace e o timeout configurado são medidas distintas; não inferir a latência HTTP por `duration_ms`. O erro visual foi reproduzido, mas sua causa permanece indeterminada. Não repetir chamada paga apenas para diagnosticar.

## Conferência Developer somente leitura (r1)

- `web.stderr.log` registra `ReadTimeout` em `2026-10-27 16:28:35.387 America/Sao_Paulo`, equivalente a `19:28:35.387 UTC`.
- A linha de `traces.sqlite3` para o request registrado tem `at=2026-10-27T19:28:36+00:00`, `status=answered` e `duration_ms=11551`. Os steps começam em `19:28:25.726 UTC`; o último começa em `19:28:36.297 UTC` e dura 4 ms.
- O timeout configurado no cliente web é 20 s. `duration_ms` mede o processamento registrado no backend, não a latência HTTP total. Sem marca de início HTTP do navegador ou telemetria ponta a ponta, a causa temporal do ReadTimeout permanece indeterminada. Nenhum retry ou chamada foi feito.
- Recuperação na UI: na base r4 não havia ação para consultar conversa por `conversation_id`. A tarefa50 implementou botão manual GET para a conversa conhecida, sem reenviar POST. A recuperação só exibe resposta encontrada após a contagem-base e não inventa `request_id`; revisão e QA dessa implementação estão pendentes em r5. “Atualizar execução” continua exigindo `latest_run.request_id` conhecido.
- Log separado em `16:29:15.599` registra `UnsupportedProtocol` durante abertura de sessão com URL sem esquema; não é o request rastreado e não identifica a causa do ReadTimeout.
- Timeout e recuperação não foram alterados.

## Critérios de conclusão

- [ ] Causa do `ReadTimeout` identificada com medições correlacionadas, não inferida só pela duração do trace.
- [ ] A resposta concluída aparece na UI ou existe caminho de recuperação que consulta a execução existente.
- [ ] Uma falha de transporte não dispara nova mensagem paga automaticamente.
- [ ] Cenário é validado com transporte controlado e uma única confirmação real, se necessária e dentro da guarda já existente.

## Validação

QA real v0.5.0, r1: observação e logs sanitizados em `docs/evidence/v050-qa-r1.md`. Nenhum retry foi feito.

## Status

```text
concluída
```

O atendimento terminava no backend e a falha era de transporte; a recuperação manual por GET ([tarefa 50](50-recuperacao-manual-chat-v050.md)) passou no [QA r3](../evidence/v050-qa-r3.md). O ajuste do timeout fixo de 20 s do cliente web segue na [tarefa 54](54-estabilizacao-v060.md).

Falha de UI reproduzida; causa temporal ainda não isolada. Recuperação manual GET implementada na tarefa50, aguardando revisão e QA; não alterar timeout por inferência.
