# 0012. Exposição pública da demonstração

## Título

Expor somente a interface Streamlit pelo IP público e porta da máquina do responsável, com autenticação, HTTPS quando possível, limites por sessão e sublimite de orçamento.

## Status

```text
proposta
```

## Contexto

O responsável prefere compartilhar a demonstração diretamente pelo IP público, sem tornar um túnel dependência. A máquina é pessoal, a conexão pode estar atrás de CGNAT e a demonstração consome a cota das APIs.

## Decisão

- Expor só a porta da interface; API, Qdrant e `mocks` ficam na rede interna.
- A interface exige login; o papel `demo` vê cenários e perfis autorizados; o papel `admin` é reservado ao responsável e verificado no backend.
- HTTPS com certificado próprio configurado no Streamlit; sem isso, a credencial de demonstração é de uso único e de baixo privilégio.
- Limite de requisições por sessão e sublimite de orçamento da demonstração, inicialmente US$1,00 e aumentável pelo responsável dentro do teto total, com bloqueio explícito ao atingir.
- Verificar cedo (v0.4.0) IP público, CGNAT e redirecionamento de porta; se impedido, registrar e oferecer túnel como alternativa documentada.
- Janela de disponibilidade definida; ao fim, fechar a porta.

## Alternativas consideradas

- **Túnel como padrão:** contraria a preferência do responsável; fica como alternativa.
- **Hospedagem em nuvem:** fora do escopo (sem serviços pagos).
- **Expor também a API:** amplia a superfície sem necessidade.

## Consequências

O recrutador acessa sem instalar nada, com risco controlado. Disponibilidade depende da máquina e da conexão do responsável. Abrir a porta no roteador é ação do responsável.

## Data

2026-10-26
