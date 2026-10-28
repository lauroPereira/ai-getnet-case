# Roteiro de teste manual v0.6.0

Segue os momentos da [história v0.6.0](historias/fechamento-v060.md). Execute com o [guia](guia-demonstracao.md) (backend no Docker ou nativo, Streamlit nativo). Registre para cada passo: horário, `request_id`, versão da base, custo exibido e resultado (aprovado/reprovado/bloqueado). Chamadas reais só dentro da campanha autorizada.

| # | Ação | Resultado esperado | Critério |
| --- | --- | --- | --- |
| 1 | Entrar como **demo** | Abas Atendimento e Resultados; sem Administração. Tentar uma escrita admin pela API (`POST /v1/profiles/reference/publish`) retorna `403` | RF-73, RF-76, CA-43 |
| 2 | Atendimento: escolher "Recebimento das vendas de ontem", perfil Referência, Router LLM, **Enviar cenário** | Resposta, estado do caso e versão da base; uma única `POST /v1/messages` (log da API) | CA-47 |
| 3 | Repetir com Router **JEV** | Execução com `router_mechanism=jev`, modelo `typesafe:jev-1.14.0`; atendimento uma vez; rótulo "Execução real" | CA-32, CA-34, CA-35 |
| 4 | Simular falha de transporte após o envio (por exemplo `BACKEND_MESSAGE_TIMEOUT_SECONDS=1` numa pergunta longa) | Pergunta pendente; **Atualizar conversa** recupera por GET; nenhum reenvio | CA-47 |
| 5 | Resultados da execução do passo 2 | Etapas, ferramentas, modelo efetivo por agente, prompts, versão da base, tokens, duração, custo, fontes, trechos, verificações com origem "rótulos do cenário", "Não avaliado" na avaliação | RF-54, CA-50 |
| 6 | Mensagem livre e Resultados | Verificações só independentes de rótulo; demais listadas como não avaliadas | RF-77 |
| 7 | **Estimar avaliação por IA** → confirmar → **Avaliar com IA** | Estimativa sem custo; avaliação com rubrica `judge` v2, avaliador fixo, evidências e custo separado; atendimento não repetido (ledger: uma linha `agent=judge`, `request_id=eval:<id>`) | CA-50 |
| 8 | Repetir a avaliação sem marcar "Repetir mesmo assim" | Devolve o registro existente; nenhuma nova linha no ledger | RF-77 |
| 9 | Comparar 2–3 perfis em 1–2 cenários | Estimativa (novas, reaproveitadas, base, exploratória), confirmação, estado final por **Atualizar comparação**; dois gráficos e tabela; barra abre as execuções; contagens de conversas/mensagens do atendimento original inalteradas | CA-48 |
| 10 | Admin: pergunta de D na V1 | `get_contract_snapshot` ausente nas etapas | CA-49 |
| 11 | Admin: editar, construir, testar e ativar a V2; perguntar de novo em nova conversa | `get_contract_snapshot` presente, trecho novo nos `hits`, versão candidata no trace | CA-41, CA-49 |
| 12 | Admin: retornar à V1; perguntar de novo | Versão anterior no trace e comportamento da V1 | CA-41, CA-49 |
| 13 | Navegar, trocar abas, mudar seleção de gráfico, recarregar | Nenhuma `POST` nova no log da API; nenhuma linha nova no ledger | RF-70 |
| 14 | Demo: iniciar mais ações pagas (mensagens, comparações, avaliações) que `DEMO_SESSION_MESSAGE_LIMIT` | `429 demo_message_limit_reached` com ação de recuperação na interface | RNF-10, RF-73 |
| 15 | Acessar de outra rede pelo IP público e porta | Interface abre e funciona, ou impedimento concreto registrado (CGNAT, roteador, firewall) | CA-51 |
| 16 | Seguir o guia do zero numa pasta limpa | Docker e Streamlit sobem; demonstração reproduzível | CA-51 |

Ao final: conferir no ledger zero reservas abertas e somar o gasto da rodada à campanha.
