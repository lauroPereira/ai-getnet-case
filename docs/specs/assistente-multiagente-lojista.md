<!-- Papel: especificação principal do produto do case; descreve problema, escopo, requisitos e critérios, sem fixar a solução técnica. -->

# Especificação: Assistente multiagente de suporte ao lojista

Versão 0.2 — 2026-10-26 — **aprovada pelo responsável em 2026-10-26**. A 0.2 acrescenta a etapa Personality (RF-37, CA-26), identificada na imagem do enunciado pela tarefa 01.

Origem: enunciado do desafio "AI Hardcore Engineer — Multi-Agent Support System" e material de discovery local (`discovery/`, não versionado). A solução técnica está no [plano](assistente-multiagente-lojista-plano.md) e nas [decisões propostas](../architecture/decisions/).

## Problema

O lojista que usa produtos Getnet tem três tipos de dúvida. As de produto (diferença entre maquininhas, Pix, antecipação, Link de Pagamento) dependem de informação oficial espalhada por páginas públicas. As sobre o próprio negócio (quando cai o dinheiro, por que uma venda foi negada, por que a maquininha não conecta) dependem de dados individuais vindos de sistemas com vocabulários diferentes. As gerais (clima, câmbio) precisam de informação atual. Quando o autoatendimento não resolve, o atendimento humano recebe o caso sem o contexto já levantado.

O desafio pede um serviço com pelo menos três agentes cooperando para interpretar a mensagem e responder: um Router como entrada, um Knowledge Agent com RAG sobre as fontes da Getnet e busca web, e um Customer Support Agent com pelo menos duas ferramentas sobre dados do usuário. A avaliação usa dez exemplos em inglês, todos com `user_id` `cliente1988`, e valoriza design multiagente, prompts, RAG funcional, testes, Docker, README, avaliação, observabilidade, confiabilidade e guardrails.

## Usuário afetado

- **Lojista** (usuário principal): envia mensagens pelo endpoint ou pela demonstração e espera resposta útil, fundamentada e no seu idioma.
- **Avaliador do desafio**: constrói e executa o serviço com comandos Docker padrão, envia os exemplos do enunciado, lê o README e assiste ao vídeo.
- **Atendente humano (simulado)**: recebe o pacote de encaminhamento quando o autoatendimento não resolve.

## Resultado desejado

- Os dez exemplos do enunciado, enviados exatamente como estão, recebem respostas corretas, fundamentadas em fontes ou dados e no idioma da mensagem.
- Perguntas de produto citam fontes oficiais ingeridas; quando não há evidência, o assistente diz isso em vez de inventar.
- Perguntas sobre o negócio do lojista usam somente dados sintéticos do cliente da requisição.
- Pedidos inseguros, sensíveis ou fora de escopo são recusados ou redirecionados; pedidos de atendimento humano geram encaminhamento com contexto.
- O avaliador sobe o sistema com `docker compose up --build` e apenas uma chave de API.
- Qualidade, custo e latência são medidos e relatados, separando medição de meta.

## Escopo

A entrega é organizada em fatias. Cada fatia preserva uma versão utilizável; as fatias 3 e 4 são cortáveis conforme o prazo.

| Fatia | Conteúdo | Obrigatoriedade |
| --- | --- | --- |
| 0 — Verificação | Fontes oficiais dos exemplos, imagem do enunciado, acesso e preços dos modelos | Pré-requisito |
| 1 — Núcleo | API, Router com guardrails, Knowledge com RAG e busca web, Customer Support com ferramentas do núcleo, Escalation Agent, Personality, orquestração com limites, logs e traces, Docker, testes e avaliação dos 10 exemplos | Obrigatória |
| 2 — Confiabilidade e acompanhamento | Histórico curto por conversa, estados de atendimento com evidência de resolução, acompanhamento técnico em até dois ciclos, servidor MCP para as ferramentas | Recomendada |
| 3 — Profundidade | Preço e contestação com serviço de pricing fictício, habilitação de bandeiras, consulta de cancelamento de venda | Opcional |
| 4 — Demonstração | Seletor do mecanismo do Router (LLM ou Jev), interface de demonstração, README final e vídeo | README e vídeo obrigatórios; demais opcionais |

