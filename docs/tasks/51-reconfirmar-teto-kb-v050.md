# Tarefa: exigir nova confirmação ao alterar o teto de custo

## Objetivo

Fazer o consentimento de build/teste corresponder ao teto
numérico efetivamente enviado.

## Especificação relacionada

[Tarefa 49](49-correcao-confirmacoes-qa-v050.md) e plano aprovado;
dentro do escopo de controles já autorizado.

## Pré-condições

- Nenhuma alteração de backend, API, guardas, limite global, credencial ou dados.
- Sem chamadas reais ou serviços pagos.

## Arquivos prováveis

Web `app.py` e teste direcionado em `tests/test_interface.py`.

## Passos

1. Reproduzir o caso com cliente falso: marcar confirmação e
   aumentar o teto deixa o botão habilitado com consentimento antigo.
2. Incluir o teto informado no contexto da confirmação de build e teste.
   Qualquer mudança de teto exige nova confirmação; preservar o valor digitado.
3. Sem reconfirmação, não enviar. Após reconfirmar e clicar, enviar uma única
   ação com o teto novo; reruns/navegação continuam sem envio.
4. Preservar recuperação manual, contexto de versões, parâmetros e backend.
   Validar regressão focal, suíte web e Ruff externo necessários à nova mudança.

## Critérios de conclusão

- [x] Alterar teto de build ou teste invalida a confirmação anterior.
- [x] Botão fica desabilitado até reconfirmar; valor digitado permanece.
- [x] Uma ação explícita envia exatamente o novo teto, sem duplicação.
- [x] Testes sem custo e Ruff passam; recuperação e backend permanecem intactos.

## Resultado

Mudar o teto de build ou de teste invalida a confirmação anterior; o botão só volta a habilitar depois de reconfirmar e envia uma única ação com o teto novo. Suíte web: 20/20 testes; Ruff aprovado; sem chamadas reais. Evidência: [resultado da v0.5.0](../evidence/v050-resultado.md).

## Status

```text
concluída (v0.5.0)
```
