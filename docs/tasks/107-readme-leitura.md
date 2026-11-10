# Tarefa 107 — README de leitura rápida e evidência

## Objetivo

Quem abre o repositório entende em minutos o que o assistente faz, como rodar e onde está a evidência de cada número.

## Especificação relacionada

[v1.0.0](../specs/leitura-acesso-v100.md): D5, CA-74. Plano: decisão 22. RF-129.

## Pré-condições

Tarefas 106 e 108 concluídas na branch `codex/v1.0.0-final`. Resultados das versões v0.12.0 e v0.13.0 em `docs/evidence/` (o Supervisor grava `v0120-resultado.md` e `v0130-resultado.md` antes desta tarefa). Nenhuma chamada paga.

## Arquivos prováveis

`README.md`, `CHANGELOG.md`, `docs/evidence/README.md` (índice), capturas em `docs/apresentacao/` (ou pasta já usada pelo README), README da interface web se a trilha depender dele.

## Passos

1. Topo do README: o que é, para quem, em três frases; status v1.0.0; como rodar em dois caminhos (imagem publicada e build local).
2. Trilha de 10 minutos: subir, perguntar como lojista, encaminhar a humano, responder como operador (aba Operador e ticketing), avaliar uma resposta; cada passo com comando ou clique e o resultado esperado.
3. Tabela antes × depois por área (atendimento, avaliação/juiz, retrieval, memória, identidade, operação): número da v0.10.0, número atual, link da evidência em `docs/evidence/`; só números já registrados em evidência versionada.
4. Capturas com dados sintéticos: aba Operador, ticketing e login por redirecionamento; Telegram só se o responsável fornecer uma captura sem nome nem identificador do grupo.
5. `docs/evidence/README.md` como índice com links válidos; CHANGELOG 1.0.0; notas de operação atualizadas (dois workers, túnel, imagem).
6. Nada de processo interno no texto (avaliação externa, notas, comparações); caminhos pessoais e dados reais proibidos.

## Critérios de conclusão

- Links relativos válidos (`checar-links.py`), caminhos pessoais limpos, suíte estrita verde.
- A trilha é executável como escrita (o QA a segue).

## Validação

Developer, rodada 1 (2026-11-10). Branch `codex/v1.0.0-final`, base `b6834f8`, commit `cf75549` (README, CHANGELOG, índice de `docs/evidence/`). Sem chamada paga, sem Docker, sem navegador, sem download; nenhum código de produção, workflow ou a seção do túnel (tarefa 108) alterados.

- **Topo do README.** O que é e para quem em três frases; status `v1.0.0 (not released)` com o que a versão traz e a base v0.13.0; dois caminhos para rodar (`docker compose up -d --wait`, imagem publicada com build local quando não há imagem; `docker compose up -d --wait --build`, build do checkout) seguidos do token e do `POST /messages`. A frase do desafio passou a abrir a tabela "Where each part of the challenge lives".
- **Trilha de 10 minutos.** Reescrita para a interface com login por redirecionamento (a interface não tem campo de senha; a página é a do emissor): 1) subir a pilha e a interface (`AUTH_ISSUER=http://api:8000`, o `JWT_ISSUER` do compose, e `http://localhost:8501/`, o redirect registrado); 2) entrar como `cliente1988` por **Entrar**; 3) perguntar em **Atendimento**; 4) pedir atendente (protocolo `HO-…`); 5) `op_ana` numa janela privada: aba **Ticketing**, **Assumir** na fila Recepção, **Responder** na fila Atendimento; 6) o lojista lê a resposta marcada `Atendente humano · rota human_reply`; 7) **Resultados**: estimar e avaliar a resposta do passo 3. Cada passo tem clique ou comando e resultado esperado, com os rótulos lidos do `app.py` da interface (`main` em `4c2c86d`). Alternativas: `curl` e comandos de operador (seção da v0.7.0) e a avaliação programada sem chave. A interface não tem aba "Operador": o papel `operator` vê só a aba **Ticketing**.
- **Tabela antes × depois** ("What changed since v0.10.0"), só com números escritos nas evidências versionadas:

  | Área | v0.10.0 (origem) | Atual (origem) |
  | --- | --- | --- |
  | Atendimento | campanha v0.8.0, a última completa: 44 casos × 3, 4.56 / 4.62 / 4.77 / 4.53 (`v080-all-r3.md`); jornadas 13/13, 12/13, 12/13 (`v080-d12-pre-holdout-r6.md`) | sem campanha completa nova; 4 casos pareados, 0 decisões `model` com `REPLAN=off` e 8 com `on` (`v0120-resultado.md`) |
  | Juiz | `judge.v3`: veredito 0.667, κ −0.200, 24 respostas, 0 de 4 genéricas (`v0100-juiz-v4.md`) | `judge.v5`: κ 0.647 (IC 0.28–0.92) em 36 seladas, `judge.v3` 0.538 nas mesmas; ±1 0.972/0.972/1.000/1.000; US$0.000945 vs US$0.000398 (`v0110-resultado.md`) |
  | Retrieval | `hybrid` no holdout: Recall@6 1.000, MRR 0.920, nDCG@6 0.921, 534 ms (`v090-retrieval.md`) | `hybrid+rerank`: 1.000 / 1.000 / 0.972, controle `hybrid@36` 0.907, 1.752 ms (`v0110-retrieval.md`) |
  | Memória | conversas 4/4, 2 a 3 turnos (`v080-conversations-r4.md`) | conversa de 27 turnos com fatos exatos, aviso e recuperação (`v0120-resultado.md`) |
  | Identidade | emissor próprio; 4 chamadas de ferramenta, 4 linhas de auditoria (`v070-resultado.md`) | 10 logins num navegador real, 10 sessões, nenhum órfão, código trocado no outro worker (`v0130-resultado.md`) |
  | Operação | comparação morta após 1 de 6 células, 5 retomadas, cada célula paga uma vez; 4 regras de alerta (`v0100-qa-ops-r1.md`) | dois workers, nenhuma célula paga duas vezes com o dono suspenso antes e depois da reserva (`v0130-resultado.md`) |
  | Testes | 2.148 aprovados (`v0100-candidato-r1.json`) | 2.698 (v0.12.0) e 2.944 (v0.13.0), sem pulados (`v0120-resultado.md`, `v0130-resultado.md`) |

  Uma nota abaixo da tabela diz que as duas linhas do juiz usam amostras diferentes (24 de um rotulador; 36 seladas de dois). A v1.0.0 ainda não tem resultado em `docs/evidence/`; a linha de operação só cita o que ela acrescenta, sem número.
