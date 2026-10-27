# Fechamento documental do candidato v0.3.0

## Identidade

`v0.3.0-local-r6-docs1`, branch `codex/v0.3.0-jornadas`, base/HEAD
`8ee14c3a77819a74c3c6de8e75d3bd67f2d6a9c4`.

[Manifesto](v030-candidato-r6-docs1.json): 49 arquivos, fingerprint
`5957a94d44675be57acad3310ece77c574e7edd4aed19d39116bd97068a1fd07`.
O [manifesto r6 original](v030-candidato-r6.json) permanece preservado.

## Delta após QA

Somente estados, checklists e referências de validação nas tarefas 21–26,
para refletir a conclusão efetiva. Nenhum critério foi alterado. Os outros
43 arquivos do manifesto são idênticos; 31 hashes de runtime e 126 insumos
Docker foram novamente conferidos, sem divergência. História, cenários,
contratos, código, dados e imagens são os mesmos do r6 validado.

Runtime: `e58e5668172b992ebabf9777237686a2e0357cdccd5c7657436acbbc703b1cde`.
API: `sha256:f3181423b249dd14368e4b49bb09790c376371097cabc723fbaaba49b41e3699`.
Mocks: `sha256:89364d891ed4a596d6caf72712a00deaec4662359c2dc116fbe9dc6043aea64e`.

## Evidências

[Developer r6](v030-developer-r6.md): 191 testes e validação estrita.
[Reviewer r6](v030-reviewer-r6.md): apto para revalidação/QA.
[QA r6](v030-qa-r6.md): apto funcionalmente, com limitações registradas.
[Replay](v030-real-http-r2-replay.md): 40/40 respostas HTTP preservadas;
[conversas reais r3](v030-real-conversations-r3.md): 4/4 no r6.
O fechamento documental não constitui nova execução ou medição do produto.

[Reviewer do fechamento](v030-reviewer-fechamento.md) e
[QA do fechamento](v030-qa-fechamento.md) confirmaram a validade para o delta
documental, sem novos agentes, testes de produto ou chamadas pagas. A ressalva
do Reviewer sobre o resumo de QA antigo foi corrigida no resultado central e
conferida pelo QA. O manifesto histórico contém hashes das tarefas, sem seu
conteúdo textual anterior; os critérios atuais foram confrontados com as fontes
canônicas. Integração, tag e publicação continuam dependentes de autorização
humana. [Resultado central](v030-resultado.md).
