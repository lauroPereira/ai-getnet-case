# 0026. Túnel de demonstração com login por redirecionamento

## Título

Publicar a demonstração por um túnel numa única origem que expõe a interface e somente a rota de autorização da API.

## Status

```text
aceita
```

Aceita pelo responsável em 2026-11-10 (opção "expor só o authorize"). Emenda a [decisão 0012](0012-exposicao-publica-da-demonstracao.md): o restante dela continua valendo.

## Contexto

A decisão 0012 expõe só a interface Streamlit; a API fica na rede interna e a interface fala com ela pelo servidor. O teste de acesso por outra rede (RF-98) ficou pendente desde a v0.6.0 e o roadmap da v1.0.0 o fixou por túnel. Desde a v0.13.0 ([decisão 0025](0025-identidade-e-operacao.md)) a interface entra por authorization code com PKCE: é o navegador do visitante que abre a página de login do emissor (`/v1/auth/authorize`) e volta à interface. Com só a interface exposta, o visitante não alcança essa página; e a interface monta o endereço do login com a URL interna da API, que fora da máquina não resolve.

## Decisão

- Um proxy reverso local, no perfil `tunnel` do compose, publica uma única origem: `GET` e `POST /v1/auth/authorize` vão para a API; todo o resto vai para a interface. Nenhuma outra rota da API é alcançável pelo túnel.
- O túnel (Cloudflare Quick Tunnel, sem conta, endereço efêmero) aponta para esse proxy. O endereço público não é versionado; o guia mostra como registrá-lo, a cada abertura, em `OAUTH_REDIRECT_URIS` e na configuração da interface.
- A interface separa a URL pública do login (montada para o navegador) da URL interna da API (usada pelo servidor para trocar o código, renovar e revogar). O emparelhamento emissor ↔ URL da API continua.
- O limite de tentativas por endereço do authorize passa a ver o proxy como um único cliente; isso deixa o limite mais restritivo, nunca mais permissivo. Cabeçalhos de encaminhamento não são confiados.
- Valem as proteções da 0012: login obrigatório, papel `demo` sem administração, limite por sessão, sublimite de orçamento e janela de disponibilidade fechada ao fim.

## Alternativas consideradas

- **Senha na interface só no modo demonstração:** mantém a 0012 intacta, mas a demonstração pública deixa de mostrar o login da v0.13.0 e reintroduz senha no Streamlit.
- **Expor a API inteira pelo túnel:** mais simples, contraria a 0012 e amplia a superfície sem necessidade.
- **IP público com redirecionamento de porta:** depende do roteador e de CGNAT, ações fora do repositório; continua possível com o mesmo proxy.
- **Túnel com conta e domínio próprio:** endereço fixo, mas exige conta e domínio; fica como opção do responsável.

## Consequências

A demonstração pública mostra o fluxo real de login com superfície mínima a mais (a página e o formulário de login, com limite de tentativas). Há uma peça nova (proxy) a manter e testar, e um passo manual por abertura do túnel (registrar o endereço efêmero). O túnel rápido não tem garantia de disponibilidade; serve à demonstração e ao teste, não a uso contínuo.

## Data

2026-11-10
