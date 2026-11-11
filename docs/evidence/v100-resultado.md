# Resultado da v1.0.0

## Capacidades

- A imagem da aplicação é publicada no GitHub Container Registry a cada tag de versão, com as dependências fixadas em `uv.lock`; o compose usa a imagem publicada e a constrói do mesmo `Dockerfile` quando ela não está no host nem no registro.
- O alvo `test` da imagem roda a suíte estrita dentro do contêiner, sem rede.
- O perfil `tunnel` abre a demonstração por um endereço público: um proxy de origem única publica a interface e a página de login da API, e nenhuma outra rota da API. Com um endereço público registrado, a API só sobe com credenciais novas.
- O README traz a trilha de 10 minutos com capturas e a tabela de evolução por área.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte estrita | 2.982 testes aprovados no host e dentro da imagem sem rede (`docker run --network none`); Ruff, links e caminhos pessoais limpos |
| Compose sem imagem publicada | O compose constrói a imagem e a pilha fica saudável em 40 s; `/ready` informa aplicação 1.0.0 e esquema 16 |
| Trilha de 10 minutos | Percorrida pela interface com modelo real: login por redirecionamento, pergunta de recebíveis com datas e valores, encaminhamento com protocolo, resposta da operadora pelo Ticketing e avaliação por IA da resposta do assistente (notas 5, 5 e 5) |
| Proxy do túnel | Só `GET` e `POST /v1/auth/authorize` chegam à API; token, revogação, mensagens, OpenAPI, saúde, métricas e JWKS são respondidos pela interface; o websocket atravessa; o logout revoga (token de acesso `401`, refresh `400`); cabeçalhos de encaminhamento não são confiados |
| Credenciais | Com endereço público registrado e credenciais de exemplo, a API não sobe e nomeia contas e variáveis, sem valores; com senhas de uso único, sobe e a senha publicada é recusada |
| Acesso por outra rede | Túnel rápido usado por um celular em rede móvel: login por redirecionamento, atendimento, encaminhamento e resposta da operadora pelo endereço público |

Gasto: campanha `v100-qa` US$0,0038 (teto US$0,10) e janela do túnel US$0,0033 (teto US$0,10).

Validação momento a momento e revisão independente: [v100-validacao.md](v100-validacao.md).

A decisão está registrada na [ADR 0026](../architecture/decisions/0026-tunel-com-login-por-redirecionamento.md).
