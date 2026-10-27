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

## Validação

Migration 0006 verificou subida/descida para schema 5 preservando dados legados; perfis publicados são imutáveis e modelos/capacidades/parâmetros validados. Parâmetros integram a versão e o digest; o snapshot registra o valor efetivo antes do payload. Cobertura em `tests/unit/data/test_migrations.py`, `tests/integration/test_v1_api.py` e `tests/unit/test_profile_output_parameters.py`; backend strict r4: 214 passed.

## Status

Implementada e testada com estado sintético; revisão independente pendente.
