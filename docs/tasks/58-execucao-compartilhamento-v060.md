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

- [x] Guia executável do zero, distinguindo Docker, execução nativa e testes.
- [x] Documentação descreve só o que foi entregue e validado; limitações explícitas.
- [x] Nenhum dado privado, credencial ou documento interno.

## Resultado

Guia único de demonstração (Docker, nativo e testes; compartilhamento com o endereço do backend travado e túnel como alternativa), roteiros de teste manual e de vídeo, README dos dois projetos e CHANGELOG 0.6.0 com retorno à 0.5.0; versões 0.6.0. Suíte estrita: backend 326 testes, web 30. Evidência: `docs/guia-demonstracao.md` na tag `v0.6.0` e [resultado da v0.6.0](../evidence/v060-resultado.md).

## Status

```text
concluída (v0.6.0)
```
