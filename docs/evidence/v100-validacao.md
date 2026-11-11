# Validação da v1.0.0

Registro da validação e da revisão independente da v1.0.0: imagem com dependências fixadas e suíte dentro do contêiner, trilha de 10 minutos do README e demonstração por endereço público com login por redirecionamento. Critérios CA-73 e CA-74 da [especificação](../specs/leitura-acesso-v100.md). Resultado consolidado: [v100-resultado.md](v100-resultado.md).

## Candidato

| Item | Valor |
| --- | --- |
| Backend integrado na `main` | commit `793fe16` ("Release v1.0.0"), árvore `670850b`, pelo merge `ed5f02e` (2026-11-10) |
| Interface integrada | commit `5d1f896`, pelo merge `04ac328` na `main` do repositório da interface |
| Validação com modelo real | campanha `v100-qa`, no candidato da versão; o integrado acrescenta o tempo de espera do ticketing no compose (15 s), as capturas e textos |
| Acesso por outra rede | na `main` integrada (`ed5f02e`) com a interface `04ac328` |

## Ambiente

- **Campanha `v100-qa`:** Docker Desktop 29.8.0 com VM de 2 GB, projeto compose novo, sem login no GHCR; só a chave da OpenAI; `BUDGET_LIMIT_USD=0.10`; interface Streamlit 1.66.1; Chrome em modo headless, com eventos reais de mouse e teclado e popup real de login; a operadora num contexto de navegador separado; credenciais fictícias de `.env.example`, trocadas por senhas de uso único na etapa da trava.
- **Acesso por outra rede:** Quick Tunnel do Cloudflare (`cloudflared` 2026.10.7), perfil `tunnel`, senhas de uso único e teto de US$0,10; lojista num celular em rede móvel, com o Wi-Fi desligado; operadora num computador, em janela privada. O endereço efêmero não é registrado.

## Imagem (CA-73)

| Passo | Esperado | Observado |
| --- | --- | --- |
| Build do alvo `test` | Dependências do lockfile, sem segredo no contexto | Exit 0 em 1 min 11 s; `uv sync --frozen`; dentro da imagem só `.env.example` |
| Suíte dentro da imagem | Suíte estrita sem rede | `docker run --rm --network none`: 2.982 testes aprovados; caminhos pessoais sem ocorrência em 704 arquivos; links sem alvo ausente em 346; Ruff e skills limpos; exit 0 |
| Imagem de execução | Usuário sem privilégio | 431 MB, usuário `app` |
| Compose sem imagem publicada | Constrói e sobe | Pull negado; o compose construiu a imagem e a pilha ficou saudável em 40 s; portas só em `127.0.0.1` |
| Prontidão | Versão e esquema | `/ready` com `ready: true`, aplicação 1.0.0, esquema 16 e 145 trechos no índice |

## Trilha de 10 minutos (CA-74)

| Passo | Esperado | Observado | Evidência |
| --- | --- | --- | --- |
| 2. Entrar como lojista | Janela de login fecha e a sessão abre | `Sessão ativa · papel merchant · merchant:cliente1988`, com as abas Atendimento e Resultados | — |
| 3. Perguntar | Datas e valores das vendas sintéticas | Pix R$ 80,00 creditado em 09/11, débito R$ 148,06 no dia e crédito R$ 1.162,20 em 11/11; rota `support`, 10 etapas, 4 ferramentas, fontes e custo por agente | `req_3b08a99226624557bed0` |
| 4. Pedir atendente | Protocolo | `HO-20261110-773AB2` na resposta e na legenda | `req_b49560a8d42f45d09d44` |
| 5. Responder como operadora | Ticket assumido e resposta entregue | "Ticket assumido. Ele aparece na fila Atendimento."; resposta entregue ao lojista com uma única `conversation.replied`; no candidato integrado, pelo endereço público, a tela confirma "Ação enviada e aceita pelo assistente." | — |
| 6. Ler a resposta | Turno da atendente | `Atendente humano · rota human_reply`; nenhum lançamento no ledger nesse turno | — |
| 7. Avaliar | Estimativa, custo separado e notas | Estimativa US$0,000159 (rubrica `judge` v2, avaliador `openai:gpt-6-luna`); avaliação `completed` com custo de US$0,000079 separado do atendimento; notas 5, 5 e 5 | — |
| Fim | Logout revoga | Dois `POST /v1/auth/revoke` 200 | — |

## Proxy do túnel e trava de credenciais

