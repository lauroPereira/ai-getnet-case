# Tarefa: exigir nova confirmação ao alterar o teto de custo

## Objetivo

Corrigir WUI-R1-01 para que o consentimento de build/teste corresponda ao teto
numérico efetivamente enviado.

## Especificação relacionada

[Tarefa49](49-correcao-confirmacoes-qa-v050.md), plano aprovado e
[Reviewer UI r1](../evidence/v050-reviewer-ui-r1.md). Correção dentro do escopo
de controles já autorizado, mesmos Developer → Reviewer → QA gpt-6-luna/high.

## Pré-condições

- Candidato r5 preservado, sem QA nesta versão; parecer exige correção P2.
- Nenhuma alteração de backend, API, guardas, limite global, credencial ou dados.
- Sem chamadas reais/serviços pagos, commits, pushes ou limpeza.

## Arquivos prováveis

Web `app.py` e teste direcionado em `tests/test_interface.py`.

## Passos

1. Reproduzir o caso do parecer com cliente falso: marcar confirmação e
   aumentar o teto deixa o botão habilitado com consentimento antigo.
2. Incluir o teto informado no contexto da confirmação de build e teste.
   Qualquer mudança de teto exige nova confirmação; preservar o valor digitado.
3. Sem reconfirmação, não enviar. Após reconfirmar e clicar, enviar uma única
   ação com o teto novo; reruns/navegação continuam sem envio.
4. Preservar recuperação manual, contexto de versões, parâmetros e backend.
   Validar regressão focal, suíte web e Ruff externo necessários à nova mudança.
5. Encerrar escrita após validar e entregar passagem UI r3. Novo candidato r6,
   revisão focada e retorno ao mesmo QA, sem novo controle financeiro.

## Critérios de conclusão

- [x] Alterar teto de build ou teste invalida a confirmação anterior.
- [x] Botão fica desabilitado até reconfirmar; valor digitado permanece.
- [x] Uma ação explícita envia exatamente o novo teto, sem duplicação.
- [x] Testes sem custo e Ruff passam; recuperação e backend permanecem intactos.
- [x] Passagem identifica resultado real; não autoaprova revisão/QA.

## Validação

Regressão sintética e validação web completas em [evidência Developer UI r3](../evidence/v050-developer-ui-r3.md). O script estrito executou 20/20 testes, estrutura e skills, mas retornou código 2 devido à ausência do Ruff no venv web; Ruff externo passou. Sem chamadas reais. A revisão independente foca no delta a congelar como r6.

## Status

Concluída — [Reviewer UI r2](../evidence/v050-reviewer-ui-r2.md) apto e teto reconfirmado na UI no [QA r2](../evidence/v050-qa-r2.md); integrada na v0.5.0.
