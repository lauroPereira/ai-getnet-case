<!-- Papel: especificação da v1.1.0 (tickets do lojista no suporte, retomada da conversa e disponibilidade de motores e perfis). -->

# Tickets e retomada — v1.1.0

Versão 0.4, 2026-11-11. Estado: entregue na v1.1.0 (2026-11-11; [resultado](../evidence/v110-resultado.md)). Nasce do uso da demonstração por outra rede (v1.0.0); a D4, decidida pelo responsável, emenda a [ADR 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md). A parte da interface fica no projeto `ai-getnet-case-web`.

**Requisitos:** RF-130 (o lojista consulta seus tickets de atendimento humano em qualquer conversa), RF-131 (a interface retoma a última conversa depois de recarregar a página), RF-132 (motor de Router e perfis sem chave do provedor aparecem como indisponíveis).

**Orçamento:** tetos de US$0,10, US$0,05 e US$0,03 nas três campanhas da versão.

## Resultado desejado

1. Em qualquer conversa, o lojista pergunta pelos seus tickets de atendimento humano e recebe protocolo, estado e, quando houver, a resposta da atendente.
2. Recarregar a página e entrar de novo devolve a última conversa do lojista, com o histórico e a resposta da atendente; o lojista pode começar outra.
3. Motor de Router e perfis cujo provedor não tem chave no backend aparecem como indisponíveis e não são enviados.

## Decisões

| ID | Decisão | Motivo |
| --- | --- | --- |
| D1 | Ferramenta de leitura `get_handoff_cases` do Customer Support (especialista, escopo `SUPPORT_READ`): casos de encaminhamento do lojista do token, mais recentes primeiro, no máximo 5; filtro opcional `protocol`, completo ou o final com pelo menos 4 caracteres alfanuméricos, sem diferenciar maiúsculas. Por caso: protocolo, estado da fila, motivo, datas de abertura, assunção, resposta e encerramento, e o texto da resposta da atendente quando houver. Não expõe identificador de operador nem caso de outro lojista; auditada como as demais. O prompt do suporte ganha uma versão nova que diz quando usar a ferramenta. Pedidos de status de ticket ou protocolo chegam ao suporte (conferido com modelo real; o prompt do Router só muda se falhar) | Consultar os próprios tickets é capacidade básica de um agente de suporte; hoje ele só lê o histórico sintético de reclamações (`support_cases`) |
| D2 | Rota `GET /v1/conversations` (Bearer, dono): conversas do lojista do token por `updated_at` decrescente, `limit` de 1 a 20 (padrão 5). Por conversa: `conversation_id`, `state`, `created_at`, `updated_at`, protocolo do caso de encaminhamento quando houver e se há resposta de atendente ainda não entregue; sem texto de mensagem (a conversa completa continua em `GET /v1/conversations/{id}`). Papéis sem lojista vinculado recebem `403 insufficient_scope`. Na interface, depois do login de lojista ou `demo` e sem conversa na sessão, a interface retoma a mais recente: carrega o histórico de `GET /v1/conversations/{id}` (turnos do lojista, do assistente e da atendente, esta marcada `Atendente humano`), avisa "Conversa retomada" e oferece **Nova conversa**; a mensagem seguinte vai na mesma conversa. `POST /v1/messages` aceita um campo opcional com o identificador do turno da atendente que a interface já exibiu: se for um turno ainda não entregue desta conversa e deste lojista, a API marca como entregues esse turno e os turnos de atendente anteriores ainda não entregues da mesma conversa e responde à mensagem normalmente, sem repeti-los; identificador de outro turno, de outra conversa ou já entregue não muda nada; sem o campo, a entrega continua como antes | A conversa vivia só no estado da sessão do Streamlit; recarregar a página (comum no celular) abria uma conversa nova e escondia a resposta da atendente |
| D3 | `GET /v1/profiles` acrescenta `available` por perfil (a chave de cada provedor dos agentes do perfil está configurada no backend) e `router_mechanisms` (`llm` e `jev`, este verdadeiro só com `TYPESAFE_API_KEY`); nenhum valor de chave sai da API. A interface marca o perfil indisponível, desabilita o JEV indisponível (atendimento e comparações) com uma frase que diz qual chave falta no backend e escolhe por padrão um perfil e um motor disponíveis. A API continua recusando com `provider_unavailable` se receber a escolha mesmo assim | A interface oferecia opções que só falhavam no envio quando o backend roda apenas com a chave da OpenAI |

| D4 | A ação **Responder** da operadora chega ao lojista com o texto que ela escreveu: o turno `via=operator` não passa pela Personality nem por outra reescrita, e é esse texto que `get_handoff_cases` devolve. **Aprovar o rascunho** (texto da IA aprovado pela operadora) e **Rejeitar com instrução** continuam pela Personality e pela guarda de saída. Checagens que não alteram o texto podem continuar. Emenda a [decisão 0018](../architecture/decisions/0018-interrupcao-retomada-webhooks.md) | A resposta marcada `Atendente humano` não pode conter frases que a atendente não escreveu |

## Critérios de aceitação

- **CA-76 (D1)** Em conversa nova, "Tenho algum ticket aberto?" e "Qual o status do ticket que termina em <final do protocolo>?" devolvem protocolo e estado do caso do próprio lojista e, quando existe, a resposta da atendente; numa lista com tickets abertos e respondidos, a pergunta pelos abertos traz cada ticket com protocolo e estado, e a resposta da atendente vem com certeza quando o lojista pergunta por aquele ticket ou por novidades dos atendimentos; outro lojista nunca vê o caso; cada chamada fica auditada. Testes com modelo roteirizado e conferência com modelo real na validação.
- **CA-77 (D2)** Recarregar a página e entrar de novo retoma a última conversa com o histórico e a resposta da atendente; a mensagem seguinte recebe resposta à própria pergunta, sem repetir a da atendente; **Nova conversa** começa outra; a rota lista só conversas do dono, sem texto, com limite; operador e serviço recebem `403`.
- **CA-78 (D3)** Sem `TYPESAFE_API_KEY` e sem `DEEPSEEK_API_KEY`, a interface não deixa enviar pelo JEV nem pelos perfis que dependem do DeepSeek e diz qual chave falta; com as chaves, tudo como antes; nenhum valor de chave sai da API.

- **CA-79 (D4)** A resposta escrita pela operadora aparece ao lojista, na interface, em `GET /v1/conversations/{id}` e em `get_handoff_cases`, idêntica ao texto enviado; aprovar o rascunho continua passando pela Personality.

## Tarefas

109. Ferramenta de tickets do lojista no suporte (D1).
110. Lista de conversas na API e retomada na interface (D2).
111. Disponibilidade de motor e perfis na API e na interface (D3).
112. Fechamento: versão 1.1.0, CHANGELOG, README (status, roadmap, tabela de versões, ferramentas do suporte, trilha) e contrato.
113. Resposta da operadora sem reescrita (D4) e ajustes da validação: estado do ticket no idioma do lojista, query do login fora do log de acesso, teste do turno de atendente mais recente na confirmação de exibição.

Ordem: 109 a 113; validação pela [história](../historias/tickets-retomada-v110.md) com modelo real e Docker. Nenhuma migração: as tabelas `handoff_cases`, `conversations` e `messages` já têm o que as rotas e a ferramenta leem.
