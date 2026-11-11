# Tarefa 111 — Disponibilidade de motor e perfis

## Objetivo

Quem roda o backend só com a chave da OpenAI não consegue escolher, na interface, o JEV nem perfis cujo provedor não tem chave; a interface diz qual chave falta.

## Especificação relacionada

[v1.1.0](../specs/tickets-retomada-v110.md): D3, CA-78, RF-132.

## Pré-condições

Tarefa 110 concluída nas duas branches da versão. Nenhuma chamada paga.

## Arquivos prováveis

Backend: `src/merchant_assistant/api/v1.py` (`GET /v1/profiles`), `profiles.py`, `docs/contracts/api-v1.md`, testes. Web: `app.py`, `README.md`, testes.

## Passos

1. `GET /v1/profiles`: cada perfil ganha `available` (verdadeiro quando o provedor de cada agente do perfil tem chave configurada no backend) e `missing_providers` (nomes dos provedores sem chave; vazio quando disponível); a resposta ganha `router_mechanisms` (`{"llm": true, "jev": <TYPESAFE_API_KEY configurada>}`). Nenhum valor de chave. A regra de chave por provedor é a mesma usada para construir os clientes de modelo.
2. Contrato `api-v1.md` atualizado.
3. Web: perfil indisponível aparece marcado como indisponível neste backend e não é enviado; o JEV indisponível fica desabilitado no atendimento, na comparação só dos Routers e na comparação de perfis, com uma frase que nomeia a chave que falta no backend (`TYPESAFE_API_KEY`, `DEEPSEEK_API_KEY`); o padrão cai para um perfil e um motor disponíveis (o perfil Híbrido deixa de puxar o JEV quando ele está indisponível). Backend antigo sem os campos novos: comportamento atual.
4. README da web e do backend (uma frase onde as chaves opcionais são descritas) e testes.

## Critérios de conclusão

- Testes da API: com e sem `TYPESAFE_API_KEY` e `DEEPSEEK_API_KEY`, os campos refletem as chaves e nenhum valor de chave aparece na resposta.
- Testes da interface: sem as chaves, JEV e perfis dependentes não são enviáveis e a frase nomeia a chave; com as chaves, tudo como antes; backend sem os campos novos mantém o comportamento atual.
- Suítes estritas do backend e da web verdes.

## Validação

Developer, rodada 1 (2026-11-10). Sem chamada paga: modelo programado, chaves sintéticas que nenhum cliente de modelo usa, Qdrant em memória e transportes falsos.

- **Commits.** Backend `codex/v1.1.0-tickets-retomada`, base `5c327c7` (tarefa 110): `3f941fc` (rota, regra de chave, contrato, README e testes) e o commit desta seção. Web `codex/v1.1.0-web-retomada`, base `29c1206` (tarefa 110): `a241175` (interface, cliente, snapshot, README e testes).
- **Rota.** `GET /v1/profiles` (`api/v1.py`): cada perfil ganha `available` e `missing_providers` (provedores sem chave, em ordem alfabética); a resposta ganha `router_mechanisms: {"llm": true, "jev": <TYPESAFE_API_KEY>}`. A regra de chave fica em `Settings.has_provider_key` (`config.py`): chave presente e não vazia. `main.py` passa a usar a mesma função para construir os clientes do DeepSeek, do TypeSafe e da Anthropic (o da OpenAI já usava `has_openai`, que agora a chama), então o que a rota informa é o que a fábrica de modelos constrói. `profiles.missing_providers` calcula a lista. Descrição e exemplo no OpenAPI. Nenhum valor de chave sai. A API não ganhou recusa nova: a escolha indisponível enviada mesmo assim continua `503 provider_unavailable`. Sem migração.
- **Contrato e README.** `docs/contracts/api-v1.md`: linha da tabela de rotas e seção "Acréscimos da v1.1.0: disponibilidade de perfis e motores". README do backend: uma frase no parágrafo das chaves opcionais.
- **Web.**
  - `getnet_web/api.py`: `profile_listing()` devolve a resposta inteira; `profiles()` continua devolvendo a lista.
  - `app.py`: `load_profiles` lê `profile_listing` quando o cliente o tem (modo Real); Simulado, Gravado e backend sem os campos ficam com tudo disponível, como antes. Atendimento: perfil indisponível aparece no seletor com "· indisponível neste backend", o padrão é o primeiro perfil disponível e, escolhido o indisponível, aparece "Perfil Híbrido indisponível: falta `DEEPSEEK_API_KEY` no backend." e os botões de envio (mensagem e cenário) ficam desabilitados. Sem JEV, o Router do atendimento fica em LLM e desabilitado, com "JEV indisponível: falta `TYPESAFE_API_KEY` no backend."; o Híbrido deixa de puxar o JEV. Comparação só dos Routers: sem JEV, seleção e **Comparar LLM e JEV** desabilitados com a mesma frase (ela sempre chama os dois Routers); com perfil indisponível, **Comparar** e **Usar esta decisão** desabilitados. Comparação de perfis: perfis indisponíveis marcados e fora do padrão, frase por perfil indisponível escolhido, estimativa e execução desabilitadas; aviso quando há menos de dois perfis disponíveis; Router das execuções em LLM e desabilitado sem JEV.
  - Escolha de JEV feita antes de a chave sumir (backend reiniciado sem ela) volta para LLM antes de o rádio ser desenhado.
  - `openapi-v1.json` reexportado do backend em `3f941fc`, do mesmo jeito que na tarefa 110 (`create_app` com as rotas de demonstração desligadas, JSON com recuo 2): só muda `GET /v1/profiles` (descrição e exemplo). `tools/generate_client.py` não muda o mapa (29 operações).
  - README da web: parágrafo "Profiles and Router engines this backend can run (v1.1.0)" e a linha do snapshot.