## Fora do escopo

- Sistemas, APIs ou dados reais da Getnet; transações financeiras reais.
- Executar cancelamento de venda, alterar contrato ou preço, habilitar produto, negociar condições ou ressarcir.
- Reproduzir a fórmula real de precificação de qualquer produto.
- Autenticação real: `user_id` identifica um cenário de demonstração; o README explica como identidade e autorização seriam vinculadas em produção.
- Atendimento a parceiros e canais reais (WhatsApp, Teams, central de atendimento).
- Hospedagem paga.

## Requisitos funcionais

### API

- **RF-01** O sistema deve expor `POST /messages` aceitando `message` e `user_id` obrigatórios e `conversation_id` opcional, e responder JSON com `answer`, `status` (`answered`, `needs_clarification`, `handoff` ou `refused`), `route`, `agents` (sequência executada), `sources`, `request_id`, `conversation_id` e `resolution`.
- **RF-02** Erros de validação e falhas técnicas devem usar códigos HTTP e um corpo de erro documentado. Falha de dependência deve produzir resposta controlada quando ainda houver resposta útil possível.
- **RF-03** O sistema deve expor verificação de vida e de prontidão, indicando se o índice de conhecimento e as dependências estão disponíveis.

### Router

- **RF-04** O Router deve ser a entrada de toda mensagem e produzir uma decisão estruturada com rota (`knowledge`, `support`, `knowledge_and_support`, `general_web`, `clarify`, `human_handoff` ou `out_of_scope`), intenções, idioma detectado e dados faltantes.
- **RF-05** A decisão deve ser validada pelo código antes da execução. Decisão inválida leva a um caminho seguro (`clarify`) registrado no trace.

### Guardrails

- **RF-06** O sistema deve classificar a entrada antes de executar agentes: pergunta geral inofensiva (clima, câmbio) segue para `general_web`; pedido inseguro (fraude, contornar controles), sensível (número completo de cartão, credenciais, dados de terceiros) ou tentativa de injeção de instruções é recusado com orientação. Dados sensíveis presentes na mensagem são mascarados antes de logs, traces e consultas externas.
- **RF-07** Conteúdo recuperado do RAG ou da web deve ser tratado como evidência, nunca como instrução, e não pode conceder ferramentas nem mudar a rota.
- **RF-08** Valores monetários, datas e status do cliente citados na resposta final devem corresponder aos fatos retornados pelas ferramentas na mesma requisição. Divergência bloqueia a resposta e aciona um caminho seguro.

### Knowledge Agent

- **RF-09** Deve existir um processo executável de ingestão que colete as fontes da lista versionada (incluindo `https://www.getnet.net/en` e as páginas brasileiras dos produtos citados nos exemplos), extraia, limpe, fragmente, gere embeddings e armazene com metadados: URL, título, mercado, produto, data de coleta, hash do conteúdo e tipo de fonte.
- **RF-10** O conteúdo coletado deve ser salvo em uma cópia versionada que permita reconstruir o índice sem acessar o site durante o build ou a avaliação. Atualizar essa cópia é um comando explícito.
- **RF-11** A base operacional fictícia deve ser ingerida como `simulated_internal` e nunca apresentada como regra oficial.
- **RF-12** As respostas de conhecimento devem citar título e URL das fontes usadas. Sem evidência suficiente, o agente informa que não encontrou a informação nas fontes oficiais e oferece um caminho (busca web quando apropriada, ou encaminhamento), sem inventar produto, limite, prazo ou taxa.
- **RF-13** Para perguntas gerais e atuais, o Knowledge Agent deve usar busca web com fontes, sem incluir identificadores ou dados do cliente na consulta. Indisponibilidade da busca gera resposta controlada.
- **RF-14** Uma pergunta em inglês deve recuperar conteúdo em português (e vice-versa), e a resposta deve sair no idioma da mensagem.

