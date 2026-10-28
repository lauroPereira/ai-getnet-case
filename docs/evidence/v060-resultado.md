# Resultado da v0.6.0

**Estado: apta nos dez itens de aceite, candidato local r5; acesso por outra rede pendente com o responsável.** Última versão com expansão funcional do case.

## Candidato

[R5](v060-candidato-r5.json): backend e web em `codex/v0.6.0-fechamento`, sobre as mains com a v0.5.0 (`c3a9027`, `4192169`). Fonte `3b6b697e53623ac08c54a521cc0aa094e2e5cc7e247b83a4c11e3ca9075a2639`, 63 arquivos backend e 13 web. Depois do QA, só documentação de fechamento mudou (README, CHANGELOG, critérios, tarefas e este registro).

## Fluxo e correções

Três subagentes Claude Opus 5.5, esforço high, contexto novo, em sequência (substitutos de `gpt-6-luna`, indisponível nesta sessão, escolhidos pelo responsável); os mesmos agentes nas correções; sem delegação aninhada. Detalhes em [supervisão](v060-supervisao.md).

| Etapa | Resultado | Evidência |
| --- | --- | --- |
| Developer, tarefas 54–58 | Implementação completa, 326/30 testes | [Passagem](v060-developer.md) |
| Reviewer r1 | Apto, 10 P3 | [Parecer](v060-reviewer.md) |
| Developer r2–r3 (tarefa 60) | P3 de orçamento, integridade e aceite corrigidos | Passagem, rodadas 2–3 |
| Reviewer r2–r3 | Apto; resíduos corrigidos | Parecer, rodadas 2–3 |
| QA r1 (r3) | Reprovado no item 3: toggle JEV executava o Router pelo LLM e registrava JEV (P1, presente desde a v0.5) | [QA](v060-qa.md) |
| Developer r4–r5 (tarefa 61) | JEV real nos dois caminhos; `R$` literal; estado após recuperação; devolução do limite pelo ledger | Passagem, rodadas 4–5 |
| Reviewer r4–r5 | Apto, sem achados novos | Parecer, rodadas 4–5 |
| QA r2 (r5) | **Apto**; sem defeito novo | QA, rodada 2 |

Validação estrita final: backend **349 passed**, web **42 passed**, Ruff limpo, código 0.

## Aceite

| Item | Resultado | Evidência principal |
| --- | --- | --- |
| 1. Regressão | Apto com ressalva | Suítes estritas; real: núcleo e desafio 27/27, conversas 4/4, habilitação e cancelamento ok; jornadas de negócio 7/13 pela rubrica literal (ver limitações) |
| 2. Chat e recuperação | Apto | Uma POST com resposta descartada pelo proxy (`req_1d17374452904ae0915e`) e um único GET; `R$` literal; estado do caso da resposta recuperada |
| 3. Toggle LLM/JEV | Apto | JEV `req_19ce44cbd8024167a0b6` com `router · jev-1.14.0` no ledger e nenhuma linha de Router LLM; contraste LLM `req_488dc6224dac4a7e8337`; comparação de perfis com JEV `pcmp_7beabd45446840389732` |
| 4. Perfis e comparação | Apto | 3 perfis × 2 cenários (`pcmp_0970a97a…`), reuso, dois gráficos, tabela e drill-down por GET; domínio original inalterado |
| 5. Efeito da documentação | Apto | V1 `req_4f72e4ce…` sem `get_contract_snapshot`; V2 `kb_29225785334648e3` com o trecho novo em primeiro (0,758), a ferramenta e a fonte do contrato; V1 restaurada sem a ferramenta (`req_105c15ea…` + 3 repetições) |
| 6. Ativação e retorno | Apto | Ciclo pela Administração; candidata extra `kb_85596ca27a774e3f` testada e não ativada |
| 7. Avaliação sob demanda | Apto | `eval:req_923c…` US$0,0000795; segunda solicitação reaproveitada sem custo |
| 8. Orçamento, isolamento e permissões | Apto | Demo `403` na Administração, limite demo `429` sem gasto, teto abaixo da estimativa `422` sem gasto; zero reservas abertas |
| 9. Execução e compartilhamento | Apto na parte local; acesso externo pendente | Docker r5 com API só em `127.0.0.1:8000`, schema 8, `knowledge_base` no `/ready`, smoke real `req_a2bcc71e79d1424f8334`; interface compartilhada com backend travado e Simulado só demo |
| 10. Documentação | Apto | README, CHANGELOG, guia, roteiros de teste manual e de vídeo alinhados a este registro |

A sonda inconclusiva da v0.5.0 não foi convertida em reprovação; o efeito da documentação foi comprovado nesta versão por ferramenta, fato, trecho e versão.

## Custos

| Ledger | Antes da v0.6 | Depois | Delta |
| --- | ---: | ---: | ---: |
| Campanha `v060-qa` (teto US$0,50) | — | 344 entradas, US$0,08627102 | US$0,08627102 |
| Volume Docker `ai-getnet-case_runtime` | 46, US$0,02523039 | 60, US$0,02696424 | US$0,00173385 |
| Primário `data/runtime/budget.sqlite3` (teto 1) | 885, US$0,34852844 | 1229, US$0,43479946 | mesmo gasto da campanha, não somado de novo |

**Custo da v0.6.0: US$0,08800487. Acumulado do projeto: US$0,68637953 de US$5.** Zero reservas abertas; nenhum teto renovado. Conferido pelo Supervisor em modo somente leitura.

## Limitações conhecidas

- Acesso por outra rede não testado: depende de redirecionamento de porta, regra de firewall e ausência de CGNAT (ações do responsável). Túnel documentado como alternativa.
- `API_DEMO_ACCESS_KEY` e `API_ADMIN_ACCESS_KEY` vazias no `.env` local: o login `/v1` da stack Docker depende de o responsável preenchê-las.
- Regressão real das jornadas de negócio 7/13 pela rubrica literal: quatro casos de preço erram só a redação esperada (ferramenta, valores e status corretos); a pergunta de condições em inglês cai em `clarify` com o Router real (a versão em português passa). Router e prompts não mudaram nesta versão.
- Legenda do gráfico custo × qualidade mostra o identificador técnico do perfil.
- R2-04 aceito como risco: integridade Qdrant verificada dentro da transação de ativação; sem contenção observada.
- Avaliação por IA não é revisão humana; comparação pequena, dependente do processo da API.

## Limpeza do Docker

A pedido do responsável, depois dos testes: removidos 9 contêineres e 7 imagens de rodadas anteriores (v0.3–v0.5), imagens soltas, todo o cache de build e uma rede sem uso. Ficaram as imagens `ai-getnet-case-api`/`mocks` do r5 e `qdrant`, os três contêineres da stack parados e os volumes `ai-getnet-case_runtime` (ledger), `ai-getnet-case_qdrant_storage` (coleções) e `getnet-v030-validation_qdrant_storage` (coleções da validação v0.3, 374 MB, preservado por precaução). Uso do Docker: imagens 3,18 GB → 0,56 GB; cache 3,6 GB → 0. O arquivo `docker_data.vhdx` só encolhe no C: depois de compactado com o Docker parado.
