# Tarefa: tornar observável a configuração de parâmetros de modelo por agente

## Objetivo

Implementar a capacidade positiva de RF-49/CA-37 para configurar, publicar e inspecionar um parâmetro de modelo suportado e documentado por agente, além de rejeitar parâmetros incompatíveis.

## Especificação relacionada

docs/specs/perfis-interface-v040-plano.md; docs/specs/api-v040-proposta.md; docs/historias/perfis-interface-v040.md; RF-49 e CA-37.

## Pré-condições

Os seis editores por agente tinham `parameters` vazio, sem catálogo ou opções documentadas. A solução adota somente `max_output_tokens`, documentado no adaptador Responses da OpenAI e na API Responses da DeepSeek; limites e fontes estão registrados em `docs/evidence/v040-parametros-modelo-fontes.md`.

## Arquivos prováveis

Contrato/configuração de perfis, adaptadores, interface administrativa, snapshot/inspector e testes de validação e publicação.

## Passos

1. Identificar, com base em adaptadores e documentação oficial aplicável, ao menos um parâmetro compatível real e os limites aceitos por agente/provedor/modelo.
2. Documentar catálogo e compatibilidade, incluindo como valores incompatíveis são rejeitados.
3. Expor a configuração no painel por agente e validar os parâmetros tanto na escrita/publicação quanto na execução.
4. Publicar perfil de teste sintético e confirmar no snapshot/inspector o parâmetro efetivo associado ao agente.
5. Acrescentar regressões para valor compatível, incompatível, publicação/versionamento e snapshot, sem chamadas pagas.
6. Executar testes e jornada administrativa em ambiente sintético; comprovar que provedores não são invocados.

## Critérios de conclusão

- [x] Há ao menos um parâmetro suportado, documentado e selecionável para um agente.
- [x] A compatibilidade é específica por provedor/modelo/agente, com rejeição estrita de chaves/tipos/faixas incompatíveis.
- [x] Um parâmetro compatível é publicado e seu valor efetivo aparece no snapshot da execução.
- [x] Valores incompatíveis são rejeitados sem criar versão ou invocar provedor.
- [x] Testes sintéticos cobrem payload do adaptador fake, reserva segura, publicação, snapshot e rejeições sem chamadas pagas.
- [x] A documentação registra Evaluation reservado para v0.6.0, JEV sem suporte e a lacuna de CA-32 real.

## Resultado

`max_output_tokens` configurável, publicado e visível no snapshot por agente compatível; chave desconhecida, booleano, valor fora dos limites e Evaluation recusados sem criar versão. Suíte estrita do backend: 214 testes; web: 12 testes e geração idempotente de 11 rotas; nenhuma inferência paga. Evidência: [parâmetros](../evidence/v040-parametros-modelo-fontes.md) e [resultado da v0.4.0](../evidence/v040-resultado.md).

## Status

```text
concluída (v0.4.0)
```
