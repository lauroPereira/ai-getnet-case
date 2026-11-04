# História: o assistente muda de caminho quando o primeiro especialista não basta, e a avaliação mostra quanto confiar nele

Versão 0 (rascunho), 2026-11-04; roteiro para revisão do responsável, antes de implementar. Spec: [orquestracao-avaliacao-v080.md](../specs/orquestracao-avaliacao-v080.md).

## Pessoas e objetivo

- **Lojista** (`cliente1988`, usuário e senha fictícios da v0.7.0): faz perguntas cuja resposta não está onde o Router mandou procurar primeiro.
- **Avaliador técnico** (papel vivido pelo QA): quer ver por que o assistente mudou de caminho e quanto a nota do juiz merece confiança.
- **Responsável** (Lauro): calibra uma amostra de respostas com a mesma rubrica do juiz.

## Critérios e candidato

CA-49, CA-50 e CA-51 (spec 0.2), UC-23 e UC-24; tarefas 69 a 73 e o holdout 72a. Candidato fixado por hashes em `docs/evidence/v080-candidato-rN.json` antes do QA.

## Condições iniciais

`main` com a v0.7.0; candidato v0.8.0. `.env` com os valores fictícios do `.env.example`, a chave de modelo do responsável e a chave do provedor do juiz independente. Campanha `v080-qa` (US$0,50) combinada com o ledger primário. Runtime e volume novos (migração 0011). Dados sintéticos da seed.

## Momentos da história

| Momento | Ação pela entrada normal | Resultado esperado | Critério | Evidência | Ponto de retorno |
| --- | --- | --- | --- | --- | --- |
| 1. Conhecimento insuficiente | Lojista pergunta sobre um produto sem evidência nas páginas oficiais | Knowledge sem evidência suficiente → `replan` (regra) → web; resposta com a fonte web ou a lacuna declarada; ≤ 3 saltos | CA-49, UC-23 | `request_id`, passos `replan` do trace | Não se aplica |
| 2. Suporte com lacuna de procedimento | Pergunta sobre a conta que pede também "como faço" | Support responde a parte da conta → `replan` → Knowledge para o procedimento; resposta única com as duas partes | CA-49 | Trace com origem de cada decisão | Não se aplica |
| 3. Falha de ferramenta | Pergunta de conta com o serviço de dados fora do ar (mock com falha) | Ferramenta falha → `replan` → escalada com protocolo `HO-`, sem inventar dado | CA-49 | Saída HTTP, caso na fila | Caso fica na fila |
| 4. Produto que depende da conta | Pergunta de produto cuja resposta depende do plano do lojista | Knowledge → `replan` → Support; resposta com o dado da conta | CA-49 | Trace | Não se aplica |
| 5. Laço evitado | Pergunta que nenhum especialista resolve | No máximo 3 saltos, nenhum especialista repetido, resposta honesta sobre o que faltou | CA-49 | Trace com `hops` | Não se aplica |
| 6. Pergunta simples | Pergunta que o Knowledge resolve de primeira | `replan` encerra por regra, sem chamada a modelo a mais | CA-49 | Trace e ledger | Não se aplica |
| 7. Campanha com juiz independente | QA roda `eval --judge --repeat 3` nos 40 casos, nas 4 conversas e nos cenários; depois `--judge-repeat 3` sobre as respostas da primeira execução | Relatório com quatro critérios e `unsupported_claim`, com a variação do assistente e a do juiz em blocos separados, por rota e split; rota medida pelo plano inicial e caminho executado à parte; provedor do juiz diferente do agente | CA-50, UC-24 | `docs/evidence/v080-*.json` e `.md`, delta do ledger | Não se aplica |
| 8. Jornadas | Campanha nas 13 jornadas de negócio | ≥ 12/13 pela rubrica | CA-51 | Relatório | Não se aplica |
| 9. Docker | `docker compose up` sem editar o `.env.example`; smoke com token; uma pergunta que replaneja | Smoke passa; trace com `replan` | CA-49 | Saídas | `docker compose down` |
| 10. Holdout, por último | Com os momentos 1 a 9 aptos: lacre conferido e uma única execução com `--split holdout_v080` | Resultado do holdout separado do desenvolvimento; se houver rodada nova depois, marcado "holdout já visto" | CA-50 | Relatório e hash | Não se aplica |
| 11. Calibração | `eval-calibrate --sample 24` gera o CSV; o responsável preenche; `--import` | Concordância humano × juiz por critério (exata, ±1, kappa), com a ressalva da amostra pequena | CA-50 | `docs/evidence/v080-calibracao.md` | Gerar nova amostra |

Percorra na ordem. O momento 11 depende do responsável e pode fechar depois do QA técnico; o relatório da versão só sai com ele.

## Experiência e exceções

O lojista não vê o replanejamento: vê uma resposta só, honesta sobre o que não conseguiu confirmar. O avaliador vê cada decisão no trace, com motivo e origem. O CSV de calibração traz instruções curtas e nenhum score do juiz.

## Resultado da rodada

A preencher pelo QA.

## Como terminou

A preencher pelo QA.
