# Tarefa: recuperar conversa após falha de transporte sem reenviar mensagem

## Objetivo

Permitir consulta manual da resposta persistida quando uma falha de transporte
impedir a interface de receber o resultado do POST.

## Especificação relacionada

[Tarefa 48](48-diagnostico-timeout-chat-ui-v050.md),
proposta aprovada, plano v0.5 e história v1; escopo adicional aprovado pelo responsável.

## Pré-condições

- Tarefa 49 implementada.
- Bytes da interface preservados antes de editar. Não tocar backend, API pública,
  dados, ledger, teto, timeout, credenciais ou políticas.

## Arquivos prováveis

Web `app.py`, cliente/fake existentes se necessários e testes da interface. Backend somente esta tarefa e evidência.

## Passos

1. Fixar um identificador de conversa válido no estado da UI antes do primeiro
   envio, pelo campo já aceito na API. Verificar compatibilidade do ID sem
   mudar contrato ou regras de autorização do backend.
2. Tratar falha de transporte: mensagem útil e estado recuperável. Preservar
   a pergunta/identificação pendente, sem traceback e sem POST automático.
3. Oferecer atualização manual somente GET. Exibir resposta persistida correta
   da conversa; não confundir histórico anterior com conclusão de pergunta
   ainda pendente. Consulta repetida, rerun e navegação não geram inferência.
4. Preservar renderização/inspeção normal quando request_id estiver disponível;
   não inventar request_id ausente. Erro na consulta GET também é recuperável.
5. Acrescentar medição HTTP sanitizada se necessária ao diagnóstico: operação,
   duração e classe do erro, sem texto, token ou credencial. Não aumentar 20 s
   nem introduzir retry automático. Registrar limites da análise histórica.
6. Validar transporte controlado e testes web completos, script exigido/Ruff
   externo se necessário. Não chamar APIs reais ou serviços pagos.

## Critérios de conclusão

- [x] ID conhecido antes do POST e preservado em falha.
- [x] Falha de transporte não escapa como traceback nem repete POST.
- [x] Recuperação usa apenas GET e mostra a resposta correta, ou informa que
  ela ainda não está disponível; histórico velho não aparece como resposta nova.
- [x] GET repetido/rerun não duplica envio/gasto; estado de erro GET é útil.
- [x] Suíte web e Ruff passaram sem chamadas reais; backend ficou idêntico.
- [x] Mesma campanha de US$0,25 preservada; evidências e candidatos anteriores mantidos.

## Resultado

ID da conversa fixado antes do POST, falha de transporte sem traceback nem reenvio e atualização manual só por GET. Suíte web: 20/20 testes; Ruff aprovado; nenhuma chamada real. Recuperação comprovada no navegador depois da [tarefa 53](53-consumir-contrato-real-conversa-v050.md). Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
