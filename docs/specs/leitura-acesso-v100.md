<!-- Papel: especificação complementar da v1.0.0 (imagem publicada, lockfile, leitura do repositório e acesso externo). -->

# Leitura e acesso — v1.0.0

Versão 0.2, 2026-11-10. Estado: entregue na v1.0.0 (2026-11-10; [resultado](../evidence/v100-resultado.md)). Deriva do [roadmap](roadmap-v0110-v100.md) (RF-127 a RF-129, RF-98) e do [plano](roadmap-v0110-v100-plano.md) (decisões 20 e 21). A D6 segue a [decisão 0026](../architecture/decisions/0026-tunel-com-login-por-redirecionamento.md), que leva ao túnel o login por redirecionamento da v0.13.0. Os registros de processo (RF-128) foram entregues na tarefa 105.

**Orçamento:** teto de US$0,10 para a campanha `v100-qa` e US$0,10 para a janela do túnel.

## Resultado desejado

1. A cada tag, a CI publica a imagem da API no GitHub Container Registry; `docker compose up` usa a imagem publicada quando existe e constrói quando não existe; dependências fixadas num lockfile versionado; a suíte estrita roda dentro da imagem sem acesso ao PyPI.
2. Quem abre o repositório entende em minutos o que o assistente faz, como rodar e onde está a evidência de cada número.
3. O acesso externo por túnel está documentado e testado.

## Decisões

| ID | Decisão | Motivo |
| --- | --- | --- |
| D1 | Job `image` no `validate.yml`, só em tag `v*`: build multi-estágio, push para `ghcr.io/<owner>/ai-getnet-case:<tag>` e `:latest` com `GITHUB_TOKEN` (`packages: write`), rótulos OCI de origem e versão; nenhum segredo novo | Imagem reproduzível por versão |
| D2 | `uv.lock` versionado e usado no Dockerfile (`uv sync --frozen`), com os extras da imagem; a CI confere que o lockfile está atualizado | Dependências fixadas |
| D3 | `docker-compose.yml` com `image: ghcr.io/<owner>/ai-getnet-case:${APP_VERSION:-latest}` e `build:` no mesmo serviço; `pull_policy: missing` | Usa a imagem publicada quando existe |
| D4 | Seção "Run the tests inside the image" no README: a suíte estrita dentro do contêiner, sem rede (`--network none`), com o basetemp em diretório temporário | Prova de que a imagem é autossuficiente |
| D5 | README com tabela antes × depois por área (número da v0.10.0, número atual, link da evidência), trilha de 10 minutos (rodar, perguntar, encaminhar, responder, avaliar) e capturas da aba Operador, do ticketing e do Telegram; CHANGELOG e notas de operação atualizados | Leitura rápida |
| D6 | Túnel (Cloudflare Tunnel rápido, sem conta) para um proxy local no perfil `tunnel` do compose, que publica numa única origem a interface e só `GET`/`POST /v1/auth/authorize` da API; a interface monta o login com a URL pública e fala com a API pela URL interna; testado por outra rede com evidência (URL efêmera não versionada) | Acesso externo comprovado com o login da v0.13.0 e sem expor o resto da API (decisão 0026, emenda à 0012) |

## Critérios de aceitação

- **CA-73** Imagem no GHCR por tag; suíte estrita roda dentro da imagem sem PyPI; lockfile versionado e conferido na CI.
- **CA-74** README com trilha de 10 minutos, capturas e tabela antes × depois por área com links válidos; `docs/evidence/` com índice; túnel testado com evidência.

## Tarefas

106. Imagem no GHCR por tag, `uv.lock`, compose com `image:`, suíte dentro da imagem (D1 a D4).
107. README antes × depois, trilha de 10 minutos, capturas, índice de `docs/evidence/`, CHANGELOG (D5).
108. Túnel com proxy de origem única e URL pública do login na interface; guia de abertura e fechamento (D6).

Ordem: 106, 108 e 107 (o README descreve o túnel pronto); depois a validação real (imagem, suíte sem rede, túnel por outra rede), registrada em [v100-resultado.md](../evidence/v100-resultado.md).
