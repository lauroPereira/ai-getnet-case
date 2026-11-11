# Resultado da v0.4.0

## Capacidades

- Os perfis Reference, Hybrid e Adjusted são validados contra um catálogo datado de provedores, e cada versão publicada é imutável.
- A API `/v1` autentica com tokens de sessão opacos de 60 minutos, guardados só como digest SHA-256; o backend aplica papéis e posse, revoga sessões e consome cada comparação uma única vez, de forma atômica.
- O adaptador JEV System One serve só ao Router, sem fallback silencioso de provedor.
- A interface Streamlit é um cliente separado, com mapa de rotas gerado do snapshot OpenAPI, fixtures Simulado e Gravado e o modo Real (API) por HTTP.
- `max_output_tokens` é configurável por agente nos modelos OpenAI e DeepSeek, limitado pelo teto do agente e aplicado igual na reserva de orçamento e no payload.
- Trocar o Router depois de uma comparação descarta o resultado; uma nova comparação só começa com clique explícito.

## Validação

| Verificação | Resultado |
| --- | --- |
| Candidato | [Manifesto r6](v040-candidato-r6.json): 51 arquivos do backend e 84 da interface, fingerprint `d54fbd3799cecfefd0c467be217eb841e59d4ae9c89f607dc1a64967ae4d9367`; runtime `b8d3a1845ac4ea16c50272bb800248bc7c4df4dbd172e40c47ae220fb063c4a5`, build `ed67d7ff81f6ed49042e9f3aa332ac145fdd004fa38d6b99e7a05072155d816d` |
| Suíte do backend | 216 testes estritos; Ruff e skills aprovados |
| Interface | 14 testes; Ruff e estrutura aprovados |
| Revisão independente | Apto; os dois sentidos da troca de Router, contadores próprios e hashes conferidos ([revisão](v040-reviewer-r6.md)) |
| Validação independente | Apto: nos dois sentidos, mudar a escolha depois da comparação invalida o resultado; rótulo Gravado, publicação de perfil, parâmetros efetivos, snapshot e rejeição sem mudança de versão comprovados ([validação](v040-qa-r6.md)) |
| Build e execução | Imagem instalada com 124 arquivos iguais ao manifesto; imagem `sha256:3dc18d777ae79407363fddd4f5ca65c862b2cbb059f5af61a08e2d9e362d5c85` reutilizada por igualdade dos mapas de runtime e build ([Docker](v040-docker-r6.json)) |
| Conferência final | Mapas 51/84/127/128, 29 arquivos protegidos da interface e 124 instalados, sem divergências ([auditoria](v040-verificacao-final-r6.json)) |
| Critérios | CA-28, CA-33, CA-34–35, CA-36 (RF-49/51) e CA-37 comprovados com transporte HTTP real e inferência programada; CA-32, o JEV com modelo real, foi comprovado na v0.6.0 ([validação](v060-qa.md)) |
| Catálogo de modelos | Conferido nas fontes oficiais ([fontes](v040-catalogo-fontes.md), [parâmetros](v040-parametros-modelo-fontes.md)); a consulta pública aos metadados, sem credenciais, respondeu 401, 401 e 403 ([registro](v040-metadados-publicos.json)) |

A validação usou transporte HTTP real com modelos e embeddings programados, sem credencial de provedor.

## Gasto

Nenhuma chamada paga nesta versão. Total registrado do projeto: US$0,59283583. Os valores de liquidação dos testes de orçamento são sintéticos.

## Decisão

Integrada na `main` com a tag `v0.4.0` ([PR backend #5](https://github.com/lauroPereira/ai-getnet-case/pull/5), [PR web #1](https://github.com/lauroPereira/ai-getnet-case-web/pull/1)); a interface ganhou repositório próprio. O retorno à v0.3.0 é pela migração 0006 → 0005, validada em bancos sintéticos.