| Verificação | Esperado | Observado |
| --- | --- | --- |
| Rotas pelo proxy | Só a página de login da API | Só `GET` e `POST /v1/auth/authorize` chegam à API. Token, revogação, mensagens, OpenAPI, documentação, saúde, prontidão, métricas, JWKS, descoberta OIDC, perfis e `/v1/auth/authorize/../token` são respondidos pela interface (405 ou 200 em HTML); o caminho em maiúsculas é reescrito para o caminho exato |
| Websocket | Interface inteira pelo proxy | `/_stcore/stream` com 101 |
| Interface parada | Erro do proxy | 502; o login continua indo à API |
| Login e logout pelo proxy | Sessão e revogação | Sessão aberta pela janela em `/v1/auth/authorize`; depois de encerrar, access 401 `invalid_token` e refresh 400 `invalid_grant` |
| Cabeçalhos de encaminhamento | Não confiados | `X-Forwarded-For`, `X-Real-IP` e `Forwarded` ignorados: o log registra só o endereço do contêiner do proxy |
| Endereço público com credenciais de exemplo | API não sobe | `CredentialConfigError` nomeia as contas e as variáveis a trocar; 0 ocorrências de senha no log |
| Senhas de uso único | Sobe e recusa a senha publicada | API e ticketing saudáveis em 26 s; senha publicada da operadora recusada ("Usuário ou senha inválidos."); `demo` com a senha nova entra, sem Administração |

## Acesso por outra rede

| Verificação | Observado |
| --- | --- |
| Interface pelo celular | Abriu pelo endereço público, com o websocket ativo |
| Login por redirecionamento | `cliente1988` com `Sessão ativa · papel merchant` |
| Pergunta de recebíveis (Router LLM) | Resposta com as três vendas sintéticas, rota `support` |
| Pedido de atendente | `HO-20261110-C0650B` na Recepção da operadora |
| Operadora pelo endereço público | `op_ana` com papel operator; Assumir e Responder; "Ação enviada e aceita pelo assistente." |

## Custo

Campanha `v100-qa`: US$0,003849 (teto US$0,10), em 22 lançamentos, todos liquidados. Janela do túnel: US$0,0033 (teto US$0,10), incluindo o índice da primeira subida.

## Revisão independente

Imagem e publicação, README, túnel e o candidato final com as capturas passaram por revisão em contexto novo.

### Re-derivado

- **Lockfile:** `uv lock --check --offline` com 111 pacotes; mudança no `pyproject` sem atualizar o lock falha.
- **Contexto da imagem:** dos arquivos versionados, só `.claude/**` e `.agents/**` ficam fora; as checagens da suíte passam na árvore do alvo `test` (697 arquivos); `docs/images` entra no contexto, e sem ela a checagem de links da imagem falha.
- **Proxy:** só `GET` e `POST /v1/auth/authorize`, com o caminho reescrito; API com `--no-proxy-headers`; perfil `tunnel` fora do padrão; nenhum endereço efêmero versionado.
- **Trava:** endereço público registrado com credencial de exemplo (sufixo `-fictitious` ou valores da suíte de testes) impede a subida, com contas e variáveis nomeadas e sem valores; 7 contornos testados.
- **Publicação:** `latest` não se move em pré-versão (`flavor: latest=false`, com asserção).
- **README:** todos os números da tabela conferidos contra as evidências; trilha conferida contra a interface, sem passo impossível; a execução do passo 3 é a última da lista de Resultados.
- **Capturas:** seis PNG de 1.440 px só com os blocos `IHDR`, `IDAT` e `IEND`, sem metadados e sem `code`, `state`, endereço de túnel ou caminho de disco; identidades e senhas sintéticas.
- **Tempo do ticketing:** `TICKETING_WEBHOOK_TIMEOUT_S` de 15 s no compose (3 s fora dele); a tela da interface espera 20 s; o evento é idempotente.

### Testes rodados

- Imagem: 28 testes focados. README: 47 testes, links, âncoras e caminhos pessoais.
- Túnel: backend 137 (6 do túnel), interface 166 com 1 pulado e 4 de integração; depois, backend 152 e interface 74 com 4 de integração; 304 testes focados na trava.
- Candidato com as capturas: suíte estrita com 2.981 aprovados e 1 pulado (extra `otel` ausente no ambiente de desenvolvimento; a imagem e a CI o instalam).

### Mutações

| Escopo | Mutações aplicadas | Não detectadas |
| --- | ---: | --- |
| Imagem, lockfile, contexto e workflow | 22 | 4 |
| Proxy do túnel, trava de credenciais, filtro de contexto e `latest` na publicação | 48 | nenhuma |
| Capturas no contexto da imagem e tempo do ticketing no compose | 9 | 2 equivalentes |

### Conclusão

Apto em todos os escopos. A decisão está registrada na [ADR 0026](../architecture/decisions/0026-tunel-com-login-por-redirecionamento.md).
