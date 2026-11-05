# Revisão independente da correção pós-QA da v0.8.0

O Reviewer usou `gpt-6.1-terra/xhigh` em contexto novo e examinou somente pacotes isolados, sem consultar o conjunto lacrado, o runtime ou o ledger.

| Candidato | Parecer | Evidência |
| --- | --- | --- |
| `f83cc212cb11de5e8d3ae999d06dfafe37c49051` | Correção necessária | P2. A frase de consistência aceitava taxas diferentes se o valor esperado aparecesse em outro trecho. Patch `e52eb4e35104d3db7e15fbd1cd38a91c07243b7b866e3a832567ca7b4232afc7`. |
| `43fd6dadafae5acf8c07753492097f596cd5cef6` | Correção necessária | P2. A frase com o valor completo ainda aceitava negações diretas. Delta `0edaf6616ba8beb3d7ab4eaff7ce4075572a2bafb4b2b3d3df245498bd90dfa0`. |
| `719cf025fb771382757a90c1d041ada504b75270` | Apto em revisão estática | As contradições conhecidas e variantes diretas são recusadas e o positivo permanece. Delta `affd2b2f4f03c619eb8f651cf88c1ea6eccd2ab252f1d41aac465ab08495051a`. |
| `4c3c8a98ddfc4f7af7bba877177f3479152159b5` | Apto em revisão estática | O teste integrado encontrou divergência no catálogo da bancada. O delta espelha somente `must_include_any` e `must_not_include` de `SC-SALE-CANCELLATION` com o caso de origem. Delta `f2770163604fdf86fe3f870912ec17180bddbec25c217b302e7850a9dd539221`. |

O delta final preserva a busca direta. O fallback web após lacuna exige sinal de evidência direta e citação, com insuficiência quando não há declaração válida. O sinal vem do modelo de busca. A fixture programada declara evidência direta só para o fato sintético que ela cobre. O Knowledge depois do Support conserva RAG e fontes oficiais, com instrução restrita ao procedimento. O blob de Personality volta ao mesmo da r3. O protocolo oferecido ao juiz vem de escalada registrada e bem-sucedida, passa pelo filtro de evidência e não altera julgamentos anteriores.

O recorte de 22 IDs e quatro conversas cobre os caminhos atingidos identificados pelo Supervisor. A rubrica literal permanece limitada às construções que consegue medir. O juiz independente continua como controle adicional. A suíte geral e o reteste real ficam fora do parecer estático. [Triagem](v080-qa-triagem-r4.md) [Recorte e orçamento](v080-revalidacao-orcamento-r4.md)
