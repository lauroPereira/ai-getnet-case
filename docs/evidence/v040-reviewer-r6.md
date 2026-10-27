# Parecer do Reviewer independente — v0.4.0 local r6

**Parecer: apto para QA da história v1.** Este parecer cobre o delta r5 → r6 na seleção e reutilização de comparação; não declara a história inteira aprovada, QA concluído ou release.

## Candidato e independência

- Candidato: `v0.4.0-local-r6`, branch `codex/v0.4.0-perfis-interface`.
- Base e HEAD: `bd549cc921ccffb37bd304a0959b8a4b690d6421`.
- Fingerprint combinado: `d54fbd3799cecfefd0c467be217eb841e59d4ae9c89f607dc1a64967ae4d9367`.
- Fingerprints runtime/build: `b8d3a1845ac4ea16c50272bb800248bc7c4df4dbd172e40c47ae220fb063c4a5` / `ed67d7ff81f6ed49042e9f3aa332ac145fdd004fa38d6b99e7a05072155d816d`, iguais aos de r5.
- Delta: uma tarefa backend adicionada (`docs/tasks/38-selecao-comparacao-v040.md`); frontend alterou `README.md`, `app.py` e `tests/test_interface.py`. Não houve alteração de código backend nesta rodada.
- Independência: não consultei relato nem conclusão do Developer. Sou o mesmo Reviewer das rodadas anteriores, portanto a revisão é independente da implementação, mas não representa outro contexto de revisão.
- Antes da revisão conferi 51/51 arquivos backend, 84/84 frontend, 127/127 runtime e 128/128 build, sem ausências ou divergências; fingerprint combinado bateu com r6.

## Requisitos e revisão

A tarefa 38 permite mudar a escolha do método depois de comparar, mas exige invalidar a comparação imutável e aguardar uma nova ação explícita para emitir outro `comparison_id`. Isso coincide com o contrato, que associa método selecionado, mensagem, conversa, estado, perfil/versão, principal e expiração ao ID, e com a história: atendimento reutiliza a decisão escolhida uma vez; rerun não repete comparação nem atendimento.

Em `app.py`, após uma comparação, a seleção corrente é comparada com `comparison["selected_mechanism"]`. Se divergir, o estado da comparação é apagado e a interface informa que o resultado foi invalidado. Como o bloco de exibição/ação só ocorre quando há comparação ativa, o botão de uso desaparece. A chamada a `api.compare()` permanece dentro do formulário e condicionada ao clique explícito. Quando uma nova comparação é criada, a seleção atual é enviada à API e o ID novo é guardado. O botão de atendimento usa o método e o ID do mesmo objeto de comparação, não um método livre da seleção corrente.

O delta web não altera o backend. A revisão r5 continua válida para seu código e contrato. O r6 preserva, portanto, a validação backend de vínculo/consumo único, reutilização da decisão selecionada sem nova chamada Router e mapa efetivo JEV vazio versus LLM configurado.

## Evidência própria

- AppTest focado: `PYTHONDONTWRITEBYTECODE=1 .venv-v040\Scripts\python.exe -m pytest -q tests\test_interface.py::test_changing_comparison_selection_invalidates_result_until_explicit_recompare --basetemp=.pytest_cache\v040-review-r6-app` — **2 passaram**, cobrindo ambos os sentidos.
- Repeti a jornada em AppTest com contadores próprios e fixtures simuladas, sem provedores: LLM→JEV e JEV→LLM invalidaram o ID anterior; um rerun após a primeira comparação e outro após a mudança mantiveram a contagem em uma chamada; só o segundo clique de comparar criou o novo ID; o envio ocorreu uma vez com o método e ID novos e o resumo do run mostrou esse método. Resultados para os dois sentidos foram equivalentes.
- A checagem do manifesto antes das verificações encontrou os mapas backend/web/runtime/build em 51/51, 84/84, 127/127 e 128/128. Após escrever este relatório, todos os mapas continuam sem ausência/divergência e o fingerprint combinado permanece `d54fbd3799cecfefd0c467be217eb841e59d4ae9c89f607dc1a64967ae4d9367`.

## Achados e limites

- Não encontrei defeito no delta r5 → r6. A mudança evita combinar método novo com ID/decisão antigos, mantém resumo e ação alinhados, e exige ação explícita para nova comparação. Não observei chamada automática nos reruns nem duplicação de envio.
- A prova de interação usa a API simulada da interface; não demonstra disponibilidade de provedor real. Não fiz chamadas pagas nem autenticadas. CA-32 real permanece pendente.
- Não rodei toda a suíte web nesta revisão. O backend r5 não mudou; seus testes específicos de reserva/decisão/snapshot e consumo único permanecem cobertos pelo parecer r5. QA da história ponta a ponta é uma etapa separada.

## Próximo responsável

QA pode executar a história no candidato r6 e registrar o que observou, mantendo explícita a pendência de CA-32 real e as limitações da validação simulada.