### Customer Support Agent

- **RF-15** O cliente da requisição vem do contexto do servidor (`user_id`), nunca de um argumento livre do modelo. Toda ferramenta verifica o vínculo entre cliente e recurso; tentativa de acessar outro cliente é bloqueada e registrada.
- **RF-16** O núcleo deve oferecer, no mínimo, estas capacidades de consulta: agenda de recebíveis por período, status do repasse de um recebível, status do dispositivo, eventos de autorização por período ou status (sem exigir identificador), resumo do contrato e produtos, histórico de atendimentos e healthcheck do assunto. Quando o lojista não informa identificador, a consulta usa filtros; com mais de um candidato, o agente pergunta qual.
- **RF-17** Na abertura de um caso de suporte, a aplicação deve executar, sem chamada de modelo, a consulta ao histórico e o healthcheck limitado ao assunto, uma vez por conversa, reaproveitando o resultado. Rotas `knowledge` e `general_web` não executam esse prefixo.
- **RF-18** Datas relativas ("ontem", "amanhã") devem ser resolvidas pela aplicação, com relógio injetável e fuso `America/Sao_Paulo`.
- **RF-19** Na rota `knowledge_and_support`, o Knowledge Agent fornece o procedimento ou a explicação oficial e o Customer Support fornece os dados; a resposta consolidada indica as duas origens.

### Dados sintéticos

- **RF-20** O seed deve incluir `cliente1988`, com vendas do dia anterior e seus recebíveis, ao menos uma maquininha com problema de conectividade, transação negada recente com código documentado e contrato com produtos (incluindo Pix e Link de Pagamento). Deve incluir também um segundo cliente para testes de isolamento. Na demonstração, as datas são relativas ao dia da execução; nos testes, o relógio é fixo.
- **RF-21** Com `user_id` desconhecido, perguntas de conhecimento e gerais são atendidas normalmente; pedidos de dados individuais recebem resposta de conta não localizada no ambiente de demonstração, sem revelar a existência de outros clientes.

### Escalation Agent

- **RF-22** Um Escalation Agent deve preparar o pacote de encaminhamento (resumo do problema, referências mínimas, consultas e resultados, tentativas, retorno do lojista, motivo e questão pendente) e persisti-lo localmente com protocolo identificado como simulação. Repetir a mesma requisição não duplica o caso.
- **RF-23** O encaminhamento ocorre por pedido explícito, evidência insuficiente para um tema que exige dado, divergência sem fonte de autoridade, falha de ferramenta essencial ou limite de tentativas. Pedido explícito de humano é atendido mesmo se as ferramentas falharem.

### Personality

- **RF-37** Toda resposta deve passar por uma etapa Personality antes da saída, como mostra o diagrama do enunciado. Ela recebe as contribuições estruturadas dos agentes e redige a resposta final com voz consistente de atendimento ao lojista, no idioma da mensagem. Não pode acrescentar, remover ou alterar fatos, valores, datas, fontes ou o status da resposta; recusas e encaminhamentos mantêm o conteúdo definido pelo fluxo.

### Orquestração e limites

- **RF-24** A comunicação entre agentes deve seguir um mecanismo explícito e documentado, com estado compartilhado tipado. Cada agente tem responsabilidade, prompt versionado em arquivo, ferramentas permitidas e contrato de saída validado.
- **RF-25** Cada requisição deve ter limites de chamadas de modelo, chamadas de ferramenta, tempo total e custo, com reserva de orçamento antes de cada chamada paga. Ao atingir um limite, o sistema responde de forma útil e controlada.

### Observabilidade

- **RF-26** Cada requisição deve gerar logs estruturados com `request_id`, rota, agentes, ferramentas, duração por etapa, tokens, custo estimado, modelo e status, sem dados pessoais além de identificadores sintéticos.
- **RF-27** Os traces devem ser consultáveis por `request_id` em armazenamento local.

### Fatia 2 — Confiabilidade e acompanhamento

