# Tarefa 108 — Túnel de demonstração com login por redirecionamento

## Objetivo

O visitante abre a demonstração por um túnel, entra pelo login por redirecionamento e usa a interface, sem expor o resto da API.

## Especificação relacionada

[v1.0.0](../specs/leitura-acesso-v100.md): D6, CA-74 (túnel testado). [Decisão 0026](../architecture/decisions/0026-tunel-com-login-por-redirecionamento.md), que emenda a 0012. RF-98.

## Pré-condições

Tarefa 106 concluída. Interface web (repositório `ai-getnet-case-web`) com a v0.13.0. Nenhuma chamada paga. A implementação e os testes não abrem túnel; a abertura pública acontece na validação.

## Arquivos prováveis

Backend: `docker-compose.yml` (perfil `tunnel` com o proxy), configuração do proxy (por exemplo `docker/tunnel/Caddyfile`), `.env.example`, ADR 0026 e índice das decisões, testes de configuração. Web: `app.py`, `src/getnet_web/oauth.py`, `README.md`, testes.

## Passos

1. Proxy no perfil `tunnel`: uma porta local; `GET`/`POST /v1/auth/authorize` → API; resto → interface (inclusive websocket do Streamlit); nenhuma outra rota da API alcançável; cabeçalhos de encaminhamento não confiados pela API.
2. Conferir que a página de login do emissor funciona atrás do proxy numa origem pública https (formulário com ação relativa ou correta, `redirect_uri` https registrado, `iss` inalterado) e que o limite por endereço do authorize fica mais restritivo atrás do proxy, nunca mais permissivo.
3. Web: configuração da URL pública do authorize, separada da URL interna da API; padrão igual ao atual (sem túnel, nada muda); emparelhamento emissor ↔ URL interna mantido; testes.
4. Guia no README do backend e da web: abrir o perfil `tunnel`, abrir o túnel rápido, registrar o endereço efêmero em `OAUTH_REDIRECT_URIS` e na interface, usuário `demo`, sublimite e janela; fechar ao fim.
5. ADR 0026 no repositório e no índice; spec D6 coerente.

## Critérios de conclusão

- Testes de configuração provam que só o authorize da API passa pelo proxy e que a interface monta o login com a URL pública quando configurada.
- Fluxo local completo pelo proxy (sem túnel) passa: login por redirecionamento, sessão aberta, logout revoga.
- Teste por outra rede com o túnel aberto; URL efêmera não versionada.

## Resultado

Perfil `tunnel` com proxy Caddy de porta única: só `GET` e `POST /v1/auth/authorize` chegam à API; a API ignora cabeçalhos de encaminhamento (`--no-proxy-headers`); a interface usa `AUTH_AUTHORIZE_URL`; com redirect público, a API não sobe com credenciais de exemplo.
`test_v100_tunnel.py` cobre o roteamento lido do Caddyfile, o fluxo do `demo` numa origem https e a trava de credenciais; a interface tem 8 testes do túnel.
Túnel rápido usado por um celular em rede móvel: login, atendimento, encaminhamento e resposta da operadora. Evidência: [resultado da v1.0.0](../evidence/v100-resultado.md) e [ADR 0026](../architecture/decisions/0026-tunel-com-login-por-redirecionamento.md).

## Status

```text
concluída (v1.0.0)
```
