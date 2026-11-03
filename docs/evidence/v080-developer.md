# Passagem do Developer: v0.8.0

## Tarefa 72a, rodada 1

- Papel e responsável: Developer do Time B (subagente), despachado pelo Supervisor.
- Objetivo e critérios: [tarefa 72a](../tasks/72a-holdout-respostas-v080.md), RF-92 e CA-50 da [spec 0.2](../specs/evolucao-pos-feedback.md), decisão técnica 15 do [plano](../specs/evolucao-pos-feedback-plano.md). Escrever e lacrar por hash o holdout de respostas antes de qualquer ajuste de prompt da v0.8.0, por quem não ajusta prompts.
- Escopo: arquivos novos `tests/scenarios/holdout_v080.jsonl`, `tests/scenarios/holdout_v080.sha256`, `tests/unit/test_holdout_v080.py`, `docs/evidence/v080-holdout-derivacao.md` e esta passagem; alterada só a tarefa 72a (Validação e Status). Nenhum arquivo do Time A tocado (`cli.py`, `evaluation/`, `orchestration/`, `api/`, `prompts/`), nenhum JSONL existente alterado. Repositório: `C:\workspace\ai-getnet-case-wt\time-b`.
- Estado: em andamento até a revisão; implementação concluída pelo Developer.
- Branch e PR: `codex/v0.8.0-avaliacao`, sem PR, sem push.
- Base e versão final: base `d7acaec`; versão final é o commit único desta tarefa, que traz esta passagem (SHA informado ao Supervisor no retorno). Hash do holdout: `4002fdc9b9efd667d253c5fe9ae6b48d7cd03eac6c489a0119984d8139e1e626` (SHA-256 do conteúdo UTF-8 com quebras normalizadas para `\n`; coincide com `sha256sum` do arquivo, que já está em LF).
- Independência: não-independente; é o próprio autor relatando. A revisão independente cabe ao Reviewer.

### Regra de autoria

`prompts/` não foi aberto. Também não foram abertos traces, avaliações nem respostas reais de modelo em `docs/evidence/`. As mensagens são paráfrases das páginas oficiais versionadas (`data/snapshots/public/pages/`, listadas em `data/sources/public-sources.json`), dos procedimentos de `data/knowledge-demo/` e dos fatos da seed. Os JSONL existentes serviram só para formato e para evitar repetição. Código lido para entender rótulos: `evaluation/runner.py` (`Case`, `load_cases`, checagens), `guardrails/output.py` (`amounts`), `tools/domain.py`, `tools/registry.py`, `data/seed.py`, `data/clock.py`, `testing.py`, `api/schemas.py` (rotas e status) e, por busca, a linha de passagem com o protocolo `SIM-` em `agents/escalation.py` e `agents/personality.py`.

### Evidência

- Composição: 25 casos, 13 pt (52%) e 12 en. Rotas: `knowledge` 6, `general_web` 2, `support` 10 (recebíveis, liquidação, dispositivo, autorização, contrato, preço ×2, cancelamento, habilitação, isolamento), `knowledge_and_support` 3, `human_handoff` 2, `out_of_scope` 2. Difíceis (`-HARD`): `HV080-EN-KNOW-PHONE-AS-TERMINAL-HARD` e `HV080-EN-KNOW-EARLY-PAYOUT-MINIMUM-HARD` (inglês sobre produto descrito só em português, sem o nome do produto), `HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD` (paráfrase distante) e `HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD` (duas intenções).
- Derivação: [v080-holdout-derivacao.md](v080-holdout-derivacao.md), com o comando em processo (seed, relógio `2026-10-26T10:00:00`, banco em `.pytest_cache/v080-b-holdout/`, `in_process_client()`), a saída de cada ferramenta e, para cada caso, a página oficial ou o procedimento demo com trecho curto.
- Teste de lacre: `tests/unit/test_holdout_v080.py`, 6 testes. Prova de violação: troquei um byte do JSONL (`smartphone` → `smartphonE`) e 2 testes falharam (`test_seal_matches_content` e `test_seal_ignores_line_endings_but_not_content`); com o arquivo restaurado, os 6 passaram e `sha256sum` voltou a `4002fdc9…e626`.
- Suíte estrita: `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v080-b-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict` terminou com código 0, 355 testes aprovados em 231,95 s, ruff sem achados, estrutura e skills válidas. A primeira execução tinha 355 testes aprovados, mas terminou com código 1 por um SIM300 (comparação invertida) na linha 62 do teste novo. Corrigi a comparação antes da segunda execução.
- Ambiente: `.venv` do worktree, Python 3.13.3; `import merchant_assistant` resolve para `C:\workspace\ai-getnet-case-wt\time-b\src\merchant_assistant`. Nenhuma chamada paga, sem `.env`, sem Docker.

