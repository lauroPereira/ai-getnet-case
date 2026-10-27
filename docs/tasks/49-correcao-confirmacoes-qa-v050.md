# Tarefa: corrigir confirmações da interface após QA r1

## Objetivo

Desbloquear as ações explícitas da base na interface, sem execução automática
ou repetição de chamadas pagas em reruns.

## Especificação relacionada

[Plano aprovado](../specs/base-versionada-v050-plano.md), história v1,
[defeito47](47-formularios-confirmacao-ui-v050.md),
[proposta aprovada](../evidence/v050-correcao-qa-proposta.md) e
[QA r1](../evidence/v050-qa-r1.md).

## Pré-condições

- QA r3 encerrado, Streamlit da rodada parado; backend18853 e fixtures18854
  preservados. Não chamar esses serviços pagos durante a implementação.
- Responsável autorizou reutilizar Developer → Reviewer gpt-6-luna/high,
  depois retornar ao mesmo QA; nenhum agente novo adicional.
- Manter branches e trabalho local já derivados das mains atualizadas.
- Preservar r3 e seus artefatos; guardar bytes dos arquivos web afetados em
  diretório novo de teste antes de editar. Sem commit/push/limpeza.

## Arquivos prováveis

Web `app.py` e testes da interface. Backend somente tarefa/evidência desta
correção; nenhum código, contrato, migração, guarda ou configuração protegido.

## Passos

1. Reproduzir sem custo o defeito47. Corrigir o mecanismo de confirmação em
   build, teste, ativação e retorno, avaliando o mesmo padrão nos quatro.
   Estado da confirmação deve atualizar a habilitação da ação correspondente.
2. Preservar ausência de envio sem confirmação, custo máximo informado,
   teste aprovado antes de ativar, revisão esperada e validação do backend.
   Nenhuma ação paga nasce de rerun, navegação ou atualização de estado.
3. Validar interação equivalente à do navegador. AppTest que força rerun após
   mudar checkbox dentro de formulário pode mascarar o defeito observado;
   a evidência deve demonstrar a atualização real dos controles.
4. Executar validação proporcional do projeto web: script exigido pelo AGENTS,
   testes web completos e Ruff. Não repetir backend293, que não será alterado.
   Nenhum teste chama o backend real ou provedores; transportes controlados.
5. Ler logs/trace existentes da [tarefa48](48-diagnostico-timeout-chat-ui-v050.md)
   somente para diagnóstico sem custo. Distinguir duração do grafo do tempo
   HTTP total. Não aumentar timeout nem implementar recuperação do chat nesta
   tarefa: devolver causa/evidência/proposta se houver ajuste necessário.
6. Entregar passagem específica, sem autoaprovação. Supervisor fixa r4,
   Reviewer revisa o delta e QA revalida a jornada no mesmo runtime/cap.

## Critérios de conclusão

- [x] Quatro ações têm confirmação eficaz e pré-requisitos preservados.
- [x] Reruns e navegação não provocam build/teste/transição (botões explícitos; rerun dos checkboxes e reruns subsequentes cobertos por AppTest).
- [x] Validação web sem custo registrada; backend não mudou.
- [x] Diagnóstico48 registra fatos, limites de medição e proposta sem retry nem mudança de timeout.
- [x] Passagem Developer registra arquivos, testes, limitações e próximo responsável.

## Validação

Implementação local concluída. Regressão sintética e validação web registradas em [evidência Developer](../evidence/v050-developer-ui-r1.md); aguarda revisão independente e nova rodada QA no candidato fixado.

## Status

Implementada — aguardando revisão independente e revalidação QA; não declarar aceite.
