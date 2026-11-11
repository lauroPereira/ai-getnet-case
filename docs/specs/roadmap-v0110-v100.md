<!-- Papel: especificação do roadmap v0.11.0 a v1.0.0. -->

# Especificação: roadmap v0.11.0 a v1.0.0

Versão 0.1, 2026-11-06. Estado: entregue da v0.11.0 à v1.0.0 (2026-11-09 a 2026-11-10). Sucede a [evolução para produção](evolucao-producao-v070-v0100.md) (v0.7.0 a v0.10.0) e substitui a definição de v1.0.0 daquela especificação: o vídeo de apresentação entregue na v0.6.0 ([release](https://github.com/lauroPereira/ai-getnet-case/releases/tag/v0.6.0)) segue como referência, e um vídeo novo (RF-99) não entra nestas versões, por decisão do responsável em 2026-11-06. Plano técnico: [roadmap-v0110-v100-plano.md](roadmap-v0110-v100-plano.md).

## Objetivo

O que uma operação real exige depois da v0.10.0, por área (a linha de base de cada área está nos [resultados da v0.10.0](../evidence/README.md)):

1. **Avaliação.** O juiz concorda com o julgamento humano no veredito de afirmação sem suporte, marca frases genéricas e julga as respostas `general_web` com o texto das páginas citadas. Regra de promoção: κ ≥ 0,6 no veredito contra rótulos de referência em respostas seladas, sem queda superior a 0,05 no acordo ±1 de nenhum critério.
2. **Orquestração.** Medir a contribuição do replanejamento com uma ablação pareada com × sem e registrar por que o desenho é um grafo com replanejamento e não um supervisor com especialistas como ferramentas.
3. **Memória.** Resumo rolante além da janela de 10 mensagens, medido numa conversa de 20+ turnos; registro de comparações compartilhado entre workers.
4. **Identidade.** Fluxo authorization code, refresh token e emissor OIDC externo, além dos usuários de demonstração.
5. **Ferramentas e negócio.** Uma ação de escrita com confirmação explícita (cancelamento de venda); jornadas medidas por uma régua que aceita paráfrases corretas.
6. **RAG.** Ganho próprio do reranker medido contra um controle na mesma profundidade (`hybrid@36`); piso de score para hits só de BM25.
7. **Supervisão humana.** Reenvio de entrega de webhook esgotada; caso aberto no turno em que a API caiu completado na subida, sem depender de o lojista reenviar; canal do operador no celular.
8. **Observabilidade.** Exportação OTLP e dashboard sobre `/metrics`.
9. **Produção.** Mais de um worker; acesso externo testado; imagem publicada que roda a suíte sem PyPI.
10. **Leitura.** Registros de processo fora do caminho de quem lê o repositório.

## Usuário afetado

- **Quem opera ou audita o assistente:** precisa encontrar, por área, o número antes e depois, e conseguir rodar o sistema sem instalar nada.
- **Rotuladores** (o responsável e um painel de dois modelos): avaliam as respostas seladas com a mesma unidade de julgamento do juiz.
- **Operador humano:** recebe o caso no celular e responde de lá.
- **Lojista:** confirma um cancelamento antes de ele acontecer; conversa longa sem perder protocolo e valores.
- **Responsável:** decide teto, rotulador, prazo e tags.

## Resultado desejado

A v1.0.0, em que cada objetivo acima tem mudança, teste determinístico, validação real e uma linha no README com o número antes e depois.

## Escopo

Quatro versões, cada uma com especificação complementar, revisão independente e validação com modelos reais sob teto de custo, com o candidato identificado por hash e o resultado registrado. Ordem do mais lento (tempo humano) para o mais barato.

| Versão | Entrega | Objetivos | Resultado |
| --- | --- | --- | --- |
| **v0.11.0 — Juiz e retrieval** | Evidência da web gravada e buscada; juiz afirmação por afirmação (`judge.v5`); pacote de calibração por afirmação; 36 respostas novas seladas, rótulos de referência do responsável e de um painel de dois modelos, κ contra o rótulo de referência; regra pré-registrada de promoção; controle do reranker e piso BM25; régua combinada das jornadas | 1, 5 (jornadas), 6 | [v0110-resultado.md](../evidence/v0110-resultado.md) (2026-11-09) |
| **v0.12.0 — Orquestração, memória e escrita** | Resumo rolante com registro de fatos; ablação do replanejamento; ADR supervisor × grafo; cancelamento de venda com confirmação | 2, 3 (resumo), 5 (escrita) | [v0120-resultado.md](../evidence/v0120-resultado.md) (2026-11-09) |
| **v0.13.0 — Segurança e operação** | Refresh token, authorization code com PKCE, emissor OIDC externo no compose; adaptador Telegram; lease de comparações e 2 workers; reenvio de webhook; caso órfão retomado; OTLP e dashboard | 3 (worker), 4, 7, 8, 9 (worker) | [v0130-resultado.md](../evidence/v0130-resultado.md) (2026-11-10) |
| **v1.0.0 — Leitura e acesso** | Imagem no GHCR por tag; lockfile; túnel testado; registros de processo fora do caminho do leitor; trilha de 10 minutos; capturas do canal do operador; README com antes e depois por área | 9, 10 | [v100-resultado.md](../evidence/v100-resultado.md) (2026-11-10) |

Calibração entregue (RF-112, RF-113): rótulos de referência formados pelas notas do responsável nas 36 respostas seladas e por um painel de dois modelos; divergências adjudicadas com proposta de um terceiro modelo e aprovadas pelo responsável ([planilhas e cálculo](../evidence/v0110-calibracao.md)). A comparação da regra mediu `judge.v3` e `judge.v5` no juiz padrão: `judge.v5` teve κ 0,647 (IC 95% 0,28 a 0,92) e foi promovido ([ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md)).

## Fora do escopo

- Reescrever a orquestração como supervisor com especialistas como ferramentas ([ADR 0024](../architecture/decisions/0024-desenho-da-orquestracao.md)).
- Recaptura dos snapshots das páginas oficiais (muda a versão da base e invalida o holdout de retrieval).
- Ticketing comercial; Evaluation Agent e ciclo de propostas (ADR 0015); ajuste fino de modelos.
- Vídeo (decisão do responsável, 2026-11-06).
- Novas jornadas de negócio além do cancelamento com confirmação.
- Rodar a calibração mais de uma vez até o κ passar: a calibração é uma; se o κ não chegar a 0,6, o número é reportado e o juiz padrão fica.

## Requisitos funcionais

### Juiz e retrieval (v0.11.0)

- **RF-109** O passo de busca web grava no trace, mascarado e limitado, o texto devolvido pela busca (resumo do modelo) e as URLs citadas, identificado como "resumo da busca", não como página.
- **RF-110** Na avaliação, para cada URL citada por uma resposta `general_web` ou pelo passo `web`, o sistema busca a página, extrai o texto, mascara e limita (mesmo teto de caracteres das demais evidências, truncamento registrado) e entrega ao juiz como evidência de página. Página indisponível cai no resumo da busca (RF-109) com a nota correspondente. A busca é na hora da avaliação, nunca na hora da resposta ao lojista.
- **RF-111** Rubrica `judge.v5` em duas etapas: (1) lista das afirmações atômicas da resposta; (2) para cada afirmação, classificação `supported`, `partial`, `generic` (orientação ou generalização dita como fato, sem fonte) ou `not_found`, com o trecho que a sustenta quando houver. Os quatro critérios de 1 a 5 continuam; `unsupported_claim` deriva da lista (qualquer `generic` ou `not_found` sobre fato, valor, data, status, promessa ou orientação não ancorada). Frases padrão de encaminhamento, protocolo e pedido de esclarecimento não são afirmações. `judge.v3` e `judge.v4` ficam intocados.
- **RF-112** Calibração por afirmação: `eval-calibrate --sample` gera, por resposta, a evidência completa que o juiz viu (páginas, trechos, resultados de ferramenta, resumo da busca) e a lista de afirmações da etapa 1; cada rotulador marca cada afirmação com a mesma escala e pode acrescentar afirmações que faltam; dá também as notas de 1 a 5. O veredito humano deriva das marcas. `--import` aceita dois rotuladores, calcula concordância humano × humano (exata, ±1, kappa) e, para as divergências, aceita um arquivo de adjudicação com o rótulo ouro e o motivo.
- **RF-113** Amostra e regra pré-registradas: 36 respostas novas sorteadas com semente, estratificadas por rota e split e enriquecidas nas rotas onde frases genéricas apareceram (`knowledge`, `knowledge_and_support`), seladas por hash antes de qualquer julgamento; as 24 da v0.8.0 são o conjunto de ajuste da rubrica. Regra escrita antes de rodar: `judge.v5` com o modelo candidato vira padrão se κ ≥ 0,6 no veredito contra o rótulo ouro nas 36 seladas, sem piorar o ±1 de nenhum critério em mais de 0,05. Candidatos: DeepSeek (padrão) e `claude-sonnet-5-5` (sonda de custo de 5 casos antes). Candidato reserva: ensemble (veredito "sim" só quando os dois marcam). O relatório traz κ nas 36 e nas 60, concordância por afirmação e a justificativa escrita da escolha do juiz padrão. **Entregue:** as 36 respostas foram sorteadas com a semente 20261107, enriquecidas e seladas antes de qualquer julgamento; o DeepSeek com `judge.v5` cumpriu a regra (κ 0,647, IC 95% 0,28 a 0,92); κ nas 36 e nas 60, concordância por afirmação e justificativa estão em [v0110-calibracao.md](../evidence/v0110-calibracao.md) e na [ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md). A sonda com `claude-sonnet-5-5` não foi adotada, porque a reserva de saída de cinco chamadas (US$0,18) passava do saldo da campanha (US$0,087); sem um segundo juiz medido, o ensemble não se aplica.
- **RF-114** Retrieval: controle sem modelo na mesma profundidade do reranker (`hybrid@36` reordenado só pela fusão) para medir o ganho próprio do reranker; piso de score configurável para hits encontrados só pelo BM25; `RERANK` decidido pela regra da ADR 0020 com os números novos, em dev e holdout de retrieval.
- **RF-115** Régua combinada das jornadas: a checagem determinística decide o que é binário (rota, status, ferramentas, valores, fontes, afirmações proibidas registradas); o conteúdo é decidido pelo juiz padrão com um piso por critério registrado antes; o relatório mostra as duas colunas e a jornada passa quando as duas passam.

### Orquestração, memória e escrita (v0.12.0)

- **RF-116** Resumo rolante: quando a conversa passa da janela (10 mensagens ou 1.200 tokens), um resumo das mensagens anteriores é gerado por chamada curta (esforço mínimo), guardado com o id da última mensagem resumida e reaproveitado até haver mensagem nova fora da janela; entregue a Router, Support e Personality como dado. Separado dele, um **registro de fatos** por conversa (protocolos, valores, datas, produtos, status) extraído deterministicamente dos resultados das ferramentas e dos casos, com origem (ferramenta e turno), nunca do texto do modelo. A guarda de saída aceita valores presentes no registro de fatos; o resumo nunca é fonte para a guarda. Medida: conversa de 20+ turnos em que o lojista pergunta no final o protocolo e o valor ditos no começo.
- **RF-117** Ablação do replanejamento: `eval --replan off` roda o grafo sem o nó `replan` (plano inicial do Router e fim); a campanha roda os mesmos casos (dev, holdout da v0.8.0 e conversas) com e sem, mesmo juiz, uma execução cada, e o relatório compara por critério e por rota, com intervalo, e lista o que o modelo decidiu nas decisões de origem `model` (observação, candidatos, escolha).
- **RF-118** ADR "supervisor com especialistas como ferramentas × grafo com replanejamento": o desenho alternativo, o que se ganharia, o que se perderia (origem nomeada de cada decisão, garantias estruturais de saltos e de escopo, reprodutibilidade dos testes com modelo roteirizado, custo por decisão) e a condição que faria rever a decisão.
- **RF-119** Cancelamento de venda com confirmação: ferramenta `request_sale_cancellation` (escopo próprio, escrita) que cria um pedido `pending_confirmation` com o que será cancelado (venda, valor, data); o assistente mostra o resumo e pede confirmação explícita; a confirmação do lojista no turno seguinte executa (`confirmed`, protocolo próprio) de forma idempotente e auditada; "não" ou silêncio por N turnos cancela o pedido; sem confirmação nada muda na conta. Jornada nova no catálogo e nos JSONL, com modelo roteirizado e modelos reais.

### Segurança e operação (v0.13.0)

- **RF-120** Emissor próprio: refresh token (rotativo, revogável, ligado ao principal) e fluxo authorization code com PKCE (`GET /v1/auth/authorize`, página de login do emissor, `POST /v1/auth/token` com `grant_type=authorization_code` e `refresh_token`); a interface Streamlit loga por redirecionamento; `password` continua só para smoke e CLI, marcado como demo no `/docs`.
- **RF-121** Emissor OIDC externo no compose (serviço leve e aberto, decisão no plano), com usuários sintéticos, e a API aceitando tokens dele por descoberta (`issuer`, JWKS) com mapeamento de claims para papéis e escopos; o emissor próprio continua como padrão; evidência com os dois emissores.
- **RF-122** Adaptador Telegram: recebe o evento `handoff.created` (webhook já existente), envia o resumo do caso ao chat do operador e traduz `/claim`, `/approve`, `/reply <texto>` e `/reject <instrução>` em chamadas a `/v1/handoffs` com token de operador; desligado por padrão (sem token no `.env`); Telegram falso em processo nos testes; cenário de uso na validação real com a resposta chegando ao lojista.
- **RF-123** Dois ou mais workers: o registro de comparações passa de threads em memória para lease no banco (`worker_id`, `heartbeat_at`, renovação periódica; órfã = heartbeat vencido), a retomada reivindica a lease em transação; locks por caso em memória removidos onde o SQLite já serializa; compose com `--workers 2`; teste que mata um worker no meio de uma comparação e confere a retomada pelo outro sem célula paga duas vezes.
- **RF-124** Entrega de webhook esgotada: estado `exhausted`, reenvio manual (`POST /v1/webhooks/deliveries/{id}/resend`, escopo de operador) e reenvio automático na subida com espera maior; eventos posteriores do mesmo destino deixam de ficar presos.
- **RF-125** Caso aberto sem ticket (API caída no turno): na subida, casos `open` sem evento de ticketing e sem intenção no outbox têm a intenção recriada e entregue; o lojista não precisa reenviar.
- **RF-126** Exportação OTLP opcional dos spans (`OTEL_EXPORTER_OTLP_ENDPOINT`), coletor no compose por perfil, e um dashboard versionado (`observability/grafana/assistant.json`) sobre `/metrics`, com captura na validação real.

### Leitura e acesso (v1.0.0)

- **RF-127** A CI publica a imagem da API no GitHub Container Registry a cada tag; `docker compose up` pode usar a imagem publicada em vez de construir; `uv.lock` (ou `requirements.lock`) versionado; o README mostra como rodar a suíte dentro da imagem sem PyPI.
- **RF-128** Registros de processo saem do caminho do leitor: relatórios de coordenação e registros intermediários ficam fora do versionamento (cópia local); `docs/evidence/` fica só com resultados e índice; um verificador de links relativos roda no `lint_and_tests.py` (tarefa 105). O README ganha uma trilha de 10 minutos (rodar, perguntar, encaminhar, responder, avaliar) e capturas do canal do operador (tela e Telegram).
- **RF-129** README com uma linha por área: número antes, número depois e link da evidência; CHANGELOG; notas de operação atualizadas.
- **RF-98** (mantido) Acesso externo testado por túnel documentado, com evidência.

## Requisitos não funcionais

- **RNF-16** Nenhum teste automatizado faz chamada paga; a busca de páginas da RF-110 roda só na avaliação e com domínio restrito às URLs citadas, sem seguir redirecionamentos para fora de `https`.
- **RNF-17** Orçamento: o limite de gasto é definido pelo responsável por provedor (desde 2026-11-07, Q21), e cada versão tem teto de campanha fixo, registrado antes da execução. A aplicação mantém o ledger por instalação (`BUDGET_LIMIT_USD`, padrão US$1,00, máximo US$5,00 por ledger) e o teto por request (US$0,05).
- **RNF-18** Migrações aditivas e reversíveis; contrato `/v1` aditivo; `grant_type=password` continua funcionando (sem mudança incompatível).
- **RNF-19** Privacidade: páginas buscadas, resumo da busca, registro de fatos, resumo rolante e mensagens do Telegram passam pela máscara antes de persistir ou sair; o Telegram só recebe o resumo de passagem já mascarado e nunca dados de cartão.
- **RNF-20** O emissor externo e o coletor OTLP entram por perfil do compose e não aumentam o uso de memória do perfil padrão.
- **RNF-21** Toda decisão estrutural tem ADR: juiz por afirmação e evidência da web (0023), supervisor × grafo (0024), identidade externa e lease multi-worker (0025).
- **RNF-22** Nada de versionar caminho pessoal, token do Telegram ou segredo do emissor externo; valores fictícios no `.env.example` nomeados como tal.

## Casos de uso

- **UC-34 Calibração com dois rotuladores.** A amostra é selada → pacotes por afirmação gerados → o responsável avalia as 36 seladas e o painel de dois modelos avalia as mesmas, sem ver notas → divergências adjudicadas em arquivo, com proposta de um terceiro modelo aprovada pelo responsável → juiz roda → relatório com κ nas 36, concordância por afirmação e decisão pela regra.
- **UC-35 Resposta da web avaliada de verdade.** Pergunta `general_web` → resposta com 2 URLs → avaliação busca as páginas, mascara, entrega ao juiz → juiz confere cada afirmação contra o texto das páginas, não contra a nota.
- **UC-36 Conversa longa.** Lojista abre caso no turno 2 (protocolo e valor) → 20 turnos sobre outros assuntos → pergunta "qual era o protocolo e o valor?" → resposta correta, com os valores vindos do registro de fatos e aceitos pela guarda.
- **UC-37 Cancelamento confirmado.** "Cancele a venda de ontem de R$ 230" → assistente mostra venda, valor e data e pede confirmação → "sim" → pedido executado com protocolo; "não" → nada muda; repetir "sim" → mesmo protocolo.
- **UC-38 Login por redirecionamento e emissor externo.** Interface redireciona ao emissor → login → código → token e refresh → token expira → renovação silenciosa; mesmo fluxo com o emissor externo do compose e `403` para token de emissor desconhecido.
- **UC-39 Operador no celular.** Caso aberto → mensagem no Telegram com o resumo → operador responde `/reply ...` → lojista recebe a resposta na conversa, `via=operator`.
- **UC-40 Dois workers.** Compose com 2 workers → comparação iniciada → worker dono morto → o outro retoma só as células que faltam → ledger sem célula duplicada.
- **UC-41 Ambiente sem PyPI.** `docker pull` da imagem publicada → `docker compose up` → suíte estrita dentro da imagem → 10 exemplos do desafio.

## Critérios de aceitação

| ID | Critério | Como comprovar |
| --- | --- | --- |
| CA-60 | Respostas `general_web` avaliadas com o texto das páginas citadas; a nota "texto não gravado" some do relatório quando a página foi buscada | Relatório da campanha v0.11.0; teste com servidor de páginas em processo. **Entregue:** 16 respostas de desenvolvimento e 4 do holdout julgadas com o texto da página citada e 3 com o resumo da busca no lugar de uma página indisponível; a nota fica só nas respostas sem URL gravada, 6 e 3 ([desenvolvimento](../evidence/v0110-qa.md), [holdout](../evidence/v0110-qa-holdout-v080.md)) |
| CA-61 | Calibração com 60 respostas, 2 rotuladores, rótulo ouro adjudicado; κ do veredito reportado nas 36 seladas e nas 60, com intervalo; concordância por afirmação; decisão do padrão pela regra escrita antes, cumprida ou não | [v0110-resultado.md](../evidence/v0110-resultado.md), [ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md) e README. **Entregue:** 60 respostas rotuladas pelo responsável e por um painel de dois modelos, 43 com adjudicação; κ do veredito 0,647 nas 36 seladas e 0,628 nas 60, com intervalo; por afirmação, κ 0,498 nas quatro marcas; regra cumprida. Recalculável dos arquivos versionados: [v0110-calibracao.md](../evidence/v0110-calibracao.md) |
| CA-62 | Padrão do projeto: κ ≥ 0,6 nas 36 seladas com algum candidato pré-registrado | Mesmo relatório; se não atingido, o número e a causa ficam escritos |
| CA-63 | Tabela híbrido × `hybrid@36` × reranker em dev e holdout de retrieval, decisão de `RERANK` pela regra; piso BM25 configurável | `eval-retrieval` |
| CA-64 | Jornadas ≥ 12/13 pela régua combinada, com as duas colunas no relatório | Campanha real. **Entregue:** 13 de 13 jornadas em cada uma das três execuções (39 de 39), com as colunas determinística e de conteúdo ([v0110-qa.md](../evidence/v0110-qa.md), seção "Jornadas") |
| CA-65 | Conversa real de 20+ turnos devolve protocolo e valor do início; teste determinístico equivalente; resumo gerado uma vez por avanço da janela | Campanha v0.12.0 e suíte |
| CA-66 | Relatório pareado de `eval-compare` com e sem replanejamento nos mesmos casos, por critério e rota, incluindo decisões de origem `model` | Relatórios JSON e Markdown gerados pelo comando. **Entregue** na v0.12.0, uma execução por lado: 44 pares de desenvolvimento, aprovados +0,045 (IC 95% −0,045 a +0,136), e 25 do holdout, −0,080 (IC 95% −0,240 a +0,080); nenhum critério com intervalo que exclua o zero; decisões de origem `model` listadas, 2 de 49 e 2 de 27 ([v0120-validacao.md](../evidence/v0120-validacao.md)) |
| CA-67 | Cancelamento só executa após confirmação explícita; repetição idempotente; recusa deixa a conta intacta; auditoria com escopo de escrita | Suíte e jornada real |
| CA-68 | Authorization code com PKCE e refresh rotativo funcionando na interface; token do emissor externo aceito; token de emissor desconhecido recusado | Suíte, validação real na interface com os dois emissores |
| CA-69 | Caso chega ao Telegram e a resposta do operador chega ao lojista; adaptador desligado por padrão | Validação real com um bot configurado |
| CA-70 | Compose com 2 workers; worker morto no meio de uma comparação; retomada pelo outro sem célula duplicada; `/metrics`, rate limit, handoffs e outbox corretos com 2 processos | Validação real de operação |
| CA-71 | Entrega esgotada reenviada; caso órfão completado na subida sem reenvio do lojista | Suíte e validação real de operação |
| CA-72 | Spans no coletor OTLP; dashboard carregado sobre `/metrics` com captura | Validação real de operação |
| CA-73 | Imagem no GHCR por tag; suíte estrita roda dentro da imagem sem PyPI; lockfile versionado | CI e evidência |
| CA-74 | Registros de processo fora do versionamento e `docs/evidence/` com índice e links válidos; README com trilha de 10 min, capturas e tabela antes × depois por área; túnel testado | Conferência do responsável; `checar-links.py` e `checar-caminhos-pessoais.py`; [v100-resultado.md](../evidence/v100-resultado.md) |

## Riscos

| Risco | Efeito | Mitigação |
| --- | --- | --- |
| Rotuladores discordam entre si | Rótulo ouro fraco | Mesma unidade de julgamento (afirmações); adjudicação registrada; concordância entre rotuladores reportada ([calibração](../evidence/v0110-calibracao.md)) |
| Páginas citadas pela busca mudam ou somem | Evidência da web incompleta | Fallback no resumo da busca com nota; extrato gravado na primeira busca e reaproveitado |
| Resumo rolante inventar ou perder números | Resposta errada em conversa longa | Registro de fatos determinístico; guarda de saída não aceita o resumo como fonte |
| Cancelamento executar sem confirmação | Efeito indevido na conta | Estado `pending_confirmation` persistido; execução só por turno de confirmação explícita; auditoria |
| Dois workers expõem outra condição de corrida | Dado duplicado | Teste com processo morto; `BEGIN IMMEDIATE` já usado |
| Telegram exige rede de saída e token | Vazamento ou bloqueio | Desligado por padrão; só resumo mascarado; token fora do repositório |
| Reorganização de `docs/` quebrar links | README com links mortos | Verificador de links no `lint_and_tests.py`; renomear por `git mv` |

## Questões decididas

| ID | Questão | Decisão |
| --- | --- | --- |
| Q21 | Teto de gasto do ciclo | Limite por provedor definido pelo responsável em 2026-11-07, com teto por campanha registrado antes de cada execução |
| Q22 | Segundo rotulador | Um painel de dois modelos, com adjudicação aprovada pelo responsável ([ADR 0023](../architecture/decisions/0023-juiz-por-afirmacao-evidencia-web.md)) |
| Q24 | Emissor OIDC externo: serviço leve (Dex) ou Keycloak | Dex, pelo consumo de memória ([ADR 0025](../architecture/decisions/0025-identidade-e-operacao.md)) |
| Q25 | `docs/process/` como pasta no repositório ou branch de arquivo | Nenhum dos dois (2026-11-06): registros de processo ficam fora do versionamento, com cópia local, e `docs/evidence/` só com resultados (tarefa 105) |
