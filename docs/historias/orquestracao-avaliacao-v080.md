# História: o assistente muda de caminho quando o primeiro especialista não basta, e a avaliação mostra quanto confiar nele

Versão 1, 2026-11-04; roteiro aprovado com a spec, antes de implementar. Spec: [orquestracao-avaliacao-v080.md](../specs/orquestracao-avaliacao-v080.md).

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

Registrado pelo Supervisor em 2026-11-05 a partir dos pareceres do QA (r3 a r7), candidato final `1baa7b3` (r11).

| Momento | Resultado | Evidência |
| --- | --- | --- |
| 1 a 6 (replanejamento) | CA-49 apto: os quatro cenários com modelos reais, origem em toda decisão, no máximo 2 saltos; `REPLAN-TOOL-DOWN` com falha real da ferramenta de preços e protocolo `HO-` | [r5](../evidence/v080-d12-pre-holdout-r5.md) |
| 7 (campanha com juiz independente) | Juiz DeepSeek sem falha; `--judge-repeat 3` sobre as 44 primeiras respostas com concordância exata 0,76 a 0,86 e ±1 ≥ 0,985 | [r6](../evidence/v080-d12-pre-holdout-r6.md) |
| 8 (jornadas) | CA-51 pela régua determinística 13/13, 12/13 e 12/13 (as duas recusas são redações corretas, limitação da régua literal); pelo `judge.v3`, 13/13 nas três | [r6](../evidence/v080-d12-pre-holdout-r6.md), [tarefa 78](../tasks/78-regua-literal-ca51-recusa-respostas-corretas-v080.md) |
| 9 (Docker) | Smoke 10/10; pergunta mista replaneja (`rule:procedure_gap`) com o caminho no trace; `down` limpo | [r6](../evidence/v080-d12-pre-holdout-r6.md) |
| 10 (holdout) | Execução única: 62/75 (0,827) pela régua, juiz 4,6 a 4,8, concordância do juiz 0,81 a 0,88; reportado à parte, sem decidir aprovação; `holdout_v080` passa a "já visto" | [r7](../evidence/v080-holdout-r7.md) |
| 11 (calibração) | CSV de 24 respostas gerado, sem notas do juiz; preenchimento e `--import` pendentes do responsável | [amostra](../evidence/v080-calibracao-amostra.csv) |

Rodadas anteriores: r3 reprovou CA-51 (9, 11 e 10 de 13) e invalidou `REPLAN-TOOL-DOWN` por mock saudável; r4 ficou inválida em 8 jornadas por seed de outro dia; r5 reprovou CA-51 só por redação. A rubrica determinística continua o critério desta versão; a régua para a v0.9.0 é decisão do responsável.

## Como terminou

O lojista recebeu uma resposta só em cada pergunta, inclusive quando o assistente precisou mudar de caminho; quando a ferramenta de preços caiu, ganhou um protocolo em vez de um número inventado. O avaliador técnico viu, em cada trace, por que o assistente mudou de rota e quanto o juiz concorda consigo mesmo. O responsável tem o CSV para dizer quanto confiar no juiz; o relatório da versão sai com essa resposta.
