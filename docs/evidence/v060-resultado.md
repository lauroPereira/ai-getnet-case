# Resultado da v0.6.0

## Capacidades

- Um catálogo de dez cenários sintéticos rotulados alimenta `GET /v1/scenarios` e o `scenario_id` opcional de `POST /v1/messages`.
- `GET /v1/runs/{id}` mostra os passos com os trechos recuperados, a rota, os prompts usados, as verificações determinísticas e as avaliações gravadas.
- Uma resposta persistida pode ser avaliada por modelo sob demanda, com estimativa confirmada, reserva de orçamento e custo separado; a avaliação é idempotente, salvo `repeat=true`.
- A comparação de perfis roda 2 a 3 perfis em até 3 cenários e 2 repetições, reaproveita execuções compatíveis e aplica os efeitos de domínio numa cópia temporária do banco sintético.
- O efeito da documentação é demonstrável: o texto V2 do documento fictício de dispositivos, com a diferença esperada registrada antes da edição.
- Cada sessão demo tem um limite de ações pagas (`DEMO_SESSION_MESSAGE_LIMIT`, padrão 20), aplicado pelo backend com `429`.
- A interface tem três áreas (Atendimento, Resultados e Administração), e cada mensagem de erro diz a ação de recuperação.

## Validação

| Verificação | Resultado |
| --- | --- |
| Candidato | [R5](v060-candidato-r5.json): 63 arquivos do backend e 13 da interface, fonte `3b6b697e53623ac08c54a521cc0aa094e2e5cc7e247b83a4c11e3ca9075a2639` |
| Suíte estrita | Backend 349 aprovados, interface 42 aprovados, Ruff limpo, código 0 |
| Revisão independente | Apta, sem achado bloqueante ([revisão](v060-reviewer.md)) |
| Validação com modelos reais | Apta nos dez itens de aceite ([validação](v060-qa.md)) |
| Regressão real | Núcleo e desafio 27/27, conversas 4/4, habilitação e cancelamento corretos; jornadas de negócio 7/13 pela rubrica literal (13/13, 12/13 e 12/13 na v0.8.0) |
| Chat e recuperação | Um POST com a resposta descartada pelo proxy (`req_1d17374452904ae0915e`) e um único GET; `R$` literal; estado do caso da resposta recuperada |
| Toggle LLM/JEV | JEV `req_19ce44cbd8024167a0b6` com `router · jev-1.14.0` no ledger e nenhuma linha de Router LLM; contraste LLM `req_488dc6224dac4a7e8337`; comparação de perfis com JEV `pcmp_7beabd45446840389732` |
| Perfis e comparação | 3 perfis × 2 cenários (`pcmp_0970a97a…`), reuso, dois gráficos, tabela e drill-down por GET; domínio original inalterado |
| Efeito da documentação | V1 `req_4f72e4ce…` sem `get_contract_snapshot`; V2 `kb_29225785334648e3` com o trecho novo em primeiro (0,758), a ferramenta e a fonte do contrato; V1 restaurada sem a ferramenta (`req_105c15ea…` e mais 3 repetições) |
| Ativação e retorno | Ciclo pela Administração; candidata extra `kb_85596ca27a774e3f` testada e não ativada |
| Avaliação sob demanda | `eval:req_923c…` US$0,0000795; a segunda solicitação reaproveitou a avaliação sem custo |
| Orçamento, isolamento e permissões | Demo recebe `403` na Administração; limite demo `429` sem gasto; teto abaixo da estimativa `422` sem gasto; zero reservas abertas |
| Execução e compartilhamento | Docker r5 com a API só em `127.0.0.1:8000`, schema 8, `knowledge_base` no `/ready`, smoke real `req_a2bcc71e79d1424f8334`; interface compartilhada com backend travado e Simulado só para demo. O acesso por outra rede foi comprovado na v1.0.0 ([resultado](v100-resultado.md)) |
| Documentação | README, CHANGELOG, guia e roteiros de teste manual e de vídeo alinhados a este registro |
| Migração | 0007 → 0008 → 0007 testada em banco sintético |

## Gasto

| Ledger | Antes da v0.6.0 | Depois | Delta |
| --- | ---: | ---: | ---: |
| Campanha `v060-qa` (teto US$0,50) | — | 344 entradas, US$0,08627102 | US$0,08627102 |
| Volume Docker `ai-getnet-case_runtime` | 46, US$0,02523039 | 60, US$0,02696424 | US$0,00173385 |
| Primário `data/runtime/budget.sqlite3` (teto 1) | 885, US$0,34852844 | 1229, US$0,43479946 | mesmo gasto da campanha, não somado de novo |

Custo da v0.6.0: US$0,08800487. Acumulado do projeto: US$0,68637953, com teto de US$5 na época. Zero reservas abertas; nenhum teto renovado.

## Decisão

O recorte da versão está na [ADR 0015](../architecture/decisions/0015-recorte-final-v060.md). A verificação de integridade do Qdrant fica dentro da transação de ativação, por decisão; não houve contenção observada. Integrada na `main` em 2026-10-28 ([backend #7](https://github.com/lauroPereira/ai-getnet-case/pull/7), [web #3](https://github.com/lauroPereira/ai-getnet-case-web/pull/3)), com a árvore idêntica à do candidato validado; a tag `v0.6.0` inclui o README reorganizado depois do merge.
