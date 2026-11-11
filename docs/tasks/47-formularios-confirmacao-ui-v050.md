# Tarefa: habilitar os formulários de confirmação da base v0.5

## Objetivo

Permitir que a confirmação explícita habilite as ações de build e teste da candidata na interface real.

## Especificação relacionada

[Plano da base versionada v0.5](../specs/base-versionada-v050-plano.md), CA-41; [história imutável](../historias/base-versionada-v050.md), cenário da edição e confirmação do build.

## Pré-condições

- API local em modo real, sessão admin sintética e documento `Transações negadas · simulated_internal` editado.
- A candidata `kb_11d9ae5b041443aa` foi criada e testada por API como evidência complementar; não repetir ações pagas sem necessidade.

## Arquivos prováveis

- `app.py`, formulários da Base de conhecimento versionada.
- Testes web existentes ou um teste direcionado ao estado dos controles, se necessário.

## Passos para reproduzir

1. Entrar na interface em modo `Real (API)` com uma sessão administrativa.
2. Abrir Base de conhecimento versionada e editar somente o documento fictício de transações negadas.
3. Salvar a edição, conferir o diff e estimar o custo da candidata.
4. Marcar `Confirmo o build e o custo máximo informado`.
5. Observar o estado de `Construir candidata`.
6. Com uma candidata disponível para teste, marcar `Confirmo o teste da candidata` e observar `Testar candidata`.

## Esperado

Cada checkbox marcado habilita o botão correspondente quando os demais pré-requisitos daquele passo estão atendidos. O clique envia uma única ação, sujeita ao custo estimado e à guarda de orçamento.

## Critérios de conclusão

- [x] Marcar a confirmação de build habilita o botão sem exigir mudança não relacionada.
- [x] Marcar a confirmação de teste habilita o botão quando a candidata satisfaz os pré-requisitos.
- [x] Cada clique explícito gera no máximo uma chamada de UI; estimativa, reserva/liquidação e validação do backend permanecem inalteradas.
- [x] Validação visual no navegador, além da regressão AppTest direcionada.

## Resultado

As confirmações de build e teste habilitam a ação correspondente; a correção, com regressão sintética, está na [tarefa 49](49-correcao-confirmacoes-qa-v050.md) e foi conferida no navegador. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