- **Índice de `docs/evidence/`.** Seções v0.12.0 e v0.13.0; JSON do retrieval da v0.11.0; frase sobre o `.json` de mesmo nome de cada relatório e link para a tabela do README.
- **CHANGELOG 1.0.0.** Imagem (a tag precisa casar com a versão; `latest` só em versão final), `uv.lock` e CI sobre o lockfile, suíte dentro da imagem, túnel (perfil `tunnel`, Caddy, `AUTH_AUTHORIZE_URL` na interface), `--no-proxy-headers`, recusa na subida com credencial de exemplo e redirect público, README de leitura; "Contract and data" com perfil e `STREAMLIT_UPSTREAM`; "Notes" com dois workers, imagem e túnel.
- **README, correções pontuais.** Notas de operação com a imagem e o túnel; tabela "Beyond the challenge" com a v1.0.0; roadmap com v0.12.0 e v0.13.0 construídas (links dos resultados) e v1.0.0 em andamento; ponteiro para os resultados da v0.11.0 a v0.13.0; seção da interface com `AUTH_ISSUER` do compose (sem ele o `iss` do token `http://api:8000` não casa com o padrão da interface, `http://127.0.0.1:8000`) e o endereço `http://localhost:8501/`. A linha `pip install -e ".[test]"` foi mantida: ela roda no projeto web, cujo `pyproject.toml` tem o extra `test` (o do backend tem `ingest`, `otel` e `dev`); ganhou um comentário dizendo isso.
- **Comandos e números** (`.venv` do repositório principal, `PYTHONPATH` = `src` deste worktree + extra `otel` local, sem chaves, `--basetemp` novo no scratchpad da sessão, `-p no:cacheprovider`): `checar-links.py`: nenhum alvo ausente em 367 arquivos Markdown; `checar-caminhos-pessoais.py`: nenhuma ocorrência em 725 arquivos; âncoras `#…` do README, do índice e do CHANGELOG conferidas contra os títulos do README por script (nenhuma ausente); `ruff check --no-cache .`: `All checks passed!`; `lint_and_tests.py` (modo padrão): exit 0; testes que leem o README (`test_v100_tunnel.py`, `test_v100_image.py`, `test_v0100_metrics.py`, `test_evaluator_settings.py`): **47 passed**. Suíte estrita completa não rodada (só documentação mudou; fica com a revisão).


Developer, rodada 2 (2026-11-10), correções da revisão. Base `d3687d0`; só `README.md`, `docs/evidence/README.md` e esta tarefa (as alterações não commitadas de outro escritor em `api/identity.py` e nos testes de identidade e túnel ficaram de fora).

