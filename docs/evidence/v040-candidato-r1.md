# Candidato v0.4.0 local — r1

## Identificação

Backend `codex/v0.4.0-perfis-interface`, base/HEAD v0.3.0
`bd549cc921ccffb37bd304a0959b8a4b690d6421`; frontend independente sem Git.
[Manifesto completo](v040-candidato-r1.json): 39 arquivos alterados backend,
83 arquivos frontend, incluindo a base documental.

Fingerprint combinado `91184b73d1c91f5b1790b831038e9853a54b20a1791407447ecd4a7380eeeaec`;
runtime completo backend `c5adab307e7e2e1a6f0519d64dc6b70ce25471520c4de44b8d843ee07e7da41c`.
Hashes de bytes locais, conforme algoritmo no JSON; evidências e ambientes
temporários não integram o fingerprint de produto. Git pode normalizar finais
de linha; a base e os hashes identificam o conteúdo local sem commit novo.

## Critérios e validação

Plano/contratos aprovados, tarefas 27–32 e história versão 1 incluídos no
manifesto. [Passagem Developer](v040-developer-r1.md): 202 testes backend,
sete frontend, Ruff, dependências independentes e execução HTTP/AppTest.
O Supervisor reconferiu os 48 hashes do manifesto dessa passagem antes de
atualizar registros de coordenação. Ele é histórico; a identidade vigente
da revisão é o manifesto completo acima, que exclui evidências mutáveis.

Reviewer `/root/reviewer_v040` acionado explicitamente `gpt-6-luna/high`,
`fork_turns=none`, com fontes/critério/candidato e sem histórico do Developer.
Parecer independente pendente; QA será acionado somente após revisão apta.

## Ambiente e limites

[Ambiente preparado](v040-qa-environment-r1.json): API HTTP e Streamlit em
loopback, com modelos programados, HashEmbedder e mock HTTP em processo.
Isso testa transporte e fluxos, sem inferência real. Nenhuma credencial de
provedor configurada; não representa a validação JEV real de CA-32.
O manifesto registra insumos de build, sem declarar novo build Docker.

Catálogo tem fontes oficiais documentadas; nova consulta autenticada
`GET /models` não foi feita sem prova de gratuidade. A lacuna deve ser avaliada
separadamente dos testes de capacidades implementadas. Nenhuma chamada paga,
commit, push, remoto web, tag ou publicação está autorizada nesta versão.

Mudança de produto, contrato, critério, dados ou ambiente relevante exige novo
candidato e revisão do escopo afetado. Correções retornam ao mesmo Developer.
