# Parecer independente — correção do teto de custo UI v0.5.0 (r2)

- Papel: Reviewer independente do Developer, rederivando a correção; não substitui QA.
- Parecer: **apto para retorno ao QA**, somente para o candidato r6 e para o escopo da tarefa 51.
- Candidato: `v0.5.0-local-r6`; branch `codex/v0.5.0-base-versionada` nos dois repositórios.
- HEAD-base backend: `ea2355b5ba8fa8dcff66200f34461ae063183250`; web: `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`.
- Fonte combinada: `45073733de04247748d583f5a57af01bfa3180979d8915616bd7db0af971aaa3`.

## Integridade e delta

Recalculei os mapas do manifesto r6 antes e depois das verificações. Os bytes atuais correspondem a todos os hashes congelados:

| Mapa | Arquivos | Fingerprint | Resultado |
| --- | ---: | --- | --- |
| Backend | 44 | `d37bfb350172c1dd15955a776d95d92ba3bde7d44072db8bba54cbf08e328371` | 44/44 iguais |
| Web | 84 | `464c72b1ee41ff63803b18fff4ffe138f53b04fab2f08424c5b9e1f27f69f9ab` | 84/84 iguais |
| Fonte combinada | 128 | `45073733de04247748d583f5a57af01bfa3180979d8915616bd7db0af971aaa3` | Igual ao manifesto |
| Runtime backend | 128 | `22556665c215a837fa5d9cc1b7b8dacd52fa3b06b40ed46e8e1b86b9ef40ce0e` | Igual ao r3 |
| Entradas de build backend | 129 | `c74764b0d0932851a123ff8f5f13b11e96e266f8530b2a4ae5ee2e1016d1c3a5` | Igual ao r3 |

O delta r5→r6 nos mapas é limitado a `app.py` e `tests/test_interface.py` no web, e ao plano aprovado e tarefa 51 na documentação backend. Runtime e entradas de build backend permanecem byte a byte iguais ao r3. O HEAD web segue como base v0.4; os 84 hashes identificam os bytes locais do candidato.

## Revalidação do WUI-R1-01

O contexto de confirmação agora inclui `float(max_cost)` em [app.py](C:/workspace/ai-getnet-case-web/app.py:513) para build e `float(test_cap)` em [app.py](C:/workspace/ai-getnet-case-web/app.py:561) para teste. `reset_confirmation_context` limpa o checkbox quando o valor muda, antes de habilitar a ação.

Fiz reprodução própria com AppTest e API fake: para cada teto, confirmei `0.125`, alterei para `0.5` e reduzi novamente para `0.125`. Em ambos os sentidos, o valor permaneceu no campo, a confirmação foi desmarcada e a ação ficou desabilitada. Reruns adicionais não chamaram a API fake. Após reconfirmar e clicar explicitamente, ocorreu exatamente uma chamada com o valor atual. Nenhum endpoint de QA ou provedor foi usado.

## Verificações

- `python -m pytest tests/test_interface.py::test_kb_confirmation_controls_enable_once_without_form_submission --basetemp .pytest_cache/reviewer-ui-r6-focused-20261027` — **1 passou**.
- Reprodução adicional temporária em `.pytest_cache/reviewer_ui_r6_cap_confirmation.py`, com basetemp `.pytest_cache/reviewer-ui-r6-custom-20261027` — **2 passaram**; cobre aumento e redução em build e teste, preservação do valor, ausência de chamada em rerun e chamada única após reconfirmação/clique com o teto atualizado.
- Ruff externo do ambiente backend nos arquivos alterados `app.py` e `tests/test_interface.py` — **All checks passed**.
- Não repeti a suíte web completa, já executada na revisão r5, pois esta revisão cobre apenas o delta de confirmação. Não repeti testes do backend; runtime e build estão inalterados.

## Limites e encaminhamento

Não encontrei outro defeito no delta da tarefa 51. A correção está apta para o mesmo QA revalidar na campanha já existente; este parecer não autoriza release nem substitui a revalidação de QA. Não fiz chamadas pagas, rede, POST a serviços do QA, operação em ledger, nem alteração de produto. Os temporários estão sob `.pytest_cache`.

Como errata documental solicitada, corrigi somente os alvos dos links de `app.py` no parecer UI r1 para caminhos absolutos; o achado e o veredito históricos foram preservados.
