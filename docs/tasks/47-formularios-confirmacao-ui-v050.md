# Tarefa: habilitar os formulários de confirmação da base v0.5

## Objetivo

Permitir que a confirmação explícita habilite as ações de build e teste da candidata na interface real.

## Especificação relacionada

[Plano da base versionada v0.5](../specs/base-versionada-v050-plano.md), CA-41; [história imutável](../historias/base-versionada-v050.md), cenário da edição e confirmação do build.

## Pré-condições

- Candidato web inicial `v0.5.0-local-r3`, HEAD `40ff199f7441a09b0fa28925bcfd0038e4b6ccbe`.
- API local de QA acessível em modo real, sessão admin sintética e documento `Transações negadas · simulated_internal` editado.
- A candidata `kb_11d9ae5b041443aa` foi criada e testada por API como evidência complementar; não repetir ações pagas sem necessidade.

## Arquivos prováveis

- `app.py`, formulários da Base de conhecimento versionada.
- Testes web existentes ou um teste direcionado ao estado dos controles, se necessário.

## Passos para reproduzir

1. Entrar na interface em modo `Real (API)` com uma sessão administrativa de QA.
2. Abrir Base de conhecimento versionada e editar somente o documento fictício de transações negadas.
3. Salvar a edição, conferir o diff e estimar o custo da candidata.
4. Marcar `Confirmo o build e o custo máximo informado`.
5. Observar o estado de `Construir candidata`.
6. Com uma candidata disponível para teste, marcar `Confirmo o teste da candidata` e observar `Testar candidata`.

## Esperado

Cada checkbox marcado habilita o botão correspondente quando os demais pré-requisitos daquele passo estão atendidos. O clique envia uma única ação, sujeita ao custo estimado e à guarda de orçamento.

## Observado no candidato r3

- No formulário de build, a árvore de acessibilidade mostrou checkbox `Value=1` e botão `Construir candidata` desabilitado. Clique e tentativa de submit pelo teclado não iniciaram a ação.
- Depois que a candidata ficou disponível, no formulário de teste o checkbox também mostrou `Value=1` e `Testar candidata` permaneceu desabilitado.
- O resultado não foi contornado pela UI. Build, teste e ativação foram executados via API real somente como evidência backend complementar; CA-41 pela UI permanece reprovada.
- Capturas da interface foram inspecionadas na sessão CUA desta rodada; nenhuma imagem foi salva em arquivo local.

## Critérios de conclusão

- [x] Marcar a confirmação de build habilita o botão sem exigir mudança não relacionada.
- [x] Marcar a confirmação de teste habilita o botão quando a candidata satisfaz os pré-requisitos.
- [x] Cada clique explícito gera no máximo uma chamada de UI; estimativa, reserva/liquidação e validação do backend permanecem inalteradas.
- [ ] Validação visual no navegador, além da regressão AppTest direcionada, permanece para QA.

## Validação

QA real r1 reproduziu o defeito. Correção Developer e regressão sintética em `docs/evidence/v050-developer-ui-r1.md`; nova revisão independente e confirmação no navegador ainda pendentes.

## Status

```text
pendente
```

Corrigido localmente na branch de trabalho. O novo candidato deve ser fixado pelo Supervisor após revisão.
