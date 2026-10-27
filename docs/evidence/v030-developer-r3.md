# Passagem do Developer — v0.3.0 ajustes da validação real

- Papel e responsável: Developer; implementação da tarefa 25 despachada pelo Supervisor.
- Objetivo: corrigir as falhas reproduzidas no relatório real r1 e preservar o isolamento corrigido em r2.
- Estado: ajustes implementados; validações locais aptas; novo candidato precisa de hashes, build/revalidação do Supervisor e revisão independente antes de QA.
- Branch e base: `codex/v0.3.0-jornadas`, baseada em `8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`; sem commit.
- Relatórios r1 foram preservados. Não editei manifestos nem relatórios do Reviewer, nem consultei ou alterei o runtime/contêiner da rodada real.

## Alterações desde a passagem r2

- `src/merchant_assistant/tools/domain.py`: `simulate_pricing` acrescenta `financial_evidence` com apresentações `money()` para valores brutos, taxas, componentes, parcelas e valores líquidos. Os registros originais dos dois serviços e seus campos `*_minor` permanecem intactos. Fontes sem comparação suficiente não recebem normalização de taxas/parcelas; moedas fora de BRL não são exibidas como reais. A correção r2 continua exigindo o cliente confiável em ambos os registros da consulta de cancelamento.
- `tests/unit/tools/test_business_journeys.py`: cobre fatos financeiros sustentados pelo pricing e cobrança, rejeita valor sem evidência, preserva acesso ao raw `net_minor`, prova que o default recente inclui uma negativa de ontem e que `today`/`yesterday` explícitos continuam distintos.
- `prompts/support.v7.md`: orienta consultas de autorização pelo histórico recente padrão quando não há período explícito; pede filtro de pricing quando modalidade e parcelas bastam; orienta a usar `financial_evidence` e não converter inteiros nem declarar taxa sem evidência.
- `prompts/router.v4.md`: diferencia dúvidas gerais sobre taxas (Knowledge) de comparação de uma cobrança, orientando pricing quando a modalidade/parcelas identificam filtros e a mensagem pede comparação.
- `tests/scenarios/business_journeys.jsonl`: adiciona alternativas semânticas e negativos aos cinco casos com falso negativo apenas de redação no real r1. Nenhuma rota aceita, status, ferramenta, valor obrigatório, requisito de fonte ou critério do produto foi removido ou alterado.
- `README.md` e `CHANGELOG.md`: descrevem a versão como candidata em validação e apontam para `docs/evidence/v030-resultado.md`; removem o texto de preparação futura e métricas antigas fixas. Não declaram aprovação ou liberação.
- `docs/evidence/v030-developer-r3.md`: esta passagem.

## Validações observadas

- Testes direcionados (`test_business_journeys.py`, `test_tools.py`, `test_use_cases.py`, `test_evaluation_runner.py`): **79 passed**.
- Avaliação programada sem custo, com política scripted e dados sintéticos isolados: **13/13 cenários v0.3.0 passaram**, incluindo conteúdo, grounding, proibições e as alternativas/negativos atualizados. Não substitui revalidação com modelo real.
- `.venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`, `PYTHONUNBUFFERED=1`, basetemp `.pytest_cache/v030-r3-strict-20261027b`: **165 passed em 100,13 s**, Ruff aprovado, estrutura válida e skills válidas. Rodada local sem API paga ou rede externa.
- Antes da rodada estrita final, uma execução preliminar passou todos os testes, mas Ruff encontrou três problemas de formatação no teste novo. Foram corrigidos antes do resultado final acima.
- `ruff check` nos dois arquivos Python alterados passou antes da rodada estrita final. `git diff --check` nos arquivos README/CHANGELOG alterados passou. O Supervisor informou que corrigiu o trailing whitespace da própria linha em `docs/evidence/orcamento.md`; não editei esse arquivo.

## Limitações e passagem

- O real r1 permanece como registro histórico: 31/40 verificações automáticas e 4/4 conversas, US$ 0,06747249. O ledger ainda tinha US$ 0,08252751 dentro do teto autorizado de US$ 0,15. Este Developer não realizou novas chamadas pagas.
- O Supervisor informou que iniciaria build em paralelo à validação estrita. O resultado do build e a revalidação real no teto compartilhado não fazem parte desta passagem.
- Nenhum critério, guardrail, permissão, orçamento, contrato HTTP, migração ou história foi relaxado. Não fiz commit, push, merge, tag ou publicação.
- Próximo responsável: Supervisor para registrar o novo candidato e completar build/revalidação autorizada; depois Reviewer independente deve revisar os arquivos e hashes r3. QA aguarda parecer apto. Não declarar aceite nem liberação com base somente nas verificações locais/scripted.
