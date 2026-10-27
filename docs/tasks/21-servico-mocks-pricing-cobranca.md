# Tarefa: Serviço fictício de pricing e cobrança

## Objetivo

Expor fontes HTTP independentes para preço esperado e cobrança registrada, com dados exclusivamente sintéticos.

## Especificação relacionada

RF-32 e RF-46; decisão 0011; [plano](../specs/jornadas-v030-plano.md).

## Pré-condições

Main atualizada, branch de trabalho criada; contratos e migração propostos aprovados antes da implementação correspondente.

## Arquivos prováveis

`src/merchant_assistant/mocks/`, clientes HTTP, `docker-compose.yml`, testes de contrato e integração.

## Passos

1. Definir schemas de simulação e cobrança, regra sintética versionada e fixtures independentes.
2. Implementar as duas rotas e clientes com timeout e erros controlados, sem acesso a APIs externas.
3. Incluir serviço interno no Compose e montagem de produção; testes com transporte em processo.
4. Validar isolamento, resposta inválida, indisponibilidade e fontes independentes.

## Critérios de conclusão

- [x] Simulação identifica regra, versão, aplicabilidade, componentes e parcelas.
- [x] Cobrança vem de registro independente e não é recalculada pelo pricing.
- [x] Clientes validam contratos e falham de forma controlada.
- [x] Serviço executável em contêiner; Compose válido e sem porta publicada.

## Validação

Validação final: **191 testes**, Ruff, estrutura e skills aprovados; Compose
válido. O serviço interno executou sem porta publicada no stack Docker, com
smoke 17/17 e comunicação HTTP real entre API e mocks. Revisão técnica e QA
independentes aptos. Evidências e limites no [resultado](../evidence/v030-resultado.md).

## Status

```text
concluída e validada; integração da entrega depende de autorização humana
```