- **Decisões além do plano.**
  - O campo `evaluation` do perfil não entra no cálculo de `available`: ele fica no esquema e nenhuma execução o usa, então não deve tornar um perfil indisponível. Reversível em `profiles.missing_providers`.
  - O nome da chave vem de um mapa na interface (`openai`, `deepseek`, `typesafe`); a API devolve só nomes de provedor, como diz o passo 1.
  - O rádio do Router é desabilitado inteiro quando falta o JEV (o Streamlit não desabilita uma opção só); o valor fica em LLM.
  - Além de desabilitar os botões, o envio também confere a disponibilidade no código, para um clique que chegue depois de a disponibilidade mudar.
- **Testes.**
  - Backend, novo `tests/integration/test_v111_profile_availability.py` (12): só OpenAI (DeepSeek e JEV indisponíveis); todas as chaves; cada chave sozinha; chave vazia conta como ausente; demo, admin e rascunho de admin com os campos; escolha indisponível enviada mesmo assim recusada com `503 provider_unavailable` pela fábrica real, sem chave nenhuma (nada chega a um provedor); OpenAPI com descrição e exemplo; `evaluation` fora do cálculo; a fábrica de modelos recusa sem chave ou com chave vazia nos quatro provedores. Nenhum valor de chave aparece em nenhuma resposta.
  - Web, novo `tests/test_v111_availability.py` (11): sem as chaves, perfis do DeepSeek marcados, padrão Referência e LLM, frases com `DEEPSEEK_API_KEY` e `TYPESAFE_API_KEY`, envio desabilitado e nada enviado, Referência com LLM enviada; comparação só dos Routers sem JEV e com perfil indisponível; comparação de perfis; com todas as chaves, tudo como antes (Híbrido com JEV); só o JEV faltando (Híbrido em LLM); escolha de JEV anterior volta a LLM; backend sem os campos; modo Simulado; cliente HTTP; snapshot.
  - Entre repositórios, novo `tests/test_v111_backend_integration.py` (1, ignorado sem o backend no caminho): o cliente da web lê a disponibilidade do backend real com só a chave da OpenAI e com todas, sem valor de chave na resposta.
- **Comandos e números.** Backend: `.venv` do repositório principal com `PYTHONPATH=src` deste worktree. Web: `.venv-v040` do checkout da web com `PYTHONPATH=src` do worktree da web. Sempre `-p no:cacheprovider` e `--basetemp` novo em `<scratchpad da sessão>` (pelo `PYTEST_ADDOPTS` nas suítes estritas).

  | Comando | Resultado |
  | --- | --- |
  | backend `pytest tests/integration/test_v111_profile_availability.py` | **12 passed** |
  | web `pytest tests/test_v111_availability.py tests/test_v070_interface.py` | **61 passed** |
  | entre repositórios, `.venv` do backend com os dois `src`: `pytest tests/test_v111_backend_integration.py tests/test_v110_backend_integration.py tests/test_oauth_backend_integration.py` (web) | **6 passed** |
  | web `python tools/scripts/lint_and_tests.py --strict` | **195 passed, 3 skipped** (os três módulos entre repositórios, sem o backend no caminho) em 4 min 3 s, `ruff` "All checks passed!", exit 0. A primeira rodada acusou 1 falha: a auditoria de chaves de widget (`test_v070_interface.py`) exige a chave do rádio do Router escrita como f-string na chamada; corrigido antes do commit da web |
  | backend `python tools/scripts/lint_and_tests.py --strict` | **3039 passed, 1 skipped**, 0 falhas, em 18 min 41 s; `ruff` "All checks passed!", links e caminhos pessoais sem ocorrência, exit 0. O skip é `test_v0130_otel.py` (o venv não tem o extra `otel`) |
  | `checar-caminhos-pessoais.py` (backend inteiro e os arquivos alterados da web) | nenhuma ocorrência |

- **Roteiro do QA** (momentos 1 e 9 da [história](../historias/tickets-retomada-v110.md)):
  1. Com só `OPENAI_API_KEY`, entrar como lojista. Esperado: seletor em "Referência · v1"; "Híbrido · v1 · indisponível neste backend" e "Ajustado · v1 · indisponível neste backend"; Router em LLM, desabilitado, com "JEV indisponível: falta `TYPESAFE_API_KEY` no backend."
  2. Escolher Híbrido. Esperado: "Perfil Híbrido indisponível: falta `DEEPSEEK_API_KEY` no backend."; **Enviar mensagem** desabilitado; Router em LLM.
  3. Abrir "Comparação só dos Routers": seleção e **Comparar LLM e JEV** desabilitados com a frase do JEV. Em Resultados, "Comparar perfis": só Referência escolhida, "A comparação precisa de dois perfis disponíveis neste backend.", Router das execuções desabilitado.
  4. `GET /v1/profiles` com o token do lojista: `available`, `missing_providers` e `router_mechanisms` coerentes; nenhum valor de chave na resposta nem nos logs.
  5. Momento 9: com `TYPESAFE_API_KEY` no `.env` e a API recriada, recarregar e entrar. Esperado: Router habilitado; uma mensagem pelo JEV com Router `typesafe:jev-1.14.0` em Resultados. Remover a chave ao fim.

## Status

```text
pronta para revisão (rodada 1); navegação pela interface com a pilha real no QA
```
