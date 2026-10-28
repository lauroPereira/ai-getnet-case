# Tarefa: execução, compartilhamento e documentação final

## Objetivo

Deixar a demonstração reproduzível e compartilhável, com um guia único e documentação alinhada à entrega real.

## Especificação relacionada

[Spec v0.6.0, bloco F](../specs/fechamento-v060.md), RF-71–74, CA-25, CA-43, CA-46, CA-51, [ADR 0012](../architecture/decisions/0012-exposicao-publica-da-demonstracao.md) e [plano](../specs/fechamento-v060-plano.md) (decisão 9).

## Pré-condições

Tarefas 54 a 57 concluídas. Sem chamada paga, abertura de porta ou alteração de firewall/roteador.

## Arquivos prováveis

`README.md` dos dois projetos, `CHANGELOG.md`, `docs/guia-demonstracao.md` (guia único), `docs/roteiro-teste-manual.md`, `docs/roteiro-video.md`, configuração do Streamlit (HTTPS opcional) e `.env.example`.

## Passos

1. Guia único e curto: pré-requisitos, `.env`, backend por Docker, Streamlit nativo, escolha de cenários, roteiro da demonstração e encerramento.
2. Instruções de compartilhamento por IP público e porta: só o Streamlit exposto, API em `127.0.0.1`, credencial demo, limite por sessão, HTTPS quando possível, ações do responsável (roteador, firewall), teste de outra rede, janela e fechamento; túnel como alternativa.
3. README dos dois projetos atualizado: três áreas, avaliação sob demanda, comparação, base versionada, limites e disponibilidade.
4. CHANGELOG 0.6.0 com funcionalidades, contratos e dados, validação, limitações e retorno à 0.5.0.
5. Roteiro de teste manual pelas jornadas da história v0.6.0.
6. Roteiro de vídeo: raciocínio, arquitetura, evolução por versões e valor de cada uma, caso resolvido, exceção encaminhada, recuperação de conversa, efeito da documentação, comparação e limitações.

## Critérios de conclusão

- [ ] Guia executável do zero, distinguindo Docker, execução nativa e testes.
- [ ] Documentação descreve só o que foi entregue e validado; limitações explícitas.
- [ ] Nenhum dado privado de `discovery/`, credencial ou documento interno.

## Validação

- Guia único [guia-demonstracao.md](https://github.com/lauroPereira/ai-getnet-case/blob/67736304ef948db41b082aea9b1b1b20c3f912b5/docs/guia-demonstracao.md) (Docker, nativo e testes distinguidos; compartilhamento com `--server.address 0.0.0.0`, `LOCK_BACKEND_URL`, HTTPS opcional, ações do responsável, teste de outra rede, janela, túnel como alternativa).
- [Roteiro de teste manual](https://github.com/lauroPereira/ai-getnet-case/blob/67736304ef948db41b082aea9b1b1b20c3f912b5/docs/roteiro-teste-manual.md) pelos momentos da história e [roteiro do vídeo](https://github.com/lauroPereira/ai-getnet-case/blob/67736304ef948db41b082aea9b1b1b20c3f912b5/docs/roteiro-video.md) com a evolução por versões e as evidências de recuperação.
- README dos dois projetos, CHANGELOG 0.6.0 (com retorno à 0.5.0), `.env.example` e contrato (`docs/contracts/api-v040.md`, seção v0.6.0) atualizados; versões 0.6.0 nos dois `pyproject.toml` e no pacote. `Dockerfile` copia `data/scenarios`.
- `test_shared_interface_can_lock_the_backend_address` cobre o travamento do endereço do backend.
- Não executado pelo Developer: `docker compose config`/build (o `.env` local não podia ser lido; build fica com o QA), abertura de porta, firewall, roteador e acesso de outra rede (ações do responsável/QA).

Validação estrita backend (`PYTEST_ADDOPTS="-p no:cacheprovider --basetemp .pytest_cache/v060-dev-strict" .venv/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`): **326 passed**, Ruff "All checks passed!", estrutura e skills válidas, código 0. Web (`.venv-v040/Scripts/python.exe tools/scripts/lint_and_tests.py --strict`): **30 passed**, Ruff sem achados, código 0. Nenhuma chamada paga, chave de provedor ou build Docker. Passagem: [v060-developer.md](../evidence/v060-developer.md).

## Status

```text
concluída; teste de outra rede pendente com o responsável
```

Revisada (Reviewer, rodadas 1–5) e validada no QA real da v0.6.0 (rodada 2, candidato r5); ver [resultado](../evidence/v060-resultado.md).
