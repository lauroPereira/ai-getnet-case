# Tarefa: interface administrativa da base

## Objetivo

Permitir a jornada documento→rascunho→diff→candidata→teste→ativação→retorno.

## Especificação relacionada

RF-63/67/70 e CA-41/44; [história v1](../historias/base-versionada-v050.md).

## Pré-condições

Contrato aprovado/implementado antes das telas e OpenAPI exportado de ambiente isolado.

## Arquivos prováveis

Projeto web app/cliente/fixtures/snapshot OpenAPI e testes AppTest.

## Passos

1. Sincronizar contrato/cliente, sem acesso direto a arquivos/bancos do backend.
2. Oferecer leitura, editor/diff e ações com custo/confirmação explícitos.
3. Mostrar ativa/anterior/candidata, testes, carregando/vazio/erro e conflitos.
4. Testar rerun sem envio, demo sem ação admin e jornada completa.

## Critérios de conclusão

- [ ] UI e backend aplicam permissões/origem; segredo não vai ao frontend.
- [ ] Build/teste/ativação/retorno não se repetem em rerun.
- [ ] Erro/confirmação claros; consumo só pela API documentada.

## Validação e status

Implementada pelo Developer r1. Jornada administrativa usa somente `/v1`; OpenAPI/cliente foram gerados de assembly sintético. Suíte web: 15 testes; Ruff e estrutura aprovados. A jornada com provedor real fica para QA após revisão.
