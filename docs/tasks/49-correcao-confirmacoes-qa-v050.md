# Tarefa: confirmações eficazes nas ações da base na interface

## Objetivo

Desbloquear as ações explícitas da base na interface, sem execução automática
ou repetição de chamadas pagas em reruns.

## Especificação relacionada

[Plano aprovado](../specs/base-versionada-v050-plano.md), história v1,
[tarefa 47](47-formularios-confirmacao-ui-v050.md) e proposta aprovada.

## Pré-condições

- Serviços pagos não são chamados durante a implementação.
- Bytes dos arquivos web afetados guardados em diretório de teste antes de editar.

## Arquivos prováveis

Web `app.py` e testes da interface. Backend somente tarefa/evidência desta
correção; nenhum código, contrato, migração, guarda ou configuração protegido.

## Passos

1. Reproduzir sem custo o caso da tarefa 47. Corrigir o mecanismo de confirmação em
   build, teste, ativação e retorno, avaliando o mesmo padrão nos quatro.
   Estado da confirmação deve atualizar a habilitação da ação correspondente.
2. Preservar ausência de envio sem confirmação, custo máximo informado,
   teste aprovado antes de ativar, revisão esperada e validação do backend.
   Nenhuma ação paga nasce de rerun, navegação ou atualização de estado.
3. Validar interação equivalente à do navegador. AppTest que força rerun após
   mudar checkbox dentro de formulário pode mascarar o defeito observado;
   a evidência deve demonstrar a atualização real dos controles.
4. Executar validação proporcional do projeto web: script estrito,
   testes web completos e Ruff. O backend não muda.
   Nenhum teste chama o backend real ou provedores; transportes controlados.
5. Ler logs/trace existentes da [tarefa 48](48-diagnostico-timeout-chat-ui-v050.md)
   somente para diagnóstico sem custo. Distinguir duração do grafo do tempo
   HTTP total. Não aumentar timeout nem implementar recuperação do chat nesta
   tarefa: devolver causa/evidência/proposta se houver ajuste necessário.
6. Fixar novo candidato, com revisão do delta e revalidação da jornada no mesmo runtime e cap.

## Critérios de conclusão

- [x] Quatro ações têm confirmação eficaz e pré-requisitos preservados.
- [x] Reruns e navegação não provocam build/teste/transição (botões explícitos; rerun dos checkboxes e reruns subsequentes cobertos por AppTest).
- [x] Validação web sem custo registrada; backend não mudou.
- [x] O diagnóstico da tarefa 48 registra fatos, limites de medição e proposta sem retry nem mudança de timeout.
- [x] Arquivos, testes e limites registrados.

## Resultado

Build, teste, ativação e retorno com confirmação que habilita a ação correspondente; reruns e navegação não enviam nada, cobertos por AppTest. Suíte web: 20 testes; revalidado no navegador. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