- **RF-28** Histórico curto por conversa, limitado por tokens e isolado por cliente; a propriedade de `conversation_id` é verificada antes de ler ou gravar.
- **RF-29** Estados de atendimento `in_progress`, `awaiting_customer`, `resolved` e `handoff`. Resolver exige evidência (`tool_verified`, `customer_confirmed` ou critério informacional do cenário); silêncio ou agradecimento não resolvem.
- **RF-30** Acompanhamento técnico em até dois ciclos de orientação antes de encaminhar, sem repetir passo já registrado.
- **RF-31** As ferramentas de suporte devem ser expostas também por um servidor MCP local, sobre a mesma camada de domínio.

### Fatia 3 — Profundidade

- **RF-32** Jornada de preço e contestação: simulação no serviço de pricing fictício (autoridade do preço esperado), cobrança registrada independente e comparação determinística em centavos, cobrindo cobrança coerente, condições diferentes, divergência e evidência insuficiente, sem prometer correção ou ressarcimento.
- **RF-33** Jornada de habilitação de bandeiras, distinguindo pedido, habilitação ativa e disponibilidade no equipamento.
- **RF-34** Consulta de cancelamento de venda, distinta de encerramento contratual; nenhuma execução de cancelamento.

### Fatia 4 — Demonstração

- **RF-35** Seletor do mecanismo de decisão do Router (LLM ou Jev) por requisição, habilitado só em modo demonstração, com comparação lado a lado que não executa ferramentas nem encaminhamentos duas vezes.
- **RF-36** Interface de demonstração que separa o chat do lojista do painel técnico (rota, traces, custo).

## Requisitos não funcionais

- **RNF-01 Execução:** `docker compose up --build` sobe a API, o armazenamento vetorial e a ingestão inicial exigindo apenas `OPENAI_API_KEY`. Provedores adicionais (Jev, DeepSeek) são opcionais e desligados por padrão.
- **RNF-02 Custo:** teto total do projeto de US$5, com reservas de US$0,25 (ingestão e calibração), US$1,25 (desenvolvimento), US$1,50 (avaliação), US$1,00 (demonstração) e US$1,00 (contingência). Testes automatizados não fazem chamadas pagas. Preço ou consumo desconhecido bloqueia novas chamadas pagas.
- **RNF-03 Latência:** p50 e p95 por requisição e por etapa medidos e relatados. Meta definida após a primeira medição da fatia 1.
- **RNF-04 Privacidade:** somente dados sintéticos versionados; `discovery/` fora do repositório; nenhum dado do cliente em consultas externas; logs com minimização.
- **RNF-05 Segurança:** segredos apenas por variáveis de ambiente; `.env` fora do Git; opções de demonstração desligadas por padrão.
- **RNF-06 Reprodutibilidade:** cópia do conteúdo coletado, modelo de embedding e configuração do índice registrados; testes com relógio fixo, modelo programado e embeddings falsos.
- **RNF-07 Idioma:** respostas no idioma do lojista (português ou inglês). Código, identificadores, prompts e README final em inglês; documentação de trabalho em português.
- **RNF-08 Manutenibilidade:** domínio separado do transporte (HTTP, MCP); agentes como módulos com contratos; lint e testes executáveis com um comando.

## Casos de uso

### Exemplos do enunciado (`user_id` `cliente1988`)

