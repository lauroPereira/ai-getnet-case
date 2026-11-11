# 0012. Exposição pública da demonstração

## Título

Expor somente a interface Streamlit pelo IP público e porta do host da demonstração, com autenticação, HTTPS quando possível, limites por sessão e sublimite de orçamento.

## Status

Aceita (2026-10-26). Emendada pela [ADR 0026](0026-tunel-com-login-por-redirecionamento.md) (v1.0.0): a publicação por túnel expõe também a rota de autorização da API.

## Contexto

A demonstração é servida por um host único, sem tornar um túnel dependência. A conexão pode estar atrás de CGNAT e a demonstração consome a cota das APIs.

## Decisão

- Expor só a porta da interface; API, Qdrant e `mocks` ficam na rede interna.
- A interface exige login; o papel `demo` vê cenários e perfis autorizados; o papel `admin` é reservado ao responsável e verificado no backend.
- HTTPS com certificado próprio configurado no Streamlit, ou credencial de demonstração de uso único e de baixo privilégio.
- Limite de requisições por sessão e sublimite de orçamento da demonstração, inicialmente US$1,00 e aumentável pelo responsável dentro do teto total, com bloqueio explícito ao atingir.
- Verificar cedo (v0.4.0) IP público, CGNAT e redirecionamento de porta, com túnel como alternativa documentada. O acesso por outra rede (RF-98) foi validado por túnel na v1.0.0 ([resultado](../../evidence/v100-resultado.md)).
- Janela de disponibilidade definida; ao fim, fechar a porta.

## Alternativas consideradas

- **Túnel como padrão:** não adotado nesta decisão, para não depender de um serviço externo; adotado na v1.0.0 com login por redirecionamento ([ADR 0026](0026-tunel-com-login-por-redirecionamento.md)).
- **Hospedagem em nuvem:** não adotada: o projeto não usa serviços pagos de hospedagem.
- **Expor também a API:** não adotado: amplia a superfície sem necessidade.

## Consequências

O visitante acessa sem instalar nada, com a superfície limitada à interface autenticada. A disponibilidade segue a janela anunciada do host; abrir a porta no roteador é passo do operador da demonstração.

## Data

2026-10-26
