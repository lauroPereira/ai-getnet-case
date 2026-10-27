# Parecer independente — correções de confirmação e recuperação web v0.5.0 (r1)

- Papel: Reviewer independente, rederivando o código e os testes; não consultei relatórios do Developer. Não substitui QA.
- Parecer: **correção necessária antes do retorno ao QA**.
- Candidato fixado: `v0.5.0-local-r5`; branch `codex/v0.5.0-base-versionada` nos dois repositórios.
- HEAD-base: backend `ea2355b5ba8fa8dcff66200f34461ae063183250`; web `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`.
- Próxima ação: Developer ajustar o contexto de confirmação dos tetos de custo; depois fixar novo mapa e retornar ao mesmo QA.

## Identidade do candidato e escopo

Recalculei os mapas do r5 antes e depois dos testes. Todos os bytes fixados permanecem iguais ao manifesto:

| Mapa | Arquivos | Fingerprint recalculado | Resultado |
| --- | ---: | --- | --- |
| Fonte backend | 43 | `a465dbf0afd62d44d16ab9f332c971e150383560df752ee4a4ee36edd8430211` | 43/43 iguais |
| Fonte web | 84 | `6d50fcf0965651a3333d68715f5637f872d46c5469d97d89ea2bf9fa09818cd2` | 84/84 iguais |
| Fonte combinada | 127 | `71818710468cd1ad63a83c49e8eec61e5db28bf5d824381b0e0e3d509e40d76c` | Igual ao manifesto |
| Runtime backend | 128 | `22556665c215a837fa5d9cc1b7b8dacd52fa3b06b40ed46e8e1b86b9ef40ce0e` | 128/128 iguais; igual a r3 |
| Entradas de build backend | 129 | `c74764b0d0932851a123ff8f5f13b11e96e266f8530b2a4ae5ee2e1016d1c3a5` | 129/129 iguais; igual a r3 |

Comparei também os mapas r3/r4/r5. De r3 para r4, os bytes web mudaram em `app.py` e `tests/test_interface.py`; de r4 para r5, em `app.py`, `src/getnet_web/api.py` e `tests/test_interface.py`. No backend, as mudanças entre r3 e r5 são documentação/evidência; os mapas completos de runtime e build não mudaram. A interface v0.5 está no working tree do candidato sobre o HEAD web v0.4; os 84 hashes representam os bytes locais do r5.

Revisei no código as quatro confirmações da base e os dois caminhos de POST de chat (`Enviar mensagem` e `Usar esta decisão e iniciar atendimento`), além do novo GET manual de conversa. Não chamei o backend/runtime do QA, endpoints reais ou provedores.

## Achado

### WUI-R1-01 — Alterar o teto depois da confirmação reutiliza o consentimento anterior (P2)

**Condição e impacto:** o contexto de confirmação de build é composto por digest, versão ativa e revisões; o de teste, por candidata e versão ativa. Nenhum inclui o teto monetário digitado. Assim, depois de marcar a confirmação, aumentar o teto deixa a confirmação selecionada e habilita o botão com o novo valor. O POST é explícito, mas carrega um limite maior que o limite que estava visível quando a confirmação foi marcada.

**Localização:** [app.py](C:/workspace/ai-getnet-case-web/app.py:505), [app.py](C:/workspace/ai-getnet-case-web/app.py:518), [app.py](C:/workspace/ai-getnet-case-web/app.py:522), [app.py](C:/workspace/ai-getnet-case-web/app.py:552), [app.py](C:/workspace/ai-getnet-case-web/app.py:557), [app.py](C:/workspace/ai-getnet-case-web/app.py:562).

**Reprodução independente com AppTest e API fake:** estimei uma candidata, defini teto `0.125`, marquei a confirmação e verifiquei botão habilitado sem chamada. Mudei o teto para `0.5`; o checkbox continuou verdadeiro e o botão permaneceu habilitado. Clique explícito enviou `max_cost_usd=0.5` com `confirmed=True`. A mesma ausência do teto no contexto de teste aparece em `app.py:552-570`. Nenhuma API ou provedor real foi chamado.

**Correção esperada:** associar cada confirmação ao teto monetário vigente ou invalidá-la sempre que o valor mudar. Preserve o número digitado nos reruns, mas peça confirmação novamente para o valor novo.

## Evidência de validação

- Suíte web completa: `.venv-v040/Scripts/python.exe -m pytest tests --basetemp C:\workspace\ai-getnet-case-web\.pytest_cache\reviewer-ui-r5-20261027-01` — **20 passaram**. AppTest e clientes usam fakes/transportes controlados.
- Validação estrita do projeto: `tools/scripts/lint_and_tests.py --strict` — **20 passaram; código 2 porque Ruff não está instalado no venv web**. A validação de estrutura e skills passou.
- Ruff externo do ambiente backend nos arquivos web afetados (`app.py`, `src/getnet_web/api.py`, `tests/test_interface.py`, `tools/generate_client.py`) — **All checks passed**.
- Reprodução adicional do teto alterado executada por AppTest com API fake — confirmação permaneceu ativa; payload do clique continha o novo teto.
- Os testes existentes passam nos quatro controles, recuperação após falha do POST, GET 404, GET vazio/ainda processando, GET com timeout, distinção de histórico anterior e ausência de POST adicional em rerun. O cliente mantém `timeout=20.0`; o GET de conversa usa a operação `/v1` existente com o bearer da sessão. Logs de falha registram somente operação, duração e classe da exceção; não registram texto, token nem payload.
- Nenhuma chamada paga ou acesso de rede foi realizado; nenhum POST foi feito em `18853`, `18854`, `18030` ou `18031`. Nenhum dado, banco ou ledger real foi aberto.

## Limites e próxima etapa

A recuperação manual do chat e os quatro caminhos de ação permanecem sem achados adicionais nesta revisão focada. A causa temporal histórica de `ReadTimeout` continua indeterminada; não inferi latência HTTP a partir de `duration_ms`. A execução visual no runtime/QA real não foi repetida e continua pertencendo ao mesmo QA após novo candidato.

Não houve alteração de produto ou testes, mudança de API/autenticação/timeout/guarda, commit, push, merge, tag ou publicação. Os únicos temporários de teste estão sob `.pytest_cache`.
