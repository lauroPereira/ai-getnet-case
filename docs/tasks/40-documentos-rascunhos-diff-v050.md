# Tarefa: documentos, rascunhos e diff

## Objetivo

Expor edição controlada do corpus fictício com leitura de oficiais.

## Especificação relacionada

[API proposta](../specs/api-kb-v050-proposta.md), RF-63/66 e CA-41.

## Pré-condições

Contrato aprovado e registro da tarefa 39 disponível.

## Arquivos prováveis

API `/v1`, registro KB, schemas e testes de autorização/validação.

## Passos

1. Listar/consultar documentos por IDs registrados no servidor.
2. Salvar rascunho somente fictício, com revisão/tamanho/origem validados.
3. Mostrar diff/hash e testar demo, oficial, revisão obsoleta e caminho inválido.

## Critérios de conclusão

- [x] Escritas admin; demo/oficial recusados sem efeito.
- [x] Limite de 64 KiB e 409 de revisão; nenhum caminho arbitrário.
- [x] Texto editado não muda ferramentas, orçamento ou autoridade financeira.

## Resultado

Leitura de fontes oficiais, rascunho só para documentos fictícios, demo sem escrita, revisão obsoleta com `409`, edição e diff, cobertos por testes unitários e de integração com transportes sintéticos. Suíte estrita do backend: 293 testes. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
