# Tarefa: build/teste de candidata e guarda de embeddings

## Objetivo

Construir/testar coleção própria com estimativa e reserva antes da rede.

## Especificação relacionada

[Plano](../specs/base-versionada-v050-plano.md), RF-64/75 e CA-41/45.

## Pré-condições

Plano aprovado e snapshots/revisões disponíveis; preços conhecidos.

## Arquivos prováveis

`rag/index.py`, `rag/embed.py`, serviço KB, montagem de runtime, API e testes.

## Passos

1. Calcular manifesto/digest e estimativa conservadora sem inferência.
2. Validar confirmação/digest/teto e criar coleção nunca usada, sem rebuild da ativa.
3. Reservar cada lote/consulta antes do provedor; liquidar sem callback duplicado.
4. Testar integridade/recuperação, estados e falhas, bloqueando ativação incompleta.

## Critérios de conclusão

- [ ] Negação/custo desconhecido gera zero chamadas; gasto anterior preservado.
- [ ] Falha não altera ativa; candidata incompleta não é pronta.
- [ ] Manifesto/modelo/dimensão conferidos; fontes tratadas como evidência.

## Validação e status

Implementada pelo Developer r1. Build cria coleção inédita, estado incompleto não ativa, estimativa é local e guarda reserva cada lote antes do provedor. Testes verificam negação antes da rede, liquidação única, persistência do sublimite de campanha e colisão sem substituir coleção. Apenas transportes/fakes sintéticos; QA real permanece na tarefa44.
