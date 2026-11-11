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

- [x] UI e backend aplicam permissões/origem; segredo não vai ao frontend.
- [x] Build/teste/ativação/retorno não se repetem em rerun.
- [x] Erro/confirmação claros; consumo só pela API documentada.

## Resultado

Jornada administrativa só por `/v1`, com OpenAPI e cliente gerados de montagem sintética; build, teste, ativação e retorno percorridos pela interface na validação real da versão. Suíte web: 15 testes; Ruff e estrutura aprovados. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