| ID | Mensagem | Rota esperada | Comportamento esperado |
| --- | --- | --- | --- |
| UC-01 | What's the difference between the Get Clássica and the Get Smart? | knowledge | Compara com base nas páginas oficiais das maquininhas, com citações; o que não constar nas fontes é dito como não encontrado |
| UC-02 | What's the weather forecast in Porto Alegre tomorrow? | general_web | Busca web com fonte; sem prefixo de suporte e sem dados do cliente na consulta |
| UC-03 | When will the money from yesterday's sales be deposited? | support | Resolve "ontem" pelo relógio; consulta agenda e repasse; informa a data prevista registrada sem afirmar crédito não confirmado |
| UC-04 | Do I need a bank account to receive my sales via Pix? | knowledge | Responde pela fonte oficial de Pix, com citação, ou declara falta de evidência |
| UC-05 | My card machine won't connect to the internet, what should I do? | knowledge_and_support | Consulta o dispositivo; recupera procedimento oficial compatível; passos curtos; oferece retorno ou encaminhamento |
| UC-06 | How does receivables advance (antecipação) work with Getnet? | knowledge | Explica pelas fontes oficiais; condições individuais dependem do contrato, sem inventar taxa |
| UC-07 | What's the euro exchange rate today? | general_web | Valor atual com fonte e horário da consulta |
| UC-08 | My card machine is showing a transaction decline error. | knowledge_and_support | Busca negativas recentes do cliente; código documentado leva aos próximos passos; motivo desconhecido permanece desconhecido; com várias, pergunta qual |
| UC-09 | How many installments can I split a sale into with the crediário? | knowledge | Número de parcelas somente se constar na fonte oficial; caso contrário, declara falta de evidência |
| UC-10 | Can I sell through WhatsApp using the Payment Link? | knowledge | Responde pela fonte oficial do Link de Pagamento, com citação |

### Casos adicionais do núcleo

| ID | Situação | Resultado esperado |
| --- | --- | --- |
| UC-11 | Variantes em português de UC-01 a UC-10 | Mesma rota e mesmos critérios, resposta em português |
| UC-12 | Pedido inseguro ou sensível (ex.: dados completos de cartão de um comprador, como contornar antifraude) | `refused` com orientação; nada sensível em logs |
| UC-13 | Mensagem pede dados de outro cliente | Ferramenta bloqueia; nenhum dado de outro cliente na resposta; evento registrado |
| UC-14 | Lojista pede atendimento humano | `handoff` com pacote completo e protocolo simulado |
| UC-15 | Armazenamento vetorial, busca web ou ferramenta indisponível | Resposta controlada, limitação informada, nenhum valor inventado |
| UC-16 | Instrução maliciosa na mensagem ou em conteúdo recuperado | Rota e ferramentas inalteradas |
| UC-17 | `user_id` desconhecido | Conhecimento e perguntas gerais funcionam; dados individuais conforme RF-21 |
| UC-18 | Pergunta ambígua ("não está funcionando") | `needs_clarification` com uma pergunta objetiva |

## Critérios de aceitação

### Núcleo (fatias 0 e 1)

- [ ] **CA-01** Os 10 exemplos, enviados exatamente como no enunciado, retornam HTTP 200 com a rota esperada ou uma rota equivalente aceita no conjunto rotulado, resposta no idioma da mensagem e fontes ou fatos verificáveis. Comprovado por teste de integração determinístico e por uma rodada real limitada.
- [ ] **CA-02** As variantes em português (UC-11) atendem os mesmos critérios.
- [ ] **CA-03** UC-05 e UC-08 mostram Knowledge e Customer Support contribuindo na mesma requisição.
- [ ] **CA-04** A ingestão indexa `https://www.getnet.net/en` e as páginas brasileiras verificadas; cada fragmento mantém seus metadados; Recall@k medido no conjunto rotulado e relatado com o tamanho da amostra.
- [ ] **CA-05** Perguntas gerais não executam histórico nem healthcheck e não enviam identificador do cliente à busca.
- [ ] **CA-06** Tentativas de acessar outro cliente são bloqueadas pela ferramenta e registradas.
- [ ] **CA-07** Com relógio fixo, os testes de datas são determinísticos; na demonstração, `cliente1988` tem vendas do dia anterior à data de execução.
- [ ] **CA-08** `user_id` desconhecido segue RF-21.
- [ ] **CA-09** UC-12 e UC-16 recebem o tratamento esperado; dados sensíveis aparecem mascarados nos logs.
- [ ] **CA-10** UC-14 gera um único caso por requisição repetida, com todos os campos do pacote.
- [ ] **CA-11** Falhas simuladas de UC-15 produzem resposta controlada e registrada.
- [ ] **CA-12** Limites de chamadas, tempo e orçamento interrompem a execução com resposta útil; custo por requisição registrado.
- [ ] **CA-13** Em ambiente limpo, com apenas `OPENAI_API_KEY`, `docker compose up --build` deixa a API pronta e os 10 exemplos executáveis; passos no README.
- [ ] **CA-14** A suíte de testes executa sem rede e sem chamadas pagas; lint limpo.
- [ ] **CA-15** Logs e traces por `request_id` mostram rota, agentes, ferramentas, duração por etapa, tokens e custo.
- [ ] **CA-16** O README cobre build, configuração, execução, testes, arquitetura, fluxo de mensagens, pipeline RAG (ingestão → armazenamento → recuperação → geração), uso de ferramentas pelos modelos, estratégia de testes, avaliação e observabilidade.
- [ ] **CA-17** Um relatório de avaliação registra configuração, amostra, resultado por caso, custo e latência, separando medições de metas.
- [ ] **CA-26** Toda resposta passa pela etapa Personality; a verificação de saída confirma que valores, datas e fontes continuam iguais aos das contribuições dos agentes.

