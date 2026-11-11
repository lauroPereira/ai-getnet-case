# Tarefa: Preparação independente do projeto web

## Objetivo

Criar a base documental de ai-getnet-case-web por snapshot controlado do template.

## Especificação relacionada

RF-41–43 e decisão 0007; [plano v0.4.0](../specs/perfis-interface-v040-plano.md).

## Pré-condições

Aprovação do destino externo e de AGENTS/CLAUDE/cópias geradas descritos na proposta; destino ausente/vazio reconferido.

## Arquivos prováveis

Somente arquivos novos de base no repositório `ai-getnet-case-web`, conforme proposta.

## Passos

1. Aplicar project-create, conferir destino e links e registrar hashes e versão da fonte, sem alterar o template.
2. Copiar somente componentes reutilizáveis; adaptar instruções exatamente conforme texto aprovado e criar README próprio.
3. Gerar cópias de skills pelo script do destino e validar estrutura, origem, neutralidade e referências.
4. Preparar SDD próprio da interface; manter sem Git ou remoto até a integração inicial autorizada.

## Critérios de conclusão

- [x] Nenhum arquivo preexistente sobrescrito; destino/source preservados.
- [x] Nenhum segredo, .git, material privado, docs/raw ou conteúdo real de outro projeto copiado.
- [x] Manifesto/origem com versão/hashes e adaptações; skills sincronizadas verificadas.
- [x] Base distinta de produto; backend acessível exclusivamente por API.

## Resultado

Base criada a partir do template 0.2.0: 47 arquivos-fonte identificados, 54 arquivos iniciais e 18 cópias geradas (9 skills). `validate-project.ps1`, `validate-agent-flow.ps1` e a validação estrutural em Python aprovados; fonte reconferida sem mudança e destino sem Git nem `.env`.

## Status

```text
concluída (v0.4.0)
```