- **P2, juiz.** A célula e a nota dizem a referência de cada lado: v0.10.0 contra um rotulador humano (o responsável, 24 respostas); atual contra rótulos ouro adjudicados em 36 respostas seladas, avaliadas pelo responsável e por um painel de modelos, com as divergências resolvidas por propostas de modelo aceitas pelo responsável (`v0110-resultado.md`). A comparação justa fica explícita: `judge.v3` 0,538 × `judge.v5` 0,647 nas mesmas respostas e rótulos.
- **P3-1.** "in the v0.7.0 QA" saiu da linha de identidade. Processo interno reescrito em tom de produto, sem perder o fato: "v0.8.0 QA" → "v0.8.0 validation" (pedido real e runtime do replanejamento), "pre-holdout QA" → "pre-holdout validation", "on each release candidate" removido da estratégia de testes, "the same QA" → "the same validation", "independent review and QA" → "specified, tested and validated with real models", "story QA" → "This sequence was validated in v0.7.0 … story validation", "ops QA" → "operation test", roadmap "specification, review and QA" → "specification and validation", parágrafo final sem "agent roles" e `docs/wiki/agents/` (fica: specs, tarefas e ADRs em `docs/`, scripts em `tools/scripts/`), "isolated for a QA run" → "an evaluation run", "fixed QA cap" → "fixed campaign cap", link "v0.10.0 candidate" → "v0.10.0 build". Ficam só identificadores literais (nomes de arquivo como `v070-qa.md` e a campanha `v080-qa` dos comandos).
- **P3-2, latência.** A linha de retrieval compara dentro da mesma execução da v0.11.0: 1.752 ms do `hybrid+rerank` contra 501 ms do `hybrid`; os 534 ms da v0.9.0 saíram.
- **P3-3, capturas.** Login: barra de endereço do popup recortada (traz `state` e `code_challenge`). Telegram: também sem nome do operador nem do bot.
- **P3-4.** A dica de PowerShell do passo 1 aponta para a seção "Streamlit interface", que tem `BACKEND_API_URL` e `AUTH_ISSUER`.
- **P3-5.** Índice de `docs/evidence/`: `v080-healthy-traces-r6.json` (junto do `v080-healthy-r6.md`) e `v080-holdout-traces-r7.json` (junto do `v080-holdout-r7.md`).
- **Comandos e números (rodada 2)** (mesmo ambiente; `PYTHONPATH` em `C:/…`, `merchant_assistant.__file__` conferido no `src` deste worktree): `checar-links.py`: nenhum alvo ausente em 367 arquivos Markdown; `checar-caminhos-pessoais.py`: nenhuma ocorrência em 725 arquivos; 24 âncoras `#…` do README, do índice e do CHANGELOG conferidas (nenhuma ausente); `ruff check --no-cache .`: `All checks passed!`; `lint_and_tests.py` (modo padrão): exit 0; `test_v100_tunnel.py`, `test_v100_image.py`, `test_v0100_metrics.py`, `test_evaluator_settings.py`: **51 passed** (47 na rodada 1; a diferença são testes novos, ainda não commitados, de outro escritor em `test_v100_tunnel.py`, rodados como estavam na árvore).

**Capturas para o QA** (não produzidas: sem navegador). Pasta `docs/images/`, PNG, largura entre 1280 e 1600 px, pilha local com `.env.example` e dados sintéticos; sem endereço do túnel, token, código ou `state` visível, sem caminho pessoal; a barra de endereço só com `localhost` ou recortada. O Supervisor acrescenta as referências ao README quando os arquivos existirem.

| Arquivo | Tela | Estado | Dados |
| --- | --- | --- | --- |
| `v100-login-redirecionamento.png` | Popup da página de login da API (`/v1/auth/authorize`) aberta por **Entrar**, com a interface atrás | Antes de enviar: usuário preenchido, senha mascarada; **barra de endereço do popup recortada** (a URL traz `state` e `code_challenge`) | `cliente1988` |
| `v100-atendimento.png` | Aba **Atendimento**, lojista | Pergunta dos recebíveis respondida e pedido de atendente com `protocolo HO-…` na legenda; barra lateral `Sessão ativa · papel merchant` | `cliente1988`, perfil Referência |
| `v100-resultados-citacoes.png` | Aba **Resultados** | Execução de uma pergunta de conhecimento (ex.: “Qual a diferença entre a Get Smart e a maquininha Clássica?”) com fontes oficiais citadas e passagens recuperadas | `cliente1988` |
| `v100-ticketing.png` | Aba **Ticketing**, operador | Fila Atendimento com o ticket `HO-…` aberto: resumo mascarado, conversa, ação **Responder** preenchida antes de enviar | `op_ana`, resposta sintética |
| `v100-resposta-operador.png` | Aba **Atendimento**, lojista | Turno marcado `Atendente humano · rota human_reply` depois de “Alguma novidade?” | `cliente1988` |
| `v100-avaliacao.png` | Aba **Resultados** | **Avaliação por IA (sob demanda)** `completed`, com avaliador, custo separado e notas | `cliente1988` |
| `v100-telegram.png` (opcional) | Chat do operador no Telegram | Caso com protocolo, resumo mascarado e os botões Claim e Approve | Só se o responsável fornecer, sem nome nem identificador do grupo, sem nome do operador nem do bot |

## Status

```text
pronta para revisão (Developer, rodada 2); capturas com o QA, referências no README pelo Supervisor
```
