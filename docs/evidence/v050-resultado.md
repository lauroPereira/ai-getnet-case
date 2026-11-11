# Resultado da v0.5.0

## Capacidades

- O registro da base de conhecimento nasce dos snapshots públicos e do corpus fictício de demonstração; só documentos `simulated_internal` são editáveis, e as fontes oficiais ficam somente leitura.
- Rascunhos têm revisões otimistas e diff; cada versão candidata é construída numa coleção Qdrant própria, com manifesto congelado e etapa explícita de teste.
- Ativação e rollback são explícitos, com verificação de integridade da coleção contra o manifesto e log de eventos com autor, hora e evidência.
- Cada execução captura uma versão identificada da base no início e termina nela, mesmo que outra seja ativada no meio.
- Lotes de embedding reservam orçamento antes da chamada e liquidam uma vez depois; o teto persistente de cada ledger (`<ledger>.limit`) é gravado no primeiro uso, e uma configuração posterior não o aumenta.
- A Administração no Streamlit cobre documentos, editor, diff, estimativa, build, teste, ativação e rollback; a conversa se recupera por GET depois de uma falha de transporte, sem reenvio automático.

## Validação

| Verificação | Resultado |
| --- | --- |
| Candidato | [R7](v050-candidato-r7.json): 46 arquivos do backend e 85 da interface, fonte `ad9cf469cd85e44210280df1949ecac766857688a6f1101bb61f8d0e9e9b8d8c`; runtime e build do backend iguais aos do r3 ([Docker r7](v050-docker-r7.json)) |
| Suíte do backend | 293 testes aprovados |
| Interface | 20 testes aprovados; Ruff limpo |
| Revisão independente | Backend apto ([revisão](v050-reviewer-r2.md)); recuperação da conversa por GET apta no r7 ([revisão da interface](v050-reviewer-ui-r3.md)) |
| Validação com modelos reais | Embeddings, construção da base de referência, ciclo rascunho → candidata → teste → ativação → rollback pela interface, proteções 403, 409 e 429, captura de versão durante a troca, comparação real de Router DeepSeek e JEV, e a resposta persistida recuperada pela interface com um GET, sem POST repetido ([validação](v050-qa-r3.md)) |
| Critérios | CA-41 e RF-63 a RF-66 com evidência nas três execuções reais |

## Gasto

US$0,00553883 na campanha (35 entradas, teto adicional de US$0,25), sem reservas abertas. O mesmo gasto aparece no ledger primário (885 entradas, US$0,34852844) e não é somado duas vezes. Acumulado do projeto: US$0,59837466, com teto de US$5 na época.

## Decisão

Integrada na `main` em 2026-10-27 (PRs backend #6 e web #2), com as tags `v0.4.0` e `v0.5.0`. O retorno à v0.4.0 é pela migração 0007 → 0006, que remove as tabelas da base e mantém as coleções Qdrant.