### Fatias 2 a 4

- [ ] **CA-18** Uma continuação como "já fiz isso e continua igual" usa o histórico, não repete o passo e encaminha no limite de dois ciclos.
- [ ] **CA-19** Resolução só é marcada com evidência adequada, identificada como `tool_verified` ou `customer_confirmed`.
- [ ] **CA-20** As ferramentas respondem igual pela camada de domínio e pelo servidor MCP.
- [ ] **CA-21** A jornada de preço demonstra os quatro comportamentos de RF-32 com dados independentes de pricing e cobrança.
- [ ] **CA-22** Habilitação em andamento com protocolo existente e habilitação ativa com divergência no dispositivo são distinguidas, sem duplicar solicitação.
- [ ] **CA-23** Pedido de encerramento contratual não aciona ferramentas de venda.
- [ ] **CA-24** O seletor alterna LLM e Jev por requisição sem reiniciar, registra o mecanismo usado e a comparação não duplica ferramentas nem encaminhamentos.
- [ ] **CA-25** Vídeo com raciocínio, arquitetura, um caso resolvido, uma exceção encaminhada e limitações.

## Riscos

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Escopo maior que o prazo | Núcleo incompleto na entrega | Fatias com corte explícito; núcleo primeiro |
| Produto citado em exemplo sem página oficial (ex.: Get Clássica, crediário) | Resposta inventada | Verificação na fatia 0; caso de "sem evidência" no conjunto rotulado |
| Página com conteúdo renderizado por JavaScript | Extração vazia ou incompleta | Verificar o texto extraído; navegador headless só se necessário |
| Modelos candidatos indisponíveis na conta ou com preço diferente | Bloqueio ou custo acima do previsto | Verificação na fatia 0; modelo configurável |
| Recuperação fraca de inglês para português | Respostas sem evidência nos exemplos | Medir cedo; consulta reescrita ou bilíngue |
| Avaliador executa em outra data | "Ontem" sem dados | Seed relativo ao dia da execução |
| Busca web paga e avaliador usando a própria chave | Custo inesperado | Limites por requisição e aviso no README |
| Contexto privado no repositório público | Exposição indevida | `discovery/` ignorado; revisão antes do primeiro push |

## Questões em aberto

| ID | Questão | Responsável | Bloqueia |
| --- | --- | --- | --- |
| Q1 | Prazo de entrega | Empresa / responsável | Corte das fatias 3 e 4 |
| Q2 | Idioma do README final e do vídeo (proposta: inglês) | Responsável | Fatia 4 |
| Q3 | Visibilidade final do repositório (criado como privado em 2026-10-26) | Responsável | Entrega |
| Q4 | Acesso e crédito no Jev | Responsável | RF-35 |
| Q5 | ~~Conteúdo da imagem incorporada ao enunciado~~ Resolvida em 2026-10-26: diagrama com etapa Personality antes da saída (RF-37) | Tarefa 01 | — |
