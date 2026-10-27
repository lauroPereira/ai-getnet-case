# Contratos propostos da API v0.4.0

Contrato aprovado no plano completo em 2026-10-27, antes das telas; a
implementação deve demonstrar sua conformidade. Origem:
[plano v0.4.0](perfis-interface-v040-plano.md), RF-42, RF-47–53 e RNF-09.
Nomes de campos/código são em inglês. `POST /messages` mantém seu contrato.

## Autenticação e erros

Sessão opaca `Authorization: Bearer <token>` em todas as rotas `/v1`, exceto
emissão de sessão. Credencial de acesso é distinta de chave de provedor.
Token expira em 60 minutos; servidor guarda somente digest e pode revogar.
Sem configuração de credenciais, `/v1/sessions` falha fechado; não há senha
padrão de produção. Respostas nunca incluem chaves de OpenAI/DeepSeek/JEV.

Erro comum: `{"error":{"code":"...","message":"...","request_id":"req_..."}}`.
401 para sessão inválida, 403 para papel/ação negados, 404 para recurso de
outro dono/ausente sem revelar existência, 409 para conflito de versão ou
comparação consumida/obsoleta, 422 para configuração incompatível, 503 para
provedor indisponível/não configurado e erro explícito de custo não verificável.

## Rotas e autorização

| Método e rota | Entrada principal | Saída principal | Permissão |
| --- | --- | --- | --- |
| `POST /v1/sessions` | `access_key` | `access_token`, `token_type`, `expires_at`, `role` | Chave validada determina principal/papel |
| `DELETE /v1/sessions/current` | Bearer | 204 | Própria sessão |
| `GET /v1/catalog/models` | — | `models`, `verified_at`, `sources` | Demo/admin; só metadados públicos |
| `GET /v1/profiles` | — | Perfis/versões publicados permitidos | Demo só perfis autorizados; admin vê rascunhos |
| `POST /v1/profiles` | `name`, `agents`, `demo_allowed` | Rascunho com ID/versão | Admin |
| `PUT /v1/profiles/{id}/draft` | `expected_version`, `agents` | Nova revisão de rascunho | Admin; rejeita edição de publicado |
| `POST /v1/profiles/{id}/publish` | `expected_version` | Versão publicada imutável | Admin; valida capacidades/preços |
| `POST /v1/messages` | `message`, `conversation_id?`, `profile_id`, `profile_version`, `router_mechanism`, `comparison_id?` | Resposta do assistente e `run` efetivo | Demo/admin; dono é resolvido no servidor |
| `POST /v1/router/compare` | Mensagem/conversa/perfil, `selected_mechanism` | `comparison_id`, decisões/metadados e `expires_at` | Demo/admin; só Routers, nenhum atendimento |
| `GET /v1/runs/{id}` | — | Snapshot, resultado, fontes, ferramentas e métricas saneados | Demo só seu escopo, admin autorizado |
| `GET /v1/conversations/{id}` | — | Estado/histórico saneado | Demo só seu escopo, admin autorizado |

A rota de rascunho detalha o ciclo previsto por RF-50; nenhum endpoint de
edição de orçamento, guardrail ou permissão é criado. Mudança posterior destes
contratos exige revisão/aceite proporcional antes de consumidores dependerem dela.

## Configuração por agente e catálogo

`agents` mapeia `router`, `knowledge`, `support`, `escalation`, `personality`
e `evaluation` para `provider`, `model`, `model_version?`, `parameters`.
Parâmetros só podem pertencer ao conjunto implementado para aquele modelo.
JEV só é válido no Router. O modelo de embeddings não é um campo editável
do perfil. Publicado inclui `profile_id`, `version`, `published_at` e digest.

Entrada do catálogo: identificador/versionamento do provedor; agentes
permitidos; capacidades verificadas (`tools`, `structured_output`, `web_search`);
parâmetros suportados; preço/unidade/moeda/data/fontes. Não oferecer um modelo
por simples presença em `/models`; capacidade não comprovada é indisponível.
Custo desconhecido bloqueia uso real, sem aparecer como zero.

## Snapshot e comparação

`run` contém `request_id`, `profile_id`, `profile_version`, `router_mechanism`,
`execution_mode` (`real`, `simulated`, `recorded`), versões de prompt/base,
modelos efetivamente usados, tempos e custo. Resultado gravado preserva método
e instante originais. Não exibir raciocínio interno ou resposta bruta de provedor.

Comparação usa exatamente o mesmo texto, histórico, prompts e snapshot para
LLM e JEV. Os dois custos passam pela guarda; nenhum especialista/ferramenta
é executado nesse endpoint. Ao enviar `comparison_id` para atendimento, o
servidor verifica dono, hash da entrada, versão/estado da conversa, snapshot,
mecanismo selecionado e validade de cinco minutos, reutiliza a decisão e
consome o registro atomicamente uma vez. Divergência ou repetição retorna 409;
não rerotear silenciosamente nem criar caso/encaminhamento em duplicidade.

## Exemplos sintéticos de fluxo

1. Sessão demo válida recebe token opaco e perfil Referência publicado.
2. Chat envia `profile_id="reference"`, versão publicada, `router_mechanism="llm"`.
3. Híbrido seleciona JEV; se indisponível, UI mostra falha explícita sem fallback.
4. Comparação retorna duas decisões e um ID; envio subsequente usa a escolhida
   uma vez. Atualizar a tela só reapresenta o resultado.
5. Demo tenta publicar perfil e recebe 403 antes de qualquer escrita.

Identificadores de modelos, versão real do JEV, preço e enumerações específicas
de parâmetros serão preenchidos somente após verificação oficial autorizada.
Os exemplos não afirmam integração real concluída.