### Decisões além do texto do plano

- 25 casos em vez dos 24 sugeridos: o recebível líquido do débito ficou como caso próprio, para separar recebíveis de liquidação.
- Difíceis marcados pelo sufixo `-HARD` no id, porque o `Case` não tem campo `notes` e `load_cases` falharia com chave extra.
- Valores das páginas oficiais (R$ 50,00 mínimo de antecipação; R$ 1,00 por link pago) em `must_include_amounts` (5000 e 100), como os valores das ferramentas.
- Teste extra que refaz as chamadas às ferramentas sobre a seed e confere que todo valor de caso com ferramenta esperada sai delas. Ele prende o holdout à seed: se a seed mudar, o teste falha. Isso é intencional, porque nesse caso os rótulos ficariam velhos.
- Todos os casos usam `cliente1988`; o isolamento é testado pelo recurso de outro lojista citado na mensagem (`dev_002_tap01`), não por `user_id` trocado.

### Rótulos que julguei ambíguos (notas, não suposições)

1. `HV080-EN-SUP-PRICE-CREDIT-CONDITIONS`: a ferramenta retorna `different_conditions`. Rotulei `answered`, seguindo `V030-PRICE-CONDITIONS`. Porém o lojista reclama de cobrança maior, e o procedimento demo diz que "contrato e pricing incompatíveis exigem análise". Uma resposta com `handoff` é defensável e falharia em `status_ok`.
2. `HV080-PT-OOS-BUYER-PERSONAL-DATA`: rotulei `out_of_scope`/`refused` pelo RF-06 (dados de terceiros). Uma resposta `answered` dizendo que não há esses dados falharia.
3. `HV080-PT-SUP-FOREIGN-DEVICE`: rotulei `support`/`answered` sem dado alheio, como o UC-13. Uma recusa `out_of_scope` falharia.
4. `HV080-PT-KNOW-ACQUIRER-ERROR-RESET-HARD`: exige "38" e "inicializa", das páginas de erro ADQ. O FAQ do crediário dá outro caminho de inicialização ("Suporte > Bandeiras > Funções Técnicas > Inicialização"), sem "38". Uma resposta que use só esse caminho falha no primeiro grupo.
5. `HV080-PT-KS-PIX-PAID-AND-ADVANCE-HARD` e `HV080-EN-SUP-PAYOUT-LINK-SALE` exigem `get_payout_status` além da agenda. Uma resposta que conclua "pago" só pelo `SETTLED` da agenda falha em `tools_ok`.
6. `HV080-EN-KS-WIFI-NEW-PASSWORD` aceita só `knowledge_and_support`, como o UC-05.

### Limitações

- Checagens por substring: `must_not_assert` só neutraliza as formas de incerteza listadas no runner. Uma negação como "não há confirmação de que o dinheiro já voltou para o cartão" seria marcada indevidamente em `HV080-PT-SUP-CANCELLATION-REFUND`. Valores oficiais só contam com prefixo `R$` ou `BRL` (por exemplo, "50 reais" não conta).
- `HV080-PT-SUP-PRICE-LINK-CONSISTENT` exige que o agente descubra a data da venda pela agenda, porque `simulate_pricing` não filtra por canal. "Semana passada" corresponde a 6 dias antes, e com `SystemClock` a expressão nem sempre é exata.
- Na campanha real o relógio é o do sistema: as datas mudam, os valores não. "Agora há pouco" depende do evento em `now − 3h10`.
- As páginas oficiais têm taxas conflitantes (por exemplo, débito do Get Tap a 1,69% numa página e 0,99% em outra). Por isso evitei perguntas de taxa pública.
- O holdout ainda não foi rodado contra nenhum modelo; nenhuma medição foi feita.

### Critérios

- Comprovados localmente: ≥ 20 casos e ≥ 50% em pt; rotas cobertas; 4 difíceis marcados; derivação reproduzível; teste de lacre passa e falha com um byte alterado; suíte estrita com código 0; nenhuma chamada paga; `prompts/` não foi aberto.
- Não verificados: comportamento do sistema real no holdout (campanha do QA na v0.8.0).

### Ação externa, identidade e próxima ação

- Ação externa: nenhuma (sem push, sem PR). Commit local único com identidade `lauroPereira <lauro.s.pereira@gmail.com>`, conferida no worktree.
- Próxima ação: o Supervisor despacha o Reviewer independente para a 72a. Depois da aprovação, o holdout fica congelado. Recomendo que quem ajustar prompts na 72b não leia o conteúdo do JSONL, para cumprir "nunca usado em ajuste".
- Decisão humana pendente: nenhuma para esta rodada. As notas de rótulo ambíguo acima ficam para o Reviewer e o Supervisor decidirem se mantêm o rótulo, sabendo que qualquer mudança exige novo hash antes da campanha.
