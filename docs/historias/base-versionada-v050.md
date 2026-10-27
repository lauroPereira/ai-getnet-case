# História: editar e publicar uma base sem interromper atendimento

Versão1, 2026-10-27; roteiro fixado antes de implementar.

## Pessoa e objetivo

Admin demonstra alteração de uma orientação fictícia. Lojista sintético deve
consultar base consistente; nenhuma edição concede ferramentas ou autoridade
financeira. Demo não administra a base.

## Condições iniciais

Mains v0.4 integradas, corpus público/fictício e ativa inicial identificada.
Unitários sem custo; aceite QA com provedores reais autorizado na v0.5 sob
guarda persistente. Candidato será fixado por commits/hashes dos dois repos.

## Momentos

| Ação | Resultado esperado | Critério |
| --- | --- | --- |
| Listar documento oficial e tentar editar | Fonte somente leitura; backend recusa | RF-63, CA-41 |
| Demo tenta criar rascunho/ativar |403 sem mudança de estado | Permissões, CA-41 |
| Admin altera fictício e revisa diff | Revisão/hash corretos, sem publicar ainda | RF-63 |
| Rever estimativa e confirmar build | Coleção candidata nova; ativa permanece | RF-64, CA-45 |
| Testar candidata completa | Resultado e manifesto rastreáveis; falha não ativa | CA-41 |
| Ativar explicitamente | Nova conversa recebe versão nova; evento com ator | RF-64–65 |
| Atendimento concorre com ativação | Termina na versão capturada no início | RF-65 |
| Retornar à anterior | Próxima conversa usa anterior íntegra, com evento | CA-41 |
| Atualizar/alternar abas | Sem build, teste pago ou ativação automática | RF-70 |
| Custo negado/provedor falha | Erro claro, ativa intacta, gasto/reserva preservados | CA-44–45 |

## Evidência e limites

QA deve usar UI normal, HTTP, versão no snapshot, alterações de fonte e custo
registrado. Baseline JEV/LLM real e modelos pendentes da v0.4 entram na rodada
limitada, sem reescrever os relatórios anteriores. Resultados programados e
pagos são separados. Esta história ainda não foi executada.
