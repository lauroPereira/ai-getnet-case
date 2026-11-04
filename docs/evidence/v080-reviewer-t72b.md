# Revisão independente da T72b — rodada 1

- **Candidato:** `c861bee52ec43128c3801a9be0609effca9e3f61` (código em `046cb73`), branch `codex/v0.8.0-replan`, worktree destacado `review-a2`; HEAD e status iguais antes e depois. Diff `5da3de5..c861bee` sem `docs/`.
- **Independência:** subagente `reviewer` (sonnet/xhigh) em contexto frio. A leitura da tarefa devolveu o arquivo inteiro, inclusive Validação e Status com os números do Developer; o Reviewer declara isso, não abriu a passagem nem a tabela caso a caso e re-derivou cada número por execução. Não abriu o holdout. Gravado pelo Supervisor a partir do relatório do Reviewer.
- **Parecer:** **correções necessárias** — 1 P2 (só rótulo), 8 P3; nenhum defeito de produto, quebra de contrato ou regressão no eval programado.

## Achado

**P2-1 — `V030-ENABLEMENT-PENDING` (EN) perdeu a âncora de valor e aceita negação.** `tests/scenarios/business_journeys.jsonl:5`: o rótulo antigo exigia o protocolo da solicitação (vindo da ferramenta), que rejeitava qualquer negação; o novo exige "pending" e "visa" e só proíbe "no longer/is not/isn't pending" e aprovação. Passam, com ferramenta, status e rota corretos: "I could not find any pending Visa enablement request.", "You have no pending Visa enablement request.", "Your Visa enablement is active. There are no pending requests.", "Your Visa request has been canceled, nothing pending.", "…pending, and it will be approved tomorrow." Nos dados sintéticos o Visa está pendente e o Mastercard ativo: negar o pendente é o erro mais provável. A troca de protocolo por status é justificada (a pergunta em inglês não pede protocolo e a resposta real está certa), mas o status ficou sem proteção contra negação. O teste (`test_v080_journeys.py:107-116`) só tem duas respostas erradas.

## P3

1. `V030-PT-PRICE-CONDITIONS`: "condições distintas" aceita negações ("Não, não foram usadas condições distintas", "Não encontrei condições distintas…"); fragilidade que já existia com "diferentes".
2. `V030-PRICE-CONSISTENT`: "matches the …" é subcadeia de "mismatches …"; falta `mismatch` nas proibições.
3. `V030-PRICE-DIVERGENCE`: "fee discrepancy" aceita "I did not find a fee discrepancy" (mesmo padrão do rótulo antigo; valor e status seguem protegendo).
4. `REPLAN-WEB`: das 20 admissões honestas plausíveis testadas, 11 reprovam ("Não consegui verificar…", "Não identifiquei…", "Não achei…", "Não sei dizer…", "Não posso afirmar…"); a invenção com ressalva ("…mas a Get XYZ aceita pagamento por aproximação") ainda passa.
5. `router.v6`: a guarda "taxas gerais são `knowledge`" cobre "rates", mas perguntas gerais sobre condições, planos e taxas por tipo de pagamento podem ser puxadas para `support/pricing`; nenhum caso dos conjuntos é pergunta geral de taxas. Sugestão: exemplos contrastivos no prompt e sondas no QA.
6. Cinco mutantes sobrevivem (escolha do tipo de pagamento no Support programado, palavra de diferença na regex de condições, "Say that it is a human agent", "um atendente", fallback com Support presente).
7. `personality.v5.md:21` diz que `unconfirmed` vem "in English"; itens de `missing` não têm idioma garantido (inofensivo).
8. A `reason` do planejador vira `unconfirmed` para a Personality; o fallback usa frase fixa e não vaza o texto, mas a obediência da Personality real não está provada.

## Comprovado por execução

- **Rótulos caso a caso:** as respostas reais gravadas que motivaram as mudanças estavam corretas; valores, ferramentas, status, rotas e fontes dos rótulos de jornada não mudaram, exceto o P2-1. `V030-CONTRACT-TERMINATION` manteve "human" e foi corrigido no prompt.
- **Re-pontuação** das respostas reais gravadas (método validado reproduzindo os 13 resultados gravados): 6/13 com os rótulos antigos, 10/13 com os novos. Continuam falhando `V030-PRICE-CONDITIONS` (EN, `clarify` no real), `V030-PT-PRICE-CONDITIONS` na primeira execução (`clarify`) e `V030-CONTRACT-TERMINATION` ("support team" sem "human"): os três dependem dos prompts novos, só medíveis no real.
- **Prompts:** `router.v5`, `personality.v4` e `replan.v1` intactos; `prompt_versions` e o trace usam `router@6`, `personality@5`, `replan@2`.
- **Acréscimos da 69:** A08, A09 e `finish`+`complete` morrem; o texto de reserva traz a lacuna uma vez e não aparece em nenhum dos 44 cenários sem lacuna.
- **Regressão:** eval programado do candidato e da `main` idênticos (25/40, conversas 4/4, 123 chamadas); trava da v0.7.0 (11 arquivos) **162 passed**, sem alteração; testes novos e afetados 133 passed. A mudança de 3 linhas em `api/v1.py` (snapshot com a versão real do Router) é justificada e não conflita com o Time B.
- **Mutação:** 33 mutantes, 28 mortos.
- **Suíte estrita** (Supervisor, neste candidato): **781 passed**, código 0.

## Não comprovado

Efeito real de `router.v6`, `personality.v5` e `replan.v2` (12/13 ou 13/13 dependem da campanha); obediência da Personality real a `unconfirmed`.
