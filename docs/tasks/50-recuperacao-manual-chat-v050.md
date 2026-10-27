# Tarefa: recuperar conversa após falha de transporte sem reenviar mensagem

## Objetivo

Permitir consulta manual da resposta persistida quando uma falha de transporte
impedir a interface de receber o resultado do POST.

## Especificação relacionada

[Tarefa48](48-diagnostico-timeout-chat-ui-v050.md),
[proposta aprovada](../evidence/v050-recuperacao-chat-proposta.md), plano v0.5,
história v1 e QA r1. Responsável aprovou explicitamente este escopo adicional.

## Pré-condições

- Tarefa49 implementada em candidato r4, ainda sem revisão/QA próprios.
- Reutilizar mesmos Developer → Reviewer → QA, todos gpt-6-luna/high.
- Manter dois projetos/branches atuais, sem nova branch, pull ou integração.
- Preservar bytes r4 antes de editar em novo diretório de teste. Não tocar
  backend, API pública, dados, ledger, teto, timeout, credenciais ou políticas.

## Arquivos prováveis

Web `app.py`, cliente/fake existentes se necessários e testes da interface.
Documentação de passagem. Backend somente esta tarefa e evidência.

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
   duração e classe do erro, sem texto, token ou credencial. Não aumentar20s
   nem introduzir retry automático. Registrar limites da análise histórica.
6. Validar transporte controlado e testes web completos, script exigido/Ruff
   externo se necessário. Não chamar APIs reais ou serviços pagos da rodada.
7. Entregar passagem `v050-developer-ui-r2.md`; parar escrita ao concluir,
   sem adendos experimentais. Supervisor fixa r5, Reviewer revisa o conjunto
   controles/recuperação e o mesmo QA revalida no orçamento já existente.

## Critérios de conclusão

- [x] ID conhecido antes do POST e preservado em falha.
- [x] Falha de transporte não escapa como traceback nem repete POST.
- [x] Recuperação usa apenas GET e mostra a resposta correta, ou informa que
  ela ainda não está disponível; histórico velho não aparece como resposta nova.
- [x] GET repetido/rerun não duplica envio/gasto; estado de erro GET é útil.
- [x] Suíte web e Ruff passaram sem chamadas reais; backend ficou idêntico.
- [x] Mesma campanhaUS$0,25 preservada; QA r1 e candidatos históricos mantidos.

## Validação

Validação sintética registrada em [evidência Developer](../evidence/v050-developer-ui-r2.md). `lint_and_tests.py --strict` executou 20/20 testes e a estrutura/skills, mas retornou código 2 porque Ruff não existe no venv web; Ruff externo passou em `app.py src tests tools`. Nenhuma chamada real foi feita. Critérios visuais e jornada integrada aguardam Reviewer e QA no candidato r5.

## Status

Implementada — aguardando revisão independente e revalidação QA no r5; não declarar aceite.
