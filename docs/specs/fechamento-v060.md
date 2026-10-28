# Especificação: simplificação, demonstração e fechamento v0.6.0

Versão 1 — 2026-10-27 — recorte aprovado pelo responsável em 2026-10-27, incluindo contratos `/v1` aditivos, migração 0008 e controles de exposição. Deriva da [especificação complementar 0.3](incrementos-pos-nucleo.md#recorte-final-v060). Plano em [fechamento-v060-plano.md](fechamento-v060-plano.md); história em [fechamento-v060.md](../historias/fechamento-v060.md); decisão em [ADR 0015](../architecture/decisions/0015-recorte-final-v060.md).

## Problema

As versões 0.1 a 0.5 entregaram atendimento multiagente, jornadas, perfis, JEV e base versionada, mas a interface reúne tudo numa tela técnica, a avaliação por modelo só roda pelo CLI, não há comparação de perfis navegável e a mudança de comportamento causada pela documentação nunca foi demonstrada. O plano antigo ainda previa duas versões com Evaluation Agent, propostas e uma plataforma de experimentos, escopo maior que o necessário para fechar o case.

## Usuário afetado

- **Recrutador ou avaliador:** experimenta cenários e perfis pela interface, sem acesso administrativo, dentro de um limite de consumo.
- **Responsável (administrador):** prepara perfis e documentos, demonstra a mudança da base e compartilha a demonstração.
- **Lojista sintético:** recebe atendimento consistente, na versão da base capturada no início.

## Resultado desejado

Um case compreensível, confiável e demonstrável: três áreas claras na interface, resultados rastreáveis com avaliação sob demanda, comparação pequena com dois gráficos, prova de que a documentação muda o comportamento e um guia único para rodar e compartilhar. Depois do aceite, a expansão funcional termina.

## Escopo

| Bloco | Conteúdo | Requisitos |
| --- | --- | --- |
| A. Simplificar | Atendimento, Resultados e Administração; poucos perfis preparados; erros com recuperação | RF-76, RF-70, CA-47 |
| B. Avaliação e observabilidade | Etapas, ferramentas, modelos efetivos, versões, tokens, duração, custo; verificações existentes; avaliador por modelo sob demanda | RF-54, RF-56, RF-77, CA-50 |
| C. Comparação | Dois ou três perfis × cenários explícitos; dois gráficos e uma tabela | RF-78, RF-75, CA-48 |
| D. Efeito da documentação | V1 → edição → candidata → teste → ativação → mudança observável → retorno | RF-63–66, RF-79, CA-41, CA-49 |
| E. Estabilização | Triagem da tarefa 46 e pendências documentadas | CA-28, CA-44, CA-45 |
| F. Execução e compartilhamento | Docker exercitado, guia único, IP público e porta, documentação final | RF-71–74, CA-43, CA-46, CA-51, CA-25 |

## Fora do escopo

Novo Evaluation Agent; workflow de propostas, candidatas e aprovações de melhorias; treinamento, otimização ou melhoria autônoma; plataforma de experimentos, exploração combinatória, agendamento, filas ou otimização automática; mapa de calor e outros gráficos; novas jornadas, provedores ou integrações; refatoração ampla; redesenho de autenticação, orçamento, migrações ou versionamento; troca de frameworks, união de repositórios ou serviços novos; hospedagem paga; enfraquecer controles para facilitar o acesso.

## Requisitos funcionais

### A. Interface em três áreas (RF-76)

1. **Atendimento:** seleção de cenário do catálogo (ou mensagem livre), perfil publicado, toggle LLM/JEV, conversa e estado do caso. A comparação só dos Routers continua disponível aqui, rotulada como tal (RF-48).
2. **Resultados:** execução selecionada com rota, etapas, ferramentas, modelo efetivo por agente, versões (perfil, prompts, base), tokens, duração e custo estimado; fontes e trechos recuperados; verificações e avaliações; comparações.
3. **Administração:** perfis e documentos, visível e utilizável só pelo papel `admin`; o backend continua recusando o papel `demo`.
4. Três perfis publicados para a demonstração (Referência, Híbrido e Ajustado), preservando a configuração por agente.
5. Mensagens de erro dizem o que aconteceu e qual ação recupera (atualizar por GET, aguardar, pedir ao administrador); nenhuma mostra erro interno.
6. Execução real, simulada e gravada continuam rotuladas de forma distinta.
7. Navegação, troca de aba e reruns do Streamlit não geram POST, inferência, publicação, build, teste ou ativação. Ações pagas exigem clique explícito e são protegidas contra repetição.

### B. Avaliação e observabilidade (RF-54, RF-56, RF-77)

1. Reutilizar o trace, o snapshot e a agregação por agente existentes; não criar Evaluation Agent.
2. Verificações determinísticas existentes (rota, estado, idioma, ferramentas, valores, conteúdo, proibições, fontes, sustentação) aplicam-se quando a execução veio de um cenário rotulado; a origem é o rótulo do cenário. Sem rótulo, só as verificações independentes de rótulo (sustentação e violações de saída, erros) e o restante aparece como "não avaliado".
3. Avaliação por modelo só sob demanda, sobre a resposta persistida, com a rubrica existente (`judge`, versão registrada): estimativa, confirmação e reserva antes; método, rubrica, evidências enviadas, configuração do avaliador (provedor, modelo, parâmetros) e custo registrados; custo separado do atendimento.
4. Repetir a avaliação com a mesma configuração devolve o registro existente, salvo pedido explícito de repetição.
5. Falhas críticas (resposta sem sustentação, assertiva ou promessa proibida, vazamento entre clientes, recusa indevida segundo o rótulo) aparecem individualmente e não se diluem em médias.
6. Não inventar notas por etapa; expor só os critérios efetivamente verificados.

### C. Comparação pequena e rastreável (RF-78)

1. Selecionar dois ou três perfis publicados e até três cenários do catálogo, com repetições explícitas (até duas).
2. Reaproveitar execuções existentes compatíveis (mesmo cenário, versão de perfil, mecanismo do Router, versão da base e prompts), rotuladas como gravadas.
3. Novas execuções só por ação explícita, com estimativa, confirmação e reserva; negação de orçamento interrompe as restantes e fica registrada como falha.
4. Efeitos isolados: nenhuma conversa, caso, tentativa ou encaminhamento do atendimento original é criado ou alterado.
5. Registrar configurações, versões e digests, versão da base capturada (uma para toda a comparação), repetições, tamanho da amostra e falhas.
6. Comparação de troca de modelo mantém fixos cenários, base, prompts, dados, ferramentas e avaliador; mais de uma mudança entre perfis fica marcada como exploratória.
7. Gráfico 1: custo × qualidade por perfil, com duração média e tamanho da amostra. Qualidade é a taxa de verificações determinísticas aprovadas sob os mesmos rótulos; nota do avaliador por modelo só quando todas as execuções do perfil foram avaliadas com a mesma configuração e rubrica. Sem avaliação, "não avaliado", nunca zero.
8. Gráfico 2: custo por agente/modelo; selecionar uma barra abre as execuções correspondentes.
9. Tabela: cenário, perfil, resultado, duração e custo, com acesso à execução.
10. Comparação só dos Routers aparece separada e nunca é somada ou comparada ao atendimento completo.

### D. Efeito da documentação no comportamento (RF-79)

1. Pergunta segura e pertinente, incluída no catálogo de cenários, que alcance o Knowledge e, pela rota `knowledge_and_support`, entregue o procedimento ao Customer Support.
2. Diferença esperada registrada antes da edição. Referência: na V1, o documento de dispositivos orienta o diagnóstico de conectividade; na V2, o procedimento acrescenta a verificação dos produtos contratados (`get_contract_snapshot`, já autorizada) antes de oferecer Link de Pagamento como alternativa, e a resposta só oferece a alternativa se o produto constar.
3. Antes de editar, executar a V1 e confirmar que a diferença ainda não ocorre; se já ocorrer, redefinir e registrar outra diferença antes da edição.
4. Conversas independentes com o mesmo cenário, perfil, prompts e ferramentas; só a versão da base varia (V1, V2, V1 restaurada).
5. Evidência: documento e trecho recuperados, versão da base no trace, fatos das ferramentas, ferramentas chamadas e resposta. Redação diferente ou marcador isolado não bastam.
6. A edição não cria prazo oficial, não altera regra financeira e não concede ferramenta; a V1 restaurada volta ao comportamento anterior.
7. O aceite da v0.5.0 permanece; a sonda inconclusiva anterior não é convertida em reprovação.

### E. Estabilização

| Item | Origem | Decisão | Motivo |
| --- | --- | --- | --- |
| R2-01 teto gravado com representação exata | Tarefa 46 | Corrigir | Integridade do orçamento |
| R2-02 publicação atômica do `.limit` | Tarefa 46 | Corrigir | Montagem concorrente não pode falhar nem sobrescrever |
| R2-03 prontidão e captura sem escrita quando o registro existe | Tarefa 46 | Corrigir | Prontidão consistente |
| R2-04 integridade Qdrant antes de `BEGIN IMMEDIATE` | Tarefa 46 | Risco aceito | QA r1–r3 sem contenção observada; mudança tocaria ativação concorrente aprovada |
| R2-05 timeout explícito no cliente OpenAI do CLI | Tarefa 46 | Corrigir | Timeouts consistentes |
| R2-07 `BudgetGuard.record`/`record_embedding` sem chamadores | Tarefa 46 | Remover se o desuso for comprovado | Código sem uso, remoção pequena |
| R2-08 testes de `max_retries == 0` e manifesto sem `chunks` | Tarefa 46 | Corrigir | Regressão sem custo |
| Timeout fixo de 20 s no cliente web | Tarefa 48 | Corrigir: coerente com `MAX_REQUEST_SECONDS` e margem; GET continua curto | ReadTimeout com atendimento concluído |
| Tarefas 47, 49–53 | QA v0.5 | Encerrar com evidência (QA r2/r3) | Já corrigidas e revalidadas |
| Ruff ausente no ambiente web | v0.5 | Corrigir ambiente ou dependência de desenvolvimento | Script estrito web deve terminar com código 0 |
| API do compose em `0.0.0.0:8000` | ADR 0012 | Ligar a `127.0.0.1` | Só a interface é exposta |
| Sem limite por sessão demo | RNF-10, RF-73 | Limite configurável de mensagens por sessão demo | Compartilhamento com risco controlado |
| Campo `evaluation` nos perfis | v0.4 | Manter no esquema, rotulado como não usado no atendimento | Preservar configuração existente |

Consistência de contratos entre cliente e backend, recuperação sem POST repetido, estados e confirmações coerentes e ausência de chamada paga em navegação têm prioridade em qualquer correção.

### F. Execução e compartilhamento

1. Guia único e curto: iniciar backend (Docker) e Streamlit, escolher cenários e conduzir a demonstração.
2. A versão empacotada em Docker é exercitada com chamadas reais limitadas, distinta de testes nativos e de inspeção de imagem.
3. Compartilhamento direto pelo IP público e porta: só o Streamlit exposto; API, Qdrant e `mocks` internos; administração protegida; credencial demo de baixo privilégio; HTTPS próprio quando possível; limite por sessão; janela definida e porta fechada ao fim.
4. Teste de outra rede; impedimento (CGNAT, roteador, firewall) documentado concretamente. Túnel é alternativa documentada, não dependência.
5. README, CHANGELOG, roteiro de teste manual e roteiro de vídeo alinhados à entrega real; o vídeo mostra a evolução por versões, o valor de cada entrega e as evidências de recuperação.

## Requisitos não funcionais

- **Compatibilidade:** `POST /messages` legado, MCP e contratos `/v1` existentes inalterados; acréscimos opcionais.
- **Permissões:** demo e admin verificados no backend; simplificar a interface não retira controles.
- **Orçamento:** teto agregado de US$5 descontado o consumo anterior (US$0,59837466 reconciliado em 2026-10-27); campanha de QA `v060-qa` com teto fixo de US$0,50 combinada com o ledger primário (teto persistente US$1, saldo US$0,65147156). Correções não renovam saldo. Custo desconhecido bloqueia.
- **Testes:** toda funcionalidade nova tem testes sem rede e sem custo; QA real pequeno, identificado e contabilizado.
- **Privacidade:** só dados sintéticos e fontes públicas; nada de `discovery/`.

## Critérios de aceitação

A v0.6.0 só está pronta com evidência de:

1. Regressão dos requisitos originais e jornadas essenciais preservadas (CA-28, CA-21–23/31).
2. Chat e recuperação funcionando na interface (CA-47, CA-44).
3. Toggle real LLM/JEV sem duplicação de atendimento (CA-32, CA-34, CA-35).
4. Perfis e comparação gráfica rastreáveis (CA-36, CA-37, CA-48).
5. Mudança de comportamento decorrente da documentação comprovada (CA-49).
6. Ativação e retorno da base preservados (CA-41 em regressão).
7. Avaliação sob demanda sem novo agente e sem nova inferência de atendimento (CA-50).
8. Orçamento, isolamento e permissões mantidos (CA-45, CA-43 nos papéis, isolamento de CA-48).
9. Execução reproduzível, instruções de compartilhamento e limitações explícitas (CA-51, CA-43).
10. README, testes manuais, changelog e vídeo alinhados à entrega real (CA-46, CA-25).

## Riscos

| Risco | Mitigação |
| --- | --- |
| Router real não escolher `knowledge_and_support` para a pergunta de D | Validar a pergunta na V1 antes de editar; ajustar a pergunta, não o critério |
| Variação do modelo mascarar a diferença em D | Diferença definida por ferramenta e fato verificáveis; repetição pequena registrada |
| Comparação longa estourar timeout HTTP | Execução fora da requisição no próprio processo da API, estado persistido e atualização por GET |
| CGNAT ou firewall impedir acesso externo | Verificar cedo; registrar impedimento; túnel como alternativa |
| Saldo do ledger primário (US$0,65) limitar QA e janela pública | Teto de campanha US$0,50; janela usa o saldo restante; elevar o `.limit` é decisão manual do responsável |
| Escopo crescer por obrigação histórica | Fora do escopo explícito; pendências registradas, sem v0.7.0 automática |

## Questões em aberto

| ID | Questão | Responsável | Bloqueia |
| --- | --- | --- | --- |
| Q11 | IP público sem CGNAT e redirecionamento de porta no roteador | Responsável | CA-51 (acesso externo) |
| Q14 | Janela de disponibilidade e porta pública | Responsável | Compartilhamento |
| Q15 | Regra de entrada no firewall do Windows para a porta do Streamlit (configuração de segurança da máquina) | Responsável | Teste de outra rede |
