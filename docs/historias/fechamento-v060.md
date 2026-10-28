# História: demonstrar o case completo em uma sessão

Versão 1, 2026-10-27; roteiro fixado antes de implementar.

## Pessoa e objetivo

Um recrutador recebe o endereço público e uma credencial demo e quer entender, em poucos minutos, como o assistente atende, o que custa e por que dá para confiar no resultado. O responsável, como administrador, demonstra que mudar a documentação fictícia muda o comportamento e que dá para voltar atrás.

## Condições iniciais

Mains com a v0.5.0 integrada; candidato v0.6.0 fixado por hashes dos dois repositórios. Três perfis publicados (Referência, Híbrido, Ajustado), catálogo de cenários sintéticos, base ativa identificada. QA real autorizado sob a campanha `v060-qa` (US$0,50) combinada com o ledger primário.

## Momentos

| Ação | Resultado esperado | Critério |
| --- | --- | --- |
| Entrar como demo | Vê Atendimento e Resultados; não vê Administração; backend recusa escrita | RF-73, RF-76, CA-43 |
| Escolher cenário e perfil e enviar | Resposta, estado do caso e versão da base; uma única POST | CA-47 |
| Repetir com o toggle em JEV | Decisão pelo JEV registrada; atendimento uma vez; rótulo correto | CA-32, CA-34, CA-35 |
| Falha de transporte após o envio | Pergunta pendente; recuperação só por GET; nenhum reenvio | CA-47 |
| Abrir Resultados | Etapas, ferramentas, modelos, versões, tokens, duração, custo, trechos e verificações com origem | RF-54, CA-50 |
| Pedir avaliação por IA | Estimativa, confirmação, resultado com rubrica e avaliador, custo separado; atendimento não repetido | CA-50 |
| Comparar dois ou três perfis | Estimativa, confirmação, dois gráficos e tabela; cada ponto abre as execuções; nada criado no atendimento original | CA-48 |
| Admin: pergunta de D na V1 | Diferença prevista ainda ausente | CA-49 |
| Admin: editar, construir, testar e ativar a V2 | Nova conversa consulta a ferramenta prevista e muda a orientação, com trecho e versão no trace | CA-41, CA-49 |
| Admin: retornar à V1 | Próxima conversa volta ao comportamento anterior | CA-41, CA-49 |
| Navegar, trocar abas e selecionar gráficos | Nenhuma chamada paga, publicação ou ação repetida | RF-70 |
| Acessar de outra rede | Interface funciona pelo IP público e porta, ou o impedimento fica registrado | CA-51 |
| Seguir o guia do zero | Docker e Streamlit sobem; demonstração reproduzível | CA-51 |

## Evidência e limites

QA usa a interface normal, HTTP, traces, snapshots e ledgers. Resultados reais, simulados e gravados ficam separados. Regressão real limitada e reuso explícito de evidências anteriores válidas. Esta história ainda não foi executada.
