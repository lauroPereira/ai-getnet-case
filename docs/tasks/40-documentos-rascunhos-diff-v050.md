# Tarefa: documentos, rascunhos e diff

## Objetivo

Expor edição controlada do corpus fictício com leitura de oficiais.

## Especificação relacionada

[API proposta](../specs/api-kb-v050-proposta.md), RF-63/66 e CA-41.

## Pré-condições

Contrato aprovado e registro da tarefa39 disponível.

## Arquivos prováveis

API `/v1`, registro KB, schemas e testes de autorização/validação.

## Passos

1. Listar/consultar documentos por IDs registrados no servidor.
2. Salvar rascunho somente fictício, com revisão/tamanho/origem validados.
3. Mostrar diff/hash e testar demo, oficial, revisão obsoleta e caminho inválido.

## Critérios de conclusão

- [ ] Escritas admin; demo/oficial recusados sem efeito.
- [ ] Limite64KiB e409 de revisão; nenhum caminho arbitrário.
- [ ] Texto editado não muda ferramentas, orçamento ou autoridade financeira.

## Validação e status

Implementada pelo Developer r1. Contrato exercitado com fonte oficial somente leitura, demo sem escrita, revisão obsoleta (`409`), edição fictícia e diff. Unitários e integração usam transportes sintéticos; nenhuma chamada paga.
