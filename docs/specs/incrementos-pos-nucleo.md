<!-- Papel: especificação complementar dos incrementos posteriores ao núcleo (v0.1.0); promove a obrigatórios os itens das fatias 2 a 4 e acrescenta os requisitos novos. -->

# Especificação complementar: incrementos pós-núcleo

Versão 0.2 — 2026-10-26 — **aprovada pelo responsável em 2026-10-26**, com a sequência de versões até a 0.7.0. A 0.2 registra as respostas às questões Q7, Q9, Q10 e Q12.

Complementa a [especificação principal](assistente-multiagente-lojista.md) (v0.2), cujo núcleo foi entregue e validado como versão 0.1.0 (PR #1, commit `29a0088`). Os requisitos RF-01 a RF-37 e os critérios CA-01 a CA-17 e CA-26 continuam valendo e não podem regredir. O plano técnico está em [incrementos-pos-nucleo-plano.md](incrementos-pos-nucleo-plano.md).

## Relação com o escopo vigente

O pedido do responsável repetiu parte do que as fatias 2 a 4 já previam. Os itens repetidos mantêm seus identificadores; os novos começam em RF-38 e CA-27.

| Item do pedido | Situação antes deste documento | Tratamento |
| --- | --- | --- |
| 1. Continuidade e versionamento | **Novo** (só havia commits e tarefas) | RF-38 a RF-40 |
| 2. Projeto web separado, contratos antes das telas | **Parcial**: RF-36 previa uma interface, sem projeto separado nem regra de acesso só por API | RF-41 a RF-43 |
| 3. Memória e acompanhamento | **Já previsto**: RF-28, RF-29, RF-30, CA-18, CA-19 | Mantidos; RF-44 acrescenta registro de orientações e atualização do prefixo |
| 4. Servidor MCP | **Já previsto**: RF-31, CA-20 | Mantido; RF-45 acrescenta instruções e demonstração verificável |
| 5. Jornadas de preço, bandeiras e cancelamento | **Já previsto**: RF-32 a RF-34, CA-21 a CA-23 | Mantidos; RF-46 detalha o endpoint de simulação |
| 6. Toggle LLM/JEV | **Previsto como opcional**: RF-35, CA-24 | Passa a **obrigatório**; RF-47 e RF-48 acrescentam rotulagem de origem do resultado e bloqueio explícito |
| 7. Modelos por agente e perfis | **Novo** (a decisão 0005 só previa troca de modelo por configuração) | RF-49 a RF-53 |
| 8. Registro e avaliação por etapa | **Parcial**: traces por etapa e avaliação por caso com rubrica da resposta final já existem | RF-54 a RF-58 |
| 9. Ciclo de melhoria supervisionada | **Novo** | RF-59 a RF-62 |
| 10. Documentação editável e versões da base | **Novo** | RF-63 a RF-66 |
| 11. Interface e comparação gráfica | **Parcial**: RF-36 previa chat e painel técnico | RF-67 a RF-70 |
| 12. Compartilhamento com o recrutador | **Novo** | RF-71 a RF-74 |
| 13. Orçamento e economia de cota | **Já previsto**: RNF-02 e guarda persistente atômica | Mantido; RF-75 acrescenta estimativa antes de experimentos; RNF-12 registra a regra de delegação no desenvolvimento |
| 14. Critérios finais | **Parcial**: README e vídeo (CA-16, CA-25) | CA-27 a CA-46 |

## Problema

O núcleo responde bem a uma mensagem isolada, mas não acompanha uma conversa, não cobre as jornadas de maior risco financeiro (preço e contestação), não expõe as ferramentas por MCP e não permite comparar mecanismos e modelos. O responsável também não tem meios de editar a base fictícia, avaliar cada etapa, testar mudanças com segurança nem mostrar o sistema a um recrutador sem entregar acesso administrativo.

## Usuário afetado

- **Lojista** (sintético): conversa em vários turnos e espera continuidade.
- **Recrutador ou avaliador**: experimenta cenários e perfis autorizados pela interface, com limite de consumo.
- **Responsável (administrador)**: configura perfis, edita documentos, executa experimentos, aprova propostas e ativa versões.

## Resultado desejado

- Conversas com histórico, estado de atendimento e encaminhamento com contexto.
- Ferramentas de suporte acessíveis também por MCP, com as mesmas regras.
- Jornadas de preço, habilitação de bandeiras e cancelamento sobre dados sintéticos.
- Router alternável entre LLM e JEV por requisição, com o JEV real.
- Perfis de modelos por agente, versionados e comparáveis em gráficos rastreáveis.
- Avaliação por etapa com critérios, evidências e custo próprios.
- Mudanças em documentos, prompts e configurações passando por proposta, teste, aprovação, ativação e retorno.
- Interface Streamlit separada, consumindo só a API, compartilhável com o recrutador.
- Tudo dentro do teto de US$5, com versões e changelog.

## Escopo

Entrega em versões pequenas, cada uma utilizável e com changelog e instruções de retorno. A sequência do pedido foi mantida, com um ajuste de dependência: a interface começa na v0.4.0, porque o toggle LLM/JEV obrigatório precisa dela, e é completada nas versões seguintes.

| Versão | Conteúdo | Requisitos |
| --- | --- | --- |
| 0.1.0 | Núcleo entregue (referência reproduzível) | RF-01 a RF-37 |
| 0.2.0 | Versionamento, memória, acompanhamento e MCP | RF-28 a RF-31, RF-38 a RF-40, RF-44, RF-45 |
| 0.3.0 | Jornadas de preço, bandeiras e cancelamento | RF-32 a RF-34, RF-46 |
| 0.4.0 | Router JEV, modelos por agente, perfis, API da interface e projeto Streamlit com chat, perfis e toggle | RF-35, RF-41 a RF-43, RF-47 a RF-53 |
| 0.5.0 | Versões da base e editor de documentos | RF-63 a RF-66 |
| 0.6.0 | Evaluation Agent por etapa e ciclo de melhoria supervisionada | RF-54 a RF-62 |
| 0.7.0 | Experimentos e gráficos, compartilhamento com o recrutador, README, changelog e roteiro de vídeo finais | RF-36, RF-67 a RF-75 |

## Fora do escopo

- Dados, sistemas ou documentos reais da Getnet; fórmula real de precificação.
- Executar cancelamentos, alterações contratuais, habilitações, ressarcimentos ou transações.
- Treinamento ou ajuste fino de modelos; melhoria autônoma sem aprovação humana.
- Hospedagem paga, compra de créditos ou contratação de serviços.
- Alterar configurações globais da máquina ou do roteador do responsável (abrir portas no roteador é ação do responsável).

## Requisitos funcionais

Os requisitos RF-28 a RF-36 da especificação principal valem como escritos, com RF-35 agora obrigatório.

### Versionamento

- **RF-38** A entrega inicial deve ter uma referência reproduzível (tag `v0.1.0` no commit validado) e cada incremento deve gerar uma versão SemVer com tag, mediante autorização do responsável.
- **RF-39** Um `CHANGELOG.md` deve registrar, por versão, funcionalidades, mudanças de contratos e de dados, validações, limitações e instruções para voltar à versão anterior.
- **RF-40** Mudanças de esquema de dados devem ser migrações numeradas e reversíveis; a versão do esquema, da base de conhecimento e dos prompts aparece em `/ready` e nos traces.

### Projeto da interface

- **RF-41** A interface deve ser um projeto separado em Streamlit (`C:\workspace\ai-getnet-case-web`), que acessa o backend apenas pela API HTTP, nunca arquivos, SQLite ou Qdrant.
- **RF-42** Os contratos da API usados pela interface devem ser definidos e versionados antes das telas (OpenAPI), com respostas simuladas para desenvolvimento da interface sem o backend.
- **RF-43** A API do assistente deve continuar funcionando sozinha, com o mesmo `POST /messages` e o mesmo Docker; a interface é um consumidor a mais.

### Memória e acompanhamento (complementa RF-28 a RF-30)

- **RF-44** O atendimento deve registrar orientações dadas, tentativas, resultados e pendências por caso. O prefixo de histórico e healthcheck é reaproveitado na conversa e refeito quando vencido ou quando o assunto muda.

### MCP (complementa RF-31)

- **RF-45** O servidor MCP deve vir com instruções de execução e uma demonstração verificável: um cliente MCP lista as ferramentas, chama ao menos duas e recebe o erro estruturado ao tentar recurso de outro cliente.

### Jornadas (complementa RF-32 a RF-34)

- **RF-46** O PRaaS fictício deve expor um endpoint de simulação que recebe a operação e o contexto aplicável e devolve identificação da regra, versão, aplicabilidade, componentes e parcelas; a cobrança vem de fonte independente; a comparação é determinística em centavos. Nenhum valor financeiro é calculado pelo modelo.

### Router JEV (complementa RF-35, agora obrigatório)

- **RF-47** O JEV deve ser integrado de verdade (`POST /v1/systemone`, modelo versionado), produzindo o mesmo contrato de decisão do Router validado pelo backend. Mecanismo, provedor, modelo, versão, confiança quando houver, duração e custo estimado ficam registrados. Indisponibilidade ou decisão inválida produzem erro explícito; o sistema nunca troca JEV por LLM sem avisar.
- **RF-48** Na comparação de roteamento, só as decisões dos Routers são executadas; o atendimento roda uma vez, com o mecanismo selecionado. A interface distingue execução real, execução simulada e resultado gravado anteriormente.

### Modelos por agente e perfis

- **RF-49** Cada agente (Router, Knowledge, Customer Support, Escalation, Personality e Evaluation) pode ter provedor, modelo e parâmetros próprios, escolhidos entre combinações implementadas e compatíveis com a função (ferramentas, saída estruturada, busca web). Provedores: OpenAI, DeepSeek e TypeSafe (JEV, só para a decisão do Router). Identificadores, capacidades e preços vêm da API do provedor e da documentação oficial, verificados antes de cada provedor ser oferecido; uma capacidade ausente (por exemplo, busca web) impede o uso do modelo na função que a exige.
- **RF-50** Perfis de execução são salvos, versionados e imutáveis depois de publicados. Perfis iniciais: Referência; Híbrido (só o Router com JEV); Ajustado (um especialista alterado por vez).
- **RF-51** A configuração é congelada no início de cada execução; mudanças posteriores não a afetam. O trace registra o perfil, sua versão e o modelo efetivamente usado em cada etapa.
- **RF-52** O modelo de embeddings é tratado à parte: trocá-lo exige reconstruir e versionar o índice (RF-64).
- **RF-53** Credenciais ficam só no servidor; a interface vê nomes e capacidades, nunca chaves.

### Registro e avaliação por etapa

- **RF-54** Cada execução gera um registro determinístico das etapas, agentes, ferramentas, modelos usados, duração, tokens e custo, extraído da execução e dos retornos dos provedores, com as evidências mínimas para avaliação (identificadores dos trechos, resultados das ferramentas, decisões estruturadas).
- **RF-55** Um Evaluation Agent, fora do caminho do atendimento, avalia as etapas com critérios próprios: Router (rota e esclarecimento), Knowledge (relevância das fontes e sustentação das afirmações), Customer Support (ferramentas, consistência dos fatos, orientação), Personality (clareza e preservação de fatos, valores, datas e fontes) e Escalation (contexto, motivo e pendências).
- **RF-56** Cada avaliação registra critério, resultado, evidência, método (determinístico ou modelo), versão da rubrica e custo. Sem evidência suficiente, o resultado é "não avaliado".
- **RF-57** Verificações determinísticas rodam em todas as execuções; o julgamento por modelo roda sob demanda ou por amostragem, e uma chamada pode avaliar várias etapas do mesmo registro.
- **RF-58** Falhas críticas (vazamento entre clientes, valor sem evidência, promessa financeira, recusa indevida) aparecem individualmente e bloqueiam a aprovação, independentemente da média.

### Melhoria supervisionada

- **RF-59** O ciclo é: execução → avaliação → proposta → versão candidata → testes de regressão → aprovação humana → ativação, com retorno à versão anterior.
- **RF-60** Propostas do avaliador alteram somente documentos fictícios, prompts ou perfis, e contêm problema observado, evidências, alteração sugerida e critério de melhoria. Permissões, guardrails, orçamento e regras financeiras não podem ser alterados por proposta.
- **RF-61** A candidata é testada nos cenários de desenvolvimento e verificada contra regressões nos reservados; o resultado fica anexado à proposta.
- **RF-62** Ativação e retorno registram quem decidiu, quando, qual versão e quais evidências sustentaram a decisão. O recurso é apresentado como melhoria supervisionada, não como treinamento.

### Documentação editável e versões da base

- **RF-63** A interface lista documentos com origem, versão e estado e permite editar só a documentação operacional fictícia, com rascunho e comparação das alterações. Fontes oficiais coletadas não são editáveis.
- **RF-64** Uma nova versão da base é preparada (fragmentação e índice próprios), testada e ativada explicitamente; uma versão incompleta nunca substitui a ativa, e a anterior pode ser restaurada.
- **RF-65** Cada execução consulta uma única versão identificada da base, registrada no trace.
- **RF-66** Documentos recuperados continuam sendo evidência: editá-los não concede ferramentas, não muda instruções dos agentes e não substitui o PRaaS como autoridade financeira.

### Interface e comparação gráfica (complementa RF-36)

- **RF-67** A interface oferece: chat com seleção de cenários sintéticos; continuidade e estado do atendimento; seleção e configuração de perfis; toggle LLM/JEV; execução explícita de experimentos; edição e publicação controlada de documentos; avaliações e propostas; inspeção de execuções (fontes, ferramentas, versões, falhas), sem mostrar raciocínio interno dos modelos.
- **RF-68** Gráficos prioritários: custo × qualidade por perfil com tempo de resposta; custo por agente e modelo; mapa de resultados por cenário e critério; linha do tempo das etapas executadas. Cada ponto abre os registros que o explicam.
- **RF-69** Experimentos mantêm fixos cenários, documentos, prompts, dados, ferramentas e avaliador ao comparar modelos (e fixam o resto ao comparar documentos); usam conversas independentes; registram repetições e tamanho da amostra; marcam como exploratória qualquer comparação com mais de uma mudança; e não criam casos ou encaminhamentos no atendimento real.
- **RF-70** Navegação, atualização de gráficos e reexecuções do Streamlit nunca disparam chamadas pagas: resultados gravados são reaproveitados e novas execuções exigem ação explícita.

### Compartilhamento com o recrutador

- **RF-71** A interface pode ser compartilhada pelo IP público e porta da máquina do responsável, com instruções de inicialização, configuração e teste de acesso externo. Túnel só como alternativa documentada se o acesso direto falhar.
- **RF-72** Só a interface é exposta; API, Qdrant e SQLite ficam acessíveis apenas internamente.
- **RF-73** Acesso de demonstração e de administração são separados e verificados no backend. O perfil de demonstração experimenta cenários e perfis autorizados, com limite próprio de consumo; publicar documentos, ativar versões e mudar configurações é exclusivo do administrador.
- **RF-74** A documentação deixa claro que a disponibilidade depende de a máquina, a conexão e os serviços estarem ativos.

### Orçamento

- **RF-75** Antes de cada experimento ou avaliação por modelo, a interface mostra o número de execuções e o custo estimado e exige confirmação. Embeddings, busca, JEV, comparações e avaliações passam pela mesma guarda persistente; custo desconhecido bloqueia a chamada e nunca aparece como zero.

## Requisitos não funcionais

- **RNF-09 Compatibilidade:** `POST /messages` mantém o contrato da v0.1.0; campos novos são opcionais. A API da interface é versionada (`/v1`).
- **RNF-10 Segurança da exposição:** a interface exposta exige autenticação, usa HTTPS quando possível (certificado próprio do Streamlit), limita requisições por sessão e não revela erros internos.
- **RNF-11 Orçamento:** teto total de US$5 mantido, descontado o já gasto (US$0,31 em 2026-10-26). A demonstração pública tem sublimite próprio e configurável, inicialmente US$1,00, que pode ser aumentado por decisão do responsável sem ultrapassar o teto total.
- **RNF-12 Processo de desenvolvimento:** o trabalho ocorre na sessão principal. Subagentes só com autorização explícita de escopo, quantidade, modelo e esforço, sem herança silenciosa nem troca por modelo mais caro. O consumo da ferramenta de desenvolvimento e o orçamento das APIs da aplicação são controles separados.
- **RNF-13 Testes:** toda funcionalidade nova tem testes sem rede e sem custo; rodadas reais são limitadas e registradas em evidências. Nenhum requisito é dado como concluído só com mock ou documentação.

## Casos de uso

| ID | Situação | Resultado esperado |
| --- | --- | --- |
| UC-19 | "Já fiz isso e continua sem conexão" na mesma conversa | Usa o histórico, não repete o passo, oferece o próximo ou encaminha no segundo ciclo |
| UC-20 | Lojista confirma "voltou a funcionar" | Caso `resolved` com evidência `customer_confirmed` |
| UC-21 | `conversation_id` de outro cliente | Recusado sem revelar a conversa |
| UC-22 | Cliente MCP chama as ferramentas | Mesmos resultados e erros da camada de domínio |
| UC-23 | "Por que descontaram mais do que a taxa que eu vi?" | Comparação PRaaS × cobrança: coerente, condições diferentes, divergência ou evidência insuficiente |
| UC-24 | "Pedi a habilitação da bandeira e ainda não consigo vender" | Reaproveita o protocolo existente e distingue pedido, ativação e equipamento |
| UC-25 | "Quero encerrar meu contrato" | Não chama ferramentas de venda; oferece esclarecimento e atendente |
| UC-26 | Toggle JEV numa requisição | Decisão pelo JEV registrada; especialistas inalterados |
| UC-27 | JEV indisponível | Erro explícito; nenhuma troca silenciosa |
| UC-28 | Experimento de perfis | Estimativa, confirmação, execução isolada e gráfico rastreável |
| UC-29 | Edição de documento fictício | Rascunho, comparação, índice candidato, teste, ativação e retorno |
| UC-30 | Proposta do avaliador | Candidata testada, aprovação registrada, ativação e retorno |
| UC-31 | Recrutador acessa pelo IP público | Usa cenários autorizados dentro do limite; não vê administração |

## Critérios de aceitação

- [x] **CA-27** A tag `v0.1.0` reproduz a entrega inicial; cada versão nova tem changelog com instruções de retorno.
- [x] **CA-28** Os critérios do núcleo continuam passando em cada versão (testes e avaliação de regressão). Comprovado na v0.2.0; refazer a cada versão.
- [x] **CA-29** UC-19 a UC-21 demonstrados com testes sem custo e com uma rodada real registrada (complementa CA-18 e CA-19).
- [x] **CA-30** Demonstração MCP verificável conforme RF-45 (complementa CA-20).
- [ ] **CA-31** Os quatro comportamentos de preço, a habilitação e o cancelamento demonstrados com dados sintéticos (complementa CA-21 a CA-23).
- [ ] **CA-32** Toggle LLM/JEV real funcionando no Streamlit, com mecanismo, versão, duração e custo registrados (complementa CA-24).
- [ ] **CA-33** Indisponibilidade do JEV produz erro explícito, sem troca silenciosa.
- [ ] **CA-34** A comparação de roteamento executa só os Routers; o atendimento roda uma vez.
- [ ] **CA-35** A interface rotula cada resultado como real, simulado ou gravado.
- [ ] **CA-36** Três perfis versionados (Referência, Híbrido, Ajustado), com configuração congelada por execução e modelo efetivo por etapa no trace.
- [ ] **CA-37** Combinações incompatíveis ou não implementadas não aparecem na interface e são recusadas pela API.
- [ ] **CA-38** Avaliação por etapa com critério, resultado, evidência, método, versão da rubrica e "não avaliado" quando cabível; custos de atendimento e de avaliação separados.
- [ ] **CA-39** Uma falha crítica isolada aparece e bloqueia a aprovação mesmo com média alta.
- [ ] **CA-40** Ciclo completo demonstrado: proposta, candidata, regressão, aprovação, ativação e retorno, com autoria e evidências.
- [ ] **CA-41** Edição de documento fictício com rascunho, comparação, índice candidato, teste, ativação e retorno; fontes oficiais não editáveis; versão da base no trace.
- [ ] **CA-42** Os quatro gráficos prioritários abrem os registros que os explicam; navegar não gera chamadas pagas.
- [ ] **CA-43** Compartilhamento pelo IP público validado de fora da rede local, ou impedimento concreto registrado; perfil de demonstração sem acesso administrativo.
- [ ] **CA-44** Estados de carregamento, ausência de dados, erro e indisponibilidade tratados nas telas.
- [ ] **CA-45** Gasto total dentro de US$5, com custo estimado antes de experimentos e bloqueio de custo desconhecido.
- [ ] **CA-46** README, changelog e roteiro de vídeo atualizados; nenhum dado privado do discovery publicado.

## Riscos

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Provedor de internet com CGNAT ou roteador sem redirecionamento de porta | Acesso direto pelo IP público impossível | Validar cedo (v0.4.0); registrar o impedimento; túnel como alternativa documentada |
| Exposição da máquina pessoal na internet | Abuso, consumo de cota, ataque | Só a interface exposta, autenticação, HTTPS, limite por sessão e sublimite de orçamento |
| JEV com acurácia menor em português | Rotas erradas no modo Híbrido | Medir por idioma; registrar; não esconder o resultado |
| DeepSeek sem as mesmas capacidades da OpenAI (busca web, formato de saída estruturada) | Perfis inválidos ou respostas fora do contrato | Catálogo de capacidades verificado; validação da saída pelo mesmo código; só dados sintéticos enviados |
| Quantidade de recursos novos | Atraso e pressa nas últimas versões | Versões pequenas; cada uma utilizável e com critérios próprios |
| Avaliador por modelo com viés ou visão parcial | Notas enganosas | Critérios determinísticos primeiro; evidências anexadas; falhas críticas isoladas |
| Experimentos consumirem o orçamento | Ultrapassar o teto | Estimativa e confirmação; reserva atômica; sublimites |
| Duas cópias de regra (API e interface) | Divergência | Interface sem regra de negócio; tudo validado no backend |

## Questões em aberto

| ID | Questão | Responsável | Bloqueia |
| --- | --- | --- | --- |
| Q7 | ~~Aprovar esta especificação e a sequência de versões~~ Aprovada em 2026-10-26, até a v0.7.0 | Responsável | — |
| Q8 | Autorizar a tag `v0.1.0` na `main` | Responsável | RF-38 |
| Q9 | ~~Repositório próprio e template para o projeto web~~ Sim: repositório próprio no GitHub, criado a partir do ai-dev-template | Responsável | — |
| Q10 | Sublimite de gasto da demonstração: ~~valor~~ inicial US$1,00, aumentável pelo responsável quando necessário (RNF-11). Janela de disponibilidade ainda a definir | Responsável | v0.7.0 (janela) |
| Q11 | Disponibilidade de redirecionamento de porta no roteador e IP público sem CGNAT | Responsável (verificação na v0.4.0) | RF-71 |
| Q12 | ~~Provedores além de OpenAI e JEV~~ Sim: DeepSeek incluído como provedor por agente (RF-49) | Responsável | — |
