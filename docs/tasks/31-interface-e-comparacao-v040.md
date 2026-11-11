# Tarefa: Interface Streamlit, perfis e comparação de Router

## Objetivo

Permitir chat e comparação com indicação do método e sem chamadas por rerun.

## Especificação relacionada

RF-41–43, RF-47–53, RF-67, RF-70 e CA-32–37/CA-44; [plano v0.4.0](../specs/perfis-interface-v040-plano.md).

## Pré-condições

Base web validada, OpenAPI e fixtures da tarefa 29 disponíveis; adaptadores reais ainda sujeitos à autorização de gasto.

## Arquivos prováveis

Pacote Streamlit, cliente HTTP gerado, fixtures, dependências, testes AppTest e documentação do projeto web.

## Passos

1. Implementar o cliente a partir do OpenAPI e o modo simulado; credenciais de provedores ficam no backend.
2. Criar chat contínuo, seleção de perfil publicado, toggle LLM/JEV e inspeção saneada da execução.
3. Implementar comparação isolada e uso único da decisão selecionada; publicação de perfil somente em modo admin.
4. Expor no editor administrativo apenas parâmetros documentados que a API lista para o modelo e agente selecionados.
5. Testar reruns, sessão expirada, vazio, loading, backend/JEV indisponível, perfil incompatível e real/simulado/gravado.

## Critérios de conclusão

- [x] Interface não acessa banco/Qdrant/arquivos do backend nem recebe chave de provedor.
- [x] Navegação/rerun não faz novo envio ou publicação; cliente de rede é reutilizado e fechado no logout/troca de modo.
- [x] Comparação executa só Routers e atendimento usa uma única vez a decisão explicitamente selecionada.
- [x] Editor admin configura `max_output_tokens` apenas para os modelos/agentes compatíveis; JEV não aceita parâmetro e Evaluation permanece reservado para v0.6.0.
- [x] AppTest e HTTP integrado passam; execução real de JEV ainda não foi validada apenas por mock. *JEV real na v0.5.0.*

## Resultado

Interface Streamlit com chat, perfis publicados, toggle LLM/JEV, comparação isolada com uso único e editor de `max_output_tokens` por agente compatível. Suíte web: 12 testes; AppTest validou login, mensagem única, rerun e logout, sem inferência de provedor. Evidência: [resultado da v0.4.0](../evidence/v040-resultado.md).

## Status

```text
concluída (v0.4.0)
```
