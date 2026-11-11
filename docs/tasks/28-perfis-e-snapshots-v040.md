# Tarefa: Perfis imutáveis e snapshots por execução

## Objetivo

Publicar perfis compatíveis e congelar configuração efetiva durante cada execução.

## Especificação relacionada

RF-40, RF-49–52 e CA-36–37; [plano v0.4.0](../specs/perfis-interface-v040-plano.md).

## Pré-condições

Tarefa 27 e autorização da migração reversível 0006; bancos sintéticos isolados.

## Arquivos prováveis

Persistência, migrações, configuração/contexto de execução, traces e testes.

## Passos

1. Criar migração 0006 para as entidades aprovadas; testar subida/descida preservando 0005 e ledger.
2. Implementar Referência, Híbrido e Ajustado com publicação imutável e validação de capacidades/preço.
3. Congelar agentes, prompts, base, mecanismo e versões no início; registrar modelos efetivos no trace.
4. Testar alteração concorrente de rascunho/publicação sem afetar execução iniciada e impedir edição de publicado.

## Critérios de conclusão

- [x] 0005→0006→0005 preserva dados anteriores em ambiente sintético.
- [x] Publicado é imutável; snapshot registra parâmetros configurados e `effective_parameters_by_agent` reservado/enviado.
- [x] Referência/Híbrido/Ajustado têm diferenças declaradas e modelos compatíveis.
- [x] Embeddings, guardrails, orçamento e regras financeiras não são campos editáveis.

## Resultado

Migração 0006 com subida e descida preservando os dados anteriores; perfis publicados imutáveis, parâmetros na versão e no digest e valor efetivo no snapshot antes do payload. Suíte estrita do backend: 214 testes. Evidência: [resultado da v0.4.0](../evidence/v040-resultado.md).

## Status

```text
concluída (v0.4.0)
```
