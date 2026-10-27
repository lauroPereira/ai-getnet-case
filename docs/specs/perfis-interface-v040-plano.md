# Plano: perfis, Router JEV e interface da v0.4.0

## Especificação relacionada

[Incrementos aprovados](incrementos-pos-nucleo.md): RF-35, RF-41–43 e
RF-47–53; CA-28 e CA-32–37. Decisões aceitas 0007 e 0008.
Base: v0.3.0, merge `bd549cc921ccffb37bd304a0959b8a4b690d6421` e
[PR #4](https://github.com/lauroPereira/ai-getnet-case/pull/4) integrado.
Branch de planejamento `codex/v0.4.0-perfis-interface`, criada após atualizar main.

**Estado:** plano completo aprovado pelo responsável em 2026-10-27, com a
resposta “Aprovar plano completo sem chamadas pagas”. Implementação local
autorizada nos contratos, autenticação, migração, base web e delegação abaixo.
O aceite da sequência até v0.7.0 permanece preservado.

## Decisões técnicas

1. Preservar `POST /messages`, ferramentas, MCP, guardrails, centavos,
   memória e teto global. A nova interface usa exclusivamente a API `/v1`.
2. Adaptadores por provedor sob a interface existente de modelos: OpenAI,
   DeepSeek e JEV/TypeSafe apenas na decisão do Router. Catálogo registra
   identificador, versão, capacidades, parâmetros e preço verificados.
   API de modelos fornece identificadores; capacidades/preços exigem também
   documentação oficial. Combinação ausente, incompatível ou não verificada
   não pode ser oferecida nem aceita. Não inventar identificadores/preços.
3. JEV usa o contrato real descrito pelo provedor para `/v1/systemone`;
   saída validada como `RouterDecision`. Erro/timeout/decisão inválida/custo
   desconhecido produzem erro explícito, sem troca silenciosa para LLM.
4. Perfis publicados são imutáveis. Referência, Híbrido e Ajustado usam
   modelos compatíveis e só diferem de forma declarada. Cada execução congela
   perfil, versões dos prompts/base, mecanismo e configuração efetiva. O
   perfil pode configurar Evaluation, mas sua execução automática pertence
   à v0.6.0. Embeddings permanecem separados e inalterados nesta versão.
5. Sessões e papéis verificados no backend, conforme
   [decisão proposta 0013](../architecture/decisions/0013-sessoes-api-e-perfis-v040.md).
   A interface não recebe chaves dos provedores. O principal demo fica
   vinculado ao lojista sintético permitido pelo servidor; informar papel
   ou ID no corpo não concede autoridade.
6. Comparação executa apenas os dois Routers, sem ferramentas, casos ou
   encaminhamentos. Um resultado armazenado pode fornecer a decisão do
   mecanismo selecionado a uma única execução de atendimento; vínculo de
   dono, mensagem, conversa, estado e snapshot é conferido no servidor.
7. Streamlit em projeto independente; modo simulado com contratos iguais,
   sem acessar arquivos/banco/Qdrant do backend. Rerun só reapresenta estado;
   enviar, comparar ou publicar exige ação explícita.

## Componentes afetados

Backend: `llm/`, agentes, montagem do grafo/contexto por execução, API,
configuração, persistência de perfis/sessões/comparações, traces, migrações,
testes e catálogo verificado. Não alterar regras financeiras ou de segurança
existentes para acomodar um modelo.

Web: base documental independente e depois pacote Streamlit, cliente HTTP
gerado dos contratos, fixtures de respostas e testes AppTest. Preparação
concreta em [base web proposta](base-web-v040-proposta.md).

## Modelo de dados

**Migração 0006, reversível, autorizada no escopo abaixo:**

| Entidade | Conteúdo e invariantes |
| --- | --- |
| `profiles` | Identidade, nome e ponteiro de versão publicada; seleção permitida para demo |
| `profile_versions` | Configuração por agente, versões e capacidades; rascunho editável, publicado imutável |
| `api_principals` | Papel e escopo sintético; referência/digest de credencial, nunca segredo em claro |
| `api_sessions` | Digest do token opaco, principal, expiração e revogação; token em claro só na emissão |
| `router_comparisons` | Dono, hash da mensagem/estado, snapshot, decisões, tempos/custos e consumo único |
| `run_snapshots` | Request ID, dono e snapshot efetivo imutável; liga-se ao trace atual sem implementar o avaliador da v0.6.0 |

Sem alteração destrutiva das tabelas de 0005. Subida/descida 0005→0006→0005
somente em bancos sintéticos novos. Descida remove apenas entidades novas;
nenhum runtime anterior ou ledger pode ser reiniciado. Segredos de sessão
reais não entram nas fixtures versionadas.

## APIs ou interfaces

[Proposta de contratos](api-v040-proposta.md), anterior ao desenvolvimento das
telas. OpenAPI gerado e validado contra os exemplos antes da integração web.
Erros estruturados e IDs rastreáveis; tokens nunca em URL, logs ou traces.

Não muda o contrato legado. A superfície `/v1` é aditiva e autenticada, com
papéis/escopo por rota. A exposição pública e configuração do roteador não
fazem parte desta implementação; apenas instruções de verificação antecipada.

## Estratégia de testes

- Adaptadores com transportes falsos sem rede: respostas válidas/inválidas,
  timeout, capacidades incompatíveis, orçamento insuficiente/custo desconhecido.
- Perfis: imutabilidade publicada e snapshot preservado durante alteração
  concorrente; comparação consome só Routers, atendimento no máximo uma vez.
- API: token ausente/expirado/revogado, demo tentando escrita admin, adulteração
  de principal/conversa/comparação, ausência de segredos, compatibilidade legado.
- Dados: 0005→0006→0005, preservação das tabelas/dados anteriores e do ledger.
- Interface: AppTest e servidor simulado HTTP; estados vazio/erro/indisponível,
  real/simulado/gravado distintos e reruns sem chamada paga/reenvio.
- Regressão: validação estrita, 40 casos e quatro conversas, história nova,
  Docker e MCP conforme escopo afetado; fontes e hashes Git fixados.
- Rodada real JEV/DeepSeek/OpenAI: só depois de preços/capacidades verificados,
  estimativa e nova autorização monetária. Sem evidência real, CA-32 fica pendente.

## Riscos técnicos e recuperação

Credencial virar seleção de papel; comparação executar atendimento duplicado;
perfil mudar durante a requisição; JEV retornar contrato/preço desconhecidos;
Streamlit repetir chamadas. Testar os limites no backend, congelar snapshot,
consumir comparação uma vez e separar modo simulado. Retorno pelo código/tag
v0.3.0 e pela migração 0006→0005 em banco sintético isolado. Se o destino web
estiver ocupado, parar antes da escrita; não apagar nem sobrescrever por inferência.

## Plano de implementação

27. [Catálogo e adaptadores](../tasks/27-catalogo-e-adaptadores-v040.md).
28. [Perfis e snapshots](../tasks/28-perfis-e-snapshots-v040.md).
29. [API e sessões](../tasks/29-api-e-sessoes-v040.md).
30. [Base do projeto web](../tasks/30-base-projeto-web-v040.md).
31. [Interface e comparação](../tasks/31-interface-e-comparacao-v040.md).
32. [Regressão e candidato](../tasks/32-regressao-candidato-v040.md).

[História versão 1](../historias/perfis-interface-v040.md), fixada antes do
Developer. Supervisor coordena; autorização explícita para esta versão:
três subagentes em sequência Developer → Reviewer → QA, cada um explicitamente
`gpt-6-luna/high`, contextos novos e nenhum agente adicional. Correções voltam
ao mesmo Developer. Developer acionado após aprovação, com os parâmetros
explícitos; Reviewer e QA entram em sequência após suas respectivas passagens.

## Aprovação registrada e limites

O conjunto aprovado inclui contratos `/v1`, autenticação/papéis, migração
0006 e preparação/criação de arquivos novos em `C:\workspace\ai-getnet-case-web`,
com governança proposta e identidade explicitadas na base web. Incluir rede
para documentação oficial, metadados de modelos sem cobrança confirmada e
dependências/builds de teste. Consultas que cobrem ou tenham custo desconhecido
permanecem bloqueadas; não usar o saldo da validação v0.3.0 como autorização nova.

Não inclui commit/push/PR/tag da v0.4.0, criação de remoto web, abertura de portas,
publicação, compra, alteração de credencial existente ou aumento do teto.
Implementar e validar offline; pedir autorização paga somente com um candidato
e estimativa. Se o destino web estiver ocupado, preservar seus arquivos e
reconciliar antes da escrita.
